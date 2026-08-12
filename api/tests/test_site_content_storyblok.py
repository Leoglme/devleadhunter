"""
Round-trip tests for the ``SiteContent`` ⇄ Storyblok bridge, focused on the image asset fields
(logo/hero/about/gallery/before-after) that must survive push → published-story → content_json.
"""

from services.templates import site_content as sc


def _flat_site() -> dict:
    """A minimal flat SiteContent carrying every image-bearing field."""
    return {
        "businessName": "Barbier d'Antan",
        "logo": "https://img.example/logo.png",
        "heroImage": "https://img.example/hero.jpg",
        "aboutImage": "https://img.example/about.jpg",
        "gallery": [
            {"url": "https://img.example/g1.jpg", "alt": "Devanture"},
            {"url": "https://img.example/g2.jpg", "alt": ""},
        ],
        "beforeAfter": [
            {"before": "https://img.example/b.jpg", "after": "https://img.example/a.jpg", "label": "Salon"}
        ],
    }


def test_images_become_storyblok_asset_objects() -> None:
    """Single images push as asset objects and the gallery pushes as a multiasset list."""
    blok = sc.to_storyblok_site_content(_flat_site())

    assert blok["logo"]["fieldtype"] == "asset"
    assert blok["heroImage"]["filename"] == "https://img.example/hero.jpg"
    assert [asset["filename"] for asset in blok["gallery"]] == [
        "https://img.example/g1.jpg",
        "https://img.example/g2.jpg",
    ]
    assert blok["beforeAfter"][0]["before"]["filename"] == "https://img.example/b.jpg"


def test_round_trip_preserves_image_urls() -> None:
    """Pushing then flattening a published story yields back the original image URLs."""
    blok = sc.to_storyblok_site_content(_flat_site())
    flat = sc.from_storyblok_site_content(blok)

    assert flat["logo"] == "https://img.example/logo.png"
    assert flat["heroImage"] == "https://img.example/hero.jpg"
    assert flat["aboutImage"] == "https://img.example/about.jpg"
    assert [image["url"] for image in flat["gallery"]] == [
        "https://img.example/g1.jpg",
        "https://img.example/g2.jpg",
    ]
    assert flat["gallery"][0]["alt"] == "Devanture"
    assert flat["beforeAfter"][0] == {
        "before": "https://img.example/b.jpg",
        "after": "https://img.example/a.jpg",
        "label": "Salon",
    }


def test_flatten_tolerates_legacy_plain_url_strings() -> None:
    """A pre-asset story (bare URL strings) still flattens without breaking."""
    legacy = {
        "component": "site_content",
        "logo": "https://img.example/legacy-logo.png",
        "heroImage": "https://img.example/legacy-hero.jpg",
    }
    flat = sc.from_storyblok_site_content(legacy)

    assert flat["logo"] == "https://img.example/legacy-logo.png"
    assert flat["heroImage"] == "https://img.example/legacy-hero.jpg"


def test_empty_images_stay_empty() -> None:
    """A missing image yields an empty asset on push and an empty string on flatten."""
    blok = sc.to_storyblok_site_content({"businessName": "Sans photo"})
    flat = sc.from_storyblok_site_content(blok)

    assert blok["logo"]["filename"] == ""
    assert blok["gallery"] == []
    assert flat["logo"] == ""
    assert flat["heroImage"] == ""
