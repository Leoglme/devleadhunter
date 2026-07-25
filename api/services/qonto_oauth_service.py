"""Qonto OAuth 2.0 service — connect a user's Qonto organization for invoicing.

Mirrors ``GmailOAuthService``: build the authorization URL, exchange the code,
refresh the access token. Two Qonto specifics are baked in here:

* Access tokens live one hour; refresh tokens live 90 days and are **one-time
  use** — every refresh invalidates the token used and returns a *new*
  ``refresh_token`` that must be persisted. ``refresh_access_token`` therefore
  always returns the rotated refresh token alongside the new access token.
* The OAuth endpoints are the same for sandbox and production; the environment
  only differs on the API calls (via the staging-token header), not here.
"""

import logging
from datetime import datetime, timedelta

import httpx

from core.config import settings

logger = logging.getLogger(__name__)

# Scopes registered for the "Automate your business operations" app. No
# organization.read (sensitive scope): the IBAN is captured manually instead.
QONTO_OAUTH_SCOPES: str = (
    "offline_access client.read client.write "
    "client_invoice.write client_invoices.read attachment.read "
    "payment_link.read payment_link.write"
)

_AUTHORIZE_URL = "https://oauth.qonto.com/oauth2/auth"
_TOKEN_URL = "https://oauth.qonto.com/oauth2/token"


class QontoOAuthService:
    """OAuth 2.0 client for the Qonto Business API."""

    def __init__(self) -> None:
        """Initialize the Qonto OAuth service from settings."""
        self.client_id = settings.qonto_client_id
        self.client_secret = settings.qonto_client_secret
        self.redirect_uri = settings.qonto_redirect_uri

    def get_authorization_url(self, state: str) -> str:
        """
        Build the Qonto authorization URL to redirect the user to.

        Args:
            state: Opaque CSRF/identity value echoed back on the callback.

        Returns:
            The authorization URL.
        """
        query = httpx.QueryParams(
            {
                "client_id": self.client_id,
                "redirect_uri": self.redirect_uri,
                "response_type": "code",
                "scope": QONTO_OAUTH_SCOPES,
                "state": state,
            }
        )
        return f"{_AUTHORIZE_URL}?{query}"

    async def exchange_code_for_tokens(self, code: str) -> dict:
        """
        Exchange an authorization code for access and refresh tokens.

        Args:
            code: Authorization code returned on the callback.

        Returns:
            Dict with ``access_token``, ``refresh_token`` and ``expires_at``.

        Raises:
            Exception: If the token exchange fails.
        """
        payload = {
            "grant_type": "authorization_code",
            "code": code,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "redirect_uri": self.redirect_uri,
        }
        return await self._post_token(payload)

    async def refresh_access_token(self, refresh_token: str) -> dict:
        """
        Refresh an expired access token, rotating the refresh token.

        Qonto refresh tokens are one-time use: the returned ``refresh_token``
        replaces the one passed in and must be persisted immediately.

        Args:
            refresh_token: The currently stored refresh token.

        Returns:
            Dict with the new ``access_token``, ``refresh_token`` and ``expires_at``.

        Raises:
            Exception: If the refresh fails.
        """
        payload = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }
        return await self._post_token(payload)

    async def _post_token(self, payload: dict) -> dict:
        """
        POST to the token endpoint and normalize the response.

        Args:
            payload: Form-encoded token request body.

        Returns:
            Dict with ``access_token``, ``refresh_token`` and ``expires_at``.

        Raises:
            Exception: If the request fails.
        """
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(_TOKEN_URL, data=payload, headers=headers, timeout=30.0)
                response.raise_for_status()
                result = response.json()

                expires_in = result.get("expires_in", 3600)
                expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
                return {
                    "access_token": result.get("access_token"),
                    "refresh_token": result.get("refresh_token"),
                    "expires_at": expires_at,
                }
        except httpx.HTTPStatusError as error:
            logger.error("Qonto OAuth error: %s", error.response.text)
            raise Exception(f"Qonto token request failed: {error.response.text}")
        except Exception as error:
            logger.error("Error during Qonto token request: %s", error)
            raise
