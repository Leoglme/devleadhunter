"""Count SMS segments, GSM-7 vs Unicode aware.

A French accent (é, è, à…) that is NOT in the GSM-7 alphabet forces the whole
message into UCS-2, dropping the per-segment budget from 160/153 to 70/67
characters — so a short-looking SMS can silently cost two segments. We count so
the compose UI can warn and the message stays sober (one segment when possible).
"""

from __future__ import annotations

# GSM 03.38 basic character set (the chars that stay single-byte).
_GSM7_BASIC: frozenset[str] = frozenset(
    "@£$¥èéùìòÇ\nØø\rÅåΔ_ΦΓΛΩΠΨΣΘΞ ÆæßÉ !\"#¤%&'()*+,-./0123456789:;<=>?"
    "¡ABCDEFGHIJKLMNOPQRSTUVWXYZÄÖÑÜ§¿abcdefghijklmnopqrstuvwxyzäöñüà"
)
# GSM-7 chars that take TWO septets (the extension table).
_GSM7_EXTENDED: frozenset[str] = frozenset("^{}\\[~]|€")

_GSM_SINGLE: int = 160
_GSM_MULTI: int = 153
_UCS2_SINGLE: int = 70
_UCS2_MULTI: int = 67


def is_gsm7(text: str) -> bool:
    """Whether *text* fits the GSM-7 alphabet (else it is sent as UCS-2).

    Args:
        text: The message body.

    Returns:
        ``True`` when every character is GSM-7 encodable.
    """
    return all(ch in _GSM7_BASIC or ch in _GSM7_EXTENDED for ch in text)


def segment_count(text: str) -> int:
    """Number of SMS segments *text* costs (each segment is billed).

    Args:
        text: The message body.

    Returns:
        The segment count (``0`` for an empty body).
    """
    if not text:
        return 0
    if is_gsm7(text):
        length = sum(2 if ch in _GSM7_EXTENDED else 1 for ch in text)
        single, multi = _GSM_SINGLE, _GSM_MULTI
    else:
        length = len(text)
        single, multi = _UCS2_SINGLE, _UCS2_MULTI
    if length <= single:
        return 1
    return -(-length // multi)  # ceil division
