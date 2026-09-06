"""
Migration: add the relance template choice to ``sms_configs``.

A J+30 SMS relance renders a template of the SMS library; each user picks which
one in Paramètres → Relance SMS. Existing rows get « Rappel court », the default.

Run with:
    python migrations/add_sms_config_relance_template.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text

from core.database import engine


def run_migration() -> None:
    print("Running migration: add_sms_config_relance_template")
    with engine.connect() as conn:
        conn.execute(
            text(
                "ALTER TABLE sms_configs ADD COLUMN IF NOT EXISTS relance_template_key "
                "VARCHAR(64) NOT NULL DEFAULT 'rappel-court'"
            )
        )
        conn.commit()
    print("  + sms_configs.relance_template_key")
    print("Migration completed successfully.")


if __name__ == "__main__":
    print("=" * 60)
    print("Migration: Add sms_configs.relance_template_key")
    print("=" * 60)
    run_migration()
