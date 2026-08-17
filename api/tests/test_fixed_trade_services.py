"""
Tests for the fixed service grid: a trade's services are standardised, so barber/mechanic use their
curated default list as-is — every card described, stable count, fake prices stripped — instead of a
scraped-driven grid with empty cards and a variable count. (Food keeps its scraped menu.)
"""

from services.templates import registry
from services.templates.barber import BARBER_SERVICES
from services.templates.mechanic_pitlane import MECHANIC_SERVICES


def _services(template_id: str, enrichment: dict) -> list[dict]:
    site = registry.build_site_content(
        template_id=template_id,
        business_name="X",
        phone="0",
        email="x@y.fr",
        city="Tours",
        area="Tours",
        subtitle="",
        palette={"primary": "#000", "secondary": "#111", "accent": "#222"},
        enrichment=enrichment,
    )
    return site["services"]


def test_barber_grid_is_the_fixed_list_regardless_of_scraped() -> None:
    services = _services("barber", {"services": ["Coloration", "Un service random"]})
    assert [s["title"] for s in services] == [s["title"] for s in BARBER_SERVICES]
    assert all(s["description"].strip() for s in services)
    assert all("€" not in s["description"] for s in services)


def test_mechanic_grid_is_the_fixed_list_and_fully_described() -> None:
    services = _services("mechanic-pitlane", {"services": []})
    assert [s["title"] for s in services] == [s["title"] for s in MECHANIC_SERVICES]
    assert all(s["description"].strip() for s in services)
