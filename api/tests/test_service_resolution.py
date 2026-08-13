"""
Tests for the shared service resolution — real scraped service names must never carry an invented
template price, and no site should ever display a made-up price.
"""

from services.templates import registry
from services.templates.site_content import resolve_trade_services, without_price

_DEFAULTS = [
    {"title": "Coupe homme", "description": "Shampooing, coupe et séchage. — 32 €"},
    {"title": "Taille de barbe", "description": "Contour et finition rasoir. — 18 €"},
]


def test_without_price_strips_trailing_price() -> None:
    """A trailing '— 32 €' is removed; the descriptive text is kept."""
    assert without_price("Shampooing, coupe et séchage. — 32 €") == "Shampooing, coupe et séchage."
    assert without_price("Contour et finition rasoir. — 18 €") == "Contour et finition rasoir."
    assert without_price("Sans prix") == "Sans prix"
    assert without_price(None) == ""


def test_scraped_services_keep_names_without_invented_price() -> None:
    """Scraped names are kept, matched to a default description with the price stripped."""
    services = resolve_trade_services(["Coupe homme", "Coloration"], _DEFAULTS)

    assert services[0] == {"title": "Coupe homme", "description": "Shampooing, coupe et séchage."}
    # An unmatched scraped name stays a clean title-only card, never a wrong/false description.
    assert services[1] == {"title": "Coloration", "description": ""}
    assert all("€" not in service["description"] for service in services)


def test_fallback_defaults_also_drop_prices() -> None:
    """With no scraped services, the template defaults are shown but with prices stripped."""
    services = resolve_trade_services([], _DEFAULTS)

    assert [service["title"] for service in services] == ["Coupe homme", "Taille de barbe"]
    assert all("€" not in service["description"] for service in services)


def test_no_launch_template_emits_a_price() -> None:
    """barber / mechanic / food never emit a '€' price, scraped or fallback."""
    for template_id in ("barber", "mechanic-pitlane", "food"):
        for scraped in ([], ["Prestation inconnue"]):
            site = registry.build_site_content(
                template_id=template_id,
                business_name="X",
                phone="0",
                email="x@y.fr",
                city="Tours",
                area="Tours",
                subtitle="",
                palette={"primary": "#000", "secondary": "#111", "accent": "#222"},
                enrichment={"services": scraped},
            )
            assert all("€" not in service.get("description", "") for service in site["services"]), (
                template_id,
                scraped,
            )
