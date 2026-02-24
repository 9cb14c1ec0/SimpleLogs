import json
import time
import uuid
from datetime import datetime, timezone

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
    PublicKeyCredentialCreationOptions,
    AuthenticatorSelectionCriteria,
    ResidentKeyRequirement,
)
from webauthn.helpers import bytes_to_base64url

from app.config import get_settings
from app.models.user import User
from app.models.passkey_credential import PasskeyCredential


_CHALLENGE_TTL = 120  # seconds

# In-memory challenge store: key -> (challenge_bytes, expiry_timestamp)
_challenges: dict[str, tuple[bytes, float]] = {}


def _cleanup_expired() -> None:
    now = time.monotonic()
    expired = [k for k, (_, exp) in _challenges.items() if exp < now]
    for k in expired:
        del _challenges[k]


def _store_challenge(key: str, challenge: bytes) -> None:
    _cleanup_expired()
    _challenges[key] = (challenge, time.monotonic() + _CHALLENGE_TTL)


def _pop_challenge(key: str) -> bytes | None:
    _cleanup_expired()
    entry = _challenges.pop(key, None)
    if entry is None:
        return None
    challenge, expiry = entry
    if expiry < time.monotonic():
        return None
    return challenge


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

        _store_challenge(f"reg:{user.id}", options.challenge)

        return options_to_json(options)

    @staticmethod
    async def verify_registration(user: User, credential_json: str, name: str) -> PasskeyCredential:
        settings = get_settings()

        challenge = _pop_challenge(f"reg:{user.id}")
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

        _store_challenge(f"auth:{challenge_id}", options.challenge)

        return options_to_json(options), challenge_id

    @staticmethod
    async def verify_authentication(credential_json: str, challenge_id: str) -> User:
        settings = get_settings()

        challenge = _pop_challenge(f"auth:{challenge_id}")
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
