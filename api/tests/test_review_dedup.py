"""
Tests for review deduplication at enrichment: the same review is sometimes captured twice (Google
panel + expanded list, or a Facebook page rendering it more than once). ``_dedupe_reviews`` keeps
the first occurrence, drops the rest (author+text, whitespace/case-insensitive), and preserves order.
"""

from scrappers.enrichment_scraper import _dedupe_reviews


def test_removes_exact_duplicate_reviews() -> None:
    reviews = [
        {"author": "TSKR", "text": "Accueil très agréable", "rating": 5},
        {"author": "Jean Marie", "text": "Super garage", "rating": 5},
        {"author": "TSKR", "text": "Accueil très agréable", "rating": 5},
    ]
    out = _dedupe_reviews(reviews)
    assert [r["author"] for r in out] == ["TSKR", "Jean Marie"]


def test_normalizes_whitespace_and_case_and_drops_empty_text() -> None:
    reviews = [
        {"author": "A", "text": "Top service"},
        {"author": "a", "text": "  top    service "},
        {"author": "B", "text": ""},
        {"author": "C", "text": "   "},
    ]
    out = _dedupe_reviews(reviews)
    assert [r["author"] for r in out] == ["A"]


def test_ignores_non_dict_entries() -> None:
    assert _dedupe_reviews([None, "x", {"author": "A", "text": "ok"}]) == [{"author": "A", "text": "ok"}]
