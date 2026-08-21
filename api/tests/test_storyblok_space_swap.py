"""Storyblok outreach space swap eligibility."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import patch

from core.config import settings
from enums.demo_site_status import DemoSiteStatus
from services.demo_site_service import DemoSiteService


def _site(**overrides: object) -> SimpleNamespace:
    base = {
        "id": 1,
        "slug": "golden-barber",
        "status": DemoSiteStatus.ACTIVE.value,
        "demo_link_sent_at": None,
        "storyblok_space_id": 999,
        "storyblok_public_token": "token",
        "storyblok_space_created_at": datetime(2026, 7, 1, tzinfo=UTC),
        "created_at": datetime(2026, 7, 1, tzinfo=UTC),
        "content_json": {"heroTitle": "Salon"},
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def test_no_swap_when_trial_covers_demo_ttl() -> None:
    service = DemoSiteService()
    at = datetime(2026, 7, 20, tzinfo=UTC)
    site = _site(storyblok_space_created_at=datetime(2026, 7, 1, tzinfo=UTC))

    with patch.object(settings, "storyblok_trial_days", 45), patch.object(settings, "demo_site_ttl_days", 21):
        assert service.storyblok_space_age_days(site, at) == 19.0
        assert service.needs_storyblok_space_swap(site, at) is False


def test_swap_needed_when_trial_would_end_before_demo_ttl() -> None:
    service = DemoSiteService()
    at = datetime(2026, 8, 1, tzinfo=UTC)
    site = _site(storyblok_space_created_at=datetime(2026, 7, 1, tzinfo=UTC))

    with patch.object(settings, "storyblok_trial_days", 45), patch.object(settings, "demo_site_ttl_days", 21):
        assert service.storyblok_space_age_days(site, at) == 31.0
        assert service.needs_storyblok_space_swap(site, at) is True


def test_no_swap_after_demo_link_emailed() -> None:
    service = DemoSiteService()
    at = datetime(2026, 8, 1, tzinfo=UTC)
    site = _site(demo_link_sent_at=datetime(2026, 8, 1, tzinfo=UTC))

    with patch.object(settings, "storyblok_trial_days", 45), patch.object(settings, "demo_site_ttl_days", 21):
        assert service.needs_storyblok_space_swap(site, at) is False


def test_boundary_exactly_enough_trial_remaining() -> None:
    service = DemoSiteService()
    created = datetime(2026, 1, 1, tzinfo=UTC)
    at = created + timedelta(days=24)
    site = _site(storyblok_space_created_at=created, created_at=created)

    with patch.object(settings, "storyblok_trial_days", 45), patch.object(settings, "demo_site_ttl_days", 21):
        assert service.needs_storyblok_space_swap(site, at) is False
        at_over = created + timedelta(days=25)
        assert service.needs_storyblok_space_swap(site, at_over) is True
