"""Purge legacy soft-deleted demo sites so their unique slugs free up for a clean regeneration.

A manually deleted demo used to keep its row (status='deleted') and thus its slug, forcing a later
regeneration onto a '-2' suffix. Deletion now hard-deletes unsold sites; this clears the backlog.
Sold sites (referenced by an order) are kept so the order's demo_site_id stays valid.
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
    with engine.connect() as conn:
        conn.execute(
            text(
                """
                DELETE FROM demo_sites
                WHERE status = 'deleted'
                  AND id NOT IN (SELECT demo_site_id FROM orders WHERE demo_site_id IS NOT NULL)
                """
            )
        )
        conn.commit()


if __name__ == "__main__":
    run_migration()
