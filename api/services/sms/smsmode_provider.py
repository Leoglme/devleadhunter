"""smsmode implementation of :class:`SmsProvider` (REST API v1).

Contract confirmed against a production integration:
``POST https://rest.smsmode.com/sms/v1/messages`` with an ``X-Api-Key`` header
and body ``{recipient:{to}, body:{text}, from, refClient?, callbackUrlStatus?}``;
the response carries ``messageId`` and, when priced, ``price.amount`` (euros).
"""

from __future__ import annotations

import logging

import httpx

from core.config import settings

from .sms_provider import SmsProvider, SmsSendResult

logger = logging.getLogger(__name__)


class SmsModeProvider(SmsProvider):
    """Send SMS through the smsmode REST v1 API (single platform account)."""

    def __init__(self) -> None:
        """Load the platform API key and base URL from settings."""
        self._api_key: str = settings.smsmode_api_key
        self._base_url: str = settings.smsmode_base_url

    @property
    def is_configured(self) -> bool:
        """Whether a smsmode API key is available.

        Returns:
            ``True`` when a non-empty key is configured.
        """
        return bool(self._api_key)

    async def send(
        self,
        *,
        to_e164: str,
        sender: str,
        text: str,
        ref_client: str | None = None,
        callback_url: str | None = None,
    ) -> SmsSendResult:
        """Send one SMS through smsmode.

        Args:
            to_e164: Recipient in E.164 format.
            sender: Alphanumeric sender id.
            text: Message body.
            ref_client: Reference echoed back on the DLR callback.
            callback_url: Delivery-receipt callback URL.

        Returns:
            The send outcome, ``success=False`` on any transport or API error.
        """
        if not self.is_configured:
            return SmsSendResult(success=False, error="smsmode non configuré (SMSMODE_API_KEY absent)")

        payload: dict[str, object] = {
            "recipient": {"to": to_e164},
            "body": {"text": text},
            "from": sender,
        }
        if ref_client:
            payload["refClient"] = ref_client
        if callback_url:
            payload["callbackUrlStatus"] = callback_url

        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as client:
                response = await client.post(
                    self._base_url,
                    json=payload,
                    headers={"X-Api-Key": self._api_key, "Accept": "application/json"},
                )
        except httpx.HTTPError as exc:
            logger.error("[smsmode] transport error sending to %s: %s", to_e164, exc)
            return SmsSendResult(success=False, error=str(exc))

        if response.status_code >= 400:
            logger.error("[smsmode] %s sending to %s: %s", response.status_code, to_e164, response.text[:500])
            return SmsSendResult(success=False, error=f"{response.status_code}: {response.text[:200]}")

        try:
            data = response.json()
        except ValueError:
            return SmsSendResult(success=False, error="Réponse smsmode illisible")

        message_id = str(data.get("messageId") or "").strip()
        if not message_id:
            logger.warning("[smsmode] response without messageId for %s: %s", to_e164, response.text[:300])
            return SmsSendResult(success=False, error="Réponse smsmode sans messageId")

        price = data.get("price") if isinstance(data.get("price"), dict) else None
        price_cents: int | None = None
        if price is not None:
            try:
                price_cents = round(float(price.get("amount", 0)) * 100)
            except (TypeError, ValueError):
                price_cents = None
        return SmsSendResult(success=True, provider_message_id=message_id, price_cents=price_cents)


smsmode_provider = SmsModeProvider()
