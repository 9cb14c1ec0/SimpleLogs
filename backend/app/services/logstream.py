import asyncio
from contextlib import asynccontextmanager
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from uuid import UUID

import asyncpg
from tortoise import connections

from app.config import get_settings

CHANNEL = "simplelogs_ingested"

# Pool options Tortoise accepts in the URL that asyncpg.connect() does not.
# Everything else is kept, TLS settings above all.
_POOL_ONLY_PARAMS = frozenset(
    {
        "minsize",
        "maxsize",
        "min_size",
        "max_size",
        "max_queries",
        "max_inactive_connection_lifetime",
    }
)


def _dsn() -> str:
    """The ORM's URL minus its pool options, which asyncpg would reject."""
    parts = urlsplit(get_settings().database_url)
    kept = [
        (key, value)
        for key, value in parse_qsl(parts.query, keep_blank_values=True)
        if key not in _POOL_ONLY_PARAMS
    ]
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(kept), ""))


class LogStream:
    """
    Fans Postgres NOTIFY out to the SSE subscribers in this process.

    The notification carries only a team id. Payloads are capped at 8000 bytes
    and a single log can be far larger, so subscribers re-query for rows past
    their own cursor instead of reading the row off the wire. That also means
    the stream reuses the search filters verbatim.

    One LISTEN connection is shared by every subscriber in the process.
    """

    def __init__(self) -> None:
        self._conn: asyncpg.Connection | None = None
        self._connect_lock = asyncio.Lock()
        self._subscribers: dict[str, set[asyncio.Event]] = {}

    async def _listen(self) -> None:
        if self._conn is not None and not self._conn.is_closed():
            return
        async with self._connect_lock:
            if self._conn is not None and not self._conn.is_closed():
                return
            conn = await asyncpg.connect(_dsn())
            await conn.add_listener(CHANNEL, self._dispatch)
            self._conn = conn

    def _dispatch(self, _conn, _pid, _channel, payload: str) -> None:
        for event in self._subscribers.get(payload, ()):
            event.set()

    @asynccontextmanager
    async def subscribe(self, team_id: UUID):
        """Yields an event that is set whenever this team ingests logs."""
        try:
            await self._listen()
        except Exception as exc:  # noqa: BLE001
            # Subscribers re-query on their heartbeat regardless, so losing the
            # listener costs latency rather than breaking the stream.
            print(f"log stream listener unavailable, falling back to heartbeat: {exc}")

        key = str(team_id)
        event = asyncio.Event()
        self._subscribers.setdefault(key, set()).add(event)
        try:
            yield event
        finally:
            events = self._subscribers.get(key)
            if events is not None:
                events.discard(event)
                if not events:
                    self._subscribers.pop(key, None)

    async def close(self) -> None:
        if self._conn is not None and not self._conn.is_closed():
            await self._conn.close()
        self._conn = None


log_stream = LogStream()


async def notify_new_logs(team_id: UUID) -> None:
    """Wake every stream watching this team. One call per ingest request."""
    conn = connections.get("default")
    await conn.execute_query("SELECT pg_notify($1, $2)", [CHANNEL, str(team_id)])
