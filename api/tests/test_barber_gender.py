"""
Barbershop (homme) and mixed salon (coiffeur mixte) share ONE template, with gendered content decided
by a name/category heuristic: a clear "Barbier …" reads as men's ("pour hommes", "votre barbier"), a
"… Coiffure/Salon" as mixed (neutral), and anything ambiguous falls back to the neutral wording.
"""

from services.templates import registry
from services.templates.barber import _ABOUT_MEN, _ABOUT_MIXED, _is_masculine_barber


def _build(business_name: str) -> dict:
    return registry.build_site_content(
        template_id="barber",
        business_name=business_name,
        phone="0",
        email="x@y.fr",
        city="Tours",
        area="Tours",
        subtitle="",
        palette={"primary": "#000", "secondary": "#111", "accent": "#222"},
        enrichment={},
    )


def test_clear_barber_is_masculine() -> None:
    assert _is_masculine_barber("Barbier d'Antan", {}) is True
    assert _is_masculine_barber("The Gentlemen Barbershop", {}) is True


def test_coiffeur_or_salon_is_mixed() -> None:
    assert _is_masculine_barber("My Coiffure By Damien Cailler", {}) is False
    assert _is_masculine_barber("Salon Éléganza", {}) is False


def test_ambiguous_name_falls_back_to_mixed() -> None:
    assert _is_masculine_barber("Damien Cailler", {}) is False


def test_barber_and_salon_together_is_mixed() -> None:
    # Both signals → safe neutral default.
    assert _is_masculine_barber("Salon Barbier Mixte", {}) is False


def test_category_from_enrichment_counts() -> None:
    assert _is_masculine_barber("Chez Damien", {"category": "Barbier"}) is True
    assert _is_masculine_barber("Chez Damien", {"category": "Salon de coiffure"}) is False


def test_masculine_build_uses_men_copy() -> None:
    site = _build("Barbier d'Antan")
    assert site["audience"] == "men"
    assert site["about"] == _ABOUT_MEN
    assert site["aboutHeading"] == "Votre barbier de quartier"
    # heroBadge carries the audience to the layer (``audience`` is stripped by the Storyblok round-trip).
    assert site["heroBadge"] == "BARBIER"


def test_mixed_build_uses_neutral_copy() -> None:
    site = _build("My Coiffure By Damien Cailler")
    assert site["audience"] == "all"
    assert site["about"] == _ABOUT_MIXED
    assert site["aboutHeading"] == "Votre salon de quartier"
    assert "pour hommes" not in site["about"]
    assert site["heroBadge"] == "COIFFEUR"
