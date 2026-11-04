from pydantic import BaseModel


class SsoSettingsResponse(BaseModel):
    enabled: bool
    issuer: str
    client_id: str
    has_client_secret: bool
    # What to enter in the provider
    redirect_uri: str
    launch_url: str


class SsoSettingsUpdate(BaseModel):
    enabled: bool
    issuer: str
    client_id: str
    # Empty keeps the saved secret
    client_secret: str | None = None
