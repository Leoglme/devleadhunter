"""
Migration: LLM intent classification on prospect replies.

``email_replies.intent`` — one of interested / not_interested / later / question /
unsubscribe / other, classified ONCE by Groq at capture and persisted (never
re-asked for the same reply).

``email_replies.content_sha`` — SHA-256 of the reply text, so an identical body
(duplicate out-of-office, webhook edge cases) reuses the stored verdict instead
of spending a second LLM call.

Run with:
    python migrations/add_reply_intent.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text

from core.database import engine


def run_migration() -> None:
    print("Running migration: add_reply_intent")
    with engine.connect() as conn:
        conn.execute(
            text("ALTER TABLE email_replies ADD COLUMN IF NOT EXISTS intent VARCHAR(20) NULL AFTER handled_at")
        )
        conn.execute(text("ALTER TABLE email_replies ADD COLUMN IF NOT EXISTS content_sha CHAR(64) NULL AFTER intent"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_email_replies_content_sha ON email_replies (content_sha)"))
        conn.commit()
    print("  + email_replies.intent")
    print("  + email_replies.content_sha (+ index)")
    print("Migration completed successfully.")


if __name__ == "__main__":
    print("=" * 60)
    print("Migration: Reply intent classification")
    print("=" * 60)
    run_migration()
