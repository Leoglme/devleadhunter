"""Add the platform commission rate to credit settings.

Applied as a Stripe Connect application fee on sales invoiced through another
user's account. Defaults to 0 — no commission until an admin sets one.
"""

from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import text

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from core.database import engine


def _column_exists(conn) -> bool:
    result = conn.execute(
        text(
            """
            SELECT COUNT(*)
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = 'credit_settings'
              AND COLUMN_NAME = 'platform_commission_percent'
            """
        )
    )
    return bool(result.scalar())


def _table_exists(conn) -> bool:
    result = conn.execute(
        text(
            """
            SELECT COUNT(*)
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'credit_settings'
            """
        )
    )
    return bool(result.scalar())


def run_migration() -> None:
    with engine.connect() as conn:
        # Fresh database: init_db() create_all builds the table with every column.
        if not _table_exists(conn):
            return
        if not _column_exists(conn):
            conn.execute(
                text(
                    """
                    ALTER TABLE credit_settings
                    ADD COLUMN platform_commission_percent DECIMAL(5,2) NOT NULL DEFAULT 0.00
                    """
                )
            )
        conn.commit()


if __name__ == "__main__":
    run_migration()
    print("credit_settings platform commission column ensured.")
