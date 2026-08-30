"""
Migration: create the SMS tables (config, messages, suppressions).

Backs the SMS relance channel: per-user sender config, a log of sent SMS, and
the STOP opt-out list.

Run with:
    python migrations/add_sms_tables.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import engine
from models.sms_config import SmsConfig
from models.sms_message import SmsMessage
from models.sms_suppression import SmsSuppression


def run_migration() -> None:
    print("Running migration: add_sms_tables")
    SmsConfig.__table__.create(engine, checkfirst=True)
    SmsMessage.__table__.create(engine, checkfirst=True)
    SmsSuppression.__table__.create(engine, checkfirst=True)
    print("  + sms_configs, sms_messages, sms_suppressions")
    print("Migration completed successfully.")


if __name__ == "__main__":
    print("=" * 60)
    print("Migration: Add SMS tables")
    print("=" * 60)
    run_migration()
