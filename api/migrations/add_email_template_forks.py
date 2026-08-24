"""Fork-on-edit and per-user hide for the shared email-template library."""

from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import text

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


def _column_exists(conn, table: str, column_name: str) -> bool:
    result = conn.execute(
        text(
            """
            SELECT COUNT(*)
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = :table_name
              AND COLUMN_NAME = :column_name
            """
        ),
        {"table_name": table, "column_name": column_name},
    )
    return bool(result.scalar())


def _table_exists(conn, table: str) -> bool:
    result = conn.execute(
        text(
            """
            SELECT COUNT(*)
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = :table_name
            """
        ),
        {"table_name": table},
    )
    return bool(result.scalar())


def run_migration() -> None:
    from core.database import engine

    with engine.connect() as conn:
        if not _column_exists(conn, "email_templates", "library_source_id"):
            conn.execute(
                text(
                    """
                    ALTER TABLE email_templates
                    ADD COLUMN library_source_id INT NULL,
                    ADD INDEX ix_email_templates_library_source_id (library_source_id),
                    ADD CONSTRAINT fk_email_templates_library_source
                        FOREIGN KEY (library_source_id) REFERENCES email_templates(id)
                        ON DELETE SET NULL
                    """
                )
            )

        if not _table_exists(conn, "email_template_library_hides"):
            conn.execute(
                text(
                    """
                    CREATE TABLE email_template_library_hides (
                        id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
                        user_id INT NOT NULL,
                        library_template_id INT NOT NULL,
                        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE KEY uq_template_hide_user_library (user_id, library_template_id),
                        INDEX ix_email_template_library_hides_user_id (user_id),
                        INDEX ix_email_template_library_hides_library_template_id (library_template_id),
                        CONSTRAINT fk_template_hide_user
                            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                        CONSTRAINT fk_template_hide_library
                            FOREIGN KEY (library_template_id) REFERENCES email_templates(id) ON DELETE CASCADE
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                    """
                )
            )

        conn.commit()


if __name__ == "__main__":
    run_migration()
    print("email template forks and library hides ensured.")
