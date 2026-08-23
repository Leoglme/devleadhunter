"""Pausing a campaign must not brick it: a resume re-enqueues the prospects the pause cancelled.

``cancel_campaign_queue`` marks pending sends ``skipped``; ``enqueue_campaign`` then treated any
existing initial row as "already queued" and dropped those prospects forever. The queue service now
purges the stale skipped rows first, so resume rebuilds a clean queue.
"""

from types import SimpleNamespace

from services.campaign_queue_service import CampaignQueueService


class _FakeScalarResult:
    def __init__(self, rows: list[object]) -> None:
        self._rows = rows

    def scalars(self) -> list[object]:
        return list(self._rows)


class _FakeDB:
    """Session stand-in whose every ``execute`` returns the same rows, recording deletes and flush."""

    def __init__(self, rows: list[object]) -> None:
        self._rows = list(rows)
        self.deleted: list[object] = []
        self.flushed = False

    def execute(self, *args: object, **kwargs: object) -> _FakeScalarResult:
        return _FakeScalarResult(self._rows)

    def delete(self, row: object) -> None:
        self.deleted.append(row)

    def flush(self) -> None:
        self.flushed = True


def test_purge_deletes_the_skipped_initial_items() -> None:
    skipped = [SimpleNamespace(id=index, status="skipped", queue_type="initial") for index in range(3)]
    db = _FakeDB(skipped)

    count = CampaignQueueService(db)._purge_skipped_initial_items(campaign_id=8)

    assert count == 3
    assert db.deleted == skipped
    assert db.flushed


def test_purge_is_a_noop_without_skipped_items() -> None:
    db = _FakeDB([])

    count = CampaignQueueService(db)._purge_skipped_initial_items(campaign_id=6)

    assert count == 0
    assert db.deleted == []
