from tortoise import fields
from tortoise.models import Model


class WebAuthnChallenge(Model):
    id = fields.UUIDField(pk=True)
    challenge_key = fields.CharField(max_length=255, unique=True)
    challenge = fields.BinaryField()
    expires_at = fields.DatetimeField()

    class Meta:
        table = "webauthn_challenges"
