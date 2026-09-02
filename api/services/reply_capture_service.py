"""
Reply capture — link inbound emails on the Resend receiving domain back to sends.

Outreach emails carry ``Reply-To: reply-<email_log_id>-<sig>@REPLY_CAPTURE_DOMAIN``.
When the prospect replies, Resend receives it (MX on the capture domain) and fires
``email.received``; the token in the ``to`` address identifies the exact send. The
signature (truncated HMAC of the id under ``SECRET_KEY``) rejects forged or
mistyped addresses — the receiving domain is a catch-all, so anything can be sent
to it. Replies without a token (prospect wrote a fresh email to the address book
entry) fall back to matching the sender address against past sends.

The webhook payload carries metadata only; body and headers are fetched from the
Resend Receiving API with the platform key (the capture domain lives on the
platform account).
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import re
from datetime import UTC, datetime
from email.utils import parseaddr
from typing import Any

import aiohttp
from sqlalchemy import select
from sqlalchemy.orm import Session

from core.config import settings
from enums.email_status import EmailStatus
from models.email_log import EmailLog
from models.email_reply import EmailReply
from services.demo_identity import posthog_distinct_id, resolve_demo_slug
from services.notification_service import notification_service
from services.posthog_service import posthog_service

logger = logging.getLogger(__name__)

_RESEND_RECEIVING_URL: str = "https://api.resend.com/emails/receiving/{email_id}"

# Truncated hex length of the HMAC signature embedded in the reply address.
_SIG_LENGTH: int = 10

_LOCALPART_RE: re.Pattern[str] = re.compile(r"^reply-(\d+)-([0-9a-f]+)$")

# Lowercase contains-markers identifying an autoresponder subject (FR + EN).
_AUTO_REPLY_SUBJECT_MARKERS: tuple[str, ...] = (
    "réponse automatique",
    "reponse automatique",
    "automatic reply",
    "auto-reply",
    "autoreply",
    "out of office",
    "absence du bureau",
    "en congé",
    "away from office",
)

# Header names whose mere presence (or non-"no" value for Auto-Submitted) marks an autoresponder.
_AUTO_REPLY_HEADERS: frozenset[str] = frozenset({"x-autoreply", "x-autorespond"})


def _capture_domain() -> str:
    """The receiving domain used for reply capture, lowercase, or empty when disabled."""
    return (getattr(settings, "reply_capture_domain", "") or "").strip().lower()


def _sign(email_log_id: int) -> str:
    """Truncated hex HMAC binding *email_log_id* to this deployment's ``SECRET_KEY``."""
    digest = hmac.new(settings.secret_key.encode(), f"reply:{email_log_id}".encode(), hashlib.sha256)
    return digest.hexdigest()[:_SIG_LENGTH]


def reply_address_for_log(email_log_id: int) -> str | None:
    """
    Build the signed Reply-To address for an outbound send.

    Args:
        email_log_id: The ``EmailLog`` row the future reply should attach to.

    Returns:
        ``reply-<id>-<sig>@<domain>``, or ``None`` when reply capture is disabled.
    """
    domain = _capture_domain()
    if not domain:
        return None
    return f"reply-{email_log_id}-{_sign(email_log_id)}@{domain}"


def parse_reply_token(addresses: list[str] | None) -> int | None:
    """
    Extract a valid ``email_log_id`` token from the recipient addresses of an inbound email.

    Args:
        addresses: The ``to`` field of the ``email.received`` payload (bare addresses).

    Returns:
        The verified ``EmailLog`` id, or ``None`` when no address carries a valid token.
    """
    domain = _capture_domain()
    if not domain or not addresses:
        return None
    for raw in addresses:
        address = parseaddr(str(raw))[1].lower()
        localpart, _, addr_domain = address.partition("@")
        if addr_domain != domain:
            continue
        match = _LOCALPART_RE.match(localpart)
        if match is None:
            continue
        log_id = int(match.group(1))
        if hmac.compare_digest(match.group(2), _sign(log_id)):
            return log_id
        logger.warning("[ReplyCapture] Invalid token signature on %s — ignored", address)
    return None


def is_auto_reply(subject: str | None, headers: dict[str, Any] | None) -> bool:
    """
    Detect an out-of-office / autoresponder rather than a human reply.

    Args:
        subject: Reply subject line.
        headers: Full headers of the received email (case-insensitive keys expected raw).

    Returns:
        ``True`` when the reply is machine-generated.
    """
    lowered_subject = (subject or "").lower()
    if any(marker in lowered_subject for marker in _AUTO_REPLY_SUBJECT_MARKERS):
        return True
    normalized: dict[str, str] = {str(k).lower(): str(v).lower() for k, v in (headers or {}).items()}
    auto_submitted = normalized.get("auto-submitted", "")
    if auto_submitted and auto_submitted != "no":
        return True
    if _AUTO_REPLY_HEADERS & normalized.keys():
        return True
    return normalized.get("precedence", "") in {"auto_reply", "auto-reply"}


def _parse_received_at(data: dict[str, Any]) -> datetime:
    """The event's own timestamp as naive UTC, falling back to now (mirrors the webhook parser)."""
    raw = data.get("created_at")
    if isinstance(raw, str):
        try:
            parsed = datetime.fromisoformat(raw.strip().replace("Z", "+00:00"))
        except ValueError:
            parsed = None
        if parsed is not None:
            if parsed.tzinfo is not None:
                parsed = parsed.astimezone(UTC).replace(tzinfo=None)
            return parsed
    return datetime.now(UTC).replace(tzinfo=None)


async def fetch_received_email(email_id: str) -> dict[str, Any] | None:
    """
    Fetch the full received email (body + headers) from the Resend Receiving API.

    Uses the platform API key — the capture domain is on the platform account.
    Best-effort: a failure degrades to storing webhook metadata only.

    Args:
        email_id: Resend received-email id from the webhook payload.

    Returns:
        The API response dict, or ``None`` on any failure.
    """
    api_key: str = getattr(settings, "resend_api_key", "") or ""
    if not api_key:
        return None
    try:
        async with (
            aiohttp.ClientSession() as session,
            session.get(
                _RESEND_RECEIVING_URL.format(email_id=email_id),
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp,
        ):
            if resp.status != 200:
                logger.warning("[ReplyCapture] Receiving API %s for email %s", resp.status, email_id)
                return None
            return await resp.json()
    except Exception as exc:
        logger.warning("[ReplyCapture] Could not fetch received email %s: %s", email_id, exc)
        return None


def _find_log_by_sender(db: Session, from_email: str) -> EmailLog | None:
    """Most recent send to *from_email* — the fallback when the reply carries no token."""
    if not from_email:
        return None
    return db.execute(
        select(EmailLog).where(EmailLog.recipient_email == from_email).order_by(EmailLog.id.desc()).limit(1)
    ).scalar_one_or_none()


async def handle_received(db: Session, data: dict[str, Any]) -> None:
    """
    Process an ``email.received`` webhook payload end-to-end.

    Matches the reply to its send (signed token first, sender address as fallback),
    stores it, advances the send to ``REPLIED`` and notifies — unless the reply is
    an autoresponder, which is stored silently.

    Args:
        db: Active database session.
        data: The ``data`` object of the webhook body.
    """
    email_id: str = str(data.get("email_id") or "")
    if not email_id:
        logger.warning("[ReplyCapture] email.received without email_id — ignored")
        return

    # Webhook retries must not create duplicate replies.
    existing = db.execute(select(EmailReply).where(EmailReply.resend_email_id == email_id)).scalar_one_or_none()
    if existing is not None:
        if existing.inbox_forwarded_at is None and not existing.is_auto_reply:
            from services.reply_inbox_forward_service import forward_reply_to_inbox

            original_log = db.get(EmailLog, existing.email_log_id)
            if original_log is not None:
                await forward_reply_to_inbox(db, existing, original_log)
        return

    from_email: str = parseaddr(str(data.get("from") or ""))[1].lower()
    to_addresses = data.get("to") if isinstance(data.get("to"), list) else []

    matched_by: str = "token"
    log_id: int | None = parse_reply_token(to_addresses)
    email_log: EmailLog | None = db.get(EmailLog, log_id) if log_id is not None else None
    if email_log is None:
        matched_by = "from"
        email_log = _find_log_by_sender(db, from_email)
    if email_log is None:
        logger.info("[ReplyCapture] No send matches reply from %s (email %s) — stored nowhere", from_email, email_id)
        return

    full = await fetch_received_email(email_id) or {}
    headers = full.get("headers") if isinstance(full.get("headers"), dict) else {}
    subject: str | None = full.get("subject") or data.get("subject") or None
    auto: bool = is_auto_reply(subject, headers)
    received_at: datetime = _parse_received_at(data)

    reply = EmailReply(
        email_log_id=email_log.id,
        user_id=email_log.user_id,
        prospect_id=email_log.prospect_id,
        from_email=from_email,
        subject=subject,
        body_text=full.get("text") or None,
        body_html=full.get("html") or None,
        resend_email_id=email_id,
        message_id=str(full.get("message_id") or data.get("message_id") or "") or None,
        matched_by=matched_by,
        is_auto_reply=auto,
        received_at=received_at,
    )
    db.add(reply)

    if not auto:
        if email_log.replied_at is None:
            email_log.replied_at = received_at
        email_log.status = EmailStatus.REPLIED.value
    db.commit()
    logger.info(
        "[ReplyCapture] EmailLog %d: reply from %s (matched_by=%s, auto=%s)",
        email_log.id,
        from_email,
        matched_by,
        auto,
    )

    if auto:
        return

    from services.reply_inbox_forward_service import forward_reply_to_inbox

    await forward_reply_to_inbox(db, reply, email_log)

    # One-shot LLM verdict on what the reply means (persisted — never re-asked).
    # Late imports: conversation_service → email_sending_service → this module.
    intent: str | None = None
    try:
        from services import reply_intent_service
        from services.conversation_service import reply_display_text

        intent = await reply_intent_service.classify_reply(db, reply, reply_display_text(reply))
    except Exception:
        logger.warning("[ReplyCapture] Intent classification failed for reply %d", reply.id, exc_info=True)

    from services.reply_intent_service import replied_event_name

    event_name: str = replied_event_name(intent)

    # Mirror into PostHog + push — same conventions as the other webhook events.
    demo_slug: str | None = resolve_demo_slug(db, email_log.user_id, email_log.prospect_id)
    await posthog_service.capture(
        distinct_id=posthog_distinct_id(demo_slug, email_log.prospect_id, email_log.recipient_email),
        event="email_replied",
        properties={
            "demo_slug": demo_slug,
            "prospect_id": email_log.prospect_id,
            "campaign_id": email_log.campaign_id,
            "ab_variant": email_log.ab_variant,
            "email_log_id": email_log.id,
            "matched_by": matched_by,
            "intent": intent,
            "$lib": "devleadhunter-api",
        },
        timestamp=received_at.isoformat(),
    )
    await notification_service.notify_email_event(
        db,
        user_id=email_log.user_id,
        event_name=event_name,
        recipient_email=email_log.recipient_email,
        prospect_id=email_log.prospect_id,
        subject=subject,
        email_log_id=email_log.id,
    )
