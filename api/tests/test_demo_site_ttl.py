"""Demo site TTL starts when the demo link is first emailed, not at generation."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from core.config import settings
from enums.demo_site_status import DemoSiteStatus
from services.demo_site_service import _PENDING_TTL_EXPIRES, DemoSiteService


class _FakeQuery:
    def __init__(self, result: object | None) -> None:
        self._result = result

    def filter(self, *args: object, **kwargs: object) -> _FakeQuery:
        return self

    def order_by(self, *args: object, **kwargs: object) -> _FakeQuery:
        return self

    def first(self) -> object | None:
        return self._result


class _FakeDB:
    def __init__(self, site: object | None) -> None:
        self._site = site
        self.committed = False

    def query(self, *args: object, **kwargs: object) -> _FakeQuery:
        return _FakeQuery(self._site)

    def commit(self) -> None:
        self.committed = True


def _site(**overrides: object) -> SimpleNamespace:
    base = {
        "id": 1,
        "slug": "golden-barber",
        "demo_url": "https://demo.dibodev.fr/golden-barber",
        "prospect_id": 35,
        "user_id": 1,
        "status": DemoSiteStatus.ACTIVE.value,
        "demo_link_sent_at": None,
        "expires_at": _PENDING_TTL_EXPIRES,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def test_new_site_uses_pending_expiry_placeholder() -> None:
    service = DemoSiteService()
    assert service._pending_ttl_expires_at() == _PENDING_TTL_EXPIRES


def test_email_body_detects_demo_slug() -> None:
    service = DemoSiteService()
    site = _site()
    assert service.email_body_contains_demo_link(site, "<p>Voici : https://demo.dibodev.fr/golden-barber</p>")
    assert not service.email_body_contains_demo_link(site, "<p>Pas de lien ici</p>")


def test_start_demo_ttl_sets_expiry_from_send_date() -> None:
    service = DemoSiteService()
    site = _site()
    db = _FakeDB(site)
    sent_at = datetime(2026, 8, 21, 10, 0, 0, tzinfo=UTC)

    assert service.start_demo_ttl(db, site, sent_at) is True
    assert site.demo_link_sent_at == sent_at
    assert site.expires_at == sent_at + timedelta(days=settings.demo_site_ttl_days)
    assert db.committed is True


def test_start_demo_ttl_is_idempotent() -> None:
    service = DemoSiteService()
    already = datetime(2026, 8, 1, tzinfo=UTC)
    site = _site(demo_link_sent_at=already, expires_at=already + timedelta(days=21))
    db = _FakeDB(site)

    assert service.start_demo_ttl(db, site, datetime(2026, 8, 21, tzinfo=UTC)) is False
    assert site.demo_link_sent_at == already


def test_maybe_start_ttl_after_demo_email() -> None:
    service = DemoSiteService()
    site = _site()
    db = _FakeDB(site)
    sent_at = datetime(2026, 8, 21, 12, 0, 0)

    service.maybe_start_ttl_after_demo_email(
        db,
        user_id=1,
        prospect_id=35,
        sent_at=sent_at,
        body_html="<a href='https://demo.dibodev.fr/golden-barber'>Voir</a>",
    )

    assert site.demo_link_sent_at is not None
    assert site.expires_at > sent_at.replace(tzinfo=UTC)


def test_public_site_stays_live_while_ttl_pending() -> None:
    service = DemoSiteService()
    pending = _site(expires_at=datetime(2020, 1, 1, tzinfo=UTC))

    class _PublicQuery:
        def filter(self, *args: object, **kwargs: object) -> _PublicQuery:
            return self

        def first(self) -> SimpleNamespace:
            return pending

    db = SimpleNamespace(query=lambda *a, **k: _PublicQuery())
    result = service.get_public_by_slug(db, "golden-barber")  # type: ignore[arg-type]
    assert result is pending


def test_public_site_hidden_after_ttl_started_and_expired() -> None:
    service = DemoSiteService()
    expired = _site(
        demo_link_sent_at=datetime(2026, 1, 1, tzinfo=UTC),
        expires_at=datetime(2026, 1, 2, tzinfo=UTC),
    )

    class _PublicQuery:
        def filter(self, *args: object, **kwargs: object) -> _PublicQuery:
            return self

        def first(self) -> SimpleNamespace:
            return expired

    db = SimpleNamespace(query=lambda *a, **k: _PublicQuery())
    result = service.get_public_by_slug(db, "golden-barber")  # type: ignore[arg-type]
    assert result is None
