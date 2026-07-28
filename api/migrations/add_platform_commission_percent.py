"""Add the platform commission (percentage + fixed part) to credit settings.

Applied as a Stripe Connect application fee on sales invoiced through another
user's account. Both default to 0 — no commission until an admin sets one.
"""

from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import text

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from core.database import engine

_COLUMNS: tuple[tuple[str, str], ...] = (
    ("platform_commission_percent", "DECIMAL(5,2) NOT NULL DEFAULT 0.00"),
    ("platform_commission_fixed_cents", "INT NOT NULL DEFAULT 0"),
)


def _column_exists(conn, column_name: str) -> bool:
    result = conn.execute(
        text(
            """
            SELECT COUNT(*)
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = 'credit_settings'
              AND COLUMN_NAME = :column_name
            """
        ),
        {"column_name": column_name},
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
        for column_name, definition in _COLUMNS:
            if not _column_exists(conn, column_name):
                conn.execute(text(f"ALTER TABLE credit_settings ADD COLUMN {column_name} {definition}"))
        conn.commit()


if __name__ == "__main__":
    run_migration()
    print("credit_settings platform commission columns ensured.")
