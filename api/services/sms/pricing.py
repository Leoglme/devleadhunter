"""Estimate the cost of an SMS when the provider returns no price.

smsmode's REST v1 send response does not carry a ``price`` for our account (the
billed amount is known from the account plan, not returned per message), so the
cost is estimated from the billed segment count and a configurable per-segment
rate (``SMSMODE_PRICE_PER_SEGMENT_EUR``). A price actually returned by the
provider is always preferred over this estimate.
"""

from __future__ import annotations

from core.config import settings


def estimate_price_cents(segments: int) -> int:
    """Estimate the cost of one send in cents from its billed segment count.

    Args:
        segments: Number of billed SMS segments (at least one is charged).

    Returns:
        The estimated cost in cents.
    """
    billed_segments = max(int(segments or 0), 1)
    return round(billed_segments * settings.smsmode_price_per_segment_eur * 100)
