"""Multi-email helpers for a prospect.

A prospect can hold several emails (imported, scraped, Facebook-sourced). ``emails[0]`` is the primary
— the one shown in the table and used to send — and ``prospect.email`` is always kept in sync with it.
Sending stays 1-to-1 on the primary; the rest are a fallback tried on a hard bounce (never a multi-To send).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models.prospect_db import ProspectDB


def _clean(value: object) -> str | None:
    """Return a trimmed email string, or None when blank/not a string."""
    return value.strip() if isinstance(value, str) and value.strip() else None


def dedupe_emails(emails: list[object]) -> list[str]:
    """Dedupe emails case-insensitively, keeping first-seen order and dropping blanks."""
    seen: set[str] = set()
    result: list[str] = []
    for candidate in emails:
        cleaned = _clean(candidate)
        if cleaned is None:
            continue
        key = cleaned.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(cleaned)
    return result


def set_prospect_emails(prospect: ProspectDB, emails: list[object]) -> list[str]:
    """Replace the prospect's whole email list with ``emails`` (deduped, order kept).

    This is the human-edit path: the caller sends the full ordered list, so it covers reorder,
    add and remove in one shot. ``emails[0]`` becomes the primary and ``email`` is synced to it.

    Args:
        prospect: The prospect to update in place.
        emails: The new ordered list; the first entry becomes the primary.

    Returns:
        The cleaned, deduped list actually stored.
    """
    cleaned = dedupe_emails(emails)
    prospect.emails = cleaned
    prospect.email = cleaned[0] if cleaned else None
    return cleaned


def sync_prospect_emails(
    prospect: ProspectDB,
    *,
    add: list[object] | None = None,
    primary: str | None = None,
) -> None:
    """Rebuild the prospect's email list (deduped) and keep ``email`` synced to ``emails[0]``.

    Args:
        prospect: The prospect to update in place.
        add: Newly discovered emails to fold in (best-first order preserved after the current ones).
        primary: An email to force to the front (e.g. the human's chosen primary).
    """
    current: list[object] = list(prospect.emails or [])
    if not current and prospect.email:
        current = [prospect.email]
    combined: list[object] = ([primary] if primary else []) + current + list(add or [])
    emails = dedupe_emails(combined)
    prospect.emails = emails
    prospect.email = emails[0] if emails else None
