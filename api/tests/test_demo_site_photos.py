"""Regenerating a site must show photos added to the prospect, without re-showing removed ones.

``_effective_photos`` keeps the curated placement, appends photos that are new since the last save
(absent from both the order and the pool snapshot), and keeps deliberately-removed photos hidden.
"""

from services.demo_site_service import DemoSiteService


def test_no_curation_returns_the_full_pool() -> None:
    assert DemoSiteService._effective_photos(["a", "b", "c"], None, None) == ["a", "b", "c"]


def test_legacy_site_without_snapshot_keeps_its_exact_order() -> None:
    # No snapshot yet (pre-feature): the curated list stays exact so nothing reappears until the next save.
    assert DemoSiteService._effective_photos(["a", "b", "c"], ["b", "a"], None) == ["b", "a"]


def test_new_photo_is_appended_and_removed_photo_stays_hidden() -> None:
    pool = ["a", "b", "c", "d"]
    order = ["b", "a"]
    snapshot = ["a", "b", "c"]  # c was known at save time but dropped from order → removed on purpose
    # d is new (absent from order and snapshot) → appended; c stays hidden.
    assert DemoSiteService._effective_photos(pool, order, snapshot) == ["b", "a", "d"]


def test_curated_order_drops_photos_no_longer_in_the_pool() -> None:
    assert DemoSiteService._effective_photos(["a", "b"], ["b", "z", "a"], ["a", "b"]) == ["b", "a"]
