import os
from pathlib import Path
from tortoise import Tortoise
from tortoise.backends.base.client import BaseDBAsyncClient


MIGRATIONS_DIR = Path(__file__).parent.parent / "migrations"


async def get_connection() -> BaseDBAsyncClient:
    return Tortoise.get_connection("default")


async def ensure_migrations_table(conn: BaseDBAsyncClient) -> None:
    """Create the migrations tracking table if it doesn't exist."""
    await conn.execute_script("""
        CREATE TABLE IF NOT EXISTS _migrations (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255) NOT NULL UNIQUE,
            applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
    """)


async def get_applied_migrations(conn: BaseDBAsyncClient) -> set[str]:
    """Get the set of already-applied migration names."""
    rows = await conn.execute_query_dict("SELECT name FROM _migrations")
    return {row["name"] for row in rows}


async def mark_migration_applied(conn: BaseDBAsyncClient, name: str) -> None:
    """Record that a migration has been applied."""
    await conn.execute_query("INSERT INTO _migrations (name) VALUES ($1)", [name])


async def run_migrations() -> None:
    """Run all pending SQL migrations in order."""
    if not MIGRATIONS_DIR.exists():
        return

    conn = await get_connection()
    await ensure_migrations_table(conn)
    applied = await get_applied_migrations(conn)

    # Get all .sql files sorted by name
    migration_files = sorted(MIGRATIONS_DIR.glob("*.sql"))

    for migration_file in migration_files:
        name = migration_file.name
        if name in applied:
            continue

        print(f"Applying migration: {name}")
        sql = migration_file.read_text(encoding="utf-8")

        try:
            await conn.execute_script(sql)
            await mark_migration_applied(conn, name)
            print(f"Migration applied: {name}")
        except Exception as e:
            print(f"Migration failed: {name} - {e}")
            raise
