"""
Tests for the fragmentary-about guard: a description assembled from scraped attribute fragments
("Food Truck à Poitiers Spécialité: poulet frit coréen") reads badly and must be rejected in favour
of a clean template default. Real prose — even long prose mentioning a specialty — is left alone.
"""

from services.templates import registry
from services.validation_service import validation_service


def test_scraped_attribute_fragments_are_flagged() -> None:
    assert validation_service.is_fragmentary_description("Food Truck à Poitiers Spécialité: poulet frit coréen")
    assert validation_service.is_fragmentary_description("Garage Catégorie: Réparation automobile")


def test_real_prose_is_not_flagged() -> None:
    assert not validation_service.is_fragmentary_description(
        "Le salon Barbier d'Antan vous accueille dans une ambiance chic et élégante inspirée des années 30."
    )
    # lowercase 'spécialité' in a sentence is prose, not a scraped label
    assert not validation_service.is_fragmentary_description(
        "Notre spécialité, c'est le poulet frit coréen préparé minute avec des produits frais."
    )
    assert not validation_service.is_fragmentary_description(None)
    assert not validation_service.is_fragmentary_description("")


def test_site_falls_back_to_default_when_about_is_fragmentary() -> None:
    site = registry.build_site_content(
        template_id="barber",
        business_name="X",
        phone="0",
        email="x@y.fr",
        city="Tours",
        area="Tours",
        subtitle="",
        palette={"primary": "#000", "secondary": "#111", "accent": "#222"},
        enrichment={"description": "Food Truck à Poitiers Spécialité: poulet frit coréen"},
    )
    assert "Spécialité:" not in site["about"]
    assert site["about"].strip()
