"""
Forward captured prospect replies to the user's readable inbox (Gmail POP, etc.).

The Reply-To capture domain never hits o2switch/cPanel — this service sends a
best-effort copy to ``REPLY_INBOX_FORWARD_TO`` or the user's ``from_email`` so
the operator can read replies in their usual mailbox. Gmail is read-only here:
answers go through the DevLeadHunter conversation drawer.
"""

from __future__ import annotations

import html as html_lib
import logging
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from core.config import settings
from models.email_log import EmailLog
from models.email_reply import EmailReply
from services.resend_service import ResendService
from services.sending_identity import SendingIdentity, resolve_sending_identity

logger = logging.getLogger(__name__)


def _inbox_target(identity: SendingIdentity) -> str | None:
    """The address that receives inbox copies for this user."""
    override = (getattr(settings, "reply_inbox_forward_to", "") or "").strip().lower()
    if override:
        return override
    target = (identity.from_email or "").strip().lower()
    return target or None


def inbox_copy_address(identity: SendingIdentity) -> str | None:
    """The address that receives inbox copies (forward + BCC) for this user."""
    return _inbox_target(identity)


def _wrap_forward_html(reply: EmailReply) -> str:
    """Prefix the prospect's message so the copy is identifiable in Gmail."""
    prospect = html_lib.escape(reply.from_email)
    subject = html_lib.escape(reply.subject or "(sans objet)")
    body_html = reply.body_html
    if body_html and body_html.strip():
        inner = body_html
    elif reply.body_text and reply.body_text.strip():
        inner = f"<pre style='white-space:pre-wrap;font-family:inherit'>{html_lib.escape(reply.body_text)}</pre>"
    else:
        inner = "<p><em>(message vide)</em></p>"
    return (
        f"<p style='color:#666;font-size:13px;margin:0 0 12px'>"
        f"<strong>Réponse prospect</strong> — {prospect}<br/>"
        f"Sujet : {subject}<br/>"
        f"Capturée par DevLeadHunter (lecture uniquement — répondre depuis l'app)</p>"
        f"<hr style='border:none;border-top:1px solid #e5e5e5;margin:12px 0'/>"
        f"{inner}"
    )


async def forward_reply_to_inbox(
    db: Session,
    reply: EmailReply,
    email_log: EmailLog,
    *,
    identity: SendingIdentity | None = None,
) -> bool:
    """
    Send a copy of a captured reply to the user's inbox address.

    Idempotent via ``reply.inbox_forwarded_at``. Best-effort: failures are logged
    and never block capture.

    Args:
        db: Active database session.
        reply: The stored inbound reply (body fields must be populated).
        email_log: The outbound send this reply answers.
        identity: Pre-resolved sending identity (resolved when omitted).

    Returns:
        ``True`` when a forward was sent and timestamped.
    """
    if reply.is_auto_reply or reply.inbox_forwarded_at is not None:
        return False

    try:
        resolved = identity or resolve_sending_identity(db, reply.user_id)
    except Exception as exc:
        logger.warning("[ReplyInboxForward] No sending identity for user %s: %s", reply.user_id, exc)
        return False

    target = _inbox_target(resolved)
    if not target:
        return False

    subject_base = (reply.subject or email_log.subject or "Réponse prospect").strip()
    forward_subject = f"Réponse : {subject_base}"

    resend = ResendService()
    try:
        await resend.send_email(
            from_email=resolved.from_email,
            from_name=resolved.from_name or "",
            to_email=target,
            subject=forward_subject,
            html_body=_wrap_forward_html(reply),
            text_body=reply.body_text,
            api_key_override=resolved.resend_api_key,
        )
    except Exception as exc:
        logger.warning(
            "[ReplyInboxForward] Failed to forward reply %d to %s: %s",
            reply.id,
            target,
            exc,
        )
        return False

    reply.inbox_forwarded_at = datetime.now(UTC).replace(tzinfo=None)
    db.commit()
    logger.info("[ReplyInboxForward] Reply %d forwarded to %s", reply.id, target)
    return True
