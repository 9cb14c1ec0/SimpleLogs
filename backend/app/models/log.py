from enum import Enum
from tortoise import fields
from tortoise.models import Model


class LogLevel(str, Enum):
    DEBUG = "debug"
    INFO = "info"
    WARN = "warn"
    ERROR = "error"
    FATAL = "fatal"


class Log(Model):
    id = fields.BigIntField(pk=True)  # Auto-increment for efficient ordering
    team = fields.ForeignKeyField("models.Team", related_name="logs", on_delete=fields.CASCADE, index=True)
    timestamp = fields.DatetimeField(index=True)
    level = fields.CharEnumField(LogLevel, index=True)
    message = fields.TextField()
    metadata = fields.JSONField(null=True)  # JSONB in PostgreSQL
    source = fields.CharField(max_length=255, null=True, index=True)
    user_id = fields.CharField(max_length=255, null=True)
    created_at = fields.DatetimeField(auto_now_add=True, index=True)

    class Meta:
        table = "logs"
        ordering = ["-id"]  # Order by id (insertion order) instead of timestamp
