"""A Storyblok failure must not condemn a demo site: it renders from content_json.

When the Storyblok trial ends the Management API returns 401. The CMS is only used by the
post-sale client editor, so a failing sync should degrade to a live demo (verification decides
the status) instead of a hard ``failed`` that blocks the outreach email.
"""

import asyncio
from types import SimpleNamespace

import pytest

import services.demo_site_service as demo_module
from enums.demo_site_status import DemoSiteStatus
from services.demo_site_service import DemoSiteService


class _FakeDB:
    """Session stand-in recording commits; queries are unused on this path."""

    def __init__(self) -> None:
        self.committed = False

    def commit(self) -> None:
        self.committed = True

    def refresh(self, row: object) -> None:
        return None


def _verification(*, public_api_ok: bool, demo_url_live: bool) -> SimpleNamespace:
    return SimpleNamespace(
        public_api_ok=public_api_ok,
        demo_url_live=demo_url_live,
        local_demo_url=None,
        local_demo_url_live=False,
        message="verified" if demo_url_live else "demo unreachable",
    )


def _site() -> SimpleNamespace:
    return SimpleNamespace(
        id=1,
        slug="barbier-d-antan",
        template_id="barber",
        demo_url="https://demo.dibodev.fr/barbier-d-antan",
        vercel_deployment_url=None,
        content_json=None,
        error_message="Storyblok API error (401): Unauthorized",
        status=DemoSiteStatus.FAILED.value,
        storyblok_space_id=4242,
        demo_url_live=False,
        local_demo_url=None,
        verification_message=None,
    )


def _stub(monkeypatch: pytest.MonkeyPatch, *, verification: SimpleNamespace) -> None:
    async def _raise(*args: object, **kwargs: object) -> None:
        raise RuntimeError("Storyblok API error (401): Unauthorized")

    async def _verify(db: object, site: object) -> SimpleNamespace:
        return verification

    monkeypatch.setattr(demo_module.storyblok_service, "configure_preview_url", _raise)
    monkeypatch.setattr(demo_module.storyblok_service, "update_home_story_content", _raise)
    monkeypatch.setattr(demo_module.demo_site_verification_service, "verify", _verify)
    monkeypatch.setattr(
        demo_module.DemoSiteService,
        "_build_content_for_site",
        lambda self, db, site: {"business": {"name": "Barbier d'Antan"}},
    )


def test_regenerate_stays_active_when_storyblok_sync_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub(monkeypatch, verification=_verification(public_api_ok=True, demo_url_live=True))
    site = _site()
    result = asyncio.run(DemoSiteService().regenerate_demo_site(_FakeDB(), site))

    assert result.status == DemoSiteStatus.ACTIVE.value
    assert result.content_json == {"business": {"name": "Barbier d'Antan"}}
    assert result.error_message is None


def test_regenerate_defers_to_verification_when_demo_unreachable(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub(monkeypatch, verification=_verification(public_api_ok=False, demo_url_live=False))
    site = _site()
    result = asyncio.run(DemoSiteService().regenerate_demo_site(_FakeDB(), site))

    assert result.status == DemoSiteStatus.FAILED.value
