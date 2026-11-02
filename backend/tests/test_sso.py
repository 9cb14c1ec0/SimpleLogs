from unittest.mock import AsyncMock, patch
from urllib.parse import parse_qs, urlparse

import httpx2
import pytest
from joserfc.errors import BadSignatureError

from app.api import sso
from app.main import app
from app.models import User
from app.services.auth import AuthService

CALLBACK_URL = "/api/v1/auth/sso/callback?code=abc&state=xyz"


@pytest.fixture
async def client(db):
    transport = httpx2.ASGITransport(app=app)
    async with httpx2.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def make_user(email: str, is_active: bool = True) -> User:
    user = User(email=email, name="Staff", is_active=is_active)
    user.set_password("pw")
    await user.save()
    return user


def provider_returns_email(email: str):
    token = {"access_token": "at", "id_token": "it", "userinfo": {"email": email}}
    return patch.object(sso.oauth.authentik, "authorize_access_token", AsyncMock(return_value=token))


async def test_login_redirects_with_pkce_and_nonce(client):
    metadata = {"authorization_endpoint": "https://sso.example.test/application/o/authorize/"}

    with patch.object(sso.oauth.authentik, "load_server_metadata", AsyncMock(return_value=metadata)):
        response = await client.get("/api/v1/auth/sso/login")

    assert response.status_code == 302
    location = urlparse(response.headers["location"])
    params = parse_qs(location.query)
    assert location.netloc == "sso.example.test"
    assert params["redirect_uri"] == ["http://test/api/v1/auth/sso/callback"]
    assert params["code_challenge_method"] == ["S256"]
    assert params["code_challenge"] and params["nonce"] and params["state"]
    assert "simplelogs_sso" in response.cookies


async def test_matching_email_signs_in(client):
    user = await make_user("staff@example.com")

    with provider_returns_email("Staff@Example.COM"):
        response = await client.get(CALLBACK_URL)

    assert response.status_code == 302
    location = urlparse(response.headers["location"])
    assert location.path == "/login"
    tokens = parse_qs(location.fragment)
    access = AuthService.decode_token(tokens["access_token"][0])
    refresh = AuthService.decode_token(tokens["refresh_token"][0])
    assert access.type == "access" and access.sub == str(user.id)
    assert refresh.type == "refresh" and refresh.sub == str(user.id)


async def test_unknown_email_is_rejected(client):
    await make_user("staff@example.com")

    with provider_returns_email("someone-else@example.com"):
        response = await client.get(CALLBACK_URL)

    assert response.status_code == 302
    assert response.headers["location"] == "/login?sso_error=no_account"


async def test_disabled_user_is_rejected(client):
    await make_user("staff@example.com", is_active=False)

    with provider_returns_email("staff@example.com"):
        response = await client.get(CALLBACK_URL)

    assert response.status_code == 302
    assert response.headers["location"] == "/login?sso_error=disabled"


async def test_bad_id_token_signature_is_rejected(client):
    await make_user("staff@example.com")
    failing = AsyncMock(side_effect=BadSignatureError())

    with patch.object(sso.oauth.authentik, "authorize_access_token", failing):
        response = await client.get(CALLBACK_URL)

    assert response.status_code == 302
    assert response.headers["location"] == "/login?sso_error=failed"


async def test_state_without_a_started_login_is_rejected(client):
    # Real Authlib check: no session holds this state, so no token exchange happens.
    await make_user("staff@example.com")

    response = await client.get(CALLBACK_URL)

    assert response.status_code == 302
    assert response.headers["location"] == "/login?sso_error=failed"
