"""
Migration: add ``recipient_name`` to ``sms_messages``.

A manual SMS can be sent to a bare number (no saved prospect), so the send needs
its own display label — mirrors ``email_logs.recipient_name``.

Run with:
    python migrations/add_sms_message_recipient_name.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text

from core.database import engine


def run_migration() -> None:
    print("Running migration: add_sms_message_recipient_name")
    with engine.connect() as conn:
        conn.execute(
            text("ALTER TABLE sms_messages ADD COLUMN IF NOT EXISTS recipient_name VARCHAR(255) NULL AFTER prospect_id")
        )
        conn.commit()
    print("  + sms_messages.recipient_name")
    print("Migration completed successfully.")


if __name__ == "__main__":
    print("=" * 60)
    print("Migration: Add sms_messages.recipient_name")
    print("=" * 60)
    run_migration()
