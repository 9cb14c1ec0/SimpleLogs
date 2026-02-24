from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Database
    database_url: str = "postgres://postgres:postgres@localhost:5432/simplelogs"

    # JWT
    secret_key: str = "change-me-in-production-use-a-long-random-string"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # Admin user (created on first run)
    admin_email: str = "admin@example.com"
    admin_password: str = "changeme"
    admin_name: str = "Admin"

    # TOTP
    totp_encryption_key: str = ""

    # WebAuthn
    webauthn_rp_id: str = "localhost"
    webauthn_rp_name: str = "SimpleLogs"
    webauthn_origin: str = "http://localhost:5173"

    # CORS
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    return Settings()
