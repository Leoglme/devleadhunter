"""Track when the current Storyblok space was created (reset on outreach swap)."""

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
              AND TABLE_NAME = 'demo_sites'
              AND COLUMN_NAME = :column_name
            """
        ),
        {"column_name": column_name},
    )
    return bool(result.scalar())


def run() -> None:
    with engine.begin() as conn:
        if not _column_exists(conn, "storyblok_space_created_at"):
            conn.execute(
                text(
                    """
                    ALTER TABLE demo_sites
                    ADD COLUMN storyblok_space_created_at DATETIME NULL
                    AFTER storyblok_invite_sent
                    """
                )
            )
            conn.execute(
                text(
                    """
                    UPDATE demo_sites
                    SET storyblok_space_created_at = created_at
                    WHERE storyblok_space_id IS NOT NULL
                      AND storyblok_space_created_at IS NULL
                    """
                )
            )
    print("demo_sites.storyblok_space_created_at column ensured and backfilled.")


if __name__ == "__main__":
    run()
