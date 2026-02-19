from tortoise import fields
from tortoise.models import Model
import secrets
import hashlib


class ApiKey(Model):
    id = fields.UUIDField(pk=True)
    team = fields.ForeignKeyField("models.Team", related_name="api_keys", on_delete=fields.CASCADE)
    label = fields.CharField(max_length=255, default="")
    api_key_hash = fields.CharField(max_length=255, unique=True, index=True)
    api_key_prefix = fields.CharField(max_length=20)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "api_keys"

    @staticmethod
    def generate_api_key() -> tuple[str, str, str]:
        """Generate a new API key. Returns (full_key, hash, prefix)."""
        random_part = secrets.token_urlsafe(32)
        prefix = f"sl_{secrets.token_urlsafe(4)}"
        full_key = f"{prefix}_{random_part}"
        key_hash = hashlib.sha256(full_key.encode()).hexdigest()
        return full_key, key_hash, prefix

    @staticmethod
    def hash_api_key(key: str) -> str:
        """Hash an API key for comparison."""
        return hashlib.sha256(key.encode()).hexdigest()

    @classmethod
    async def get_team_by_api_key(cls, api_key: str):
        """Find a team by API key."""
        key_hash = cls.hash_api_key(api_key)
        row = await cls.filter(api_key_hash=key_hash).select_related("team").first()
        if row is None:
            return None
        return row.team
