"""Sign in with an OpenID Connect provider (Authentik).

Only links existing accounts: the ID token's email must match a user here.
"""
import logging
from urllib.parse import urlencode

from authlib.integrations.starlette_client import OAuth, OAuthError
from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import RedirectResponse

from app.config import get_settings
from app.models import User
from app.services.auth import AuthService

logger = logging.getLogger(__name__)
settings = get_settings()
router = APIRouter()


def sso_enabled() -> bool:
    return bool(settings.oidc_issuer and settings.oidc_client_id and settings.oidc_client_secret)


oauth = OAuth()
if sso_enabled():
    oauth.register(
        name="authentik",
        client_id=settings.oidc_client_id,
        client_secret=settings.oidc_client_secret,
        server_metadata_url=settings.oidc_issuer.rstrip("/") + "/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile", "code_challenge_method": "S256"},
    )


def _login_error(code: str) -> RedirectResponse:
    """Send the browser back to the login page with an error code it knows how to show."""
    return RedirectResponse(f"/login?sso_error={code}", status_code=status.HTTP_302_FOUND)


@router.get("/config")
async def sso_config():
    return {"enabled": sso_enabled()}


@router.get("/login")
async def sso_login(request: Request):
    """Start the sign-in flow. Also used as the Authentik launch URL."""
    if not sso_enabled():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SSO is not configured")

    redirect_uri = request.url_for("sso_callback")
    return await oauth.authentik.authorize_redirect(request, redirect_uri)


@router.get("/callback", name="sso_callback")
async def sso_callback(request: Request):
    """Finish the flow: check state, nonce and ID token, then sign in the matching user."""
    if not sso_enabled():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SSO is not configured")

    try:
        # Authlib checks state, exchanges the code with the PKCE verifier, and
        # validates the ID token signature (issuer JWKS), issuer, audience and nonce.
        token = await oauth.authentik.authorize_access_token(request)
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
