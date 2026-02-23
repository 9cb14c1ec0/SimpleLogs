from fastapi import APIRouter, HTTPException, status
from app.models import User
from app.models.totp_attempt import TotpAttempt
from app.schemas import (
    Token, LoginRequest, RefreshRequest, UserResponse,
    LoginResponse, TOTPVerifyLoginRequest, TOTPSetupResponse,
    TOTPVerifySetupRequest, TOTPDisableRequest,
)
from app.services.auth import AuthService
from app.services.totp import TOTPService
from app.api.deps import CurrentUser

router = APIRouter()

_TOTP_MAX_ATTEMPTS = 5


async def _check_totp_attempts(jti: str) -> None:
    """Raise 401 if this token has exceeded the attempt limit."""
    count = await TotpAttempt.filter(jti=jti).count()
    if count >= _TOTP_MAX_ATTEMPTS:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Too many TOTP attempts, please log in again",
        )


async def _record_totp_failure(jti: str) -> None:
    await TotpAttempt.create(jti=jti)


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """Authenticate user and return tokens, or TOTP challenge if 2FA is enabled."""
    user = await User.filter(email=request.email, is_active=True).first()

    if user is None or not user.verify_password(request.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if user.totp_enabled:
        totp_token = AuthService.create_totp_token(str(user.id))
        return LoginResponse(
            totp_required=True,
            totp_token=totp_token,
        )

    access_token, refresh_token = AuthService.create_tokens(str(user.id))
    return LoginResponse(
        totp_required=False,
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.post("/verify-totp", response_model=Token)
async def verify_totp(request: TOTPVerifyLoginRequest):
    """Verify TOTP code and issue real JWT tokens."""
    payload = AuthService.decode_token(request.totp_token)

    if payload is None or payload.type != "totp_required" or not payload.jti:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired TOTP token",
        )

    await _check_totp_attempts(payload.jti)

    user = await User.filter(id=payload.sub, is_active=True).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    if not await TOTPService.verify_login_code(user, request.code):
        await _record_totp_failure(payload.jti)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid TOTP code",
        )

    # Success — clean up attempt records for this token
    await TotpAttempt.filter(jti=payload.jti).delete()

    access_token, refresh_token = AuthService.create_tokens(str(user.id))
    return Token(access_token=access_token, refresh_token=refresh_token)


@router.post("/totp/setup", response_model=TOTPSetupResponse)
async def totp_setup(user: CurrentUser):
    """Begin TOTP setup: generate secret, QR code, and recovery codes."""
    if user.totp_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="TOTP is already enabled",
        )

    result = await TOTPService.setup_begin(user)
    return TOTPSetupResponse(**result)


@router.post("/totp/setup/verify")
async def totp_setup_verify(user: CurrentUser, request: TOTPVerifySetupRequest):
    """Verify the first TOTP code to complete setup."""
    if user.totp_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="TOTP is already enabled",
        )

    if not await TOTPService.setup_verify(user, request.code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid TOTP code",
        )

    return {"message": "TOTP enabled successfully"}


@router.post("/totp/disable")
async def totp_disable(user: CurrentUser, request: TOTPDisableRequest):
    """Disable TOTP (requires password confirmation)."""
    if not user.totp_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="TOTP is not enabled",
        )

    if not user.verify_password(request.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid password",
        )

    await TOTPService.disable(user)
    return {"message": "TOTP disabled successfully"}


@router.post("/refresh", response_model=Token)
async def refresh(request: RefreshRequest):
    """Get new access token using refresh token."""
    payload = AuthService.decode_token(request.refresh_token)

    if payload is None or payload.type != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    user = await User.filter(id=payload.sub, is_active=True).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    access_token, refresh_token = AuthService.create_tokens(str(user.id))

    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(user: CurrentUser):
    """Get current authenticated user info."""
    return UserResponse.model_validate(user, from_attributes=True)


@router.post("/logout")
async def logout(user: CurrentUser):
    """Logout user (client should discard tokens)."""
    return {"message": "Logged out successfully"}
