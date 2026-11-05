import httpx2
from authlib.integrations.starlette_client import OAuth, StarletteOAuth2App

from app.models import SsoSettings
from app.services.totp import TOTPService


def discovery_url(issuer: str) -> str:
    return issuer.rstrip("/") + "/.well-known/openid-configuration"


async def fetch_provider_metadata(issuer: str) -> dict:
    """Load the issuer's OpenID configuration. Raises ValueError if it can't be used."""
    try:
        async with httpx2.AsyncClient(timeout=10) as client:
            response = await client.get(discovery_url(issuer))
            response.raise_for_status()
            metadata = response.json()
    except Exception as e:
        raise ValueError(f"Couldn't load the OpenID configuration from {discovery_url(issuer)}") from e

    if not isinstance(metadata, dict) or "authorization_endpoint" not in metadata:
        raise ValueError(f"{discovery_url(issuer)} isn't an OpenID configuration")
    return metadata


# One Authlib client per distinct config, so its metadata and JWKS stay cached
# between requests. Keyed by the saved values, so a settings change takes effect at once.
_client_cache: dict[tuple[str, str, str], StarletteOAuth2App] = {}


def get_client(settings: SsoSettings) -> StarletteOAuth2App:
    client_secret = TOTPService.decrypt_secret(settings.client_secret_encrypted)
    key = (settings.issuer, settings.client_id, client_secret)

    client = _client_cache.get(key)
    if client is None:
        oauth = OAuth()
        client = oauth.register(
            name="sso",
            client_id=settings.client_id,
            client_secret=client_secret,
            server_metadata_url=discovery_url(settings.issuer),
            client_kwargs={"scope": "openid email profile", "code_challenge_method": "S256"},
        )
        _client_cache.clear()
        _client_cache[key] = client
    return client
