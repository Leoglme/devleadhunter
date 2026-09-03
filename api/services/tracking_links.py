"""Stamp outbound demo/video links with a marketing-channel attribution param.

Each channel that pushes a prospect their demo link tags it with ``?src=<channel>``
(email / sms) so PostHog can attribute the demo visit to the channel it came from
— separate from the A/B ``?v=`` variant. An untagged link (a direct visit or a
bookmark) reads as « direct » on the tracking side.
"""

from __future__ import annotations

CHANNEL_EMAIL: str = "email"
CHANNEL_SMS: str = "sms"


def append_query_param(url: str, key: str, value: str) -> str:
    """Append ``key=value`` to *url*, choosing ``?`` or ``&`` as needed.

    Args:
        url: The base URL (may already carry a query string).
        key: Query parameter name.
        value: Query parameter value (ASCII, no escaping needed for our channels/variants).

    Returns:
        The URL with the parameter appended.
    """
    separator = "&" if "?" in url else "?"
    return f"{url}{separator}{key}={value}"
