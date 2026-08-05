"""Add ``theme`` to email_templates (thematic group for the collapsible cards).

Nullable free-text French label ("Visibilité", "Site en panne", …) used to fold
the templates page into per-angle accordion cards. Existing rows keep NULL until
the reseed migration assigns the canonical library its themes.
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
              AND TABLE_NAME = 'email_templates'
              AND COLUMN_NAME = :column_name
            """
        ),
        {"column_name": column_name},
    )
    return bool(result.scalar())


def run_migration() -> None:
    with engine.connect() as conn:
        if not _column_exists(conn, "theme"):
            conn.execute(text("ALTER TABLE email_templates ADD COLUMN theme VARCHAR(64) NULL"))
        conn.commit()


if __name__ == "__main__":
    run_migration()
    print("email_templates.theme ensured.")
