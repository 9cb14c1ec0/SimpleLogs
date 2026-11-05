from tortoise import fields
from tortoise.models import Model

SINGLETON_ID = 1


class SsoSettings(Model):
    """OpenID Connect provider settings. There is at most one row."""

    id = fields.IntField(pk=True)
    enabled = fields.BooleanField(default=False)
    issuer = fields.CharField(max_length=500, default="")
    client_id = fields.CharField(max_length=255, default="")
    client_secret_encrypted = fields.TextField(null=True, default=None)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "sso_settings"

    @classmethod
    async def load(cls) -> "SsoSettings":
        """The saved settings, or unsaved defaults (SSO off) if none were saved yet."""
        row = await cls.filter(id=SINGLETON_ID).first()
        return row or cls(id=SINGLETON_ID)

    @property
    def is_usable(self) -> bool:
        return self.enabled and bool(self.issuer and self.client_id and self.client_secret_encrypted)
