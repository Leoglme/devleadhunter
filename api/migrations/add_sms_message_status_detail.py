"""
Migration: add ``status_detail`` to ``sms_messages``.

Holds the human delivery reason from the smsmode DLR (e.g. ``UNDELIVERABLE`` /
``Spam`` / ``Numéro non attribué``) so a failed SMS shows *why* it failed.

Run with:
    python migrations/add_sms_message_status_detail.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text

from core.database import engine


def run_migration() -> None:
    print("Running migration: add_sms_message_status_detail")
    with engine.connect() as conn:
        conn.execute(
            text("ALTER TABLE sms_messages ADD COLUMN IF NOT EXISTS status_detail VARCHAR(255) NULL AFTER status")
        )
        conn.commit()
    print("  + sms_messages.status_detail")
    print("Migration completed successfully.")


if __name__ == "__main__":
    print("=" * 60)
    print("Migration: Add sms_messages.status_detail")
    print("=" * 60)
    run_migration()
