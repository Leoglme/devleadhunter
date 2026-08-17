"""
Two automation guards from the buyer's-eye review of the acquisition tunnel:

- ``create_from_prospects`` refuses — and persists NOTHING — when the selection has no eligible
  prospect and there is no full-auto query. Previously the empty run was committed first, then the
  route rejected it, leaving an orphan draft in the DB.
- deleting a demo site frees its prospect from any live automation
  (``_free_prospect_from_automation`` marks the non-terminal item SKIPPED), so the prospect can be
  re-run and the orchestrator never campaigns a site that no longer exists.
"""

from types import SimpleNamespace

import pytest

from enums.acquisition import AcquisitionItemStep
from services.acquisition_service import AcquisitionService, CreateSequenceInput
from services.demo_site_service import DemoSiteService


class _RecordingDB:
    """Session stand-in recording add/flush/commit, to assert whether anything was persisted."""

    def __init__(self) -> None:
        self.added: list[object] = []
        self.flushed = False
        self.committed = False

    def add(self, row: object) -> None:
        self.added.append(row)

    def flush(self) -> None:
        self.flushed = True

    def commit(self) -> None:
        self.committed = True

    def refresh(self, row: object) -> None:
        pass


def _no_credits(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("services.acquisition_service.CreditService.get_user_credits_consumed", lambda *a, **k: 0)


def test_create_refuses_and_persists_nothing_when_no_eligible_and_no_query(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    svc = AcquisitionService()
    # Every selected prospect is already used → no eligible items; no query target either.
    monkeypatch.setattr(svc, "_visible_prospect_ids", lambda *a, **k: {1, 2})
    monkeypatch.setattr(svc, "used_prospect_ids", lambda *a, **k: {1, 2})
    _no_credits(monkeypatch)
    db = _RecordingDB()
    payload = CreateSequenceInput(name="Vide", prospect_ids=[1, 2])
    with pytest.raises(ValueError):
        svc.create_from_prospects(db, user_id=1, organization_id=None, payload=payload)
    # Nothing persisted: the run was never added or committed.
    assert db.added == []
    assert not db.committed


def test_create_persists_a_run_when_a_prospect_is_eligible(monkeypatch: pytest.MonkeyPatch) -> None:
    svc = AcquisitionService()
    monkeypatch.setattr(svc, "_visible_prospect_ids", lambda *a, **k: {1, 2})
    monkeypatch.setattr(svc, "used_prospect_ids", lambda *a, **k: {1})  # prospect #2 is free
    _no_credits(monkeypatch)
    db = _RecordingDB()
    payload = CreateSequenceInput(name="OK", prospect_ids=[1, 2])
    run = svc.create_from_prospects(db, user_id=1, organization_id=None, payload=payload)
    assert db.committed
    assert run is not None


class _FakeResult:
    def __init__(self, items: list[object]) -> None:
        self._items = items

    def scalars(self) -> "_FakeResult":
        return self

    def all(self) -> list[object]:
        return self._items


class _FakeExecDB:
    def __init__(self, items: list[object]) -> None:
        self._items = items

    def execute(self, *_a: object, **_k: object) -> _FakeResult:
        return _FakeResult(self._items)


def test_deleting_a_demo_frees_the_prospect_by_skipping_its_item() -> None:
    item = SimpleNamespace(step=AcquisitionItemStep.GENERATED.value, prospect_id=5)
    db = _FakeExecDB([item])
    DemoSiteService._free_prospect_from_automation(db, 5)
    assert item.step == AcquisitionItemStep.SKIPPED.value


def test_free_is_a_noop_without_a_prospect() -> None:
    class _Boom:
        def execute(self, *_a: object, **_k: object) -> object:
            raise AssertionError("must not query the DB when prospect_id is None")

    # No prospect_id → early return, no query issued.
    DemoSiteService._free_prospect_from_automation(_Boom(), None)
