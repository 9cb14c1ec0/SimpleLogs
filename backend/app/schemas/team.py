from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from app.models.team import TeamRole


class TeamCreate(BaseModel):
    name: str
    retention_days: int | None = None


class TeamUpdate(BaseModel):
    name: str | None = None
    retention_days: int | None = None


class ApiKeyResponse(BaseModel):
    id: UUID
    team_id: UUID
    label: str
    api_key_prefix: str
    created_at: datetime

    class Config:
        from_attributes = True


class ApiKeyWithSecret(ApiKeyResponse):
    """Response when creating an API key - includes the full key (shown only once)."""
    api_key: str


class ApiKeyCreate(BaseModel):
    label: str = ""
    api_key: str | None = None


class TeamResponse(BaseModel):
    id: UUID
    name: str
    api_keys: list[ApiKeyResponse]
    retention_days: int | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TeamCreateResponse(BaseModel):
    """Response when creating a team - includes the first API key with secret."""
    id: UUID
    name: str
    api_keys: list[ApiKeyResponse]
    retention_days: int | None
    created_at: datetime
    updated_at: datetime
    api_key: str


class MembershipCreate(BaseModel):
    user_id: UUID
    role: TeamRole = TeamRole.MEMBER


class MembershipResponse(BaseModel):
    id: UUID
    user_id: UUID
    user_email: str
    user_name: str
    team_id: UUID
    role: TeamRole
    created_at: datetime
