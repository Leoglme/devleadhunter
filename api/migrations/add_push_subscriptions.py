"""Migration: create ``push_subscriptions`` (Web Push / VAPID device endpoints).

One row per browser / PWA install a user subscribed for mobile notifications.
Idempotent — creating the table is a no-op when it already exists.

Run with:
    python migrations/add_push_subscriptions.py
"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from core.database import engine
from models.push_subscription import PushSubscription


def run_migration() -> None:
    # Create the push_subscriptions table (no-op if it already exists).
    PushSubscription.__table__.create(engine, checkfirst=True)


if __name__ == "__main__":
    run_migration()
    print("push_subscriptions ensured.")
