"""Backfill demo URLs from the dev preview host to the canonical public host.

``demo_url`` used to be built from ``DEMO_HOST_BASE_URL``, which fell back to
``http://localhost:3001`` in every environment where the variable was unset —
production included. That shipped dead ``localhost`` links in ``{lien_demo}`` /
``{lien_video}`` and made live sites read as "offline" in the dashboard.

This one-off rewrites those rows to ``PUBLIC_DEMO_HOST_BASE_URL`` (reconstructed
from the slug) and restores the live state for sites that carry content — the
public demo-host serves every active slug, so a site flagged "unavailable" only
because its ``demo_url`` pointed at localhost is really live.
"""

from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import text

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from core.config import settings
from core.database import engine
from enums.demo_site_status import DemoSiteStatus


def run_migration() -> None:
    """Rewrite localhost demo URLs to the public host and refresh the live state."""
    public_base: str = settings.public_demo_host_base_url.rstrip("/")

    with engine.begin() as conn:
        # 1) Rewrite the stored URLs, rebuilding each from its slug so any localhost
        #    host/port variant collapses to the canonical public host.
        conn.execute(
            text(
                """
                UPDATE demo_sites
                SET demo_url = CONCAT(:base, '/', slug)
                WHERE demo_url LIKE 'http://localhost%' OR demo_url LIKE 'http://127.0.0.1%'
                """
            ),
            {"base": public_base},
        )
        conn.execute(
            text(
                """
                UPDATE demo_sites
                SET vercel_deployment_url = CONCAT(:base, '/', slug)
                WHERE vercel_deployment_url LIKE 'http://localhost%'
                   OR vercel_deployment_url LIKE 'http://127.0.0.1%'
                """
            ),
            {"base": public_base},
        )

        # 2) A site that only read "offline" because its demo_url pointed at localhost is
        #    actually served at demo.dibodev.fr/{slug}. Restore its live state so the
        #    dashboard reflects reality (a manual re-verification refreshes it either way).
        conn.execute(
            text(
                """
                UPDATE demo_sites
                SET status = :active,
                    demo_url_live = 1,
                    local_demo_url = NULL,
                    verification_message = 'Demo site is live and reachable.',
                    error_message = NULL
                WHERE (status = :active OR status = :unavailable)
                  AND content_json IS NOT NULL
                  AND demo_url LIKE :public_prefix
                """
            ),
            {
                "active": DemoSiteStatus.ACTIVE.value,
                "unavailable": DemoSiteStatus.UNAVAILABLE.value,
                "public_prefix": f"{public_base}/%",
            },
        )


if __name__ == "__main__":
    run_migration()
    print("Demo URLs backfilled to the public host.")
