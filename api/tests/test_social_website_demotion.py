"""A social page (Facebook/Instagram) must never count as a prospect's real website.

It made prospects read as "has a site", hiding them from the without-a-site targeting. The URL is
demoted at create/update time — a Facebook page is preserved as ``facebook_url``, then the website cleared.
"""

from services.prospect_service import ProspectService
from services.validation_service import ValidationService


def test_is_social_url_matches_social_pages() -> None:
    assert ValidationService.is_social_url("http://www.facebook.com/mcbydc") is True
    assert ValidationService.is_social_url("https://instagram.com/salon") is True
    assert ValidationService.is_social_url("https://m.facebook.com/mcbydc") is True


def test_is_social_url_does_not_match_real_sites() -> None:
    assert ValidationService.is_social_url("https://www.mon-salon.fr") is False
    # "x.com" is a social domain but must not match a real site that merely ends with those letters.
    assert ValidationService.is_social_url("https://max.com") is False
    assert ValidationService.is_social_url(None) is False


def test_is_valid_website_still_rejects_social_and_accepts_real() -> None:
    assert ValidationService.is_valid_website("https://www.facebook.com/mybusiness") is False
    assert ValidationService.is_valid_website("http://example.fr") is True


def test_facebook_website_is_moved_to_facebook_url_and_cleared() -> None:
    website, status, facebook = ProspectService._demote_social_website("http://www.facebook.com/mcbydc", "live", None)
    assert website is None
    assert status is None
    assert facebook == "http://www.facebook.com/mcbydc"


def test_existing_facebook_url_is_not_overwritten() -> None:
    website, _, facebook = ProspectService._demote_social_website(
        "http://www.facebook.com/mcbydc", "live", "https://facebook.com/original"
    )
    assert website is None
    assert facebook == "https://facebook.com/original"


def test_real_website_is_left_untouched() -> None:
    website, status, facebook = ProspectService._demote_social_website("https://www.mon-salon.fr", "live", None)
    assert website == "https://www.mon-salon.fr"
    assert status == "live"
    assert facebook is None
