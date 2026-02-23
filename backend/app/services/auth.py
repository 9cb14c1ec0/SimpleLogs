from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
from app.config import get_settings
from app.schemas.auth import TokenPayload

settings = get_settings()


class AuthService:
    @staticmethod
    def create_access_token(user_id: str) -> str:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
        payload = {
            "sub": user_id,
            "type": "access",
            "exp": expire,
        }
        return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)

    @staticmethod
    def create_refresh_token(user_id: str) -> str:
        expire = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)
        payload = {
            "sub": user_id,
            "type": "refresh",
            "exp": expire,
        }
        return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)

    @staticmethod
    def create_totp_token(user_id: str) -> str:
        expire = datetime.now(timezone.utc) + timedelta(minutes=5)
        payload = {
            "sub": user_id,
            "type": "totp_required",
            "exp": expire,
        }
        return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)

    @staticmethod
    def decode_token(token: str) -> TokenPayload | None:
        try:
            payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
            return TokenPayload(sub=payload["sub"], type=payload["type"])
        except JWTError:
            return None

    @classmethod
    def create_tokens(cls, user_id: str) -> tuple[str, str]:
        access_token = cls.create_access_token(user_id)
        refresh_token = cls.create_refresh_token(user_id)
        return access_token, refresh_token
