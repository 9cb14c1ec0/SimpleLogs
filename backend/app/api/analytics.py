from uuid import UUID
from typing import Annotated, Literal
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Query
from tortoise import connections
from app.models import LogLevel
from app.schemas import VolumeResponse, VolumeBucket, TopResponse, TopItem, HeatmapResponse, HeatmapCell
from app.api.deps import get_team_member, CurrentUser

router = APIRouter()

VALID_LEVELS = [e.value for e in LogLevel]


def _default_range(
    from_time: datetime | None,
    to_time: datetime | None,
) -> tuple[datetime, datetime]:
    now = datetime.now(timezone.utc)
    return (
        from_time or now - timedelta(hours=24),
        to_time or now,
    )


BUCKET_SQL = {
    "hour": "date_trunc('hour', timestamp)",
    "day": "date_trunc('day', timestamp)",
    "week": "date_trunc('week', timestamp)",
}


@router.get("/{team_id}/analytics/volume", response_model=VolumeResponse)
async def analytics_volume(
    team_id: UUID,
    user: CurrentUser,
    bucket: Literal["hour", "day", "week"] = "hour",
    split_by: Literal["level", "source", "omit"] = "level",
    from_time: datetime | None = Query(None, alias="from"),
    to_time: datetime | None = Query(None, alias="to"),
):
    team, _ = await get_team_member(team_id, user)
    start, end = _default_range(from_time, to_time)
    conn = connections.get("default")

    trunc = BUCKET_SQL[bucket]

    if split_by == "omit":
        rows = await conn.execute_query_dict(
            f"""
            SELECT {trunc} AS bucket, count(*) AS count
            FROM logs
            WHERE team_id = $1 AND timestamp >= $2 AND timestamp <= $3
            GROUP BY bucket ORDER BY bucket
            """,
            [str(team.id), start, end],
        )
        buckets = [VolumeBucket(bucket=str(r["bucket"]), count=r["count"]) for r in rows]
    elif split_by == "level":
        rows = await conn.execute_query_dict(
            f"""
            SELECT {trunc} AS bucket, level, count(*) AS count
            FROM logs
            WHERE team_id = $1 AND timestamp >= $2 AND timestamp <= $3
            GROUP BY bucket, level ORDER BY bucket, level
            """,
            [str(team.id), start, end],
        )
        buckets = [VolumeBucket(bucket=str(r["bucket"]), level=r["level"], count=r["count"]) for r in rows]
    else:
        rows = await conn.execute_query_dict(
            f"""
            SELECT {trunc} AS bucket, source, count(*) AS count
            FROM logs
            WHERE team_id = $1 AND timestamp >= $2 AND timestamp <= $3
            GROUP BY bucket, source ORDER BY bucket, source
            """,
            [str(team.id), start, end],
        )
        buckets = [VolumeBucket(bucket=str(r["bucket"]), source=r["source"], count=r["count"]) for r in rows]

    # Totals by level
    total_rows = await conn.execute_query_dict(
        """
        SELECT level, count(*) AS count
        FROM logs
        WHERE team_id = $1 AND timestamp >= $2 AND timestamp <= $3
        GROUP BY level
        """,
        [str(team.id), start, end],
    )
    totals = {r["level"]: r["count"] for r in total_rows}

    return VolumeResponse(buckets=buckets, totals=totals)


@router.get("/{team_id}/analytics/top", response_model=TopResponse)
async def analytics_top(
    team_id: UUID,
    user: CurrentUser,
    field: Literal["source", "message", "user_id"] = "source",
    level: Annotated[list[LogLevel] | None, Query()] = None,
    limit: int = Query(10, ge=1, le=100),
    from_time: datetime | None = Query(None, alias="from"),
    to_time: datetime | None = Query(None, alias="to"),
):
    team, _ = await get_team_member(team_id, user)
    start, end = _default_range(from_time, to_time)
    conn = connections.get("default")

    col = {"source": "source", "message": "message", "user_id": "user_id"}[field]

    where = "team_id = $1 AND timestamp >= $2 AND timestamp <= $3"
    params: list = [str(team.id), start, end]

    if level:
        level_values = [lv.value for lv in level]
        placeholders = ", ".join(f"${i}" for i in range(4, 4 + len(level_values)))
        where += f" AND level IN ({placeholders})"
        params.extend(level_values)

    # Exclude nulls for the grouped field
    where += f" AND {col} IS NOT NULL"

    rows = await conn.execute_query_dict(
        f"""
        SELECT {col} AS value, count(*) AS count
        FROM logs
        WHERE {where}
        GROUP BY {col}
        ORDER BY count DESC
        LIMIT ${len(params) + 1}
        """,
        [*params, limit],
    )

    return TopResponse(items=[TopItem(value=r["value"], count=r["count"]) for r in rows])


@router.get("/{team_id}/analytics/heatmap", response_model=HeatmapResponse)
async def analytics_heatmap(
    team_id: UUID,
    user: CurrentUser,
    source_limit: int = Query(20, ge=1, le=100),
    from_time: datetime | None = Query(None, alias="from"),
    to_time: datetime | None = Query(None, alias="to"),
):
    team, _ = await get_team_member(team_id, user)
    start, end = _default_range(from_time, to_time)
    conn = connections.get("default")

    # Get top N sources by volume
    top_sources = await conn.execute_query_dict(
        """
        SELECT source, count(*) AS count
        FROM logs
        WHERE team_id = $1 AND timestamp >= $2 AND timestamp <= $3
          AND source IS NOT NULL
        GROUP BY source
        ORDER BY count DESC
        LIMIT $4
        """,
        [str(team.id), start, end, source_limit],
    )

    source_list = [r["source"] for r in top_sources]

    if not source_list:
        return HeatmapResponse(sources=[], levels=VALID_LEVELS, data=[])

    placeholders = ", ".join(f"${i}" for i in range(4, 4 + len(source_list)))
    rows = await conn.execute_query_dict(
        f"""
        SELECT source, level, count(*) AS count
        FROM logs
        WHERE team_id = $1 AND timestamp >= $2 AND timestamp <= $3
          AND source IN ({placeholders})
        GROUP BY source, level
        """,
        [str(team.id), start, end, *source_list],
    )

    data = [HeatmapCell(source=r["source"], level=r["level"], count=r["count"]) for r in rows]

    return HeatmapResponse(sources=source_list, levels=VALID_LEVELS, data=data)
