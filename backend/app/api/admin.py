from uuid import UUID
from fastapi import APIRouter, HTTPException, status
from app.models import User, Team, TeamMembership, TeamRole
from app.schemas import (
    UserCreate, UserUpdate, UserResponse,
    TeamCreate, TeamUpdate, TeamResponse, TeamWithKey,
    MembershipCreate, MembershipResponse,
)
from app.api.deps import AdminUser

router = APIRouter()


# ============== Users ==============

@router.get("/users", response_model=list[UserResponse])
async def list_users(admin: AdminUser):
    """List all users."""
    users = await User.all()
    return [UserResponse.model_validate(u, from_attributes=True) for u in users]


@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(admin: AdminUser, data: UserCreate):
    """Create a new user."""
    existing = await User.filter(email=data.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    user = User(
        email=data.email,
        name=data.name,
        is_admin=data.is_admin,
    )
    user.set_password(data.password)
    await user.save()

    return UserResponse.model_validate(user, from_attributes=True)


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(admin: AdminUser, user_id: UUID):
    """Get a user by ID."""
    user = await User.filter(id=user_id).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return UserResponse.model_validate(user, from_attributes=True)


@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(admin: AdminUser, user_id: UUID, data: UserUpdate):
    """Update a user."""
    user = await User.filter(id=user_id).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if data.email is not None:
        existing = await User.filter(email=data.email).exclude(id=user_id).first()
        if existing:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already in use")
        user.email = data.email

    if data.name is not None:
        user.name = data.name
    if data.is_admin is not None:
        user.is_admin = data.is_admin
    if data.is_active is not None:
        user.is_active = data.is_active
    if data.password is not None:
        user.set_password(data.password)

    await user.save()
    return UserResponse.model_validate(user, from_attributes=True)


@router.delete("/users/{user_id}")
async def delete_user(admin: AdminUser, user_id: UUID):
    """Delete a user."""
    user = await User.filter(id=user_id).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Prevent deleting yourself
    if user.id == admin.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot delete yourself")

    await user.delete()
    return {"message": "User deleted"}


# ============== Teams ==============

@router.get("/teams", response_model=list[TeamResponse])
async def list_teams(admin: AdminUser):
    """List all teams."""
    teams = await Team.all()
    return [TeamResponse.model_validate(t, from_attributes=True) for t in teams]


@router.post("/teams", response_model=TeamWithKey, status_code=status.HTTP_201_CREATED)
async def create_team(admin: AdminUser, data: TeamCreate):
    """Create a new team. Returns the API key (shown only once)."""
    existing = await Team.filter(name=data.name).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Team name already exists")

    api_key, key_hash, prefix = Team.generate_api_key()

    team = await Team.create(
        name=data.name,
        api_key_hash=key_hash,
        api_key_prefix=prefix,
        retention_days=data.retention_days,
    )

    return TeamWithKey(
        id=team.id,
        name=team.name,
        api_key_prefix=team.api_key_prefix,
        retention_days=team.retention_days,
        created_at=team.created_at,
        updated_at=team.updated_at,
        api_key=api_key,
    )


@router.get("/teams/{team_id}", response_model=TeamResponse)
async def get_team(admin: AdminUser, team_id: UUID):
    """Get a team by ID."""
    team = await Team.filter(id=team_id).first()
    if team is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found")
    return TeamResponse.model_validate(team, from_attributes=True)


@router.put("/teams/{team_id}", response_model=TeamResponse)
async def update_team(admin: AdminUser, team_id: UUID, data: TeamUpdate):
    """Update a team."""
    team = await Team.filter(id=team_id).first()
    if team is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found")

    if data.name is not None:
        existing = await Team.filter(name=data.name).exclude(id=team_id).first()
        if existing:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Team name already in use")
        team.name = data.name

    if data.retention_days is not None:
        team.retention_days = data.retention_days

    await team.save()
    return TeamResponse.model_validate(team, from_attributes=True)


@router.delete("/teams/{team_id}")
async def delete_team(admin: AdminUser, team_id: UUID):
    """Delete a team and all its logs."""
    team = await Team.filter(id=team_id).first()
    if team is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found")

    await team.delete()
    return {"message": "Team deleted"}


@router.post("/teams/{team_id}/regenerate-key", response_model=TeamWithKey)
async def regenerate_api_key(admin: AdminUser, team_id: UUID):
    """Regenerate a team's API key. Returns the new key (shown only once)."""
    team = await Team.filter(id=team_id).first()
    if team is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found")

    api_key, key_hash, prefix = Team.generate_api_key()
    team.api_key_hash = key_hash
    team.api_key_prefix = prefix
    await team.save()

    return TeamWithKey(
        id=team.id,
        name=team.name,
        api_key_prefix=team.api_key_prefix,
        retention_days=team.retention_days,
        created_at=team.created_at,
        updated_at=team.updated_at,
        api_key=api_key,
    )


# ============== Team Members ==============

@router.get("/teams/{team_id}/members", response_model=list[MembershipResponse])
async def list_team_members(admin: AdminUser, team_id: UUID):
    """List all members of a team."""
    team = await Team.filter(id=team_id).first()
    if team is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found")

    memberships = await TeamMembership.filter(team=team).prefetch_related("user")

    return [
        MembershipResponse(
            id=m.id,
            user_id=m.user.id,
            user_email=m.user.email,
            user_name=m.user.name,
            team_id=team_id,
            role=m.role,
            created_at=m.created_at,
        )
        for m in memberships
    ]


@router.post("/teams/{team_id}/members", response_model=MembershipResponse, status_code=status.HTTP_201_CREATED)
async def add_team_member(admin: AdminUser, team_id: UUID, data: MembershipCreate):
    """Add a user to a team."""
    team = await Team.filter(id=team_id).first()
    if team is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found")

    user = await User.filter(id=data.user_id).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    existing = await TeamMembership.filter(team=team, user=user).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User already a member")

    membership = await TeamMembership.create(
        team=team,
        user=user,
        role=data.role,
    )

    return MembershipResponse(
        id=membership.id,
        user_id=user.id,
        user_email=user.email,
        user_name=user.name,
        team_id=team_id,
        role=membership.role,
        created_at=membership.created_at,
    )


@router.delete("/teams/{team_id}/members/{user_id}")
async def remove_team_member(admin: AdminUser, team_id: UUID, user_id: UUID):
    """Remove a user from a team."""
    membership = await TeamMembership.filter(team_id=team_id, user_id=user_id).first()
    if membership is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Membership not found")

    await membership.delete()
    return {"message": "Member removed"}
