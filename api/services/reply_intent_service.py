"""
Reply intent — one Groq verdict per reply, persisted, deduplicated by content.

Guarantees around LLM spend:
- A reply is classified AT MOST ONCE: the verdict is stored on the row and
  never re-asked.
- Identical content (SHA-256 of the text) reuses an existing verdict instead of
  spending a second call — duplicate out-of-office bodies, twin replies.
- ``temperature=0`` on the model, so the same content yields the same verdict.

The verdict only ever SUGGESTS: no automated unsubscribe, no automated answer —
the user validates every action in the UI.
"""

from __future__ import annotations

import hashlib
import logging
import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from models.email_reply import EmailReply
from services.llm_service import llm_service

logger = logging.getLogger(__name__)

# The closed set of verdicts; anything else from the model is discarded.
INTENTS: frozenset[str] = frozenset({"interested", "not_interested", "later", "question", "unsubscribe", "other"})

# Verdicts that must cool the prospect down instead of heating it up.
NEGATIVE_INTENTS: frozenset[str] = frozenset({"not_interested", "unsubscribe"})


def replied_event_name(intent: str | None) -> str:
    """The notification event for a captured reply, colored by its verdict."""
    if intent == "interested":
        return "email_replied_interested"
    if intent in NEGATIVE_INTENTS:
        return "email_replied_negative"
    return "email_replied"


def content_sha(text: str) -> str:
    """SHA-256 of the normalized reply text (whitespace-insensitive)."""
    normalized = re.sub(r"\s+", " ", text.strip().lower())
    return hashlib.sha256(normalized.encode()).hexdigest()


def normalize_verdict(raw: str | None) -> str | None:
    """
    Coerce the model output to a valid intent, or ``None``.

    Tolerates decoration («interested.», "NOT_INTERESTED", «l'intent est: later»)
    by keeping the first known intent word found.

    Args:
        raw: Raw model output.

    Returns:
        A member of :data:`INTENTS`, or ``None`` when nothing valid is found.
    """
    if not raw:
        return None
    lowered = raw.strip().lower().replace("-", "_")
    for token in re.findall(r"[a-z_]+", lowered):
        if token in INTENTS:
            return token
    return None


async def classify_reply(db: Session, reply: EmailReply, text: str) -> str | None:
    """
    Ensure *reply* carries an intent verdict, spending at most one LLM call.

    Order: already classified → reuse; identical content already classified on
    another reply → copy; otherwise one Groq call. A failed call leaves the
    intent ``NULL`` (retried on the next opportunity, never mislabeled).

    Args:
        db: Active database session.
        reply: The reply to classify (mutated + committed on success).
        text: The reply's plain text (HTML already stripped by the caller).

    Returns:
        The verdict, or ``None`` when unclassifiable for now.
    """
    if reply.intent:
        return reply.intent
    cleaned = (text or "").strip()
    if not cleaned:
        return None

    sha = content_sha(cleaned)

    # Same content already judged on another reply → reuse, zero LLM spend.
    twin: EmailReply | None = db.execute(
        select(EmailReply).where(EmailReply.content_sha == sha, EmailReply.intent.isnot(None)).limit(1)
    ).scalar_one_or_none()
    if twin is not None:
        reply.intent = twin.intent
        reply.content_sha = sha
        db.commit()
        return reply.intent

    verdict = normalize_verdict(await llm_service.classify_reply_intent(cleaned))
    if verdict is None:
        return None
    reply.intent = verdict
    reply.content_sha = sha
    db.commit()
    logger.info("[ReplyIntent] Reply %d classified as %s", reply.id, verdict)
    return verdict
