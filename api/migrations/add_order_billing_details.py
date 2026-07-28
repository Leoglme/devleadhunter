"""Add editable billing-address columns to orders.

Qonto rejects an invoice whose client has no valid postal address, and prospect
enrichment often only yields a free-form street line. These columns hold the
operator-reviewed address used to create the provider-side client.
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
    ("billing_address", "VARCHAR(255) NULL"),
    ("billing_city", "VARCHAR(120) NULL"),
    ("billing_zip_code", "VARCHAR(20) NULL"),
    ("billing_country_code", "VARCHAR(2) NULL"),
    ("billing_tax_id", "VARCHAR(64) NULL"),
    ("billing_vat_number", "VARCHAR(64) NULL"),
)


def _column_exists(conn, column_name: str) -> bool:
    result = conn.execute(
        text(
            """
            SELECT COUNT(*)
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = 'orders'
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
            WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'orders'
            """
        )
    )
    return bool(result.scalar())


def run_migration() -> None:
    with engine.connect() as conn:
        # Fresh database: init_db() create_all builds orders with every column.
        if not _table_exists(conn):
            return
        for column_name, definition in _COLUMNS:
            if not _column_exists(conn, column_name):
                conn.execute(text(f"ALTER TABLE orders ADD COLUMN {column_name} {definition}"))
        conn.commit()


if __name__ == "__main__":
    run_migration()
    print("orders billing-details columns ensured.")
