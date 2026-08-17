"""
Facebook-CDN URLs (fbcdn.net / fbsbx.com) are signed and session-bound: the VPS gets 403 fetching
them, so they never rehost to Storyblok and render broken on the site. Generation drops them — from
both the photo pool and the logo — so the template's fallback imagery fills the slot (a complete site)
instead of broken tiles. Google-hosted photos are untouched.
"""

from services.templates import registry


def _site(photos: list[str], logo: str = "") -> dict:
    return registry.build_site_content(
        template_id="food",
        business_name="Tacos Maru",
        phone="0",
        email="x@y.fr",
        city="Poitiers",
        area="Poitiers",
        subtitle="",
        palette={"primary": "#000", "secondary": "#111", "accent": "#222"},
        enrichment={"photos": photos, "logo_url": logo},
    )


def test_fbcdn_photos_are_dropped_from_every_slot() -> None:
    fb = "https://scontent-cdg4-3.xx.fbcdn.net/v/t39.30808-6/abc.jpg?oh=1&oe=2"
    site = _site([fb, fb + "second", fb + "third"])
    blob = f"{site.get('heroImage')}{site.get('aboutImage')}{site.get('gallery')}"
    assert "fbcdn" not in blob


def test_google_photos_survive() -> None:
    google = "https://lh3.googleusercontent.com/p/AF1QipABC=w800"
    site = _site([google])
    assert site.get("heroImage") == google


def test_fbcdn_logo_is_dropped_so_the_favicon_falls_back() -> None:
    site = _site([], logo="https://scontent.xx.fbcdn.net/v/logo.jpg?oh=1")
    assert site.get("logo") == ""
