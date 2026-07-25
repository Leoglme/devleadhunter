"""Add provider-agnostic payment/invoice columns to orders.

``payment_provider`` / ``payment_url`` / ``invoice_id`` / ``invoice_number`` let
a sale be invoiced through Qonto or Stripe (per the user's PaymentAccount),
superseding the Stripe-only ``stripe_*`` columns without dropping them.
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
        if not _column_exists(conn, "payment_provider"):
            conn.execute(
                text(
                    """
                    ALTER TABLE orders
                    ADD COLUMN payment_provider VARCHAR(20) NULL,
                    ADD INDEX ix_orders_payment_provider (payment_provider)
                    """
                )
            )
        if not _column_exists(conn, "payment_url"):
            conn.execute(text("ALTER TABLE orders ADD COLUMN payment_url TEXT NULL"))
        if not _column_exists(conn, "invoice_id"):
            conn.execute(
                text(
                    """
                    ALTER TABLE orders
                    ADD COLUMN invoice_id VARCHAR(255) NULL,
                    ADD INDEX ix_orders_invoice_id (invoice_id)
                    """
                )
            )
        if not _column_exists(conn, "invoice_number"):
            conn.execute(text("ALTER TABLE orders ADD COLUMN invoice_number VARCHAR(64) NULL"))
        conn.commit()


if __name__ == "__main__":
    run_migration()
    print("orders payment-provider columns ensured.")
