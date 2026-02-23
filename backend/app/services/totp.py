import base64
import io
import secrets
import string

import bcrypt
import pyotp
import qrcode
from cryptography.fernet import Fernet

from app.config import get_settings
from app.models.user import User
from app.models.recovery_code import RecoveryCode


class TOTPService:
    @staticmethod
    def _get_fernet() -> Fernet:
        settings = get_settings()
        key = settings.totp_encryption_key
        if not key:
            raise ValueError(
                "TOTP_ENCRYPTION_KEY is not set. "
                "Generate one with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
            )
        try:
            return Fernet(key.encode())
        except Exception as exc:
            raise ValueError(
                f"TOTP_ENCRYPTION_KEY is not a valid Fernet key: {exc}. "
                "Generate one with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
            ) from exc

    @classmethod
    def encrypt_secret(cls, secret: str) -> str:
        return cls._get_fernet().encrypt(secret.encode()).decode()

    @classmethod
    def decrypt_secret(cls, encrypted: str) -> str:
        return cls._get_fernet().decrypt(encrypted.encode()).decode()

    @staticmethod
    def generate_secret() -> str:
        return pyotp.random_base32()

    @staticmethod
    def verify_code(secret: str, code: str) -> bool:
        totp = pyotp.TOTP(secret)
        return totp.verify(code, valid_window=1)

    @staticmethod
    def get_provisioning_uri(secret: str, email: str) -> str:
        totp = pyotp.TOTP(secret)
        return totp.provisioning_uri(name=email, issuer_name="SimpleLogs")

    @staticmethod
    def generate_qr_base64(uri: str) -> str:
        img = qrcode.make(uri)
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        b64 = base64.b64encode(buffer.getvalue()).decode()
        return f"data:image/png;base64,{b64}"

    @staticmethod
    def generate_recovery_codes(count: int = 8) -> list[str]:
        alphabet = string.ascii_lowercase + string.digits
        return ["".join(secrets.choice(alphabet) for _ in range(8)) for _ in range(count)]

    @staticmethod
    def hash_recovery_code(code: str) -> str:
        return bcrypt.hashpw(code.encode(), bcrypt.gensalt()).decode()

    @classmethod
    async def setup_begin(cls, user: User) -> dict:
        """Begin TOTP setup: generate secret, QR code, and recovery codes."""
        secret = cls.generate_secret()
        encrypted = cls.encrypt_secret(secret)

        # Store encrypted secret but don't enable yet
        user.totp_secret_encrypted = encrypted
        await user.save()

        uri = cls.get_provisioning_uri(secret, user.email)
        qr_code = cls.generate_qr_base64(uri)

        # Generate and store recovery codes
        plain_codes = cls.generate_recovery_codes()

        # Delete any existing recovery codes for this user
        await RecoveryCode.filter(user=user).delete()

        for code in plain_codes:
            await RecoveryCode.create(
                user=user,
                code_hash=cls.hash_recovery_code(code),
            )

        return {
            "secret": secret,
            "qr_code": qr_code,
            "recovery_codes": plain_codes,
        }

    @classmethod
    async def setup_verify(cls, user: User, code: str) -> bool:
        """Verify the first TOTP code and enable 2FA."""
        if not user.totp_secret_encrypted:
            return False

        secret = cls.decrypt_secret(user.totp_secret_encrypted)
        if not cls.verify_code(secret, code):
            return False

        user.totp_enabled = True
        await user.save()
        return True

    @classmethod
    async def verify_login_code(cls, user: User, code: str) -> bool:
        """Verify a TOTP or recovery code during login."""
        if not user.totp_secret_encrypted:
            return False

        secret = cls.decrypt_secret(user.totp_secret_encrypted)

        # Try TOTP code first
        if cls.verify_code(secret, code):
            return True

        # Fallback to recovery codes
        normalized = code.strip().lower()
        recovery_codes = await RecoveryCode.filter(user=user, used=False).all()
        for rc in recovery_codes:
            if rc.verify_code(normalized):
                rc.used = True
                await rc.save()
                return True

        return False

    @classmethod
    async def disable(cls, user: User) -> None:
        """Disable TOTP and clean up."""
        user.totp_secret_encrypted = None
        user.totp_enabled = False
        await user.save()
        await RecoveryCode.filter(user=user).delete()
