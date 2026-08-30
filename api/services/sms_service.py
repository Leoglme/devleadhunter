"""SMS orchestration — normalise, guard, send, log.

Sends ONE relance SMS to a prospect: normalise the number to E.164, verify it is
a mobile, honour the per-user STOP suppression list, send through the configured
provider, and log the outcome. The legal send window is enforced by the caller
(the queue) and re-checked here as a hard backstop. The body carries the plain
demo URL (never a shortened link — French operators filter those) and always the
mandatory « STOP au 36180 » opt-out mention.
"""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from core.config import settings
from enums.sms_status import SmsStatus
from models.prospect_db import ProspectDB
from models.sms_config import SmsConfig
from models.sms_message import SmsMessage
from models.sms_suppression import SmsSuppression
from services.sms.gsm_segments import segment_count
from services.sms.phone_normalizer import is_mobile_fr, to_e164_fr
from services.sms.sms_provider import SmsProvider, SmsSendResult
from services.sms.smsmode_provider import smsmode_provider

logger = logging.getLogger(__name__)

# Mandatory opt-out mention appended to every marketing SMS (36180 = the free
# French STOP short code operators route back to the provider).
_STOP_MENTION: str = " STOP au 36180"


class SmsSendOutcome:
    """Result of a prospect-level send attempt (thin wrapper for the route)."""

    def __init__(self, *, sent: bool, reason: str | None = None, message: SmsMessage | None = None) -> None:
        self.sent = sent
        self.reason = reason
        self.message = message


class SmsService:
    """Send relance SMS and manage the STOP suppression list."""

    def __init__(self, provider: SmsProvider | None = None) -> None:
        """Bind the SMS provider (defaults to smsmode)."""
        self._provider: SmsProvider = provider or smsmode_provider

    def is_suppressed(self, db: Session, user_id: int, phone_e164: str) -> bool:
        """Whether *phone_e164* opted out of this user's SMS.

        Args:
            db: Active database session.
            user_id: Sender.
            phone_e164: Normalised number.

        Returns:
            ``True`` when the number is on the user's STOP list.
        """
        return (
            db.query(SmsSuppression.id)
            .filter(SmsSuppression.user_id == user_id, SmsSuppression.phone_e164 == phone_e164)
            .first()
            is not None
        )

    def suppress(self, db: Session, user_id: int, phone_e164: str, *, reason: str = "stop") -> None:
        """Add a number to the user's STOP list (idempotent).

        Args:
            db: Active database session.
            user_id: Sender.
            phone_e164: Normalised number to suppress.
            reason: ``stop`` (opt-out reply) or ``manual``.
        """
        if not phone_e164 or self.is_suppressed(db, user_id, phone_e164):
            return
        db.add(SmsSuppression(user_id=user_id, phone_e164=phone_e164, reason=reason))
        db.commit()
        logger.info("SMS suppression added for user %s (%s)", user_id, reason)

    def compose_body(self, *, greeting: str, business_name: str, sender: str, demo_url: str) -> str:
        """Build a sober one-segment relance body with the mandatory STOP mention.

        Args:
            greeting: Safe greeting (``Bonjour`` / ``Bonjour Prénom``).
            business_name: Prospect's business name.
            sender: The user's sender id, signed at the end.
            demo_url: Plain demo URL (no shortener).

        Returns:
            The message body.
        """
        core = (
            f"{greeting}, je vous ai envoye par email un apercu de site web pour {business_name} : "
            f"{demo_url} — {sender}."
        )
        return core + _STOP_MENTION

    async def send_to_prospect(
        self,
        db: Session,
        *,
        user_id: int,
        prospect: ProspectDB,
        config: SmsConfig,
        demo_url: str,
        greeting: str,
    ) -> SmsSendOutcome:
        """Send one relance SMS to *prospect*, logging the outcome.

        Args:
            db: Active database session.
            user_id: Sender.
            prospect: Recipient prospect.
            config: The user's SMS config (sender + enabled).
            demo_url: Plain demo URL to push.
            greeting: Safe greeting for the body.

        Returns:
            The send outcome (``sent`` + reason when skipped).
        """
        if not config.enabled or not config.sender:
            return SmsSendOutcome(sent=False, reason="Canal SMS non configuré")
        if not self._provider.is_configured:
            return SmsSendOutcome(sent=False, reason="smsmode non configuré")

        to_e164 = to_e164_fr(prospect.phone)
        if not to_e164 or not is_mobile_fr(prospect.phone):
            return SmsSendOutcome(sent=False, reason="Pas de mobile 06/07 pour ce prospect")
        if self.is_suppressed(db, user_id, to_e164):
            return SmsSendOutcome(sent=False, reason="Numéro désinscrit (STOP)")

        body = self.compose_body(
            greeting=greeting,
            business_name=prospect.name or "votre entreprise",
            sender=config.sender,
            demo_url=demo_url,
        )
        message = SmsMessage(
            user_id=user_id,
            prospect_id=prospect.id,
            to_e164=to_e164,
            sender=config.sender,
            body=body,
            status=SmsStatus.PENDING.value,
            segments=segment_count(body),
        )
        db.add(message)
        db.commit()
        db.refresh(message)

        callback_url = f"{settings.api_base_url}/api/v1/sms/callbacks/dlr" if settings.api_base_url else None
        result: SmsSendResult = await self._provider.send(
            to_e164=to_e164,
            sender=config.sender,
            text=body,
            ref_client=str(message.id),
            callback_url=callback_url,
        )
        if result.success:
            message.status = SmsStatus.SENT.value
            message.provider_message_id = result.provider_message_id
            message.price_cents = result.price_cents
        else:
            message.status = SmsStatus.FAILED.value
            message.error = result.error
        db.commit()
        db.refresh(message)
        return SmsSendOutcome(sent=result.success, reason=result.error, message=message)


sms_service = SmsService()
