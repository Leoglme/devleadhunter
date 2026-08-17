"""
Tests for how enrichment photos map to the template slots. The prospect's logo has its own slot and
must never be reused as a hero / about / gallery tile, even when it was scraped into the photo pool.
"""

from services.templates import registry


def _site(enrichment: dict) -> dict:
    return registry.build_site_content(
        template_id="barber",
        business_name="X",
        phone="0",
        email="x@y.fr",
        city="Tours",
        area="Tours",
        subtitle="",
        palette={"primary": "#000", "secondary": "#111", "accent": "#222"},
        enrichment=enrichment,
    )


def test_logo_is_never_used_as_a_photo_slot() -> None:
    site = _site(
        {
            "logo_url": "https://cdn/logo.png",
            "photos": [
                "https://cdn/hero.jpg",
                "https://cdn/logo.png",
                "https://cdn/about.jpg",
                "https://cdn/g1.jpg",
            ],
        }
    )
    used = [site["heroImage"], site["aboutImage"], *[g["url"] for g in site["gallery"]]]
    assert "https://cdn/logo.png" not in used
    assert site["heroImage"] == "https://cdn/hero.jpg"
    assert site["aboutImage"] == "https://cdn/about.jpg"
    assert [g["url"] for g in site["gallery"]] == ["https://cdn/g1.jpg"]


def test_no_logo_leaves_photos_untouched() -> None:
    site = _site({"photos": ["https://cdn/a.jpg", "https://cdn/b.jpg"]})
    assert site["heroImage"] == "https://cdn/a.jpg"
    assert site["aboutImage"] == "https://cdn/b.jpg"
