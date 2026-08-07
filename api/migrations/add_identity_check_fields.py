"""Add the Maps place identity + cross-source identity check to enrichments."""

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
              AND TABLE_NAME = 'prospect_enrichments'
              AND COLUMN_NAME = :column_name
            """
        ),
        {"column_name": column_name},
    )
    return bool(result.scalar())


def run_migration() -> None:
    with engine.connect() as conn:
        if not _column_exists(conn, "place_title"):
            conn.execute(
                text(
                    """
                    ALTER TABLE prospect_enrichments
                    ADD COLUMN place_title VARCHAR(300) NULL,
                    ADD COLUMN place_city VARCHAR(120) NULL,
                    ADD COLUMN place_postal_code VARCHAR(10) NULL,
                    ADD COLUMN identity_check_status VARCHAR(16) NULL,
                    ADD COLUMN identity_check_detail VARCHAR(400) NULL
                    """
                )
            )
        conn.commit()


if __name__ == "__main__":
    run_migration()
