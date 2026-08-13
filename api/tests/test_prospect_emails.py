"""
Tests for the prospect multi-email helpers and the Facebook email extraction: emails are deduped,
``email`` stays synced to ``emails[0]`` (the primary), and a Facebook page's contact email is found.
"""

from scrappers.facebook_enrichment_scraper import _extract_emails
from services.prospect_emails import dedupe_emails, sync_prospect_emails


class _Prospect:
    def __init__(self, email: str | None = None, emails: list[str] | None = None) -> None:
        self.email = email
        self.emails = emails


def test_dedupe_is_case_insensitive_and_keeps_order() -> None:
    assert dedupe_emails(["A@x.fr", "b@x.fr", "a@X.FR", "", None, "  "]) == ["A@x.fr", "b@x.fr"]


def test_sync_backfills_from_single_email() -> None:
    prospect = _Prospect(email="jean@x.fr")
    sync_prospect_emails(prospect)
    assert prospect.emails == ["jean@x.fr"]
    assert prospect.email == "jean@x.fr"


def test_sync_adds_new_email_and_keeps_primary_first() -> None:
    prospect = _Prospect(email="jean@x.fr", emails=["jean@x.fr"])
    sync_prospect_emails(prospect, add=["contact@my-coiffure.fr", "jean@x.fr"])
    assert prospect.emails == ["jean@x.fr", "contact@my-coiffure.fr"]
    assert prospect.email == "jean@x.fr"


def test_sync_can_force_a_new_primary() -> None:
    prospect = _Prospect(email="jean@x.fr", emails=["jean@x.fr", "contact@my-coiffure.fr"])
    sync_prospect_emails(prospect, primary="contact@my-coiffure.fr")
    assert prospect.emails == ["contact@my-coiffure.fr", "jean@x.fr"]
    assert prospect.email == "contact@my-coiffure.fr"


def test_extract_emails_from_facebook_text() -> None:
    intro = "48 faubourg saint jacques\n05 49 21 83 64\ncontact@my-coiffure.fr\nfacebook.com/mcbydc"
    assert _extract_emails(intro, "", "") == ["contact@my-coiffure.fr"]


def test_extract_emails_filters_cdn_and_facebook_noise() -> None:
    noisy = "photo scontent-x.fbcdn.net/v/t1.jpg no-reply@facebook.com real@salon.fr"
    assert _extract_emails(noisy) == ["real@salon.fr"]
