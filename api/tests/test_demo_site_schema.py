"""Guard: DemoSiteResponse must expose prospect_id.

The prospect drawer matches a demo to its prospect client-side with
`site.prospect_id === prospect.id`. When the response schema omitted the field,
every prospect showed "Aucun site démo pour ce prospect" even with a demo linked,
because `site.prospect_id` was always undefined. This locks the field in.
"""

from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace

from schemas.demo_site import DemoSiteResponse


def test_demo_site_response_exposes_prospect_id() -> None:
    """The serialized demo site carries prospect_id so the drawer can match it."""
    site = SimpleNamespace(
        id=1,
        slug="my-coiffure-by-damien-cailler",
        prospect_id=22,
        template_id="barber-x",
        business_name="My Coiffure",
        status="active",
        expires_at=datetime(2026, 9, 1),
        created_at=datetime(2026, 8, 1),
    )
    dumped = DemoSiteResponse.model_validate(site).model_dump()
    assert dumped["prospect_id"] == 22


def test_demo_site_response_prospect_id_defaults_to_none() -> None:
    """A demo not linked to any prospect serializes prospect_id as None, not a crash."""
    site = SimpleNamespace(
        id=2,
        slug="orphan-demo",
        template_id="barber-x",
        business_name="Orphan",
        status="active",
        expires_at=datetime(2026, 9, 1),
        created_at=datetime(2026, 8, 1),
    )
    dumped = DemoSiteResponse.model_validate(site).model_dump()
    assert dumped["prospect_id"] is None
