from typing import Annotated
from uuid import UUID
from fastapi import Depends, HTTPException, status, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.models import User, Team, TeamMembership, TeamRole, ApiKey
from app.services.auth import AuthService

security = HTTPBearer()


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)]
) -> User:
    """Validate JWT and return current user."""
    token = credentials.credentials
    payload = AuthService.decode_token(token)

    if payload is None or payload.type != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    user = await User.filter(id=payload.sub, is_active=True).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    return user


async def get_admin_user(
    user: Annotated[User, Depends(get_current_user)]
) -> User:
    """Require admin privileges."""
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )
    return user


async def get_team_from_api_key(
    x_api_key: Annotated[str, Header()]
) -> Team:
    """Validate API key and return the team."""
    team = await ApiKey.get_team_by_api_key(x_api_key)
    if team is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )
    return team


async def get_team_member(
    team_id: UUID,
    user: Annotated[User, Depends(get_current_user)]
) -> tuple[Team, TeamMembership]:
    """Verify user is a member of the team and return both."""
    team = await Team.filter(id=team_id).first()
    if team is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found",
        )

    # Admins can access all teams
    if user.is_admin:
        membership = await TeamMembership.filter(team=team, user=user).first()
        if membership is None:
            # Create a virtual membership for admin access
            membership = TeamMembership(
                user=user,
                team=team,
                role=TeamRole.MANAGER,
            )
        return team, membership

    membership = await TeamMembership.filter(team=team, user=user).first()
    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this team",
        )

    return team, membership


# Type aliases for cleaner endpoint signatures
CurrentUser = Annotated[User, Depends(get_current_user)]
AdminUser = Annotated[User, Depends(get_admin_user)]
TeamFromApiKey = Annotated[Team, Depends(get_team_from_api_key)]
