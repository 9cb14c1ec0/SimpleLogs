from enum import Enum
from tortoise import fields
from tortoise.models import Model


class TeamRole(str, Enum):
    VIEWER = "viewer"    # Can view logs
    MEMBER = "member"    # Can view and manage logs
    MANAGER = "manager"  # Can manage team members


class Team(Model):
    id = fields.UUIDField(pk=True)
    name = fields.CharField(max_length=255, unique=True)
    retention_days = fields.IntField(null=True)  # null = keep forever
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    # Reverse relations
    memberships: fields.ReverseRelation["TeamMembership"]
    api_keys: fields.ReverseRelation["ApiKey"]
    logs: fields.ReverseRelation["Log"]

    class Meta:
        table = "teams"


class TeamMembership(Model):
    id = fields.UUIDField(pk=True)
    user = fields.ForeignKeyField("models.User", related_name="team_memberships", on_delete=fields.CASCADE)
    team = fields.ForeignKeyField("models.Team", related_name="memberships", on_delete=fields.CASCADE)
    role = fields.CharEnumField(TeamRole, default=TeamRole.MEMBER)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "team_memberships"
        unique_together = [("user", "team")]
