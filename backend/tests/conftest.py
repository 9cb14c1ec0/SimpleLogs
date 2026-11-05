import os

from cryptography.fernet import Fernet

# Settings are read once at import, so set them before the app loads.
os.environ.setdefault("TOTP_ENCRYPTION_KEY", Fernet.generate_key().decode())

import httpx2
import pytest
from tortoise import Tortoise

from app.main import app


@pytest.fixture
async def db():
    await Tortoise.init(
        db_url="sqlite://:memory:",
        modules={"models": ["app.models.user", "app.models.sso_settings"]},
    )
    await Tortoise.generate_schemas()
    yield
    await Tortoise.close_connections()


@pytest.fixture
async def client(db):
    transport = httpx2.ASGITransport(app=app)
    async with httpx2.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
