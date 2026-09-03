"""
Migration: add the SMS automation opt-in columns to ``sms_configs``.

Two opt-in switches (off by default) plus the relance delay: cold-SMS a prospect
who has a mobile but no email, and auto-relance an emailed prospect who never
reacted. Both stay manual until the user turns them on in Paramètres → Relance SMS.

Run with:
    python migrations/add_sms_config_automation.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text

from core.database import engine


def run_migration() -> None:
    print("Running migration: add_sms_config_automation")
    with engine.connect() as conn:
        conn.execute(
            text("ALTER TABLE sms_configs ADD COLUMN IF NOT EXISTS cold_sms_enabled TINYINT(1) NOT NULL DEFAULT 0")
        )
        conn.execute(
            text("ALTER TABLE sms_configs ADD COLUMN IF NOT EXISTS auto_relance_enabled TINYINT(1) NOT NULL DEFAULT 0")
        )
        conn.execute(
            text("ALTER TABLE sms_configs ADD COLUMN IF NOT EXISTS auto_relance_after_days INT NOT NULL DEFAULT 30")
        )
        conn.commit()
    print("  + sms_configs.cold_sms_enabled / auto_relance_enabled / auto_relance_after_days")
    print("Migration completed successfully.")


if __name__ == "__main__":
    print("=" * 60)
    print("Migration: Add sms_configs automation columns")
    print("=" * 60)
    run_migration()
