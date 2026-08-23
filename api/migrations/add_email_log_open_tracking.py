"""Add human-open tracking to email_logs + backfill the first real campaign.

Splits machine prefetch from human reads: ``opened_at`` now means the first HUMAN
open, ``machine_opened_at`` holds the delivery-time pixel prefetch, and
``open_count`` / ``last_open_at`` track reopens. Backfills the 3 wave-1 emails from
their Resend dashboard event timelines (the per-open history is not re-fetchable
via the API, only readable in the dashboard).
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

from sqlalchemy import text

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from core.database import engine

# Wave-1 emails corrected from the Resend dashboard event timelines (naive UTC).
# Guarded by recipient so a dev database with different rows at these ids is left untouched.
_WAVE1_BACKFILL: tuple[dict[str, object], ...] = (
    {
        "id": 19,
        "recipient": "niortauto@gmail.com",
        "status": "delivered",  # only a machine prefetch fired — no human read
        "opened_at": None,
        "open_count": 0,
        "last_open_at": None,
        "machine_opened_at": datetime(2026, 8, 21, 9, 47, 21),
    },
    {
        "id": 20,
        "recipient": "contact@my-coiffure.fr",
        "status": "opened",
        "opened_at": datetime(2026, 8, 21, 10, 28, 0),
        "open_count": 2,
        "last_open_at": datetime(2026, 8, 21, 16, 30, 0),
        "machine_opened_at": None,
    },
    {
        "id": 21,
        "recipient": "foodtruckmexicaintacosmaru@gmail.com",
        "status": "opened",
        "opened_at": datetime(2026, 8, 21, 11, 33, 0),
        "open_count": 5,
        "last_open_at": datetime(2026, 8, 21, 17, 41, 0),
        "machine_opened_at": datetime(2026, 8, 21, 10, 27, 30),
    },
)


def _column_exists(conn, column_name: str) -> bool:
    result = conn.execute(
        text(
            """
            SELECT COUNT(*)
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = 'email_logs'
              AND COLUMN_NAME = :column_name
            """
        ),
        {"column_name": column_name},
    )
    return bool(result.scalar())


def _add_columns(conn) -> None:
    if not _column_exists(conn, "open_count"):
        conn.execute(text("ALTER TABLE email_logs ADD COLUMN open_count INT NOT NULL DEFAULT 0"))
    if not _column_exists(conn, "machine_opened_at"):
        conn.execute(text("ALTER TABLE email_logs ADD COLUMN machine_opened_at DATETIME NULL"))
    if not _column_exists(conn, "last_open_at"):
        conn.execute(text("ALTER TABLE email_logs ADD COLUMN last_open_at DATETIME NULL"))


def _backfill(conn) -> None:
    # Every already-opened email counts as at least one human open so the UI never shows "×0".
    conn.execute(text("UPDATE email_logs SET open_count = 1 WHERE opened_at IS NOT NULL AND open_count = 0"))
    # Precise wave-1 correction — overrides the generic pass above.
    for row in _WAVE1_BACKFILL:
        conn.execute(
            text(
                """
                UPDATE email_logs
                SET status = :status,
                    opened_at = :opened_at,
                    open_count = :open_count,
                    last_open_at = :last_open_at,
                    machine_opened_at = :machine_opened_at
                WHERE id = :id AND recipient_email = :recipient
                """
            ),
            row,
        )


def run_migration() -> None:
    with engine.connect() as conn:
        _add_columns(conn)
        _backfill(conn)
        conn.commit()


if __name__ == "__main__":
    run_migration()
    print("email_logs open-tracking columns ensured and wave-1 opens backfilled.")
