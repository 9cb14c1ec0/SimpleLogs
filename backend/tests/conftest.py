import os

# Settings are read once at import, so SSO must be configured before the app loads.
os.environ.setdefault("OIDC_ISSUER", "https://sso.example.test/application/o/simplelogs/")
os.environ.setdefault("OIDC_CLIENT_ID", "test-client")
os.environ.setdefault("OIDC_CLIENT_SECRET", "test-secret")

import pytest
from tortoise import Tortoise


@pytest.fixture
async def db():
    await Tortoise.init(db_url="sqlite://:memory:", modules={"models": ["app.models.user"]})
    await Tortoise.generate_schemas()
    yield
    await Tortoise.close_connections()
