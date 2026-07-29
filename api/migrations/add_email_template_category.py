"""Migration — add ``email_templates.category`` and backfill it from the name.

Until now the step a template belonged to only lived in its name (« Relance J+3 »,
« J1 — Variante A »), so the app had no way to separate first emails from
follow-ups. The column makes it explicit and editable, including for templates
the user writes themselves.

Backfill rule: a template whose name mentions « relance » is a follow-up,
everything else is a first email — which matches every seeded name.

Idempotent: the ALTER is guarded by INFORMATION_SCHEMA, and the backfill only
targets rows still holding the default value.

Run with:
    python migrations/add_email_template_category.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text

from core.database import engine
from enums.email_template_category import EmailTemplateCategory


def _column_exists(conn, table: str, column: str) -> bool:
    """Return True when ``table.column`` already exists in the current schema."""
    result = conn.execute(
        text(
            "SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS "
            "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :t AND COLUMN_NAME = :c"
        ),
        {"t": table, "c": column},
    ).scalar()
    return bool(result)


def run_migration() -> None:
    """Add the category column and classify existing templates."""
    print("Running migration: add_email_template_category")

    with engine.begin() as conn:
        if _column_exists(conn, "email_templates", "category"):
            print("  ~ email_templates.category already exists")
        else:
            conn.execute(
                text(
                    "ALTER TABLE email_templates ADD COLUMN category VARCHAR(20) "
                    f"NOT NULL DEFAULT '{EmailTemplateCategory.FIRST_EMAIL.value}'"
                )
            )
            print("  + email_templates.category")

        # Only rows still on the default are reclassified, so a manual choice is never overwritten.
        updated = conn.execute(
            text(
                "UPDATE email_templates SET category = :follow_up "
                "WHERE category = :first_email AND LOWER(name) LIKE '%relance%'"
            ),
            {
                "follow_up": EmailTemplateCategory.FOLLOW_UP.value,
                "first_email": EmailTemplateCategory.FIRST_EMAIL.value,
            },
        ).rowcount
        print(f"  ~ {updated} template(s) classified as follow-up")

    print("Migration completed successfully.")


if __name__ == "__main__":
    print("=" * 60)
    print("Migration: Add email template category")
    print("=" * 60)
    run_migration()
