"""Tests for the multi-email bounce fallback selection logic (the pure, DB-free part)."""

from services.bounce_fallback_service import next_fallback_email


def test_returns_first_untried_email() -> None:
    emails = ["jean@x.fr", "contact@my-coiffure.fr"]
    assert next_fallback_email(emails, {"jean@x.fr"}) == "contact@my-coiffure.fr"


def test_tried_check_is_case_insensitive() -> None:
    emails = ["Jean@X.fr", "contact@my-coiffure.fr"]
    assert next_fallback_email(emails, {"jean@x.fr"}) == "contact@my-coiffure.fr"


def test_returns_none_when_all_tried() -> None:
    emails = ["jean@x.fr", "contact@my-coiffure.fr"]
    assert next_fallback_email(emails, {"jean@x.fr", "contact@my-coiffure.fr"}) is None


def test_skips_blank_entries() -> None:
    emails = ["", "  ", "contact@my-coiffure.fr"]
    assert next_fallback_email(emails, set()) == "contact@my-coiffure.fr"


def test_first_email_when_nothing_tried() -> None:
    emails = ["jean@x.fr", "contact@my-coiffure.fr"]
    assert next_fallback_email(emails, set()) == "jean@x.fr"
