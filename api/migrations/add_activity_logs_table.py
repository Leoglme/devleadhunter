"""
Migration: create the ``activity_logs`` table (admin monitoring feed).

One append-only row per meaningful action (email / SMS / demo / sale / scraping /
prospect / site / campaign / error). The table is created from the SQLAlchemy
model so the schema stays the single source of truth.

Run with:
    python migrations/add_activity_logs_table.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import engine
from models.activity_log import ActivityLog


def run_migration() -> None:
    print("Running migration: add_activity_logs_table")
    ActivityLog.__table__.create(engine, checkfirst=True)
    print("  + activity_logs")
    print("Migration completed successfully.")


if __name__ == "__main__":
    print("=" * 60)
    print("Migration: Add activity_logs table")
    print("=" * 60)
    run_migration()
