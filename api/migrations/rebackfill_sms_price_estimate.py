"""
Migration: recompute the estimated SMS cost at the real per-segment rate.

The first backfill used a 0.045 €/segment placeholder; the real smsmode rate is
0.061 €/segment (``SMSMODE_PRICE_PER_SEGMENT_EUR``). Since smsmode returns no
price on send, every recorded cost is an estimate, so this recomputes them all
for the rows that reached the provider (sent / delivered). Runs once, now, while
no row carries a real provider price to preserve.

Run with:
    python migrations/rebackfill_sms_price_estimate.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text

from core.config import settings
from core.database import engine


def run_migration() -> None:
    print("Running migration: rebackfill_sms_price_estimate")
    price_per_segment_eur = settings.smsmode_price_per_segment_eur
    with engine.connect() as conn:
        result = conn.execute(
            text(
                "UPDATE sms_messages "
                "SET price_cents = ROUND(GREATEST(segments, 1) * :price_per_segment_eur * 100) "
                "WHERE status IN ('sent', 'delivered')"
            ),
            {"price_per_segment_eur": price_per_segment_eur},
        )
        conn.commit()
    print(f"  + recomputed price on {result.rowcount} SMS ({price_per_segment_eur} €/segment)")
    print("Migration completed successfully.")


if __name__ == "__main__":
    print("=" * 60)
    print("Migration: Recompute sms_messages.price_cents at the real rate")
    print("=" * 60)
    run_migration()
