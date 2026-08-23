"""Reclassify historical machine-only opens as delivered.

An email whose only open landed within 60 s of delivery (and was never reopened)
was a Gmail/scanner pixel prefetch, not a human read. This corrects such rows in
bulk by timing — independent of any id/recipient — so it fixes the wave-1 email
the id-based backfill missed, and any similar historical row.
"""

from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import text

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from core.database import engine

# Same window as the live webhook classifier (webhooks._MACHINE_OPEN_WINDOW_SECONDS).
_MACHINE_OPEN_WINDOW_SECONDS = 60


def run_migration() -> None:
    with engine.connect() as conn:
        conn.execute(
            text(
                """
                UPDATE email_logs
                SET machine_opened_at = COALESCE(machine_opened_at, opened_at),
                    opened_at = NULL,
                    last_open_at = NULL,
                    open_count = 0,
                    status = 'delivered'
                WHERE status = 'opened'
                  AND opened_at IS NOT NULL
                  AND open_count <= 1
                  AND COALESCE(delivered_at, sent_at) IS NOT NULL
                  AND TIMESTAMPDIFF(SECOND, COALESCE(delivered_at, sent_at), opened_at) <= :window
                """
            ),
            {"window": _MACHINE_OPEN_WINDOW_SECONDS},
        )
        conn.commit()


if __name__ == "__main__":
    run_migration()
    print("Historical machine-only opens reclassified as delivered.")
