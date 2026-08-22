"""Migration: create ``notifications`` (persisted in-app notification log).

One row per notification raised by the app, attributed to a user, kept even when
no Web Push is delivered. Idempotent — creating the table is a no-op when it
already exists.

Run with:
    python migrations/add_notifications_table.py
"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from core.database import engine
from models.notification import Notification


def run_migration() -> None:
    # Create the notifications table (no-op if it already exists).
    Notification.__table__.create(engine, checkfirst=True)


if __name__ == "__main__":
    run_migration()
    print("notifications ensured.")
