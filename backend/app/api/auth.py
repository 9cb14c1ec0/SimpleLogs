from fastapi import APIRouter, HTTPException, status
from app.models import User
from app.schemas import Token, LoginRequest, RefreshRequest, UserResponse
from app.services.auth import AuthService
from app.api.deps import CurrentUser

router = APIRouter()


@router.post("/login", response_model=Token)
async def login(request: LoginRequest):
    """Authenticate user and return tokens."""
    user = await User.filter(email=request.email, is_active=True).first()

    if user is None or not user.verify_password(request.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    access_token, refresh_token = AuthService.create_tokens(str(user.id))

    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
    )


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
    # JWT tokens are stateless, so we just return success
    # Client is responsible for discarding the tokens
    return {"message": "Logged out successfully"}
