from tortoise import fields
from tortoise.models import Model


class TotpAttempt(Model):
    id = fields.UUIDField(pk=True)
    jti = fields.CharField(max_length=36, index=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "totp_attempts"
