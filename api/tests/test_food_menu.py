"""
Tests for the food template menu: a food truck's menu is its identity, so a real scraped menu is used
when present, and the fallback (when nothing was scraped) is cuisine-NEUTRAL — never typed dishes
(a burger/hot-dog default clashed with, e.g., a Korean or Mexican truck).
"""

from services.templates import registry


def _food_service_titles(enrichment: dict) -> list[str]:
    site = registry.build_site_content(
        template_id="food",
        business_name="Tasty Korea",
        phone="0",
        email="x@y.fr",
        city="Poitiers",
        area="Poitiers",
        subtitle="",
        palette={"primary": "#000", "secondary": "#111", "accent": "#222"},
        enrichment=enrichment,
    )
    return [s["title"] for s in site["services"]]


def test_fallback_menu_is_cuisine_neutral() -> None:
    joined = " ".join(_food_service_titles({})).lower()
    assert "burger" not in joined
    assert "hot-dog" not in joined
    assert "hot wings" not in joined
    assert "plat signature" in joined


def test_real_scraped_menu_is_used_when_present() -> None:
    titles = _food_service_titles({"services": ["Tacos mexicains", "Guacamole maison"]})
    assert "Tacos mexicains" in titles
