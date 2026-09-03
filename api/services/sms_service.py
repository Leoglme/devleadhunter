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

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from core.config import settings
from enums.sms_status import SmsStatus
from models.prospect_db import ProspectDB
from models.sms_config import SmsConfig
from models.sms_message import SmsMessage
from models.sms_suppression import SmsSuppression
from services.activity_log_service import CATEGORY_SMS, STATUS_WARNING, activity_log_service
from services.notification_service import notification_service
from services.sms.gsm_segments import segment_count
from services.sms.phone_normalizer import is_mobile_fr, to_e164_fr
from services.sms.pricing import estimate_price_cents
from services.sms.send_window import is_within_window, next_send_slot, now_in_paris
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

    def legal_window_refusal(self) -> str | None:
        """Refusal reason when the current Paris time is outside the legal SMS window.

        Marketing SMS is only legal Mon–Fri 8h–20h, Sat 10h–19h, never Sunday or a
        French public holiday — a HARD guardrail, whatever the user configured.

        Returns:
            A human refusal naming the next legal slot, or ``None`` when a send may go out now.
        """
        now = now_in_paris()
        if is_within_window(now):
            return None
        slot = next_send_slot(now)
        return (
            "Hors de la fenêtre légale d'envoi SMS (lun–ven 8h–20h, sam 10h–19h, jamais dimanche ni jour férié). "
            f"Prochain créneau : {slot.strftime('%d/%m à %Hh%M')}."
        )

    def log_window_block(self, user_id: int, *, prospect_id: int | None = None, detail: str | None = None) -> None:
        """Record in the activity feed that a relance was blocked by the legal window.

        Args:
            user_id: Owner of the blocked send.
            prospect_id: Prospect the relance targeted, when known.
            detail: The refusal reason (names the next legal slot).
        """
        activity_log_service.record(
            category=CATEGORY_SMS,
            action="sms_window_blocked",
            status=STATUS_WARNING,
            title="Relance SMS bloquée · hors fenêtre légale d'envoi",
            detail=detail,
            user_id=user_id,
            entity_type="prospect" if prospect_id else None,
            entity_id=prospect_id,
        )

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
            config: The user's SMS config (sender).
            demo_url: Plain demo URL to push.
            greeting: Safe greeting for the body.

        Returns:
            The send outcome (``sent`` + reason when skipped).
        """
        # A configured sender is the single switch: no separate « enabled » flag.
        if not config.sender:
            return SmsSendOutcome(sent=False, reason="Expéditeur SMS non configuré")
        if not self._provider.is_configured:
            return SmsSendOutcome(sent=False, reason="smsmode non configuré")
        refusal = self.legal_window_refusal()
        if refusal:
            self.log_window_block(user_id, prospect_id=prospect.id, detail=refusal)
            return SmsSendOutcome(sent=False, reason=refusal)

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
            recipient_name=prospect.name,
            to_e164=to_e164,
            sender=config.sender,
            body=body,
            status=SmsStatus.PENDING.value,
            segments=segment_count(body),
        )
        return await self._send_and_log(db, message=message)

    def compose_manual_body(self, text: str) -> str:
        """Append the mandatory STOP mention to a free-text manual SMS (idempotent).

        Args:
            text: The body typed by the user.

        Returns:
            The body with the ``STOP au 36180`` mention appended once.
        """
        cleaned = (text or "").strip()
        if "36180" in cleaned:
            return cleaned
        return cleaned + _STOP_MENTION

    async def send_manual(
        self,
        db: Session,
        *,
        user_id: int,
        config: SmsConfig,
        to_raw: str,
        text: str,
        prospect_id: int | None = None,
        recipient_name: str | None = None,
    ) -> SmsSendOutcome:
        """Send one free-text SMS to a bare number (manual composer / self-test).

        Args:
            db: Active database session.
            user_id: Sender.
            config: The user's SMS config (sender).
            to_raw: Recipient number as typed (any French format).
            text: Free-text body (the STOP mention is appended automatically).
            prospect_id: Prospect id, when the number belongs to a saved prospect.
            recipient_name: Display label when there is no saved prospect.

        Returns:
            The send outcome (``sent`` + reason when skipped).
        """
        # A configured sender is the channel's only switch.
        if not config.sender:
            return SmsSendOutcome(sent=False, reason="Renseignez un nom d'expéditeur dans Paramètres → Relance SMS")
        if not self._provider.is_configured:
            return SmsSendOutcome(sent=False, reason="smsmode non configuré")
        # The legal window guards marketing to a saved prospect; a bare-number self-test stays free.
        if prospect_id is not None:
            refusal = self.legal_window_refusal()
            if refusal:
                self.log_window_block(user_id, prospect_id=prospect_id, detail=refusal)
                return SmsSendOutcome(sent=False, reason=refusal)

        to_e164 = to_e164_fr(to_raw)
        if not to_e164 or not is_mobile_fr(to_raw):
            return SmsSendOutcome(sent=False, reason="Numéro invalide : un mobile français 06/07 est requis")
        if self.is_suppressed(db, user_id, to_e164):
            return SmsSendOutcome(sent=False, reason="Numéro désinscrit (STOP)")
        body = self.compose_manual_body(text)
        if not body:
            return SmsSendOutcome(sent=False, reason="Message vide")

        message = SmsMessage(
            user_id=user_id,
            prospect_id=prospect_id,
            recipient_name=recipient_name,
            to_e164=to_e164,
            sender=config.sender,
            body=body,
            status=SmsStatus.PENDING.value,
            segments=segment_count(body),
        )
        return await self._send_and_log(db, message=message)

    async def _send_and_log(self, db: Session, *, message: SmsMessage) -> SmsSendOutcome:
        """Persist the row, hand it to the provider, record the outcome, notify.

        Args:
            db: Active database session.
            message: A ready-to-send SMS row (recipient, sender, body set).

        Returns:
            The send outcome.
        """
        db.add(message)
        db.commit()
        db.refresh(message)

        callback_url = f"{settings.api_base_url}/api/v1/sms/callbacks/dlr" if settings.api_base_url else None
        result: SmsSendResult = await self._provider.send(
            to_e164=message.to_e164,
            sender=message.sender,
            text=message.body,
            # smsmode requires refClient to be 3–140 chars, so a bare id ("1") is rejected.
            ref_client=f"dlh-{message.id}",
            callback_url=callback_url,
        )
        if result.success:
            message.status = SmsStatus.SENT.value
            message.provider_message_id = result.provider_message_id
            # smsmode returns no price for our account, so fall back to a segment-based estimate.
            message.price_cents = (
                result.price_cents if result.price_cents is not None else estimate_price_cents(message.segments)
            )
        else:
            message.status = SmsStatus.FAILED.value
            message.error = result.error
        db.commit()
        db.refresh(message)
        await self._notify_send(db, message, success=result.success)
        return SmsSendOutcome(sent=result.success, reason=result.error, message=message)

    async def _notify_send(self, db: Session, message: SmsMessage, *, success: bool) -> None:
        """Raise the send/failure notification for a just-sent SMS (best-effort).

        Args:
            db: Active database session.
            message: The persisted SMS row.
            success: Whether the provider accepted the send.
        """
        await notification_service.notify_sms_event(
            db,
            user_id=message.user_id,
            event_name="sms_sent" if success else "sms_failed",
            prospect_id=message.prospect_id,
            fallback_name=message.recipient_name or message.to_e164,
        )

    def list_messages(self, db: Session, user_id: int, *, limit: int = 500) -> list[tuple[SmsMessage, str | None]]:
        """Return the user's sent SMS (newest first) with the prospect name resolved.

        Args:
            db: Active database session.
            user_id: Owner.
            limit: Max rows to return.

        Returns:
            ``(message, prospect_name)`` pairs; the name is ``None`` for a manual send.
        """
        rows = db.execute(
            select(SmsMessage, ProspectDB.name)
            .join(ProspectDB, ProspectDB.id == SmsMessage.prospect_id, isouter=True)
            .where(SmsMessage.user_id == user_id)
            .order_by(SmsMessage.created_at.desc())
            .limit(limit)
        ).all()
        return [(row[0], row[1]) for row in rows]

    def stats(self, db: Session, user_id: int) -> dict[str, int]:
        """Aggregate counts + total cost of the user's SMS.

        Args:
            db: Active database session.
            user_id: Owner.

        Returns:
            Totals keyed by ``total``, ``sent``, ``delivered``, ``failed``, ``pending``, ``cost_cents``.
        """
        counts = dict(
            db.execute(
                select(SmsMessage.status, func.count()).where(SmsMessage.user_id == user_id).group_by(SmsMessage.status)
            ).all()
        )
        cost = db.execute(
            select(func.coalesce(func.sum(SmsMessage.price_cents), 0)).where(SmsMessage.user_id == user_id)
        ).scalar_one()
        sent = int(counts.get(SmsStatus.SENT.value, 0))
        delivered = int(counts.get(SmsStatus.DELIVERED.value, 0))
        # « Envoyés » counts everything that reached the provider (sent + later delivered).
        return {
            "total": sum(int(v) for v in counts.values()),
            "sent": sent + delivered,
            "delivered": delivered,
            "failed": int(counts.get(SmsStatus.FAILED.value, 0)),
            "pending": int(counts.get(SmsStatus.PENDING.value, 0)),
            "cost_cents": int(cost or 0),
        }


sms_service = SmsService()
