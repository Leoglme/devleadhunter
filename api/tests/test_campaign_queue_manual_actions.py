"""Manual queue controls replace the old auto-skip-on-open rule.

A relance no longer stops itself when the prospect opens the J1 (opens are noisy — bot/proxy
prefetch inflates them). Instead the operator drives sends by hand from the campaign queue:
cancel a pending item so it never goes out, or re-queue a skipped one so the worker sends it on
its next tick. Both are guarded status transitions — only a ``pending`` item cancels, only a
``skipped`` item re-sends.
"""

from datetime import datetime
from types import SimpleNamespace

import pytest

from services.campaign_queue_service import CampaignQueueService


class _FakeDB:
    """Session stand-in — these transitions only ever ``commit``."""

    def __init__(self) -> None:
        self.commits = 0

    def commit(self) -> None:
        self.commits += 1


def _item(**overrides: object) -> SimpleNamespace:
    base: dict[str, object] = {
        "id": 7,
        "status": "pending",
        "skip_reason": None,
        "scheduled_at": "2026-08-28T09:47:00",
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def test_cancel_marks_a_pending_item_skipped_with_a_manual_reason() -> None:
    db = _FakeDB()
    item = _item(status="pending")

    CampaignQueueService(db).cancel_queue_item(item)

    assert item.status == "skipped"
    assert item.skip_reason == "Annulé manuellement"
    assert db.commits == 1


def test_cancel_rejects_an_item_that_is_not_pending() -> None:
    db = _FakeDB()
    item = _item(status="sent")

    with pytest.raises(ValueError):
        CampaignQueueService(db).cancel_queue_item(item)

    assert item.status == "sent"
    assert db.commits == 0


def test_requeue_puts_a_skipped_item_back_to_pending_now_and_clears_the_reason() -> None:
    db = _FakeDB()
    item = _item(status="skipped", skip_reason="Annulé manuellement")

    CampaignQueueService(db).requeue_item(item)

    assert item.status == "pending"
    assert item.skip_reason is None
    assert isinstance(item.scheduled_at, datetime)  # rescheduled to now
    assert db.commits == 1


def test_requeue_rejects_an_item_that_is_not_skipped() -> None:
    db = _FakeDB()
    item = _item(status="pending")

    with pytest.raises(ValueError):
        CampaignQueueService(db).requeue_item(item)

    assert item.status == "pending"
    assert db.commits == 0
