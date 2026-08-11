"""Unit tests for the Facebook enrichment parsers — pure functions, no browser."""

from scrappers.facebook_enrichment_scraper import (
    FacebookEnrichmentScraper,
    _parse_about_stats,
    _parse_reviews,
    _rating_from_pct,
)

# Real text captured from a public Facebook page's « À propos » panel.
_ABOUT_TEXT = """Food truck mexicain Tacos Maru
1,7 K followers • 2,1 K suivi(e)s
À propos
Coordonnées
., Châtellerault, France, 86100
Adresse
06 29 34 58 99
Mobile
+33 6 14 92 78 16
WhatsApp
foodtruckmexicaintacosmaru@gmail.com
E-mail
Recommandé par 96 % (22 avis)
Fourchette de prix · €€"""

# Real text captured from the same page's « Avis » panel.
_REVIEWS_TEXT = """Recommandé par 96 % (22 avis)
Fox Emmanuel  recommande Food truck mexicain Tacos Maru.
27 septembre 2025
·
Copieux et délicieux on n'en demande pas plus et ça fait passer une très bonne soirée
Merci beaucoup
Plats excellents
Toutes les réactions :
1"""


def test_rating_from_pct_converts_and_clamps() -> None:
    """A recommendation rate maps to /5, clamped to [0, 5]; None stays None."""
    assert _rating_from_pct(96) == 4.8
    assert _rating_from_pct(100) == 5.0
    assert _rating_from_pct(0) == 0.0
    assert _rating_from_pct(120) == 5.0
    assert _rating_from_pct(None) is None


def test_parse_about_stats_reads_rate_and_count() -> None:
    """« Recommandé par 96 % (22 avis) » yields (96, 22)."""
    assert _parse_about_stats(_ABOUT_TEXT) == (96, 22)


def test_parse_reviews_extracts_author_and_body_without_date_or_reactions() -> None:
    """A review keeps author + body, drops the date line and the reactions footer."""
    reviews = _parse_reviews(_REVIEWS_TEXT)
    assert len(reviews) == 1
    assert reviews[0]["author"] == "Fox Emmanuel"
    assert reviews[0]["rating"] == 5
    assert "Copieux et délicieux" in reviews[0]["text"]
    assert "Plats excellents" in reviews[0]["text"]
    assert "27 septembre 2025" not in reviews[0]["text"]
    assert "Toutes les réactions" not in reviews[0]["text"]


def test_parse_reviews_marks_a_non_recommendation_lower() -> None:
    """« ne recommande pas » is a negative signal (2/5, not 5/5)."""
    text = (
        "Paul ne recommande pas Food truck mexicain Tacos Maru.\n"
        "1 janvier 2025\n"
        "À éviter vraiment\n"
        "Toutes les réactions :"
    )
    reviews = _parse_reviews(text)
    assert len(reviews) == 1
    assert reviews[0]["author"] == "Paul"
    assert reviews[0]["rating"] == 2


def test_build_from_raw_produces_facebook_enrichment() -> None:
    """The raw about payload + reviews text become a « facebook » EnrichmentData."""
    dom = {
        "place_title": "Food truck mexicain Tacos Maru",
        "about_text": _ABOUT_TEXT,
        "social": {
            "facebook": "https://www.facebook.com/TacosMexicanosMaru/",
            "instagram": "https://www.instagram.com/food_truck_mexicano_tacos_maru",
            "tiktok": "https://www.tiktok.com/@food.truck.mexicai",
        },
        "website": None,
        "photos": ["https://scontent.xx.fbcdn.net/v/t1/photo.jpg"],
    }
    data = FacebookEnrichmentScraper._build_from_raw(dom, _REVIEWS_TEXT)
    assert data.source == "facebook"
    assert data.rating == 4.8
    assert data.reviews_count == 22
    assert data.social_links["tiktok"].endswith("food.truck.mexicai")
    assert data.website is None
    assert data.photos == ["https://scontent.xx.fbcdn.net/v/t1/photo.jpg"]
    assert len(data.reviews) == 1
