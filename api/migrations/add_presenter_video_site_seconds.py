"""Add ``site_seconds`` to presenter_videos (user-chosen length of the site-scroll part).

The Storyblok editor sequence gets the remainder of the middle segment. NULL keeps
the historical automatic split.
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
              AND TABLE_NAME = 'presenter_videos'
              AND COLUMN_NAME = :column_name
            """
        ),
        {"column_name": column_name},
    )
    return bool(result.scalar())


def run_migration() -> None:
    with engine.connect() as conn:
        if not _column_exists(conn, "site_seconds"):
            conn.execute(text("ALTER TABLE presenter_videos ADD COLUMN site_seconds FLOAT NULL"))
        conn.commit()


if __name__ == "__main__":
    run_migration()
    print("presenter_videos.site_seconds column ensured.")
