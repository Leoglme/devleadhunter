"""
Colour editor by ROLES: every template maps its palette keys (primary/secondary/accent) to canonical
roles (action/fond/secondaire), only exposing the roles a layer visibly consumes. The action role must
equal ``brand_color_key`` so the logo colour lands on the real CTA — and ``use_brand_color=False`` keeps
the template's default action colour.
"""

from services.demo_site_service import DemoSiteService
from services.templates import registry
from services.templates.registry import AVAILABLE_TEMPLATES


def test_every_template_declares_color_roles_with_action_matching_brand_key() -> None:
    for meta in AVAILABLE_TEMPLATES:
        roles = meta.get("color_roles")
        assert isinstance(roles, dict) and roles, f"{meta['id']} has no color_roles"
        assert "action" in roles, f"{meta['id']} has no action role"
        # The action role's key must be the brand_color_key (what the logo colour overrides).
        assert roles["action"] == registry.brand_color_key(meta["id"]), (
            f"{meta['id']} action role {roles['action']} != brand_color_key {registry.brand_color_key(meta['id'])}"
        )
        # Every mapped key is a real palette key.
        assert all(key in ("primary", "secondary", "accent") for key in roles.values())


def test_plumber_signature_action_is_accent() -> None:
    # Audit finding: the coral "signal" (accent) is the CTA colour, not the petrol primary.
    assert registry.brand_color_key("plumber-signature") == "accent"


def test_dead_roles_are_hidden() -> None:
    # artisan-edito + barber only theme via accent → the editor shows a single "action" role.
    assert set(registry.color_roles("barber")) == {"action"}
    assert set(registry.color_roles("artisan-edito")) == {"action"}


def test_use_brand_color_false_keeps_template_action_colour() -> None:
    base = {"primary": "#111", "secondary": "#222", "accent": "#333"}
    enrichment = {"logo_url": "https://example.com/logo.png"}
    # Flag off → palette returned unchanged, regardless of the logo.
    off = DemoSiteService._apply_brand_color(base, "food", enrichment, use_brand_color=False)
    assert off == base
