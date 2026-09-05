"""Make email_queue.template_id nullable.

SMS-channel queue items carry no email template (the SMS body is composed from the prospect + demo
link at dispatch). Email-channel items still always set it. The FK is dropped, the column widened to
NULL, then the FK re-added with ON DELETE RESTRICT (unchanged behaviour for email rows).
"""

from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import text

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from core.database import engine


def _is_nullable(conn) -> bool:
    row = conn.execute(
        text(
            """
            SELECT IS_NULLABLE
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = 'email_queue'
              AND COLUMN_NAME = 'template_id'
            """
        )
    ).scalar()
    return str(row).upper() == "YES"


def run_migration() -> None:
    print("Running migration: nullable_queue_template_id")
    with engine.connect() as conn:
        if _is_nullable(conn):
            print("  ~ email_queue.template_id already nullable — nothing to do")
            return

        fk_row = conn.execute(
            text(
                "SELECT CONSTRAINT_NAME FROM information_schema.KEY_COLUMN_USAGE "
                "WHERE TABLE_NAME = 'email_queue' "
                "AND COLUMN_NAME = 'template_id' "
                "AND REFERENCED_TABLE_NAME = 'email_templates' "
                "AND TABLE_SCHEMA = DATABASE() LIMIT 1"
            )
        ).first()

        if fk_row:
            conn.execute(text(f"ALTER TABLE email_queue DROP FOREIGN KEY {fk_row[0]}"))

        conn.execute(text("ALTER TABLE email_queue MODIFY COLUMN template_id INT NULL"))
        conn.execute(
            text(
                "ALTER TABLE email_queue "
                "ADD CONSTRAINT fk_email_queue_template "
                "FOREIGN KEY (template_id) REFERENCES email_templates(id) ON DELETE RESTRICT"
            )
        )
        conn.commit()
    print("  ~ email_queue.template_id: NULL now allowed")
    print("Migration completed successfully.")


if __name__ == "__main__":
    run_migration()
