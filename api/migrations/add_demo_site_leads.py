"""
Migration: create the demo_site_leads table.

Stores the leads left through the « Ce site vous plaît ? » banner on live demo
pages — durable, attached to the prospect, unlike notifications (purged ~90 d).

Run with:
    python migrations/add_demo_site_leads.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import engine
from models.demo_site_lead import DemoSiteLead


def run_migration() -> None:
    print("Running migration: add_demo_site_leads")
    DemoSiteLead.__table__.create(engine, checkfirst=True)
    print("  + demo_site_leads table")
    print("Migration completed successfully.")


if __name__ == "__main__":
    print("=" * 60)
    print("Migration: Add demo_site_leads table")
    print("=" * 60)
    run_migration()
