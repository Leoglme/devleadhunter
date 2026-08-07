"""
Unit tests for the enrichment identity guard — the check that the scraped
Google Maps place really is the prospect's business, not a homonym's listing.
All offline: the guard and the raw-payload parser are exercised on fixtures.
"""

import json
from types import SimpleNamespace

from scrappers.enrichment_scraper import EnrichmentData, EnrichmentScraper
from services.enrichment_service import EnrichmentService
from services.validation_service import ValidationService

# ── Place identity check ─────────────────────────────────────────────────────


def test_matching_place_passes() -> None:
    """Same name, same département → the data is about the right business."""
    assert (
        ValidationService.place_identity_mismatch(
            prospect_name="Plomberie Vidal",
            prospect_city="Rennes",
            prospect_postal_code="35000",
            place_title="Plomberie Vidal",
            place_city="Rennes",
            place_postal_code="35000",
        )
        is None
    )


def test_wrong_business_name_is_rejected() -> None:
    """A place named after a completely different business is rejected."""
    reason = ValidationService.place_identity_mismatch(
        prospect_name="Plomberie Vidal",
        prospect_city="Rennes",
        prospect_postal_code="35000",
        place_title="Boulangerie Martin",
        place_city="Rennes",
        place_postal_code="35000",
    )
    assert reason is not None
    assert "ne correspond pas" in reason


def test_same_name_other_department_is_rejected() -> None:
    """The homonym case: right name, wrong département → someone else's data."""
    reason = ValidationService.place_identity_mismatch(
        prospect_name="Plomberie Vidal",
        prospect_city="Clermont-Ferrand",
        prospect_postal_code="63000",
        place_title="Plomberie Vidal",
        place_city="Lille",
        place_postal_code="59000",
    )
    assert reason is not None
    assert "département" in reason


def test_neighbouring_commune_same_department_passes() -> None:
    """An artisan listed one commune away (same département) is NOT a homonym."""
    assert (
        ValidationService.place_identity_mismatch(
            prospect_name="Plomberie Vidal",
            prospect_city="Rennes",
            prospect_postal_code="35000",
            place_title="Plomberie Vidal",
            place_city="Cesson-Sévigné",
            place_postal_code="35510",
        )
        is None
    )


def test_city_comparison_used_when_postal_codes_missing() -> None:
    """Without postal codes, a plainly different city still exposes the homonym."""
    reason = ValidationService.place_identity_mismatch(
        prospect_name="Plomberie Vidal",
        prospect_city="Clermont-Ferrand",
        prospect_postal_code=None,
        place_title="Plomberie Vidal",
        place_city="Lille",
        place_postal_code=None,
    )
    assert reason is not None
    assert "homonyme" in reason


def test_city_spelling_variants_are_not_a_mismatch() -> None:
    """« Clermont Ferrand » vs « Clermont-Ferrand » is the same city."""
    assert (
        ValidationService.place_identity_mismatch(
            prospect_name="Plomberie Vidal",
            prospect_city="Clermont-Ferrand",
            prospect_postal_code=None,
            place_title="Plomberie Vidal",
            place_city="Clermont Ferrand",
            place_postal_code=None,
        )
        is None
    )


def test_missing_place_identity_skips_the_check() -> None:
    """Payloads from older desktop sidecars carry no place identity → no rejection."""
    assert (
        ValidationService.place_identity_mismatch(
            prospect_name="Plomberie Vidal",
            prospect_city="Rennes",
            prospect_postal_code="35000",
            place_title=None,
            place_city=None,
            place_postal_code=None,
        )
        is None
    )


def test_service_parses_prospect_postal_code_from_address() -> None:
    """The guard reads the prospect's postal code out of its free-text address."""
    prospect = SimpleNamespace(
        name="Plomberie Vidal",
        address="12 rue des Forges, 63000 Clermont-Ferrand",
        city="Clermont-Ferrand",
    )
    data = EnrichmentData(place_title="Plomberie Vidal", place_city="Lille", place_postal_code="59000")
    reason = EnrichmentService._place_mismatch(prospect, data)
    assert reason is not None
    assert "département" in reason


# ── Raw-payload parsing (place identity extraction) ──────────────────────────


def test_build_from_raw_extracts_place_identity() -> None:
    """The h1 title and the JSON-LD address feed the identity fields."""
    ld_block = json.dumps(
        {
            "@type": "Plumber",
            "name": "Plomberie Vidal",
            "telephone": "+33 3 20 00 00 00",
            "address": {
                "@type": "PostalAddress",
                "streetAddress": "4 rue de la Clef",
                "postalCode": "59000",
                "addressLocality": "Lille",
            },
        }
    )
    data = EnrichmentScraper._build_from_raw(
        {"place_title": "Plomberie Vidal", "ld": [ld_block]},
        business_name="Plomberie Vidal",
        city="Lille",
    )
    assert data.place_title == "Plomberie Vidal"
    assert data.place_city == "Lille"
    assert data.place_postal_code == "59000"


def test_build_from_raw_without_identity_stays_none() -> None:
    """No h1 and no JSON-LD → identity fields stay None (check skipped later)."""
    data = EnrichmentScraper._build_from_raw({}, business_name="Plomberie Vidal", city="Lille")
    assert data.place_title is None
    assert data.place_city is None
    assert data.place_postal_code is None
