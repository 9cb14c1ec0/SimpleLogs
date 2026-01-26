import bcrypt
from tortoise import fields
from tortoise.models import Model


class User(Model):
    id = fields.UUIDField(pk=True)
    email = fields.CharField(max_length=255, unique=True, index=True)
    password_hash = fields.CharField(max_length=255)
    name = fields.CharField(max_length=255)
    is_admin = fields.BooleanField(default=False)
    is_active = fields.BooleanField(default=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    # Reverse relations
    team_memberships: fields.ReverseRelation["TeamMembership"]

    class Meta:
        table = "users"

    def set_password(self, password: str):
        self.password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    def verify_password(self, password: str) -> bool:
        return bcrypt.checkpw(password.encode(), self.password_hash.encode())

    async def get_teams(self):
        """Get all teams this user belongs to."""
        from app.models.team import TeamMembership
        memberships = await TeamMembership.filter(user=self).prefetch_related("team")
        return [m.team for m in memberships]
