"""Demote social pages wrongly saved as a prospect's website (kept only if it marks a real site).

A Facebook/Instagram page listed as the "website" made a prospect count as "has a site", hiding it from
the without-a-site targeting. This clears such websites; a Facebook page is preserved as ``facebook_url``.
Going forward, ``prospect_service`` demotes them at create/update time.
"""

from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import text

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from core.database import engine

_SOCIAL_LIKE = (
    "LOWER(website) LIKE '%facebook.com%' OR LOWER(website) LIKE '%instagram.com%' "
    "OR LOWER(website) LIKE '%twitter.com%' OR LOWER(website) LIKE '%linkedin.com%' "
    "OR LOWER(website) LIKE '%youtube.com%' OR LOWER(website) LIKE '%pinterest.com%' "
    "OR LOWER(website) LIKE '%tiktok.com%' OR LOWER(website) LIKE '%snapchat.com%'"
)


def run_migration() -> None:
    with engine.connect() as conn:
        # A Facebook page wrongly stored as the website is kept as facebook_url when none is set yet.
        conn.execute(
            text(
                "UPDATE prospects SET facebook_url = website "
                "WHERE website IS NOT NULL AND LOWER(website) LIKE '%facebook.com%' "
                "AND (facebook_url IS NULL OR facebook_url = '')"
            )
        )
        # No social page is a real website → clear it so the prospect reads as site-less.
        conn.execute(
            text(
                f"UPDATE prospects SET website = NULL, website_status = NULL WHERE website IS NOT NULL AND ({_SOCIAL_LIKE})"
            )
        )
        conn.commit()


if __name__ == "__main__":
    run_migration()
