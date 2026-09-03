"""
Migration: add the « ne plus contacter » columns to ``prospects``.

An operator decision to stop all outreach to a prospect (e.g. he said no by phone):
a flag, an optional reason, and when it was set. Blocks campaign enqueue + dispatch
and SMS relance/cold — distinct from the prospect-driven opt-outs (STOP / unsubscribe).

Run with:
    python migrations/add_prospect_do_not_contact.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text

from core.database import engine


def run_migration() -> None:
    print("Running migration: add_prospect_do_not_contact")
    with engine.connect() as conn:
        conn.execute(
            text("ALTER TABLE prospects ADD COLUMN IF NOT EXISTS do_not_contact TINYINT(1) NOT NULL DEFAULT 0")
        )
        conn.execute(text("ALTER TABLE prospects ADD COLUMN IF NOT EXISTS do_not_contact_reason VARCHAR(500) NULL"))
        conn.execute(text("ALTER TABLE prospects ADD COLUMN IF NOT EXISTS do_not_contact_at DATETIME NULL"))
        conn.commit()
    print("  + prospects.do_not_contact / do_not_contact_reason / do_not_contact_at")
    print("Migration completed successfully.")


if __name__ == "__main__":
    print("=" * 60)
    print("Migration: Add prospects do-not-contact columns")
    print("=" * 60)
    run_migration()
