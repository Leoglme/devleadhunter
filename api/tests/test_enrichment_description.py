"""Unit tests for the enrichment description validation.

Real-world bug (30/07/2026): the enrichment stored the Google Maps page's own
meta description ("Find local businesses, view maps and get driving directions
in Google Maps.") as the prospect's description, which then rendered verbatim
on his demo site. These tests pin the three guards: the scraper extraction, the
server-side ingestion of sidecar payloads, and the site-content mapping.
"""

from scrappers.enrichment_scraper import EnrichmentScraper
from services.templates.site_content import map_prospect_and_enrichment
from services.validation_service import ValidationService

GOOGLE_META_EN = "Find local businesses, view maps and get driving directions in Google Maps."
GOOGLE_META_FR = "Avec Maps, trouvez des commerces locaux, consultez des plans et calculez des itinéraires routiers."
PLACE_META = "Debiolle Patrick, Saint-Germain-Lembron : garage automobile, réparation toutes marques."
BUSINESS_LD_DESCRIPTION = "Réparation toutes marques, entretien et pneus depuis 1987."


def test_google_boilerplate_is_detected_in_both_languages() -> None:
    assert ValidationService.is_generic_platform_description(GOOGLE_META_EN)
    assert ValidationService.is_generic_platform_description(GOOGLE_META_FR)
    assert not ValidationService.is_generic_platform_description(PLACE_META)
    assert not ValidationService.is_generic_platform_description(None)


def test_description_mentions_business_matches_name_or_city() -> None:
    assert ValidationService.description_mentions_business(PLACE_META, "Debiolle Patrick", None)
    assert ValidationService.description_mentions_business(PLACE_META, "Autre Nom", "Saint-Germain-Lembron")
    assert not ValidationService.description_mentions_business(
        GOOGLE_META_EN, "Debiolle Patrick", "Saint-Germain-Lembron"
    )


def test_description_mentions_business_passes_without_reference_data() -> None:
    """With nothing to compare against, the check must not reject anything."""
    assert ValidationService.description_mentions_business("N'importe quel texte.", None, None)


def test_build_from_raw_drops_google_boilerplate_meta() -> None:
    data = EnrichmentScraper._build_from_raw(
        {"description": GOOGLE_META_EN},
        business_name="Debiolle Patrick",
        city="Saint-Germain-Lembron",
    )
    assert data.description is None


def test_build_from_raw_drops_meta_about_another_business() -> None:
    data = EnrichmentScraper._build_from_raw(
        {"description": "Boulangerie Martin à Clermont-Ferrand, pains et viennoiseries."},
        business_name="Debiolle Patrick",
        city="Saint-Germain-Lembron",
    )
    assert data.description is None


def test_build_from_raw_keeps_place_meta_naming_the_business() -> None:
    data = EnrichmentScraper._build_from_raw(
        {"description": PLACE_META},
        business_name="Debiolle Patrick",
        city="Saint-Germain-Lembron",
    )
    assert data.description == PLACE_META


def test_build_from_raw_keeps_json_ld_description_without_name_mention() -> None:
    """A JSON-LD description is place data — trusted even when it names nobody."""
    ld_block = f'{{"@type": "AutoRepair", "name": "Debiolle Patrick", "description": "{BUSINESS_LD_DESCRIPTION}"}}'
    data = EnrichmentScraper._build_from_raw(
        {"description": GOOGLE_META_EN, "ld": [ld_block]},
        business_name="Debiolle Patrick",
        city="Saint-Germain-Lembron",
    )
    assert data.description == BUSINESS_LD_DESCRIPTION


def test_site_content_falls_back_to_default_on_stored_boilerplate() -> None:
    """Enrichments poisoned before the fix must never leak onto a demo site."""
    content = map_prospect_and_enrichment(
        business_name="Debiolle Patrick",
        phone=None,
        email=None,
        city="Saint-Germain-Lembron",
        area="Saint-Germain-Lembron",
        subtitle="Garage automobile",
        palette={},
        enrichment={"description": GOOGLE_META_EN},
        about_default="Un garage de confiance, proche de chez vous.",
    )
    assert content["about"] == "Un garage de confiance, proche de chez vous."


def test_site_content_keeps_real_description() -> None:
    content = map_prospect_and_enrichment(
        business_name="Debiolle Patrick",
        phone=None,
        email=None,
        city="Saint-Germain-Lembron",
        area="Saint-Germain-Lembron",
        subtitle="Garage automobile",
        palette={},
        enrichment={"description": BUSINESS_LD_DESCRIPTION},
        about_default="Un garage de confiance, proche de chez vous.",
    )
    assert content["about"] == BUSINESS_LD_DESCRIPTION
