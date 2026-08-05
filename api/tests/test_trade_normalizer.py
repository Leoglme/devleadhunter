"""Tests for TradeNormalizer — raw scraped category to natural trade word."""

from __future__ import annotations

import pytest

from services.trade_normalizer import TradeNormalizer


@pytest.mark.parametrize(
    ("category", "expected"),
    [
        ("Atelier de réparation automobile", "garagiste"),
        ("Garage automobile", "garagiste"),
        ("Plombier", "plombier"),
        ("Plomberie chauffage", "plombier"),
        ("Salon de coiffure", "coiffeur"),
        ("Électricien", "électricien"),
        ("Restaurant traditionnel", "restaurant"),
        ("Pizzeria", "restaurant"),
        ("Dentiste", "dentiste"),
        ("Paysagiste", "paysagiste"),
        ("Fleuriste, Décoration", "fleuriste"),
        ("Opticien", "opticien"),
    ],
)
def test_maps_and_cleans_known_and_unknown_categories(category: str, expected: str) -> None:
    """A verbose or clean category resolves to the natural trade word."""
    assert TradeNormalizer.normalize(category) == expected


@pytest.mark.parametrize("category", ["Entreprise", "Inconnu", "Établissement", "", None])
def test_generic_or_empty_falls_back_to_professionnel(category: str | None) -> None:
    """Scraper placeholders and empty input degrade to a neutral noun."""
    assert TradeNormalizer.normalize(category) == "professionnel"
