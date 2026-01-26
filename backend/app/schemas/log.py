from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from typing import Any
from app.models.log import LogLevel


class LogCreate(BaseModel):
    level: LogLevel = LogLevel.INFO
    message: str
    metadata: dict[str, Any] | None = None
    source: str | None = None
    timestamp: datetime | None = None  # If not provided, server time is used


class LogBatchCreate(BaseModel):
    logs: list[LogCreate] = Field(..., max_length=1000)


class LogResponse(BaseModel):
    id: int
    team_id: UUID
    timestamp: datetime
    level: LogLevel
    message: str
    metadata: dict[str, Any] | None
    source: str | None
    created_at: datetime

    class Config:
        from_attributes = True


class LogSearchParams(BaseModel):
    q: str | None = None  # Full-text search query
    level: list[LogLevel] | None = None
    source: str | None = None
    from_time: datetime | None = None
    to_time: datetime | None = None
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=50, ge=1, le=1000)
    # Metadata filters will be parsed from query params like metadata.field=value
