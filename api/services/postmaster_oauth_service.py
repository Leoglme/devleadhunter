"""Google OAuth for Gmail Postmaster Tools (per-user, read-only).

Separate from Gmail sending OAuth: different scope, callback and stored tokens.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from urllib.parse import quote

import httpx

from core.config import settings

logger = logging.getLogger(__name__)

POSTMASTER_SCOPE: str = "https://www.googleapis.com/auth/postmaster.traffic.readonly"


class PostmasterOAuthService:
    """OAuth2 helper for the Postmaster Tools API."""

    def __init__(self) -> None:
        """Initialize with the shared Google OAuth client credentials."""
        self.client_id = settings.google_client_id
        self.client_secret = settings.google_client_secret
        self.redirect_uri = settings.google_postmaster_redirect_uri
        self.token_url = "https://oauth2.googleapis.com/token"

    @property
    def is_platform_configured(self) -> bool:
        """Whether the Google OAuth client is configured on the server.

        Returns:
            True when client id and secret are set.
        """
        return bool(self.client_id and self.client_secret)

    def get_authorization_url(self, state: str) -> str:
        """Build the Google consent URL for Postmaster read access.

        Args:
            state: CSRF token (``postmaster_user_<id>``).

        Returns:
            URL to redirect the browser to.
        """
        scope = quote(POSTMASTER_SCOPE, safe="")
        redirect = quote(self.redirect_uri, safe="")
        return (
            "https://accounts.google.com/o/oauth2/v2/auth?"
            f"client_id={self.client_id}&"
            f"redirect_uri={redirect}&"
            "response_type=code&"
            f"scope={scope}&"
            "access_type=offline&"
            "prompt=consent&"
            f"state={quote(state, safe='')}"
        )

    async def exchange_code_for_tokens(self, code: str) -> dict:
        """Exchange an authorization code for access and refresh tokens.

        Args:
            code: Authorization code from Google.

        Returns:
            Dict with access_token, optional refresh_token and expires_at.

        Raises:
            Exception: When the token exchange fails.
        """
        payload = {
            "code": code,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "redirect_uri": self.redirect_uri,
            "grant_type": "authorization_code",
        }
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(self.token_url, data=payload, timeout=30.0)
                response.raise_for_status()
                result = response.json()
        except httpx.HTTPStatusError as exc:
            logger.error("Postmaster OAuth token exchange failed: %s", exc.response.text)
            raise Exception(f"Failed to exchange code for tokens: {exc.response.text}") from exc

        expires_in = int(result.get("expires_in", 3600))
        return {
            "access_token": result.get("access_token"),
            "refresh_token": result.get("refresh_token"),
            "expires_at": datetime.utcnow() + timedelta(seconds=expires_in),
            "token_type": result.get("token_type"),
        }

    async def refresh_access_token(self, refresh_token: str) -> dict:
        """Refresh an expired access token.

        Args:
            refresh_token: Stored refresh token.

        Returns:
            Dict with access_token and expires_at.

        Raises:
            Exception: When refresh fails (token revoked, app in testing mode, etc.).
        """
        payload = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(self.token_url, data=payload, timeout=30.0)
                response.raise_for_status()
                result = response.json()
        except httpx.HTTPStatusError as exc:
            logger.error("Postmaster OAuth refresh failed: %s", exc.response.text)
            raise Exception(f"Failed to refresh token: {exc.response.text}") from exc

        expires_in = int(result.get("expires_in", 3600))
        return {
            "access_token": result.get("access_token"),
            "expires_at": datetime.utcnow() + timedelta(seconds=expires_in),
            "token_type": result.get("token_type"),
        }

    async def get_user_info(self, access_token: str) -> dict:
        """Fetch the Google account profile for the connected user.

        Args:
            access_token: Valid access token.

        Returns:
            Google userinfo payload (email, verified_email, name, …).
        """
        headers = {"Authorization": f"Bearer {access_token}"}
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers=headers,
                timeout=30.0,
            )
            response.raise_for_status()
            return response.json()
