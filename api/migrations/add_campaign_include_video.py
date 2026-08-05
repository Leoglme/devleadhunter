"""Add ``include_video`` to campaigns (prospection-video toggle, default on).

When False, the campaign never attaches the prospection video: ``{vignette_video}``
renders empty and combo templates fall back to their demo link. Existing campaigns
default to 1 (video on) so behaviour is unchanged.
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
              AND TABLE_NAME = 'campaigns'
              AND COLUMN_NAME = :column_name
            """
        ),
        {"column_name": column_name},
    )
    return bool(result.scalar())


def run_migration() -> None:
    with engine.connect() as conn:
        if not _column_exists(conn, "include_video"):
            conn.execute(
                text(
                    """
                    ALTER TABLE campaigns
                    ADD COLUMN include_video TINYINT(1) NOT NULL DEFAULT 1
                    """
                )
            )
        conn.commit()


if __name__ == "__main__":
    run_migration()
    print("campaigns.include_video column ensured.")
