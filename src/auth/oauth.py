from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class OAuthConfig:
    """OAuth configuration for a provider."""

    client_id: str
    client_secret: str
    redirect_uri: str
    scope: list[str]


class GoogleOAuth:
    """Google OAuth handler."""

    AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
    TOKEN_URL = "https://oauth2.googleapis.com/token"

    def __init__(self, config: OAuthConfig) -> None:
        self.config = config

    def get_auth_url(self, state: str | None = None) -> str:
        """Generate the authorization URL."""
        params = {
            "client_id": self.config.client_id,
            "redirect_uri": self.config.redirect_uri,
            "response_type": "code",
            "scope": " ".join(self.config.scope),
        }
        if state:
            params["state"] = state

        from urllib.parse import urlencode

        return f"{self.AUTH_URL}?{urlencode(params)}"

    async def exchange_code(self, code: str) -> dict[str, Any]:
        """Exchange authorization code for tokens."""
        import httpx

        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.TOKEN_URL,
                data={
                    "client_id": self.config.client_id,
                    "client_secret": self.config.client_secret,
                    "code": code,
                    "redirect_uri": self.config.redirect_uri,
                    "grant_type": "authorization_code",
                },
            )
            response.raise_for_status()
            return response.json()


class MicrosoftOAuth:
    """Microsoft OAuth handler."""

    AUTH_URL = "https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/authorize"
    TOKEN_URL = "https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"

    def __init__(self, config: OAuthConfig, tenant_id: str = "common") -> None:
        self.config = config
        self.tenant_id = tenant_id

    def get_auth_url(self, state: str | None = None) -> str:
        """Generate the authorization URL."""
        auth_url = self.AUTH_URL.format(tenant_id=self.tenant_id)
        params = {
            "client_id": self.config.client_id,
            "redirect_uri": self.config.redirect_uri,
            "response_type": "code",
            "scope": " ".join(self.config.scope),
        }
        if state:
            params["state"] = state

        from urllib.parse import urlencode

        return f"{auth_url}?{urlencode(params)}"

    async def exchange_code(self, code: str) -> dict[str, Any]:
        """Exchange authorization code for tokens."""
        import httpx

        token_url = self.TOKEN_URL.format(tenant_id=self.tenant_id)

        async with httpx.AsyncClient() as client:
            response = await client.post(
                token_url,
                data={
                    "client_id": self.config.client_id,
                    "client_secret": self.config.client_secret,
                    "code": code,
                    "redirect_uri": self.config.redirect_uri,
                    "grant_type": "authorization_code",
                },
            )
            response.raise_for_status()
            return response.json()
