"""Widen prospect_enrichments.logo_url to TEXT so a rehosted base64 logo isn't truncated.

The Facebook logo is captured as a base64 data URI at scrape time (fbcdn URLs expire); a
VARCHAR(1000) silently cut it to 1000 chars → broken preview and broken favicon. TEXT holds it,
then generation uploads it to the Storyblok library like the photos.
"""

from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import text

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from core.database import engine


def run_migration() -> None:
    """Alter logo_url so a base64 data-URI logo fits (MODIFY is idempotent)."""
    with engine.connect() as conn:
        conn.execute(
            text(
                """
                ALTER TABLE prospect_enrichments
                MODIFY COLUMN logo_url TEXT NULL
                """
            )
        )
        conn.commit()


if __name__ == "__main__":
    run_migration()
    print("prospect_enrichments.logo_url widened to TEXT.")
