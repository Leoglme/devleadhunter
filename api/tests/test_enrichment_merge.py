"""Unit tests for enrichment merge guards — collections must never degrade."""

from types import SimpleNamespace

from scrappers.enrichment_scraper import EnrichmentData, EnrichmentScraper
from services.enrichment_service import EnrichmentService


def _record(**overrides: object) -> SimpleNamespace:
    base = {
        "source": "import",
        "rating": 4.7,
        "reviews_count": 70,
        "description": "Garage depuis 1984",
        "logo_url": None,
        "photos": ["https://example.com/a.jpg"],
        "reviews": [{"author": "Client", "text": "Super garage", "rating": 5}],
        "opening_hours": [
            {"day": "Lundi", "hours": "08:00 – 19:00"},
            {"day": "Mardi", "hours": "08:00 – 19:00"},
            {"day": "Mercredi", "hours": "08:00 – 19:00"},
            {"day": "Jeudi", "hours": "08:00 – 19:00"},
            {"day": "Vendredi", "hours": "08:00 – 19:00"},
            {"day": "Samedi", "hours": "08:00 – 12:00"},
            {"day": "Dimanche", "hours": "Fermé"},
        ],
        "services": [],
        "social_links": {},
        "place_title": "Garage Brisse Bonnet",
        "place_city": "Châteauroux",
        "place_postal_code": "36000",
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def test_apply_data_keeps_full_hours_when_scrape_is_partial() -> None:
    """A wave-1 scrape with one day must not overwrite a full weekly schedule."""
    record = _record()
    partial = EnrichmentData(
        opening_hours=[{"day": "Mardi", "hours": "08:00–19:00"}],
        reviews_count=70,
    )
    EnrichmentService()._apply_data(record, partial)
    assert len(record.opening_hours) == 7


def test_apply_data_replaces_hours_when_scrape_is_more_complete() -> None:
    """A richer weekly schedule from Google replaces a shorter existing one."""
    record = _record(opening_hours=[{"day": "Mardi", "hours": "08:00–19:00"}])
    richer = EnrichmentData(
        opening_hours=[
            {"day": "Lundi", "hours": "08:00 – 19:00"},
            {"day": "Mardi", "hours": "08:00 – 19:00"},
            {"day": "Mercredi", "hours": "08:00 – 19:00"},
            {"day": "Jeudi", "hours": "08:00 – 19:00"},
            {"day": "Vendredi", "hours": "08:00 – 19:00"},
        ]
    )
    EnrichmentService()._apply_data(record, richer)
    assert len(record.opening_hours) == 5


def test_apply_data_merges_reviews_instead_of_replacing() -> None:
    """New review snippets are appended; existing ones stay."""
    record = _record(reviews=[{"author": "Client", "text": "Super garage", "rating": 5}])
    incoming = EnrichmentData(
        reviews=[
            {"author": "Client", "text": "Super garage", "rating": 5},
            {"author": "Paul", "text": "Très pro", "rating": 5},
        ]
    )
    EnrichmentService()._apply_data(record, incoming)
    assert len(record.reviews) == 2
    assert record.reviews[1]["author"] == "Paul"


def test_apply_data_keeps_existing_reviews_when_scrape_is_poorer() -> None:
    """A single scraped review must not drop previously imported ones."""
    record = _record(
        reviews=[
            {"author": "Client", "text": "Super garage", "rating": 5},
            {"author": "Paul", "text": "Très pro", "rating": 5},
        ]
    )
    incoming = EnrichmentData(reviews=[{"author": "Autre", "text": "Bien", "rating": 4}])
    EnrichmentService()._apply_data(record, incoming)
    assert len(record.reviews) == 3


def test_apply_data_facebook_poorer_rerun_does_not_readd_same_author() -> None:
    """A Facebook relance that only paints one DOM review must not duplicate that author."""
    record = _record(
        reviews=[
            {"author": "Fox Emmanuel", "text": "Copieux et délicieux Merci beaucoup", "rating": 5},
            {"author": "Marie Breton", "text": "Assaisonnement parfait", "rating": 5},
        ]
    )
    incoming = EnrichmentData(
        source="facebook",
        reviews=[
            {
                "author": "Fox Emmanuel",
                "text": "Copieux et délicieux Merci beaucoup Plats excellents",
                "rating": 5,
            }
        ],
    )
    EnrichmentService()._apply_data(record, incoming)
    authors = [review["author"] for review in record.reviews]
    assert authors == ["Fox Emmanuel", "Marie Breton"]
    assert "Plats excellents" not in record.reviews[0]["text"]


def test_apply_data_facebook_replace_dedupes_incoming() -> None:
    """A fuller Facebook re-scrape still collapses Relay + DOM copies of the same author."""
    record = _record(reviews=[])
    incoming = EnrichmentData(
        source="facebook",
        reviews=[
            {"author": "Fox Emmanuel", "text": "Copieux et délicieux Merci beaucoup", "rating": 5},
            {
                "author": "Fox Emmanuel",
                "text": "Copieux et délicieux Merci beaucoup Plats excellents",
                "rating": 5,
            },
        ],
    )
    EnrichmentService()._apply_data(record, incoming)
    assert len(record.reviews) == 1
    assert record.reviews[0]["author"] == "Fox Emmanuel"


def test_merge_attempt_data_keeps_best_hours_across_attempts() -> None:
    """Retry loop keeps the richest attempt instead of the last partial one."""
    partial = EnrichmentData(
        reviews_count=None,
        opening_hours=[{"day": "Mardi", "hours": "08:00–19:00"}],
        reviews=[{"author": "Client", "text": "Bon accueil", "rating": 5}],
    )
    complete = EnrichmentData(
        reviews_count=70,
        opening_hours=[
            {"day": "Lundi", "hours": "08:00 – 19:00"},
            {"day": "Mardi", "hours": "08:00 – 19:00"},
            {"day": "Mercredi", "hours": "08:00 – 19:00"},
            {"day": "Jeudi", "hours": "08:00 – 19:00"},
            {"day": "Vendredi", "hours": "08:00 – 19:00"},
        ],
        reviews=[{"author": "Paul", "text": "Très pro", "rating": 5}],
    )
    merged = EnrichmentScraper._merge_attempt_data(partial, complete)
    assert merged.reviews_count == 70
    assert len(merged.opening_hours) == 5
    assert len(merged.reviews) == 2


def test_is_extraction_ready_requires_review_count_and_weekly_hours() -> None:
    """Readiness waits for wave-2 markers, not just the business name."""
    assert not EnrichmentScraper._is_extraction_ready(
        EnrichmentData(reviews_count=None, opening_hours=[{"day": "Mardi", "hours": "08:00–19:00"}])
    )
    assert EnrichmentScraper._is_extraction_ready(
        EnrichmentData(
            reviews_count=70,
            opening_hours=[{"day": f"Jour {index}", "hours": "08:00–19:00"} for index in range(5)],
        )
    )
