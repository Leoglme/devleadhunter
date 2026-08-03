"""
Enum for the liveness of a prospect's scraped website.

Stored as a plain string in a ``String`` column, following the Order/DemoSite
convention. ``None`` in the database means "no website found" or "never checked"
(prospects saved before the check existed).
"""

from enum import Enum


class WebsiteStatus(str, Enum):
    """Liveness classification of a website URL found during scraping."""

    LIVE = "live"
    # DNS dead, connection refused, 4xx/5xx, or a hosting "site not found" page.
    DEAD = "dead"
    # Directory mini-site (business.site, Solocal, wixsite…) — not a real website.
    PLACEHOLDER = "placeholder"
