"""Add ``max_emails_per_day`` to campaigns (per-campaign daily send cap).

NULL means no per-campaign limit — only the user's global SendPolicy cap applies
(existing behaviour). Set to a small integer (e.g. 1) to spread a single-métier
campaign at one prospect per day so several campaigns can run 1/day each side by
side (1 barber + 1 garage + 1 food per day).
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
              AND TABLE_NAME = 'campaigns'
              AND COLUMN_NAME = :column_name
            """
        ),
        {"column_name": column_name},
    )
    return bool(result.scalar())


def run_migration() -> None:
    with engine.connect() as conn:
        if not _column_exists(conn, "max_emails_per_day"):
            conn.execute(
                text(
                    """
                    ALTER TABLE campaigns
                    ADD COLUMN max_emails_per_day INT NULL
                    """
                )
            )
        conn.commit()


if __name__ == "__main__":
    run_migration()
    print("campaigns.max_emails_per_day column ensured.")
