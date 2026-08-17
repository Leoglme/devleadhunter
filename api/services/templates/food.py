"""
'food' demo template — self-contained registration.

Food truck / street food template: cream & forest-green DA (Pencil food trucks landing).
Flat ``SiteContent`` path only — Storyblok uses the shared ``site_content``
blok family; the Nuxt layer is ``devleadhunter-template-food``.

Exposes the stable names consumed by the shared services (see ``registry``):

- ``TEMPLATE_META``       → catalogue entry
- ``build_site_content``  → flat ``SiteContent`` builder
- ``BODY_COMPONENTS`` / ``COMPONENT_SCHEMAS`` → none beyond the shared base
"""

from __future__ import annotations

from typing import Any

from services.templates.site_content import (  # noqa: F401 — re-exported for the registry
    SITE_CONTENT_SCHEMAS,
    format_rating_value,
    format_review_count,
    map_prospect_and_enrichment,
    resolve_trade_services,
    to_storyblok_site_content,
)

TEMPLATE_ID: str = "food"

TEMPLATE_META: dict[str, object] = {
    "id": TEMPLATE_ID,
    "name": "Food Truck",
    "description": (
        "Vitrine food truck / street food « crème & vert forêt » : hero, à propos "
        "avec collage photo, menu spécialités, avis, formulaire de réservation. "
        "One-page vendable inspirée d'une landing food trucks."
    ),
    "preview_image_url": None,
    "category": "artisan",
    "trades": ["restaurant", "foodtruck", "food truck", "traiteur", "restauration"],
    "default_theme": {
        "primary": "#055346",
        "secondary": "#f9efe6",
        "accent": "#f3c395",
    },
}

# Shared base bloks only (flat SiteContent).
BODY_COMPONENTS: list[str] = []
COMPONENT_SCHEMAS: list[dict[str, Any]] = []

# Sections this template renders — drives the client's Storyblok editor so it shows no dead sections.
USED_SECTIONS: list[str] = ["hero", "trust", "about", "services", "gallery", "reviews", "faq", "contact"]


def default_subtitle(area: str) -> str:
    """Food-truck-aware default hero subtitle when the prospect has no description.

    Args:
        area: Service area / city label.

    Returns:
        A food-truck subtitle.
    """
    return f"Cuisine de rue faite maison à {area}, préparée minute — sur place ou à emporter."


_SITE_ABOUT_DEFAULT: str = (
    "Food truck de quartier : cuisine simple et généreuse, sauces maison et "
    "service rapide. On privilégie les produits frais et on vient à vous — "
    "sur vos places préférées ou pour vos événements."
)

# Trade defaults when enrichment provides no services / FAQ.
# Mirror of layer defaults in devleadhunter-template-food (food.ts).
# Cuisine-NEUTRAL fallback (used only when no real menu was scraped): a food truck's menu is its
# identity, so we never invent typed dishes (a burger/hot-dog default clashed with, e.g., a Korean
# or Mexican truck). Real scraped items win; these neutral cards just avoid a wrong-cuisine menu.
FOOD_SERVICES: list[dict[str, str]] = [
    {
        "title": "Plat signature",
        "description": "Notre recette phare, préparée minute avec des produits frais.",
    },
    {
        "title": "Formule du midi",
        "description": "Un plat, un accompagnement et une boisson — rapide et généreux.",
    },
    {
        "title": "Sur place ou à emporter",
        "description": "Servi chaud, prêt à déguster sur le pouce ou à emporter.",
    },
    {
        "title": "Boisson & douceur",
        "description": "Boissons fraîches et petites douceurs pour compléter le repas.",
    },
]

FOOD_FAQ: list[dict[str, str]] = [
    {
        "question": "Où vous trouver cette semaine ?",
        "answer": (
            "On publie chaque lundi notre planning sur Instagram et Facebook. "
            "Appelez-nous aussi : on vous indique la place du jour."
        ),
    },
    {
        "question": "Acceptez-vous les groupes et événements ?",
        "answer": (
            "Oui — mariages, séminaires, festivals. Écrivez-nous ou réservez via "
            "le formulaire, on revient vers vous rapidement."
        ),
    },
    {
        "question": "Proposez-vous des options végétariennes ?",
        "answer": ("Oui, un burger veggie et des sides (frites, salade) sont toujours au menu."),
    },
    {
        "question": "Quels moyens de paiement acceptez-vous ?",
        "answer": "Espèces et carte bancaire, sur place.",
    },
]

# Editorial copy pre-filled into the CMS — EXACT mirror of the layer defaults
# (devleadhunter-template-food app/types/food.ts).
_EDITORIAL_DEFAULTS: dict[str, Any] = {
    "heroBadge": "Food truck",
    "heroPoints": ["Fait maison", "Produits frais", "Sur place ou à emporter"],
    "ctaCallLabel": "Envoyer la demande",
    "ctaQuoteLabel": "Voir le menu",
    "trustItems": [
        {"value": "4,9/5", "label": "Avis clients"},
        {"value": "12K+", "label": "Sur Instagram"},
    ],
    "servicesHeading": "Nos spécialités",
    "galleryHeading": "En images",
    "reviewsHeading": "Ce qu’ils en disent",
    "faqHeading": "Questions fréquentes",
    "aboutHeading": "Notre histoire gourmande",
    "contactHeading": "Réserver une table",
}


def _apply_real_food_stats(site: dict[str, Any], enrichment: dict[str, Any] | None) -> None:
    """Replace the two hero-collage stats with the prospect's real Google rating and review count.

    The template ships a "4,9/5" placeholder and a fabricated "12K+ / Sur Instagram"; a real
    review count (e.g. 2 227) is both truthful and a stronger proof point than an invented follower
    number. Each stat falls back to its editorial default when the matching figure is missing.
    """
    enr = enrichment or {}
    rating_value = format_rating_value(enr.get("rating"))
    count_value = format_review_count(enr.get("reviews_count"))
    stats = site.get("trustItems")
    if not isinstance(stats, list):
        return
    # Copy so the shared, module-level ``_EDITORIAL_DEFAULTS`` is never mutated across generations.
    stats = [dict(item) if isinstance(item, dict) else item for item in stats]
    if rating_value and len(stats) >= 1:
        stats[0] = {"value": rating_value, "label": "Avis Google"}
    if count_value and len(stats) >= 2:
        stats[1] = {"value": count_value, "label": "Avis clients"}
    site["trustItems"] = stats


def build_site_content(
    *,
    business_name: str,
    phone: str | None,
    email: str | None,
    city: str | None,
    area: str,
    subtitle: str,
    palette: dict[str, str],
    enrichment: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the flat ``SiteContent`` for this template (Phase 4b).

    Prospect fields + enrichment map through the shared helper; services come from the
    scraped enrichment when present, else the food-truck editorial defaults; the template
    layer supplies section headings and remaining boilerplate. See ``site_content.py``.
    """
    site = map_prospect_and_enrichment(
        business_name=business_name,
        phone=phone,
        email=email,
        city=city,
        area=area,
        subtitle=subtitle,
        palette=palette,
        enrichment=enrichment,
        about_default=_SITE_ABOUT_DEFAULT,
    )
    enr = enrichment or {}
    site["services"] = resolve_trade_services(enr.get("services"), FOOD_SERVICES)
    site["faq"] = FOOD_FAQ
    site.update(_EDITORIAL_DEFAULTS)
    _apply_real_food_stats(site, enrichment)
    return site
