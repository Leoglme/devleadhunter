"""Migration — convert every legacy latin1 table to utf8mb4.

Some tables were created while the MySQL server default was still latin1. Any
string comparison against them then fails at runtime:

    (1267, "Illegal mix of collations (latin1_swedish_ci,IMPLICIT)
            and (utf8mb4_general_ci,COERCIBLE) for operation '='")

That is what silently broke the email template seeder on every deploy: the error
was caught and logged, so the deploy stayed green while production never got its
templates.

Idempotent: only tables that still hold a non-utf8mb4 charset are touched, so a
second run finds nothing to do.

Run with:
    python migrations/fix_utf8mb4_collation.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text

from core.database import engine

_TARGET_CHARSET = "utf8mb4"
_TARGET_COLLATION = "utf8mb4_unicode_ci"

# A table is stale when its own collation is not utf8mb4, or when any of its
# character columns kept an older charset (CONVERT TO fixes both at once).
_STALE_TABLES_SQL = """
SELECT DISTINCT t.TABLE_NAME
FROM INFORMATION_SCHEMA.TABLES t
LEFT JOIN INFORMATION_SCHEMA.COLUMNS c
       ON c.TABLE_SCHEMA = t.TABLE_SCHEMA
      AND c.TABLE_NAME = t.TABLE_NAME
WHERE t.TABLE_SCHEMA = DATABASE()
  AND t.TABLE_TYPE = 'BASE TABLE'
  AND (
        t.TABLE_COLLATION NOT LIKE :collation_prefix
     OR (c.CHARACTER_SET_NAME IS NOT NULL AND c.CHARACTER_SET_NAME <> :charset)
      )
ORDER BY t.TABLE_NAME
"""


def run_migration() -> None:
    """Convert every table still holding a legacy charset to utf8mb4."""
    print("Running migration: fix_utf8mb4_collation")

    with engine.connect() as conn:
        stale_tables = [
            row[0]
            for row in conn.execute(
                text(_STALE_TABLES_SQL),
                {"collation_prefix": f"{_TARGET_CHARSET}%", "charset": _TARGET_CHARSET},
            ).all()
        ]

        if not stale_tables:
            print(f"  ~ every table is already in {_TARGET_CHARSET}")
        for table in stale_tables:
            # Identifiers cannot be bound as parameters; they come from
            # INFORMATION_SCHEMA, so they are server-provided, not user input.
            conn.execute(
                text(f"ALTER TABLE `{table}` CONVERT TO CHARACTER SET {_TARGET_CHARSET} COLLATE {_TARGET_COLLATION}")
            )
            print(f"  + {table} -> {_TARGET_COLLATION}")

        conn.commit()

    # Future tables created by create_all inherit the schema default, so fix it
    # too — otherwise the same drift reappears with the next new table.
    try:
        with engine.connect() as conn:
            conn.execute(
                text(
                    f"ALTER DATABASE `{conn.engine.url.database}` "
                    f"CHARACTER SET {_TARGET_CHARSET} COLLATE {_TARGET_COLLATION}"
                )
            )
            conn.commit()
        print(f"  + schema default -> {_TARGET_COLLATION}")
    # Preventive only (the table conversions above are the actual fix), so a
    # missing ALTER privilege must never fail the deploy.
    except Exception as exc:
        print(f"  [WARN] schema default left unchanged ({exc.__class__.__name__}): {exc}")

    print(f"Migration completed successfully ({len(stale_tables)} table(s) converted).")


if __name__ == "__main__":
    print("=" * 60)
    print("Migration: Fix utf8mb4 collation")
    print("=" * 60)
    run_migration()
