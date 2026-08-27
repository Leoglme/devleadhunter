"""
Migration: create the facebook_page_exclusions table.

Stores the Facebook pages rejected by the discovery match filter (no email /
has a website) so a later search never re-enriches the same page.

Run with:
    python migrations/add_facebook_page_exclusions.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import engine
from models.facebook_exclusion import FacebookPageExclusion


def run_migration() -> None:
    print("Running migration: add_facebook_page_exclusions")
    FacebookPageExclusion.__table__.create(engine, checkfirst=True)
    print("  + facebook_page_exclusions table")
    print("Migration completed successfully.")


if __name__ == "__main__":
    print("=" * 60)
    print("Migration: Add facebook_page_exclusions table")
    print("=" * 60)
    run_migration()
