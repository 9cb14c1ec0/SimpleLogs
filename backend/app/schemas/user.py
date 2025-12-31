from pydantic import BaseModel, EmailStr
from uuid import UUID
from datetime import datetime


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: str
    is_admin: bool = False


class UserUpdate(BaseModel):
    email: EmailStr | None = None
    password: str | None = None
    name: str | None = None
    is_admin: bool | None = None
    is_active: bool | None = None


class UserResponse(BaseModel):
    id: UUID
    email: str
    name: str
    is_admin: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
