"""Add the multi-email list to prospects (primary = ``emails[0]``, kept in sync with ``email``)."""

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
              AND TABLE_NAME = 'prospects'
              AND COLUMN_NAME = 'emails'
            """
        )
    )
    return bool(result.scalar())


def run_migration() -> None:
    with engine.connect() as conn:
        if not _column_exists(conn):
            conn.execute(text("ALTER TABLE prospects ADD COLUMN emails JSON NULL"))
            # Seed the list from the existing single email so nothing is lost.
            conn.execute(
                text(
                    "UPDATE prospects SET emails = JSON_ARRAY(email) "
                    "WHERE email IS NOT NULL AND email <> '' AND emails IS NULL"
                )
            )
        conn.commit()


if __name__ == "__main__":
    run_migration()
