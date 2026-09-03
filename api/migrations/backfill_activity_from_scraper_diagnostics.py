"""
Migration: seed the activity feed with the existing scraper diagnostics.

The monitoring page moved from a scraper-only journal to a unified activity
feed backed by ``activity_logs``. That table starts empty, so the historical
scraping/enrichment runs (hundreds of rows in ``scraper_diagnostics``) would
vanish from the page. This copies each diagnostic into the feed with the exact
same mapping as ``scraper_diagnostics_service._log_activity`` — original
timestamp preserved, and the « Voir le HTML » drill-down kept for blocked runs.

Single atomic ``INSERT ... SELECT`` so a failure leaves nothing behind.

Run with:
    python migrations/backfill_activity_from_scraper_diagnostics.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text

from core.database import engine

_INSERT_SQL = """
INSERT INTO activity_logs (user_id, category, action, status, title, detail, entity_type, entity_id, created_at)
SELECT
    sd.user_id,
    'scraping',
    CONCAT('scraping_', sd.status),
    CASE sd.status WHEN 'ok' THEN 'success' WHEN 'empty' THEN 'warning' ELSE 'error' END,
    LEFT(
        CONCAT(
            sd.source,
            COALESCE(CONCAT(' · ', NULLIF(TRIM(CONCAT_WS(' ', sd.category, sd.city)), '')), ''),
            CASE WHEN sd.status = 'ok' THEN CONCAT(' — ', sd.results_count, ' résultat(s)') ELSE '' END
        ),
        255
    ),
    sd.error_message,
    CASE WHEN sd.html_snapshot IS NOT NULL THEN 'scraper_diagnostic' ELSE NULL END,
    CASE WHEN sd.html_snapshot IS NOT NULL THEN sd.id ELSE NULL END,
    sd.created_at
FROM scraper_diagnostics sd
"""


def run_migration() -> None:
    print("Running migration: backfill_activity_from_scraper_diagnostics")
    with engine.connect() as conn:
        result = conn.execute(text(_INSERT_SQL))
        conn.commit()
    print(f"  + seeded {result.rowcount} scraping runs into the activity feed")
    print("Migration completed successfully.")


if __name__ == "__main__":
    print("=" * 60)
    print("Migration: Backfill activity_logs from scraper_diagnostics")
    print("=" * 60)
    run_migration()
