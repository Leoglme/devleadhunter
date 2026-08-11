"""Add the attached payment-link id to orders.

Qonto card/Apple Pay payments clear through Mollie and only settle onto the
invoice days later; storing the payment link's id lets reconciliation read the
link status and mark the order paid as soon as the buyer has paid.
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
        if not _column_exists(conn, "payment_link_id"):
            conn.execute(
                text(
                    """
                    ALTER TABLE orders
                    ADD COLUMN payment_link_id VARCHAR(255) NULL,
                    ADD INDEX ix_orders_payment_link_id (payment_link_id)
                    """
                )
            )
        conn.commit()


if __name__ == "__main__":
    run_migration()
    print("orders payment_link_id column ensured.")
