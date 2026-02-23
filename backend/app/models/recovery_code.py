import bcrypt
from tortoise import fields
from tortoise.models import Model


class RecoveryCode(Model):
    id = fields.UUIDField(pk=True)
    user = fields.ForeignKeyField("models.User", related_name="recovery_codes", on_delete=fields.CASCADE)
    code_hash = fields.CharField(max_length=255)
    used = fields.BooleanField(default=False)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "recovery_codes"

    def verify_code(self, code: str) -> bool:
        """Check a plaintext recovery code against the stored hash."""
        return bcrypt.checkpw(code.encode(), self.code_hash.encode())
