"""Introduce SUPER_ADMIN, optional company name, and shared email-template library.

- Existing ``ADMIN`` rows become ``SUPER_ADMIN`` (platform owner).
- ``users.company_name`` stores the optional business label used in AI prompts and UI placeholders.
- ``email_templates.is_library`` marks the canonical cold-email library visible to every user.
"""

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


def run_migration() -> None:
    from core.database import engine

    with engine.connect() as conn:
        conn.execute(text("UPDATE users SET role = 'SUPER_ADMIN' WHERE role = 'ADMIN'"))

        if not _column_exists(conn, "users", "company_name"):
            conn.execute(
                text(
                    """
                    ALTER TABLE users
                    ADD COLUMN company_name VARCHAR(255) NULL
                    """
                )
            )

        if not _column_exists(conn, "email_templates", "is_library"):
            conn.execute(
                text(
                    """
                    ALTER TABLE email_templates
                    ADD COLUMN is_library TINYINT(1) NOT NULL DEFAULT 0
                    """
                )
            )
            # Every template owned by a super-admin becomes part of the shared library.
            conn.execute(
                text(
                    """
                    UPDATE email_templates et
                    INNER JOIN users u ON u.id = et.user_id
                    SET et.is_library = 1
                    WHERE u.role = 'SUPER_ADMIN'
                    """
                )
            )

        conn.commit()


if __name__ == "__main__":
    run_migration()
    print("SUPER_ADMIN role, company_name and is_library ensured.")
