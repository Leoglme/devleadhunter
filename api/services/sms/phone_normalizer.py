"""Normalise a French phone number to E.164, and tell mobiles from landlines.

smsmode (like every A2P provider) requires E.164 (``+33612345678``). Our scraped
numbers come in every French shape (``06 12 34 56 78``, ``0612345678``,
``+33 6 12…``), and a text SMS can only reach a **mobile** (06/07) — a landline
(01–05) or VoIP (09) silently never receives it, so we must filter before paying
for a send.
"""

from __future__ import annotations

import re

# Any non-digit separator a human or a scraper might use between groups.
_NON_DIGITS: re.Pattern[str] = re.compile(r"\D")


def to_e164_fr(raw: str | None) -> str | None:
    """Convert a French phone number to E.164 (``+33…``), or ``None`` if invalid.

    Accepts the national form (``0X…``), the already-international form
    (``+33X…`` / ``0033X…``) and any spacing/punctuation. A number that is not a
    plausible 9-digit French subscriber number returns ``None``.

    Args:
        raw: The phone number in any French format.

    Returns:
        The number as ``+33XXXXXXXXX``, or ``None`` when it is not a valid FR number.
    """
    if not raw:
        return None
    digits = _NON_DIGITS.sub("", raw)
    if digits.startswith("0033"):
        digits = digits[4:]
    elif digits.startswith("33") and len(digits) == 11:
        digits = digits[2:]
    elif digits.startswith("0"):
        digits = digits[1:]
    # A French subscriber number is 9 digits, first digit 1–9.
    if len(digits) != 9 or digits[0] == "0":
        return None
    return f"+33{digits}"


def is_mobile_fr(raw: str | None) -> bool:
    """Whether a French number is a mobile (06/07) — the only kind an SMS reaches.

    Args:
        raw: The phone number in any French format.

    Returns:
        ``True`` when the normalised number is a French mobile (``+336…`` / ``+337…``).
    """
    e164 = to_e164_fr(raw)
    return bool(e164 and e164[3] in {"6", "7"})
