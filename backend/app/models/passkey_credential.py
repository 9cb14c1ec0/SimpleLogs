from tortoise import fields
from tortoise.models import Model


class PasskeyCredential(Model):
    id = fields.UUIDField(pk=True)
    user = fields.ForeignKeyField("models.User", related_name="passkey_credentials", on_delete=fields.CASCADE)
    credential_id = fields.BinaryField(unique=True)
    public_key = fields.BinaryField()
    sign_count = fields.BigIntField(default=0)
    transports = fields.TextField(null=True, default=None)
    name = fields.CharField(max_length=255, default="Passkey")
    created_at = fields.DatetimeField(auto_now_add=True)
    last_used_at = fields.DatetimeField(null=True, default=None)

    class Meta:
        table = "passkey_credentials"
