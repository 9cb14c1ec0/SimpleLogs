import json
import uuid
from datetime import datetime, timedelta, timezone

from webauthn import (
    generate_registration_options,
    verify_registration_response,
    generate_authentication_options,
    verify_authentication_response,
    options_to_json,
)
from webauthn.helpers.structs import (
    PublicKeyCredentialDescriptor,
    AuthenticatorTransport,
    UserVerificationRequirement,
    AuthenticatorSelectionCriteria,
    ResidentKeyRequirement,
)

from app.config import get_settings
from app.models.user import User
from app.models.passkey_credential import PasskeyCredential
from app.models.webauthn_challenge import WebAuthnChallenge


_CHALLENGE_TTL = 120  # seconds


async def _store_challenge(key: str, challenge: bytes) -> None:
    """Store a challenge in the database, replacing any existing one for this key."""
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=_CHALLENGE_TTL)
    existing = await WebAuthnChallenge.filter(challenge_key=key).first()
    if existing:
        existing.challenge = challenge
        existing.expires_at = expires_at
        await existing.save()
    else:
        await WebAuthnChallenge.create(
            challenge_key=key,
            challenge=challenge,
            expires_at=expires_at,
        )


async def _pop_challenge(key: str) -> bytes | None:
    """Retrieve and delete a challenge. Returns None if expired or missing."""
    row = await WebAuthnChallenge.filter(challenge_key=key).first()
    if row is None:
        return None
    await row.delete()
    if row.expires_at < datetime.now(timezone.utc):
        return None
    return bytes(row.challenge)


async def _cleanup_expired() -> None:
    """Delete expired challenges."""
    await WebAuthnChallenge.filter(expires_at__lt=datetime.now(timezone.utc)).delete()


class WebAuthnService:
    @staticmethod
    async def generate_registration_options_for_user(user: User) -> str:
        settings = get_settings()

        existing = await PasskeyCredential.filter(user=user).all()
        exclude_credentials = [
            PublicKeyCredentialDescriptor(
                id=bytes(cred.credential_id),
                transports=[AuthenticatorTransport(t) for t in json.loads(cred.transports)]
                if cred.transports else [],
            )
            for cred in existing
        ]

        options = generate_registration_options(
            rp_id=settings.webauthn_rp_id,
            rp_name=settings.webauthn_rp_name,
            user_id=str(user.id).encode(),
            user_name=user.email,
            user_display_name=user.name,
            exclude_credentials=exclude_credentials,
            authenticator_selection=AuthenticatorSelectionCriteria(
                resident_key=ResidentKeyRequirement.PREFERRED,
                user_verification=UserVerificationRequirement.PREFERRED,
            ),
        )

        await _store_challenge(f"reg:{user.id}", options.challenge)

        return options_to_json(options)

    @staticmethod
    async def verify_registration(user: User, credential_json: str, name: str) -> PasskeyCredential:
        settings = get_settings()

        challenge = await _pop_challenge(f"reg:{user.id}")
        if challenge is None:
            raise ValueError("Registration challenge expired or not found")

        verification = verify_registration_response(
            credential=credential_json,
            expected_challenge=challenge,
            expected_rp_id=settings.webauthn_rp_id,
            expected_origin=settings.webauthn_origin,
        )

        transports_json = None
        if verification.credential_device_type:
            # Store transports from the credential response if available
            try:
                parsed = json.loads(credential_json)
                raw_transports = parsed.get("response", {}).get("transports")
                if raw_transports:
                    transports_json = json.dumps(raw_transports)
            except (json.JSONDecodeError, AttributeError):
                pass

        credential = await PasskeyCredential.create(
            user=user,
            credential_id=verification.credential_id,
            public_key=verification.credential_public_key,
            sign_count=verification.sign_count,
            transports=transports_json,
            name=name,
        )

        return credential

    @staticmethod
    async def generate_authentication_options_for_login() -> tuple[str, str]:
        settings = get_settings()
        challenge_id = str(uuid.uuid4())

        options = generate_authentication_options(
            rp_id=settings.webauthn_rp_id,
            user_verification=UserVerificationRequirement.PREFERRED,
        )

        await _store_challenge(f"auth:{challenge_id}", options.challenge)

        return options_to_json(options), challenge_id

    @staticmethod
    async def verify_authentication(credential_json: str, challenge_id: str) -> User:
        settings = get_settings()

        challenge = await _pop_challenge(f"auth:{challenge_id}")
        if challenge is None:
            raise ValueError("Authentication challenge expired or not found")

        parsed = json.loads(credential_json)
        raw_id = parsed.get("rawId", parsed.get("id", ""))

        # Find the credential in the database
        from webauthn.helpers import base64url_to_bytes
        credential_id_bytes = base64url_to_bytes(raw_id)

        passkey = await PasskeyCredential.filter(credential_id=credential_id_bytes).prefetch_related("user").first()
        if passkey is None:
            raise ValueError("Credential not found")

        user = passkey.user
        if not user.is_active:
            raise ValueError("User account is inactive")

        verification = verify_authentication_response(
            credential=credential_json,
            expected_challenge=challenge,
            expected_rp_id=settings.webauthn_rp_id,
            expected_origin=settings.webauthn_origin,
            credential_public_key=bytes(passkey.public_key),
            credential_current_sign_count=passkey.sign_count,
        )

        passkey.sign_count = verification.new_sign_count
        passkey.last_used_at = datetime.now(timezone.utc)
        await passkey.save()

        return user
