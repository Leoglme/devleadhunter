"""Migration — record why a queue row was skipped, and how long a follow-up waits.

``email_queue.skip_reason`` explains a skipped row on the campaign page (today: a
demo site that expires before its follow-up would leave).

``send_policies.follow_up_delay_days`` moves the follow-up delay next to the rest
of the sending cadence, counted in sending days rather than calendar days.

Idempotent: each ALTER is guarded by INFORMATION_SCHEMA.

Run with:
    python migrations/add_queue_skip_reason_and_follow_up_delay.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text

from core.database import engine

_COLUMNS: list[tuple[str, str, str]] = [
    ("email_queue", "skip_reason", "VARCHAR(160) NULL"),
    ("send_policies", "follow_up_delay_days", "INT NOT NULL DEFAULT 5"),
]


def _column_exists(conn, table: str, column: str) -> bool:
    """Return True when ``table.column`` already exists in the current schema."""
    result = conn.execute(
        text(
            "SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS "
            "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :t AND COLUMN_NAME = :c"
        ),
        {"t": table, "c": column},
    ).scalar()
    return bool(result)


def _table_exists(conn, table: str) -> bool:
    """Return True when ``table`` exists in the current schema."""
    result = conn.execute(
        text("SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :t"),
        {"t": table},
    ).scalar()
    return bool(result)


def run_migration() -> None:
    """Add the skip reason and the follow-up delay columns."""
    print("Running migration: add_queue_skip_reason_and_follow_up_delay")
    with engine.begin() as conn:
        for table, column, ddl in _COLUMNS:
            if not _table_exists(conn, table):
                continue
            if _column_exists(conn, table, column):
                print(f"  ~ {table}.{column} already exists")
                continue
            conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}"))
            print(f"  + {table}.{column}")
    print("Migration completed successfully.")


if __name__ == "__main__":
    run_migration()
