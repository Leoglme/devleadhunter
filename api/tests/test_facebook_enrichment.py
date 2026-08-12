"""Unit tests for the Facebook enrichment parsers — pure functions, no browser."""

from scrappers.facebook_enrichment_scraper import (
    FacebookEnrichmentScraper,
    _clean_social_url,
    _dedupe_photos,
    _parse_about_stats,
    _parse_intro_description,
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

# Intro card text from the public page home (not the polished marketing rewrite).
_INTRO_TEXT = """Intro
Food Truck Mexicain Tacos Maru C’est un Food Truck qui vous fait découvrir les spécialités et saveurs mexicaines.
Des recettes faites maison dans les traditions du Mexique
Qui apportant les saveurs traditionnelles, faite de manière artisanale
Page · Food truck
06 29 34 58 99
+33 6 14 92 78 16
Foodtruckmexicaintacosmaru@gmail.com
tiktok.com/@food.truck.mexicai
instagram.com/food_truck_mexicano_tacos_maru
facebook.com/TacosMexicanosMaru
Sièges en terrasse
Recommandé par 96 % (22 avis)"""

# Real text captured from the same page's « Avis » panel (several reviews after login dismiss + scroll).
_REVIEWS_TEXT = """Recommandé par 96 % (22 avis)
Fox Emmanuel  recommande Food truck mexicain Tacos Maru.
27 septembre 2025
·
Copieux et délicieux on n'en demande pas plus et ça fait passer une très bonne soirée
Merci beaucoup
Plats excellents
Toutes les réactions :
1
Marie Breton  recommande Food truck mexicain Tacos Maru.
14 août 2025
·
Dégustation de 4 tacos si bons....!!! Assaisonnement parfait qui fait voyager instantanément.
Plats excellents
Toutes les réactions :
2
Guillaume Fournier  recommande Food truck mexicain Tacos Maru.
30 août 2023
·
Des plats tous aussi bons les un que les autres, du personnel au top du top !
Plats excellents
Toutes les réactions :
1
Mélissa Lambelin  ne recommande pas Food truck mexicain Tacos Maru.
1 janvier 2024
·
Pas convaincue
Toutes les réactions :
0"""


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


def test_parse_intro_description_keeps_blurb_and_stops_at_contacts() -> None:
    """Intro text is kept; category / phone / socials are stripped."""
    description = _parse_intro_description(_INTRO_TEXT)
    assert description is not None
    assert "spécialités et saveurs mexicaines" in description
    assert "faite de manière artisanale" in description
    assert "Page ·" not in description
    assert "06 29" not in description
    assert "instagram.com" not in description


def test_parse_reviews_extracts_multiple_authors_and_bodies() -> None:
    """Several reviews keep author + body, drop dates and reaction footers."""
    reviews = _parse_reviews(_REVIEWS_TEXT)
    assert len(reviews) == 4
    assert reviews[0]["author"] == "Fox Emmanuel"
    assert reviews[0]["rating"] == 5
    assert "Copieux et délicieux" in reviews[0]["text"]
    assert "Plats excellents" in reviews[0]["text"]
    assert "27 septembre 2025" not in reviews[0]["text"]
    assert "Toutes les réactions" not in reviews[0]["text"]
    assert reviews[1]["author"] == "Marie Breton"
    assert "Assaisonnement parfait" in reviews[1]["text"]
    assert reviews[2]["author"] == "Guillaume Fournier"
    assert reviews[3]["author"] == "Mélissa Lambelin"
    assert reviews[3]["rating"] == 2


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


def test_dedupe_photos_drops_static_ui_icons() -> None:
    """UI glyphs on static.xx.fbcdn / rsrc.php must not enter the photo list."""
    photos = _dedupe_photos(
        [
            "https://static.xx.fbcdn.net/rsrc.php/yL/r/VLNVMYsRNQ9.webp",
            "https://scontent.xx.fbcdn.net/v/t39.30808-6/photo.jpg",
            "https://scontent.xx.fbcdn.net/v/t39.30808-6/photo.jpg",
            "https://scontent.xx.fbcdn.net/v/t39.30808-6/taco.jpg",
        ]
    )
    assert photos == [
        "https://scontent.xx.fbcdn.net/v/t39.30808-6/photo.jpg",
        "https://scontent.xx.fbcdn.net/v/t39.30808-6/taco.jpg",
    ]


def test_clean_social_url_strips_tracking_params() -> None:
    """Instagram / TikTok tracking junk is removed from stored social links."""
    cleaned = _clean_social_url("https://www.instagram.com/food_truck_mexicano_tacos_maru?igsh=abc&utm_source=qr")
    assert cleaned == "https://www.instagram.com/food_truck_mexicano_tacos_maru"


def test_build_from_raw_produces_facebook_enrichment() -> None:
    """The raw page payload + reviews text become a « facebook » EnrichmentData."""
    dom = {
        "place_title": "Food truck mexicain Tacos Maru",
        "about_text": _ABOUT_TEXT,
        "intro_text": _INTRO_TEXT,
        "social": {
            "facebook": "https://www.facebook.com/TacosMexicanosMaru/",
            "instagram": "https://www.instagram.com/food_truck_mexicano_tacos_maru?igsh=abc",
            "tiktok": "https://www.tiktok.com/@food.truck.mexicai?_r=1&_t=ZN-93MqQbLcVJ0",
        },
        "website": None,
    }
    gallery = [
        "https://static.xx.fbcdn.net/rsrc.php/icon.webp",
        "https://scontent.xx.fbcdn.net/v/t1/photo.jpg",
    ]
    data = FacebookEnrichmentScraper._build_from_raw(dom, _REVIEWS_TEXT, gallery)
    assert data.source == "facebook"
    assert data.rating == 4.8
    assert data.reviews_count == 22
    assert data.description is not None
    assert "saveurs mexicaines" in data.description
    assert data.social_links["tiktok"].endswith("food.truck.mexicai")
    assert "igsh=" not in data.social_links["instagram"]
    assert data.website is None
    assert data.photos == ["https://scontent.xx.fbcdn.net/v/t1/photo.jpg"]
    assert len(data.reviews) == 4
