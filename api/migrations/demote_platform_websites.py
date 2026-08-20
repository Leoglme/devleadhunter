"""Demote booking/marketplace/directory platforms wrongly saved as a prospect's website.

A Planity/Treatwell/PagesJaunes… page listed as the "website" made a prospect count as "has a site",
hiding it from the without-a-site targeting. This clears such websites. Going forward,
``ValidationService.is_valid_website`` rejects them at create / update / enrichment time.
"""

from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import text

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from core.database import engine

# Kept in sync with ``ValidationService._PLATFORM_DOMAINS`` (a one-time snapshot: new domains added there
# later are prevented at write time, so this backfill only needs the platforms present in the DB today).
_PLATFORM_LIKE = (
    "LOWER(website) LIKE '%planity.com%' OR LOWER(website) LIKE '%treatwell.%' "
    "OR LOWER(website) LIKE '%fresha.com%' OR LOWER(website) LIKE '%kiute.fr%' "
    "OR LOWER(website) LIKE '%resalib.fr%' OR LOWER(website) LIKE '%balinea.com%' "
    "OR LOWER(website) LIKE '%wavy.pro%' OR LOWER(website) LIKE '%pagesjaunes.fr%' "
    "OR LOWER(website) LIKE '%thefork.%' OR LOWER(website) LIKE '%lafourchette.com%' "
    "OR LOWER(website) LIKE '%deliveroo.%' OR LOWER(website) LIKE '%ubereats.com%' "
    "OR LOWER(website) LIKE '%just-eat.fr%'"
)


def run_migration() -> None:
    with engine.connect() as conn:
        # A platform listing is never a real website → clear it so the prospect reads as site-less.
        conn.execute(
            text(
                f"UPDATE prospects SET website = NULL, website_status = NULL "
                f"WHERE website IS NOT NULL AND ({_PLATFORM_LIKE})"
            )
        )
        conn.commit()


if __name__ == "__main__":
    run_migration()
