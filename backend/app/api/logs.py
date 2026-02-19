from uuid import UUID
from typing import Annotated
from datetime import datetime
from fastapi import APIRouter, Query, Depends, HTTPException, status, Request
from tortoise import connections
from app.models import Log, LogLevel, TeamRole
from app.schemas import LogResponse, UserIdBackfillRequest, UserIdBackfillResponse
from app.api.deps import get_team_member, CurrentUser

router = APIRouter()


@router.get("/{team_id}/logs")
async def search_logs(
    team_id: UUID,
    user: CurrentUser,
    request: Request,
    q: str | None = None,
    level: Annotated[list[LogLevel] | None, Query()] = None,
    source: str | None = None,
    user_id: str | None = None,
    from_time: datetime | None = Query(None, alias="from"),
    to_time: datetime | None = Query(None, alias="to"),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=1000),
):
    """
    Search logs with filters.

    - **q**: Full-text search on message
    - **level**: Filter by log levels (can specify multiple)
    - **source**: Filter by source
    - **user_id**: Filter by user ID
    - **from/to**: Date range filter
    - **metadata.field=value**: Filter by JSON metadata fields

    Example:
    ```
    GET /api/v1/teams/{team_id}/logs?q=error&level=error&level=fatal&from=2024-01-01T00:00:00Z
    GET /api/v1/teams/{team_id}/logs?metadata.user_id=123&metadata.status=failed
    ```
    """
    team, membership = await get_team_member(team_id, user)

    query = Log.filter(team=team)

    # Full-text search on message
    if q:
        # Use PostgreSQL full-text search
        query = query.filter(
            message__icontains=q  # Simple fallback - for real full-text, use raw SQL
        )
        # For proper full-text search, you'd use:
        # query = query.annotate(
        #     search_rank=RawSQL("ts_rank(to_tsvector('english', message), plainto_tsquery('english', %s))", [q])
        # ).filter(search_rank__gt=0).order_by("-search_rank")

    # Level filter
    if level:
        query = query.filter(level__in=level)

    # Source filter
    if source:
        query = query.filter(source=source)

    # User ID filter
    if user_id:
        query = query.filter(user_id=user_id)

    # Date range
    if from_time:
        query = query.filter(timestamp__gte=from_time)
    if to_time:
        query = query.filter(timestamp__lte=to_time)

    # Metadata filters (parse query params like metadata.field=value)
    for key, value in request.query_params.items():
        if key.startswith("metadata."):
            field = key[9:]  # Remove "metadata." prefix
            # Use PostgreSQL JSONB containment
            query = query.filter(metadata__contains={field: value})

    # Pagination
    offset = (page - 1) * limit
    total = await query.count()
    logs = await query.offset(offset).limit(limit)  # Uses default ordering by -id

    return {
        "items": [LogResponse.model_validate(log, from_attributes=True) for log in logs],
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total + limit - 1) // limit,
    }


@router.get("/{team_id}/logs/{log_id}", response_model=LogResponse)
async def get_log(team_id: UUID, log_id: int, user: CurrentUser):
    """Get a single log entry by ID."""
    team, membership = await get_team_member(team_id, user)

    log = await Log.filter(id=log_id, team=team).first()
    if log is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Log not found",
        )

    return LogResponse.model_validate(log, from_attributes=True)


@router.delete("/{team_id}/logs")
async def delete_logs(
    team_id: UUID,
    user: CurrentUser,
    request: Request,
    level: Annotated[list[LogLevel] | None, Query()] = None,
    source: str | None = None,
    user_id: str | None = None,
    from_time: datetime | None = Query(None, alias="from"),
    to_time: datetime | None = Query(None, alias="to"),
):
    """
    Bulk delete logs matching filters.
    At least one filter must be specified to prevent accidental deletion of all logs.
    """
    team, membership = await get_team_member(team_id, user)

    # Require at least one filter
    has_filter = any([level, source, user_id, from_time, to_time])
    metadata_filters = [k for k in request.query_params.keys() if k.startswith("metadata.")]

    if not has_filter and not metadata_filters:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one filter must be specified",
        )

    query = Log.filter(team=team)

    if level:
        query = query.filter(level__in=level)
    if source:
        query = query.filter(source=source)
    if user_id:
        query = query.filter(user_id=user_id)
    if from_time:
        query = query.filter(timestamp__gte=from_time)
    if to_time:
        query = query.filter(timestamp__lte=to_time)

    for key, value in request.query_params.items():
        if key.startswith("metadata."):
            field = key[9:]
            query = query.filter(metadata__contains={field: value})

    deleted = await query.delete()

    return {"deleted": deleted}


@router.post("/{team_id}/logs/backfill-user-id", response_model=UserIdBackfillResponse)
async def backfill_user_id(
    team_id: UUID,
    user: CurrentUser,
    body: UserIdBackfillRequest,
):
    """
    Backfill the user_id column from a metadata key.

    - **metadata_key**: The key in the metadata JSONB to copy into user_id
    - **overwrite**: If false (default), only updates rows where user_id IS NULL
    """
    team, membership = await get_team_member(team_id, user)

    if membership.role not in (TeamRole.MEMBER, TeamRole.MANAGER):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only members and managers can perform backfill operations",
        )

    conn = connections.get("default")

    sql = """
        UPDATE logs
        SET user_id = metadata->>$1
        WHERE team_id = $2
          AND metadata ? $1
    """
    if not body.overwrite:
        sql += " AND user_id IS NULL"

    result = await conn.execute_query(sql, [body.metadata_key, str(team.id)])
    updated = result[0]

    return UserIdBackfillResponse(
        updated=updated,
        message=f"Updated {updated} rows from metadata key '{body.metadata_key}'",
    )
