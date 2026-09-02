"""
Migration: ``email_replies.inbox_forwarded_at`` — idempotent inbox copy timestamp.

Run with:
    python migrations/add_email_reply_inbox_forwarded_at.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text

from core.database import engine


def run_migration() -> None:
    print("Running migration: add_email_reply_inbox_forwarded_at")
    with engine.connect() as conn:
        conn.execute(
            text(
                "ALTER TABLE email_replies "
                "ADD COLUMN IF NOT EXISTS inbox_forwarded_at DATETIME NULL AFTER handled_at"
            )
        )
        conn.commit()
    print("  + email_replies.inbox_forwarded_at")
    print("Migration completed successfully.")


if __name__ == "__main__":
    print("=" * 60)
    print("Migration: email_replies.inbox_forwarded_at")
    print("=" * 60)
    run_migration()
