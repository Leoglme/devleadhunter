"""
Tests for the demo-site image-placement editor: the usable photo pool, cleaning a user-curated
order against it, and the fact that a curated order reorders the hero/about/gallery slots.
"""

from types import SimpleNamespace

import pytest

from services.demo_site_service import DemoSiteService
from services.templates import registry
from services.templates.site_content import usable_site_photos


def _site_with_photos(photos: list[str]) -> dict:
    return registry.build_site_content(
        template_id="barber",
        business_name="X",
        phone="0",
        email="x@y.fr",
        city="Tours",
        area="Tours",
        subtitle="",
        palette={"primary": "#000", "secondary": "#111", "accent": "#222"},
        enrichment={"photos": photos},
    )


def test_usable_pool_dedupes_and_drops_logo_and_broken_hosts() -> None:
    pool = usable_site_photos(
        {
            "logo_url": "https://cdn/logo.png",
            "photos": [
                "https://cdn/a.jpg",
                "https://cdn/a.jpg",  # duplicate
                "https://cdn/logo.png",  # logo, excluded
                "https://scontent.xx.fbcdn.net/x.jpg",  # unrehostable, dropped
                "https://cdn/b.jpg",
            ],
        }
    )
    assert pool == ["https://cdn/a.jpg", "https://cdn/b.jpg"]


def test_usable_pool_handles_no_enrichment() -> None:
    assert usable_site_photos(None) == []
    assert usable_site_photos({}) == []


def test_clean_image_order_keeps_pool_urls_in_order_without_duplicates() -> None:
    pool = ["a", "b", "c"]
    # unknown "z" dropped, duplicate "b" collapsed, order honoured
    assert DemoSiteService._clean_image_order(["c", "z", "b", "b", "a"], pool) == ["c", "b", "a"]


def test_clean_image_order_rejects_non_list() -> None:
    assert DemoSiteService._clean_image_order(None, ["a"]) == []
    assert DemoSiteService._clean_image_order("a", ["a"]) == []


@pytest.mark.asyncio
async def test_update_demo_site_saves_image_order_with_a_single_regeneration(monkeypatch) -> None:
    """The unified PATCH (template/colours/images together) cleans the order and regenerates once."""
    service = DemoSiteService()
    # SimpleNamespace stand-in (house pattern): a real DemoSite() would configure every mapper.
    site = SimpleNamespace(template_id="barber", business_name="X", image_order=None, use_brand_color=True)
    regenerate_calls: list[object] = []

    async def fake_regenerate(_self: DemoSiteService, _db: object, demo_site: object) -> object:
        regenerate_calls.append(demo_site)
        return demo_site

    monkeypatch.setattr(DemoSiteService, "regenerate_demo_site", fake_regenerate)
    monkeypatch.setattr(DemoSiteService, "_enrichment_dict_for_site", lambda _self, _db, _site: {})
    monkeypatch.setattr("services.demo_site_service.usable_site_photos", lambda _enrichment: ["a", "b", "c"])

    await service.update_demo_site(None, site, template_id="food", image_order=["c", "z", "a"])

    assert site.template_id == "food"
    assert site.image_order == ["c", "a"]  # unknown "z" dropped, order kept
    assert len(regenerate_calls) == 1


@pytest.mark.asyncio
async def test_update_demo_site_stores_default_image_order_as_null(monkeypatch) -> None:
    """An order matching the pool means « follow the scraped order »: stored as NULL, not a copy."""
    service = DemoSiteService()
    site = SimpleNamespace(template_id="barber", business_name="X", image_order=["b", "a"], use_brand_color=True)

    async def fake_regenerate(_self: DemoSiteService, _db: object, demo_site: object) -> object:
        return demo_site

    monkeypatch.setattr(DemoSiteService, "regenerate_demo_site", fake_regenerate)
    monkeypatch.setattr(DemoSiteService, "_enrichment_dict_for_site", lambda _self, _db, _site: {})
    monkeypatch.setattr("services.demo_site_service.usable_site_photos", lambda _enrichment: ["a", "b"])

    await service.update_demo_site(None, site, image_order=["a", "b"])

    assert site.image_order is None


def test_curated_order_reorders_hero_about_gallery() -> None:
    # This is exactly what the service injects into enrichment["photos"] when image_order is set.
    default = _site_with_photos(["h.jpg", "ab.jpg", "g1.jpg", "g2.jpg"])
    assert default["heroImage"] == "h.jpg"
    assert default["aboutImage"] == "ab.jpg"

    curated = _site_with_photos(["g2.jpg", "h.jpg", "ab.jpg"])  # promote g2 to hero, drop g1
    assert curated["heroImage"] == "g2.jpg"
    assert curated["aboutImage"] == "h.jpg"
    assert [g["url"] for g in curated["gallery"]] == ["ab.jpg"]
