"""
Migration: conversation state for prospect replies.

``email_replies.handled_at`` — when the user dealt with the reply (answered from
the app, or marked handled after replying from their own mailbox). A human reply
with ``handled_at IS NULL`` is « à traiter ».

``email_logs.is_conversation_reply`` — marks sends that are direct answers to a
prospect's reply (threaded from the app). Those are correspondence, not outreach:
they are excluded from the outreach funnel stats.

Run with:
    python migrations/add_reply_conversations.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text

from core.database import engine


def run_migration() -> None:
    print("Running migration: add_reply_conversations")
    with engine.connect() as conn:
        conn.execute(
            text("ALTER TABLE email_replies ADD COLUMN IF NOT EXISTS handled_at DATETIME NULL AFTER received_at")
        )
        conn.execute(
            text(
                "ALTER TABLE email_logs ADD COLUMN IF NOT EXISTS is_conversation_reply TINYINT(1) NOT NULL DEFAULT 0"
                " AFTER ab_variant"
            )
        )
        conn.commit()
    print("  + email_replies.handled_at")
    print("  + email_logs.is_conversation_reply")
    print("Migration completed successfully.")


if __name__ == "__main__":
    print("=" * 60)
    print("Migration: Reply conversation state")
    print("=" * 60)
    run_migration()
