from datetime import datetime, timedelta, timezone
from uuid import UUID

from tortoise import Tortoise
from tortoise.backends.base.client import BaseDBAsyncClient

from app.models import Team


def _team_hex(team_id: UUID) -> str:
    """Return the hex representation of a team UUID (no dashes) for use in partition names."""
    return team_id.hex


def _partition_name(team_id: UUID) -> str:
    """Top-level team partition name: logs_<hex>."""
    return f"logs_{_team_hex(team_id)}"


def _monthly_partition_name(team_id: UUID, year: int, month: int) -> str:
    """Monthly sub-partition name: logs_<hex>_YYYY_MM."""
    return f"logs_{_team_hex(team_id)}_{year:04d}_{month:02d}"


def _default_subpartition_name(team_id: UUID) -> str:
    """Default sub-partition for a team: logs_<hex>_default."""
    return f"logs_{_team_hex(team_id)}_default"


async def _get_conn() -> BaseDBAsyncClient:
    return Tortoise.get_connection("default")


async def _table_exists(conn: BaseDBAsyncClient, table_name: str) -> bool:
    rows = await conn.execute_query_dict(
        "SELECT 1 FROM pg_class WHERE relname = $1 AND relkind IN ('r', 'p')",
        [table_name],
    )
    return len(rows) > 0


async def create_team_partition(team_id: UUID) -> None:
    """Create team-level LIST partition + default sub-partition + current & next month."""
    conn = await _get_conn()
    part_name = _partition_name(team_id)

    if await _table_exists(conn, part_name):
        return

    team_id_str = str(team_id)

    # Create team partition (sub-partitioned by range on created_at)
    await conn.execute_script(
        f"CREATE TABLE {part_name} PARTITION OF logs "
        f"FOR VALUES IN ('{team_id_str}') "
        f"PARTITION BY RANGE (created_at);"
    )

    # Create default sub-partition (safety net)
    default_name = _default_subpartition_name(team_id)
    await conn.execute_script(
        f"CREATE TABLE {default_name} PARTITION OF {part_name} DEFAULT;"
    )

    # Create current and next month sub-partitions
    now = datetime.now(timezone.utc)
    await create_monthly_partition(team_id, now.year, now.month)

    # Next month
    next_month = (now.replace(day=1) + timedelta(days=32)).replace(day=1)
    await create_monthly_partition(team_id, next_month.year, next_month.month)


async def create_monthly_partition(team_id: UUID, year: int, month: int) -> None:
    """Create a single monthly RANGE sub-partition for a team."""
    conn = await _get_conn()
    part_name = _monthly_partition_name(team_id, year, month)

    if await _table_exists(conn, part_name):
        return

    team_part = _partition_name(team_id)

    # Calculate range boundaries: [start_of_month, start_of_next_month)
    start = datetime(year, month, 1, tzinfo=timezone.utc)
    if month == 12:
        end = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
    else:
        end = datetime(year, month + 1, 1, tzinfo=timezone.utc)

    start_str = start.strftime("%Y-%m-%d")
    end_str = end.strftime("%Y-%m-%d")

    await conn.execute_script(
        f"CREATE TABLE {part_name} PARTITION OF {team_part} "
        f"FOR VALUES FROM ('{start_str}') TO ('{end_str}');"
    )


async def drop_team_partition(team_id: UUID) -> None:
    """Drop team partition (cascades to all monthly sub-partitions). Instant."""
    conn = await _get_conn()
    part_name = _partition_name(team_id)

    if not await _table_exists(conn, part_name):
        return

    await conn.execute_script(f"DROP TABLE {part_name};")


async def drop_monthly_partition(team_id: UUID, year: int, month: int) -> None:
    """Drop a specific monthly sub-partition. Used for retention."""
    conn = await _get_conn()
    part_name = _monthly_partition_name(team_id, year, month)

    if not await _table_exists(conn, part_name):
        return

    await conn.execute_script(f"DROP TABLE {part_name};")


async def ensure_upcoming_partitions() -> None:
    """For all teams, ensure current + next month sub-partitions exist.
    Called by scheduler and at startup."""
    now = datetime.now(timezone.utc)
    next_month = (now.replace(day=1) + timedelta(days=32)).replace(day=1)

    teams = await Team.all()
    conn = await _get_conn()

    for team in teams:
        team_part = _partition_name(team.id)

        # Only create monthly partitions if the team partition exists
        if not await _table_exists(conn, team_part):
            # Team partition missing — create the full structure
            await create_team_partition(team.id)
        else:
            # Just ensure current + next month exist
            await create_monthly_partition(team.id, now.year, now.month)
            await create_monthly_partition(team.id, next_month.year, next_month.month)


async def cleanup_expired_partitions() -> None:
    """For teams with retention_days, drop monthly partitions older than cutoff.
    For partial-month boundaries, use DELETE on the boundary month."""
    conn = await _get_conn()
    teams = await Team.filter(retention_days__isnull=False)

    for team in teams:
        if team.retention_days is None:
            continue

        cutoff = datetime.now(timezone.utc) - timedelta(days=team.retention_days)
        team_part = _partition_name(team.id)

        if not await _table_exists(conn, team_part):
            continue

        # Find all monthly sub-partitions for this team
        rows = await conn.execute_query_dict(
            "SELECT c.relname FROM pg_class c "
            "JOIN pg_inherits i ON c.oid = i.inhrelid "
            "JOIN pg_class p ON p.oid = i.inhparent "
            "WHERE p.relname = $1 AND c.relname != $2 "
            "ORDER BY c.relname",
            [team_part, _default_subpartition_name(team.id)],
        )

        for row in rows:
            relname = row["relname"]

            # Parse partition name: logs_<hex>_YYYY_MM
            parts = relname.rsplit("_", 2)
            if len(parts) < 3:
                continue
            try:
                p_year = int(parts[-2])
                p_month = int(parts[-1])
            except ValueError:
                continue

            # End of this partition's month
            if p_month == 12:
                partition_end = datetime(p_year + 1, 1, 1, tzinfo=timezone.utc)
            else:
                partition_end = datetime(p_year, p_month + 1, 1, tzinfo=timezone.utc)

            partition_start = datetime(p_year, p_month, 1, tzinfo=timezone.utc)

            if partition_end <= cutoff:
                # Entire partition is expired — drop it (instant)
                await conn.execute_script(f"DROP TABLE {relname};")
                print(f"Dropped expired partition {relname}")
            elif partition_start < cutoff < partition_end:
                # Partial month — delete rows before cutoff
                cutoff_str = cutoff.strftime("%Y-%m-%d %H:%M:%S+00")
                result = await conn.execute_query(
                    f"DELETE FROM {relname} WHERE created_at < $1",
                    [cutoff_str],
                )
                deleted = result[0]
                if deleted:
                    print(f"Deleted {deleted} rows from boundary partition {relname}")
