"""Add demo_link_sent_at and backfill TTL: starts on first emailed demo link, not at generation."""

from __future__ import annotations

import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy import text

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from core.config import settings
from core.database import engine

_PENDING_TTL_EXPIRES = datetime(2099, 12, 31, 23, 59, 59)


def _column_exists(conn, column_name: str) -> bool:
    result = conn.execute(
        text(
            """
            SELECT COUNT(*)
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = 'demo_sites'
              AND COLUMN_NAME = :column_name
            """
        ),
        {"column_name": column_name},
    )
    return bool(result.scalar())


def _backfill_ttl(conn) -> None:
    """Sites already emailed keep TTL from first send; others wait until the link goes out."""
    ttl_days: int = settings.demo_site_ttl_days
    sites = (
        conn.execute(
            text(
                """
            SELECT id, slug, demo_url, prospect_id, user_id, status
            FROM demo_sites
            WHERE status IN ('active', 'unavailable', 'pending', 'provisioning', 'failed')
            """
            )
        )
        .mappings()
        .all()
    )

    for site in sites:
        slug: str = site["slug"] or ""
        prospect_id = site["prospect_id"]
        user_id = site["user_id"]
        first_sent = None

        if prospect_id is not None:
            first_sent = conn.execute(
                text(
                    """
                    SELECT MIN(sent_at)
                    FROM email_logs
                    WHERE user_id = :user_id
                      AND prospect_id = :prospect_id
                      AND status = 'sent'
                      AND sent_at IS NOT NULL
                      AND (
                        body_html LIKE :slug_needle
                        OR (:demo_url <> '' AND body_html LIKE :demo_needle)
                      )
                    """
                ),
                {
                    "user_id": user_id,
                    "prospect_id": prospect_id,
                    "slug_needle": f"%/{slug}%",
                    "demo_url": site["demo_url"] or "",
                    "demo_needle": f"%{site['demo_url']}%" if site["demo_url"] else "",
                },
            ).scalar()

        if first_sent:
            sent_at = first_sent.replace(tzinfo=UTC) if first_sent.tzinfo is None else first_sent.astimezone(UTC)
            expires_at = sent_at + timedelta(days=ttl_days)
            conn.execute(
                text(
                    """
                    UPDATE demo_sites
                    SET demo_link_sent_at = :sent_at, expires_at = :expires_at
                    WHERE id = :id
                    """
                ),
                {
                    "id": site["id"],
                    "sent_at": sent_at.replace(tzinfo=None),
                    "expires_at": expires_at.replace(tzinfo=None),
                },
            )
        else:
            conn.execute(
                text(
                    """
                    UPDATE demo_sites
                    SET demo_link_sent_at = NULL, expires_at = :expires_at
                    WHERE id = :id
                    """
                ),
                {"id": site["id"], "expires_at": _PENDING_TTL_EXPIRES.replace(tzinfo=None)},
            )


def run_migration() -> None:
    with engine.connect() as conn:
        if not _column_exists(conn, "demo_link_sent_at"):
            conn.execute(
                text(
                    """
                    ALTER TABLE demo_sites
                    ADD COLUMN demo_link_sent_at DATETIME NULL
                    """
                )
            )
        _backfill_ttl(conn)
        conn.commit()


if __name__ == "__main__":
    run_migration()
    print("demo_sites.demo_link_sent_at column ensured and TTL backfilled.")
