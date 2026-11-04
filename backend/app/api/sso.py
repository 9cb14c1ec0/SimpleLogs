"""Sign in with an OpenID Connect provider (Authentik).

Only links existing accounts: the ID token's email must match a user here.
"""
import logging
from urllib.parse import urlencode

from authlib.integrations.starlette_client import OAuthError
from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import RedirectResponse

from app.models import SsoSettings, User
from app.services.auth import AuthService
from app.services.sso import get_client

logger = logging.getLogger(__name__)
router = APIRouter()


def _login_error(code: str) -> RedirectResponse:
    """Send the browser back to the login page with an error code it knows how to show."""
    return RedirectResponse(f"/login?sso_error={code}", status_code=status.HTTP_302_FOUND)


async def _usable_settings() -> SsoSettings:
    settings = await SsoSettings.load()
    if not settings.is_usable:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SSO is not set up")
    return settings


@router.get("/config")
async def sso_config():
    settings = await SsoSettings.load()
    return {"enabled": settings.is_usable}


@router.get("/login")
async def sso_login(request: Request):
    """Start the sign-in flow. Also used as the Authentik launch URL."""
    settings = await _usable_settings()
    redirect_uri = request.url_for("sso_callback")
    try:
        return await get_client(settings).authorize_redirect(request, redirect_uri)
    except Exception:
        logger.exception("Couldn't start SSO sign-in")
        return _login_error("failed")


@router.get("/callback", name="sso_callback")
async def sso_callback(request: Request):
    """Finish the flow: check state, nonce and ID token, then sign in the matching user."""
    settings = await _usable_settings()

    try:
        # Authlib checks state, exchanges the code with the PKCE verifier, and
        # validates the ID token signature (issuer JWKS), issuer, audience and nonce.
        token = await get_client(settings).authorize_access_token(request)
    except OAuthError as e:
        logger.warning("SSO callback rejected: %r", e)
        return _login_error("failed")
    except Exception:
        logger.exception("SSO token exchange or ID token check failed")
        return _login_error("failed")

    email = (token.get("userinfo") or {}).get("email")
    if not email:
        logger.warning("SSO ID token has no email claim")
        return _login_error("failed")

    user = await User.filter(email__iexact=email).first()
    if user is None:
        return _login_error("no_account")
    if not user.is_active:
        return _login_error("disabled")

    access_token, refresh_token = AuthService.create_tokens(str(user.id))
    # A URL fragment never reaches a server or its logs; the login page stores it and clears it.
    fragment = urlencode({"access_token": access_token, "refresh_token": refresh_token})
    return RedirectResponse(f"/login#{fragment}", status_code=status.HTTP_302_FOUND)
