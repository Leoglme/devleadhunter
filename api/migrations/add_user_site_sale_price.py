"""Add ``site_sale_price_cents`` to users (configurable website sale price).

Defaults to 50000 (500 €), Léo's launch price. ``ADD COLUMN`` with a DEFAULT sets
every existing row to 500 € in place, so no separate backfill pass is needed.
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
              AND TABLE_NAME = 'users'
              AND COLUMN_NAME = :column_name
            """
        ),
        {"column_name": column_name},
    )
    return bool(result.scalar())


def run_migration() -> None:
    with engine.connect() as conn:
        if not _column_exists(conn, "site_sale_price_cents"):
            conn.execute(
                text(
                    """
                    ALTER TABLE users
                    ADD COLUMN site_sale_price_cents INT NOT NULL DEFAULT 50000
                    """
                )
            )
        conn.commit()


if __name__ == "__main__":
    run_migration()
    print("users.site_sale_price_cents ensured.")
