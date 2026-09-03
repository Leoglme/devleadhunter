"""
Migration: estimate the cost of already-sent SMS with no recorded price.

smsmode does not return a price on send, so every ``sms_messages`` row created
before the estimate fallback shipped has ``price_cents = NULL`` and the « Coût
total » tile showed 0 €. This backfills a segment-based estimate (billed
segments x ``SMSMODE_PRICE_PER_SEGMENT_EUR``) on the rows that actually reached
the provider (sent / delivered), leaving failed and pending sends untouched.

Run with:
    python migrations/backfill_sms_price_estimate.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text

from core.config import settings
from core.database import engine


def run_migration() -> None:
    print("Running migration: backfill_sms_price_estimate")
    price_per_segment_eur = settings.smsmode_price_per_segment_eur
    with engine.connect() as conn:
        result = conn.execute(
            text(
                "UPDATE sms_messages "
                "SET price_cents = ROUND(GREATEST(segments, 1) * :price_per_segment_eur * 100) "
                "WHERE price_cents IS NULL AND status IN ('sent', 'delivered')"
            ),
            {"price_per_segment_eur": price_per_segment_eur},
        )
        conn.commit()
    print(f"  + estimated price on {result.rowcount} SMS ({price_per_segment_eur} €/segment)")
    print("Migration completed successfully.")


if __name__ == "__main__":
    print("=" * 60)
    print("Migration: Backfill sms_messages.price_cents estimate")
    print("=" * 60)
    run_migration()
