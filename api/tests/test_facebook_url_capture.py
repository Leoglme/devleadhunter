"""
Tests for capturing a prospect's Facebook page URL from Google Maps enrichment — a Facebook link on
the listing (as the "website" link or a social link) must be surfaced so a later Facebook enrichment
can recover a second contact email.
"""

from services.enrichment_service import EnrichmentService


class _Scraped:
    def __init__(self, social_links: dict | None = None, website: str | None = None) -> None:
        self.social_links = social_links
        self.website = website


def test_facebook_url_from_social_link() -> None:
    """An explicit Facebook social link is used."""
    data = _Scraped(social_links={"facebook": "https://facebook.com/mcbydc", "instagram": "https://instagram.com/x"})
    assert EnrichmentService._facebook_url_from_data(data) == "https://facebook.com/mcbydc"


def test_facebook_url_from_website_link() -> None:
    """When the Maps 'website' link points to Facebook, it is captured as the Facebook URL."""
    assert EnrichmentService._facebook_url_from_data(_Scraped(website="http://www.facebook.com/mcbydc")) == (
        "http://www.facebook.com/mcbydc"
    )


def test_real_website_is_not_a_facebook_url() -> None:
    """A real website (non-Facebook) is not mistaken for a Facebook page."""
    assert EnrichmentService._facebook_url_from_data(_Scraped(website="https://mon-salon.fr")) is None
    assert EnrichmentService._facebook_url_from_data(_Scraped()) is None
