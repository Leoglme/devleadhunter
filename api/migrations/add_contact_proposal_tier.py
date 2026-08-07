"""Add the « à confirmer » contact tier + provenance columns, and reclassify.

Names auto-resolved under the old single-threshold rules (no primary-source
gate, no geo requirement) are downgraded to PENDING PROPOSALS: they stop
feeding « Bonjour {Prénom} » until a human confirms them or a re-run of the
new cascade re-promotes them. Manually-set names are left untouched.
"""

from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import text

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from core.database import engine


def _column_exists(conn, column_name: str) -> bool:
    result = conn.execute(
        text(
            """
            SELECT COUNT(*)
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = 'prospect_enrichments'
              AND COLUMN_NAME = :column_name
            """
        ),
        {"column_name": column_name},
    )
    return bool(result.scalar())


def run_migration() -> None:
    with engine.connect() as conn:
        if not _column_exists(conn, "proposed_first_name"):
            conn.execute(
                text(
                    """
                    ALTER TABLE prospect_enrichments
                    ADD COLUMN contact_name_status VARCHAR(16) NULL,
                    ADD COLUMN contact_name_provenance VARCHAR(500) NULL,
                    ADD COLUMN contact_siren VARCHAR(20) NULL,
                    ADD COLUMN proposed_first_name VARCHAR(120) NULL,
                    ADD COLUMN proposed_last_name VARCHAR(120) NULL,
                    ADD COLUMN proposed_gender VARCHAR(1) NULL,
                    ADD COLUMN proposed_source VARCHAR(50) NULL,
                    ADD COLUMN proposed_confidence FLOAT NULL,
                    ADD COLUMN proposed_provenance VARCHAR(500) NULL,
                    ADD COLUMN proposed_state VARCHAR(16) NULL,
                    ADD COLUMN name_candidates JSON NULL
                    """
                )
            )

        # Manually-set names stay trusted, just labelled.
        conn.execute(
            text(
                """
                UPDATE prospect_enrichments
                SET contact_name_status = 'manual'
                WHERE contact_name_manual = 1
                  AND (contact_first_name IS NOT NULL OR contact_last_name IS NOT NULL)
                  AND contact_name_status IS NULL
                """
            )
        )

        # Machine-resolved names predate the primary-source + geo gates: move
        # them to pending proposals and stop using them in emails right away.
        conn.execute(
            text(
                """
                UPDATE prospect_enrichments
                SET proposed_first_name = contact_first_name,
                    proposed_last_name = contact_last_name,
                    proposed_gender = contact_gender,
                    proposed_source = contact_name_source,
                    proposed_confidence = contact_name_confidence,
                    proposed_provenance = 'Repris de l''ancienne résolution automatique (avant durcissement des règles)',
                    proposed_state = 'pending',
                    contact_first_name = NULL,
                    contact_last_name = NULL,
                    contact_gender = NULL,
                    contact_name_source = NULL,
                    contact_name_confidence = NULL
                WHERE contact_name_manual = 0
                  AND (contact_first_name IS NOT NULL OR contact_last_name IS NOT NULL)
                  AND contact_name_status IS NULL
                """
            )
        )
        conn.commit()


if __name__ == "__main__":
    run_migration()
