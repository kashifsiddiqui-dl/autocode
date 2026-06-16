"""Azure AD OIDC integration via authlib."""

from __future__ import annotations

import logging
from typing import Any

import httpx
from authlib.integrations.httpx_client import AsyncOAuth2Client
from authlib.jose import jwt as authlib_jwt
from authlib.oidc.core import JsonWebKey

from app.config import settings
from app.core.exceptions import ExternalServiceError, UnauthorizedError

logger = logging.getLogger(__name__)

_AZURE_BASE = "https://login.microsoftonline.com"


class AzureADProvider:
    """Handles Azure AD OIDC authorisation code flow."""

    def __init__(self) -> None:
        self.tenant_id = settings.AZURE_AD_TENANT_ID
        self.client_id = settings.AZURE_AD_CLIENT_ID
        self.client_secret = settings.AZURE_AD_CLIENT_SECRET
        self._oidc_config: dict[str, Any] | None = None
        self._jwks: dict[str, Any] | None = None

    @property
    def _authority(self) -> str:
        return f"{_AZURE_BASE}/{self.tenant_id}"

    @property
    def _openid_config_url(self) -> str:
        return f"{self._authority}/v2.0/.well-known/openid-configuration"

    async def _fetch_oidc_config(self) -> dict[str, Any]:
        if self._oidc_config is not None:
            return self._oidc_config
        async with httpx.AsyncClient() as client:
            resp = await client.get(self._openid_config_url, timeout=10)
            resp.raise_for_status()
            self._oidc_config = resp.json()
            return self._oidc_config

    async def _fetch_jwks(self) -> dict[str, Any]:
        if self._jwks is not None:
            return self._jwks
        config = await self._fetch_oidc_config()
        async with httpx.AsyncClient() as client:
            resp = await client.get(config["jwks_uri"], timeout=10)
            resp.raise_for_status()
            self._jwks = resp.json()
            return self._jwks

    async def get_authorization_url(
        self,
        tenant_slug: str,
        redirect_uri: str,
        state: str | None = None,
    ) -> str:
        """Build the Azure AD authorisation URL."""
        config = await self._fetch_oidc_config()
        oauth = AsyncOAuth2Client(
            client_id=self.client_id,
            client_secret=self.client_secret,
            scope="openid email profile",
            redirect_uri=redirect_uri,
        )
        url, _state = oauth.create_authorization_url(
            config["authorization_endpoint"],
            state=state or tenant_slug,
        )
        return url

    async def handle_callback(
        self,
        code: str,
        redirect_uri: str,
    ) -> dict[str, Any]:
        """Exchange the authorisation code for user info.

        Returns a dict with keys: sub, email, name, oid (Azure object ID).
        """
        config = await self._fetch_oidc_config()
        try:
            oauth = AsyncOAuth2Client(
                client_id=self.client_id,
                client_secret=self.client_secret,
                redirect_uri=redirect_uri,
            )
            token_resp = await oauth.fetch_token(
                config["token_endpoint"],
                code=code,
                grant_type="authorization_code",
            )
        except Exception as exc:
            logger.exception("Azure AD token exchange failed")
            raise ExternalServiceError("Failed to exchange authorisation code.") from exc

        id_token = token_resp.get("id_token")
        if not id_token:
            raise UnauthorizedError("No id_token returned from Azure AD.")

        jwks = await self._fetch_jwks()
        try:
            claims = authlib_jwt.decode(
                id_token,
                JsonWebKey.import_key_set(jwks),
            )
            claims.validate()
        except Exception as exc:
            logger.exception("Azure AD id_token validation failed")
            raise UnauthorizedError("Invalid id_token.") from exc

        return {
            "sub": claims.get("sub"),
            "email": claims.get("email") or claims.get("preferred_username"),
            "name": claims.get("name", ""),
            "oid": claims.get("oid"),
        }


azure_ad_provider = AzureADProvider()
