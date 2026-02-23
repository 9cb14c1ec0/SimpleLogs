from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    sub: str  # user id
    type: str  # "access", "refresh", or "totp_required"
    jti: str | None = None  # unique token id (used for totp_required tokens)


class LoginResponse(BaseModel):
    totp_required: bool = False
    # Present when totp_required is False (normal login)
    access_token: str | None = None
    refresh_token: str | None = None
    token_type: str = "bearer"
    # Present when totp_required is True
    totp_token: str | None = None


class TOTPVerifyLoginRequest(BaseModel):
    totp_token: str
    code: str


class TOTPSetupResponse(BaseModel):
    secret: str
    qr_code: str
    recovery_codes: list[str]


class TOTPVerifySetupRequest(BaseModel):
    code: str


class TOTPDisableRequest(BaseModel):
    password: str
