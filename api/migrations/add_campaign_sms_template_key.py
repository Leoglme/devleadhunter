"""Add ``sms_template_key`` to campaigns (the SMS library template an SMS campaign renders).

NULL means the default first-contact template. Email campaigns ignore it (they use template_id).
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
        if not _column_exists(conn, "sms_template_key"):
            conn.execute(text("ALTER TABLE campaigns ADD COLUMN sms_template_key VARCHAR(64) NULL"))
        conn.commit()


if __name__ == "__main__":
    run_migration()
    print("campaigns.sms_template_key column ensured.")
