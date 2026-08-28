"""
Migration: purge the facebook_page_exclusions table.

The first live runs of the Facebook match filter blacklisted pages from
enrichments that had silently returned EMPTY payloads (browser never actually
read the page), so every recorded exclusion is untrustworthy. The empty-payload
guard now fails such scrapes instead of persisting them — wipe the poisoned
rows so pages get a real test on the next search.

Run with:
    python migrations/purge_facebook_page_exclusions.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text

from core.database import engine


def run_migration() -> None:
    print("Running migration: purge_facebook_page_exclusions")
    with engine.connect() as conn:
        result = conn.execute(text("DELETE FROM facebook_page_exclusions"))
        conn.commit()
    print(f"  - {result.rowcount} poisoned exclusion(s) removed")
    print("Migration completed successfully.")


if __name__ == "__main__":
    print("=" * 60)
    print("Migration: Purge facebook_page_exclusions")
    print("=" * 60)
    run_migration()
