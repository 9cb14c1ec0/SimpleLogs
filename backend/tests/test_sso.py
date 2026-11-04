from unittest.mock import AsyncMock, patch
from urllib.parse import parse_qs, urlparse

import pytest
from authlib.integrations.starlette_client import StarletteOAuth2App
from joserfc.errors import BadSignatureError

from app.models import SsoSettings, User
from app.services.auth import AuthService
from app.services.totp import TOTPService

CALLBACK_URL = "/api/v1/auth/sso/callback?code=abc&state=xyz"


@pytest.fixture
async def sso_on(db):
    await SsoSettings.create(
        id=1,
        enabled=True,
        issuer="https://sso.example.test/application/o/simplelogs/",
        client_id="test-client",
        client_secret_encrypted=TOTPService.encrypt_secret("test-secret"),
    )


async def make_user(email: str, is_active: bool = True) -> User:
    user = User(email=email, name="Staff", is_active=is_active)
    user.set_password("pw")
    await user.save()
    return user


def provider_returns_email(email: str):
    token = {"access_token": "at", "id_token": "it", "userinfo": {"email": email}}
    return patch.object(StarletteOAuth2App, "authorize_access_token", AsyncMock(return_value=token))


async def test_sso_is_off_until_set_up(client):
    response = await client.get("/api/v1/auth/sso/config")
    assert response.json() == {"enabled": False}

    response = await client.get("/api/v1/auth/sso/login")
    assert response.status_code == 404


async def test_login_redirects_with_pkce_and_nonce(client, sso_on):
    metadata = {"authorization_endpoint": "https://sso.example.test/application/o/authorize/"}

    with patch.object(StarletteOAuth2App, "load_server_metadata", AsyncMock(return_value=metadata)):
        response = await client.get("/api/v1/auth/sso/login")

    assert response.status_code == 302
    location = urlparse(response.headers["location"])
    params = parse_qs(location.query)
    assert location.netloc == "sso.example.test"
    assert params["client_id"] == ["test-client"]
    assert params["redirect_uri"] == ["http://test/api/v1/auth/sso/callback"]
    assert params["code_challenge_method"] == ["S256"]
    assert params["code_challenge"] and params["nonce"] and params["state"]
    assert "simplelogs_sso" in response.cookies


async def test_matching_email_signs_in(client, sso_on):
    user = await make_user("staff@example.com")

    with provider_returns_email("Staff@Example.COM"):
        response = await client.get(CALLBACK_URL)

    assert response.status_code == 302
    location = urlparse(response.headers["location"])
    assert location.path == "/login"
    tokens = parse_qs(location.fragment)
    access = AuthService.decode_token(tokens["access_token"][0])
    refresh = AuthService.decode_token(tokens["refresh_token"][0])
    assert access is not None and access.type == "access" and access.sub == str(user.id)
    assert refresh is not None and refresh.type == "refresh" and refresh.sub == str(user.id)


async def test_unknown_email_is_rejected(client, sso_on):
    await make_user("staff@example.com")

    with provider_returns_email("someone-else@example.com"):
        response = await client.get(CALLBACK_URL)

    assert response.status_code == 302
    assert response.headers["location"] == "/login?sso_error=no_account"


async def test_disabled_user_is_rejected(client, sso_on):
    await make_user("staff@example.com", is_active=False)

    with provider_returns_email("staff@example.com"):
        response = await client.get(CALLBACK_URL)

    assert response.status_code == 302
    assert response.headers["location"] == "/login?sso_error=disabled"


async def test_bad_id_token_signature_is_rejected(client, sso_on):
    await make_user("staff@example.com")
    failing = AsyncMock(side_effect=BadSignatureError())

    with patch.object(StarletteOAuth2App, "authorize_access_token", failing):
        response = await client.get(CALLBACK_URL)

    assert response.status_code == 302
    assert response.headers["location"] == "/login?sso_error=failed"


async def test_state_without_a_started_login_is_rejected(client, sso_on):
    # Real Authlib check: no session holds this state, so no token exchange happens.
    await make_user("staff@example.com")

    response = await client.get(CALLBACK_URL)

    assert response.status_code == 302
    assert response.headers["location"] == "/login?sso_error=failed"


# ============== Admin settings ==============

ISSUER = "https://sso.example.test/application/o/simplelogs/"
PROVIDER_OK = patch(
    "app.api.admin.fetch_provider_metadata",
    AsyncMock(return_value={"authorization_endpoint": "x"}),
)


async def auth_headers(is_admin: bool) -> dict:
    user = User(email=f"{'admin' if is_admin else 'user'}@example.com", name="A", is_admin=is_admin)
    user.set_password("pw")
    await user.save()
    return {"Authorization": f"Bearer {AuthService.create_access_token(str(user.id))}"}


async def test_admin_saves_settings_and_secret_is_encrypted(client):
    headers = await auth_headers(is_admin=True)
    body = {"enabled": True, "issuer": ISSUER, "client_id": "cid", "client_secret": "s3cret"}

    with PROVIDER_OK:
        response = await client.put("/api/v1/admin/sso", json=body, headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert data["has_client_secret"] is True and "client_secret" not in data
    assert data["redirect_uri"] == "http://test/api/v1/auth/sso/callback"
    assert data["launch_url"] == "http://test/api/v1/auth/sso/login"

    saved = await SsoSettings.load()
    assert saved.client_secret_encrypted != "s3cret"
    assert TOTPService.decrypt_secret(saved.client_secret_encrypted) == "s3cret"
    assert (await client.get("/api/v1/auth/sso/config")).json() == {"enabled": True}


async def test_blank_secret_keeps_the_saved_one(client, sso_on):
    headers = await auth_headers(is_admin=True)
    body = {"enabled": True, "issuer": ISSUER, "client_id": "new-client", "client_secret": ""}

    with PROVIDER_OK:
        response = await client.put("/api/v1/admin/sso", json=body, headers=headers)

    assert response.status_code == 200
    saved = await SsoSettings.load()
    assert saved.client_id == "new-client"
    assert TOTPService.decrypt_secret(saved.client_secret_encrypted) == "test-secret"


async def test_unreachable_issuer_is_not_saved(client):
    headers = await auth_headers(is_admin=True)
    body = {"enabled": True, "issuer": "https://nowhere.invalid/", "client_id": "cid", "client_secret": "s"}
    failing = AsyncMock(side_effect=ValueError("Couldn't load the OpenID configuration"))

    with patch("app.api.admin.fetch_provider_metadata", failing):
        response = await client.put("/api/v1/admin/sso", json=body, headers=headers)

    assert response.status_code == 400
    assert (await SsoSettings.load()).enabled is False


async def test_non_admin_cannot_change_settings(client):
    headers = await auth_headers(is_admin=False)
    body = {"enabled": False, "issuer": "", "client_id": ""}

    response = await client.put("/api/v1/admin/sso", json=body, headers=headers)

    assert response.status_code == 403
