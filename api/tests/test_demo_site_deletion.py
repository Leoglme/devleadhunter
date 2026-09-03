"""Deleting a demo site frees its slug: an unsold site is hard-deleted, a sold one is kept.

The slug column is unique, so a soft-deleted row keeps its slug reserved and forces a later
regeneration onto a ``-2`` suffix. Only a site tied to a sale (delivered, or referenced by an
order) must survive so the order's ``demo_site_id`` stays valid.
"""

import asyncio
from types import SimpleNamespace

import pytest

import services.demo_site_service as demo_module
from enums.demo_site_status import DemoSiteStatus
from services.demo_site_service import DemoSiteService


class _FakeQuery:
    """Query stand-in whose ``.filter(...).first()`` returns a fixed result."""

    def __init__(self, result: object | None) -> None:
        self._result = result

    def filter(self, *args: object, **kwargs: object) -> "_FakeQuery":
        return self

    def first(self) -> object | None:
        return self._result


class _FakeDB:
    """Session stand-in recording hard deletes and reporting whether an order references the site."""

    def __init__(self, *, order_exists: bool) -> None:
        self._order_exists = order_exists
        self.deleted: list[object] = []
        self.committed = False

    def query(self, *args: object, **kwargs: object) -> _FakeQuery:
        return _FakeQuery(object() if self._order_exists else None)

    def delete(self, row: object) -> None:
        self.deleted.append(row)

    def commit(self) -> None:
        self.committed = True


def _site(status: str = DemoSiteStatus.ACTIVE.value) -> SimpleNamespace:
    return SimpleNamespace(
        id=1,
        user_id=1,
        slug="barbier-d-antan",
        status=status,
        business_name="Barbier d'Antan",
        storyblok_space_id=None,
        storyblok_editor_url=None,
        prospect_id=None,
    )


def _stub_side_effects(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _no_space(**kwargs: object) -> None:
        return None

    monkeypatch.setattr(demo_module.storyblok_service, "delete_demo_space", _no_space)
    monkeypatch.setattr("services.demo_video_service.delete_files_for_slug", lambda slug: None)


def test_unsold_site_is_hard_deleted(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_side_effects(monkeypatch)
    db = _FakeDB(order_exists=False)
    site = _site()
    asyncio.run(DemoSiteService().delete_demo_site(db, site))
    assert site in db.deleted
    assert site.status != DemoSiteStatus.DELETED.value


def test_site_referenced_by_an_order_is_kept(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_side_effects(monkeypatch)
    db = _FakeDB(order_exists=True)
    site = _site()
    asyncio.run(DemoSiteService().delete_demo_site(db, site))
    assert db.deleted == []
    assert site.status == DemoSiteStatus.DELETED.value


def test_delivered_site_is_kept(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_side_effects(monkeypatch)
    db = _FakeDB(order_exists=False)
    site = _site(status=DemoSiteStatus.DELIVERED.value)
    asyncio.run(DemoSiteService().delete_demo_site(db, site))
    assert db.deleted == []
    assert site.status == DemoSiteStatus.DELETED.value
