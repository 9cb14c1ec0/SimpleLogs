from enum import Enum
from tortoise import fields
from tortoise.models import Model
import secrets
import hashlib


class TeamRole(str, Enum):
    VIEWER = "viewer"    # Can view logs
    MEMBER = "member"    # Can view and manage logs
    MANAGER = "manager"  # Can manage team members


class Team(Model):
    id = fields.UUIDField(pk=True)
    name = fields.CharField(max_length=255, unique=True)
    api_key_hash = fields.CharField(max_length=255, unique=True, index=True)
    api_key_prefix = fields.CharField(max_length=20)  # For identification: sl_xxxx
    retention_days = fields.IntField(null=True)  # null = keep forever
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    # Reverse relations
    memberships: fields.ReverseRelation["TeamMembership"]
    logs: fields.ReverseRelation["Log"]

    class Meta:
        table = "teams"

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
    async def get_by_api_key(cls, api_key: str) -> "Team | None":
        """Find a team by API key."""
        key_hash = cls.hash_api_key(api_key)
        return await cls.filter(api_key_hash=key_hash).first()


class TeamMembership(Model):
    id = fields.UUIDField(pk=True)
    user = fields.ForeignKeyField("models.User", related_name="team_memberships", on_delete=fields.CASCADE)
    team = fields.ForeignKeyField("models.Team", related_name="memberships", on_delete=fields.CASCADE)
    role = fields.CharEnumField(TeamRole, default=TeamRole.MEMBER)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "team_memberships"
        unique_together = [("user", "team")]
