"""
A scraped food description is often too fragmentary to use as an about ("Food Truck à Poitiers
Spécialité: poulet frit coréen"), but its "Spécialité: …" is the truck's identity. Rather than discard
it with the whole description, food surfaces the specialty in the about — but only when it fell back to
the generic default (a real, usable description is never overwritten).
"""

from services.templates import registry
from services.templates.food import _SITE_ABOUT_DEFAULT
from services.templates.site_content import extract_specialty


def _about(description: str) -> str:
    site = registry.build_site_content(
        template_id="food",
        business_name="Tasty Korea",
        phone="0",
        email="x@y.fr",
        city="Poitiers",
        area="Poitiers",
        subtitle="",
        palette={"primary": "#000", "secondary": "#111", "accent": "#222"},
        enrichment={"description": description},
    )
    return site["about"]


def test_extract_specialty_basic() -> None:
    assert extract_specialty("Food Truck à Poitiers Spécialité: poulet frit coréen") == "poulet frit coréen"


def test_extract_specialty_stops_before_next_glued_label() -> None:
    assert extract_specialty("Spécialités : tacos maison Horaires: 9h-18h") == "tacos maison"


def test_extract_specialty_absent() -> None:
    assert extract_specialty("Un food truck sympa au centre-ville") == ""


def test_fragmentary_description_surfaces_specialty_in_about() -> None:
    about = _about("Food Truck à Poitiers Spécialité: poulet frit coréen")
    assert about.startswith("Spécialité maison : poulet frit coréen.")
    assert _SITE_ABOUT_DEFAULT in about


def test_real_description_is_not_overwritten() -> None:
    real = (
        "Notre food truck coréen sillonne Poitiers depuis 2019 : du poulet frit maison, "
        "des bols généreux et une équipe qui prépare tout minute devant vous, avec le sourire."
    )
    assert _about(real) == real
