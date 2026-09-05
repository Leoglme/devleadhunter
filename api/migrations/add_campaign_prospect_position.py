"""Add ``position`` to the campaign_prospects association (explicit send order within a campaign).

The send queue pairs ascending time-slots to a campaign's prospects in this order, so with
``max_emails_per_day=1`` the operator controls which group goes on which day (1 métier/jour). Bulk
inserts share one ``added_at`` second, so ``added_at`` alone cannot order them — hence this column.

Existing rows are backfilled with a per-campaign rank over (added_at, prospect_id) so old campaigns
keep a sane, stable order. New rows get their position set explicitly by the app at insert time.
"""

from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import text

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from core.database import engine


def _column_exists(conn, column_name: str) -> bool:
    result = conn.execute(
        text(
            """
            SELECT COUNT(*)
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = 'campaign_prospects'
              AND COLUMN_NAME = :column_name
            """
        ),
        {"column_name": column_name},
    )
    return bool(result.scalar())


def run_migration() -> None:
    with engine.connect() as conn:
        if not _column_exists(conn, "position"):
            conn.execute(
                text(
                    """
                    ALTER TABLE campaign_prospects
                    ADD COLUMN position INT NOT NULL DEFAULT 0
                    """
                )
            )
            conn.commit()
            # Best-effort backfill for pre-existing rows (needs MySQL 8+ window functions). Failure is
            # non-fatal: the relationship's secondary sort (added_at, prospect_id) still orders them.
            try:
                conn.execute(
                    text(
                        """
                        UPDATE campaign_prospects cp
                        JOIN (
                            SELECT campaign_id, prospect_id,
                                   ROW_NUMBER() OVER (
                                       PARTITION BY campaign_id ORDER BY added_at, prospect_id
                                   ) - 1 AS rn
                            FROM campaign_prospects
                        ) ranked
                          ON ranked.campaign_id = cp.campaign_id
                         AND ranked.prospect_id = cp.prospect_id
                        SET cp.position = ranked.rn
                        """
                    )
                )
                conn.commit()
            except Exception as exc:
                print(f"  ~ position backfill skipped ({exc.__class__.__name__}); default 0 kept.")


if __name__ == "__main__":
    run_migration()
    print("campaign_prospects.position column ensured.")
