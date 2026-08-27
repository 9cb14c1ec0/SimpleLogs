from datetime import datetime, timezone
from fastapi import APIRouter
from app.models import Log
from app.schemas import LogCreate, LogBatchCreate
from app.api.deps import TeamFromApiKey
from app.services.logstream import notify_new_logs

router = APIRouter()


@router.post("")
async def ingest_log(log: LogCreate, team: TeamFromApiKey):
    """
    Ingest a single log entry.

    Example:
    ```
    curl -X POST https://your-server/api/v1/ingest \\
      -H "X-API-Key: sl_xxxx_xxxxxxxxxxxxx" \\
      -H "Content-Type: application/json" \\
      -d '{"level": "info", "message": "User logged in", "metadata": {"user_id": 123}}'
    ```
    """
    await Log.create(
        team=team,
        timestamp=log.timestamp or datetime.now(timezone.utc),
        level=log.level,
        message=log.message,
        metadata=log.metadata,
        source=log.source,
        user_id=log.user_id,
    )
    await notify_new_logs(team.id)

    return {"status": "ok"}


@router.post("/batch")
async def ingest_logs_batch(batch: LogBatchCreate, team: TeamFromApiKey):
    """
    Ingest multiple log entries in a single request (up to 1000).

    Example:
    ```
    curl -X POST https://your-server/api/v1/ingest/batch \\
      -H "X-API-Key: sl_xxxx_xxxxxxxxxxxxx" \\
      -H "Content-Type: application/json" \\
      -d '{"logs": [{"level": "info", "message": "Log 1"}, {"level": "error", "message": "Log 2"}]}'
    ```
    """
    now = datetime.now(timezone.utc)

    logs_to_create = [
        Log(
            team=team,
            timestamp=log.timestamp or now,
            level=log.level,
            message=log.message,
            metadata=log.metadata,
            source=log.source,
            user_id=log.user_id,
        )
        for log in batch.logs
    ]

    await Log.bulk_create(logs_to_create)
    await notify_new_logs(team.id)

    return {"status": "ok", "count": len(logs_to_create)}
