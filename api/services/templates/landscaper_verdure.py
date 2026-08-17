"""
'landscaper-verdure' demo template — self-contained registration.

Paysagiste / verdure one-page (Pencil DA « Eco Landscaping » : Inter, vert d'eau,
encre sapin, lime en accent). Flat ``SiteContent`` path only — Storyblok uses the
shared ``site_content`` blok family; the Nuxt layer is
``devleadhunter-template-landscaper-verdure``.

Exposes the stable names consumed by the shared services (see ``registry``):

- ``TEMPLATE_META``       → catalogue entry
- ``build_site_content``  → flat ``SiteContent`` builder
- ``BODY_COMPONENTS`` / ``COMPONENT_SCHEMAS`` → none beyond the shared base
"""

from __future__ import annotations

from typing import Any

from services.templates.site_content import (  # noqa: F401 — re-exported for the registry
    SITE_CONTENT_SCHEMAS,
    fixed_trade_services,
    map_prospect_and_enrichment,
    to_storyblok_site_content,
)

TEMPLATE_ID: str = "landscaper-verdure"

TEMPLATE_META: dict[str, object] = {
    "id": TEMPLATE_ID,
    "name": "Paysagiste Verdure",
    "description": (
        "Vitrine one-page paysagiste / verdure « Eco Landscaping » : hero plein cadre, "
        "grille de prestations à encoches, pourquoi nous choisir, méthode en trois "
        "étapes, réalisations, FAQ (crédit d'impôt inclus) et bandeau contact. "
        "Fond vert d'eau, encre sapin, lime en accent."
    ),
    "preview_image_url": None,
    "category": "artisan",
    "trades": ["paysagiste", "jardinier", "fleuriste", "paysagisme", "espaces verts", "elagage", "landscaper"],
    "default_theme": {
        "primary": "#2d746d",
        "secondary": "#003f2e",
        "accent": "#bcff83",
    },
}

# Shared base bloks only (flat SiteContent).
BODY_COMPONENTS: list[str] = []
COMPONENT_SCHEMAS: list[dict[str, Any]] = []

# Sections this template renders — drives the client's Storyblok editor so it shows no dead sections.
USED_SECTIONS: list[str] = ["hero", "about", "services", "gallery", "faq", "contact"]


def default_subtitle(area: str) -> str:
    """Landscaper-aware default hero subtitle when the prospect has no description.

    Args:
        area: Service area / city label.

    Returns:
        A landscaper subtitle.
    """
    return f"Création, aménagement et entretien de jardins à {area} — devis gratuit et pratiques durables."


_SITE_ABOUT_DEFAULT: str = (
    "Paysagiste local, nous accompagnons particuliers et professionnels dans la "
    "création et l'entretien de leurs espaces verts. Chaque projet commence par une "
    "visite et un devis gratuit — et se termine par un extérieur dont on prend "
    "plaisir à profiter."
)

# Trade defaults when enrichment provides no services / FAQ.
# Mirror of layer defaults in devleadhunter-template-landscaper-verdure (verdure.ts).
VERDURE_SERVICES: list[dict[str, str]] = [
    {
        "title": "Création de jardins",
        "description": (
            "Conception et plantation d'un jardin qui vous ressemble, pensé pour durer au fil des saisons."
        ),
    },
    {
        "title": "Entretien & tonte",
        "description": (
            "Tonte, taille, désherbage et soins réguliers pour une pelouse dense et des massifs impeccables."
        ),
    },
    {
        "title": "Terrasses & allées",
        "description": (
            "Terrasses, allées et murets : des aménagements minéraux propres qui structurent votre extérieur."
        ),
    },
    {
        "title": "Arrosage & clôtures",
        "description": ("Arrosage automatique, clôtures et portails posés dans les règles, sans mauvaise surprise."),
    },
]

VERDURE_FAQ: list[dict[str, str]] = [
    {
        "question": "À quelle fréquence intervenez-vous pour l'entretien ?",
        "answer": (
            "Selon vos besoins : au contrat à l'année (passages réguliers planifiés ensemble) ou à la "
            "demande. En pleine saison de pousse, un passage toutes les une à deux semaines garde un "
            "jardin impeccable."
        ),
    },
    {
        "question": "Le devis est-il vraiment gratuit ?",
        "answer": (
            "Oui. Nous nous déplaçons, écoutons votre projet et vous remettons un devis écrit, détaillé "
            "et sans engagement, avant tout début de chantier."
        ),
    },
    {
        "question": "Travaillez-vous avec des produits respectueux de l'environnement ?",
        "answer": (
            "Absolument. Nous privilégions les traitements naturels, le paillage, des végétaux adaptés "
            "au climat local et l'évacuation responsable des déchets verts."
        ),
    },
    {
        "question": "Puis-je bénéficier du crédit d'impôt pour l'entretien de jardin ?",
        "answer": (
            "Oui, les prestations d'entretien courant (tonte, taille de haies…) ouvrent droit au crédit "
            "d'impôt services à la personne de 50 % dans la limite du plafond en vigueur. Nous vous "
            "fournissons l'attestation."
        ),
    },
]

# Editorial copy pre-filled into the CMS — EXACT mirror of the layer defaults
# (devleadhunter-template-landscaper-verdure app/types/verdure.ts fallbacks).
# ``aboutHeading`` is left out on purpose: empty, the layer derives it from the name.
_EDITORIAL_DEFAULTS: dict[str, Any] = {
    "ctaCallLabel": "Être rappelé",
    "ctaQuoteLabel": "Demander un devis gratuit",
    "servicesHeading": "Un seul artisan pour tout votre extérieur",
    "galleryHeading": "Nos derniers chantiers",
    "faqHeading": "Vos questions, nos réponses",
}


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
    """Build the flat ``SiteContent`` for this template.

    Prospect fields + enrichment map through the shared helper; services come from the
    scraped enrichment when present, else the landscaper editorial defaults; the template
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
    site["services"] = fixed_trade_services(VERDURE_SERVICES)
    site["faq"] = VERDURE_FAQ
    site.update(_EDITORIAL_DEFAULTS)
    return site
