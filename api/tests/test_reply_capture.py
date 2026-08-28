"""Unit tests for reply capture — token addresses, parsing, auto-reply detection."""

from __future__ import annotations

import pytest

from services import reply_capture_service as rc


@pytest.fixture(autouse=True)
def _capture_domain(monkeypatch: pytest.MonkeyPatch) -> None:
    """Every test runs with the capture domain configured."""
    monkeypatch.setattr(rc.settings, "reply_capture_domain", "reply.example.fr", raising=False)


def test_reply_address_roundtrip() -> None:
    """An address built for a log id parses back to that id."""
    address = rc.reply_address_for_log(42)
    assert address is not None
    assert address.endswith("@reply.example.fr")
    assert rc.parse_reply_token([address]) == 42


def test_reply_address_disabled_without_domain(monkeypatch: pytest.MonkeyPatch) -> None:
    """No capture domain configured → no Reply-To is produced, nothing parses."""
    monkeypatch.setattr(rc.settings, "reply_capture_domain", "", raising=False)
    assert rc.reply_address_for_log(42) is None
    assert rc.parse_reply_token(["reply-42-abcdef1234@reply.example.fr"]) is None


def test_parse_rejects_forged_signature() -> None:
    """A guessed/tampered signature must not resolve — the domain is a catch-all."""
    assert rc.parse_reply_token(["reply-42-0000000000@reply.example.fr"]) is None


def test_parse_rejects_signature_of_other_id() -> None:
    """A valid signature for one id must not authenticate another id."""
    other = rc.reply_address_for_log(41)
    assert other is not None
    sig = other.split("@")[0].rsplit("-", 1)[1]
    assert rc.parse_reply_token([f"reply-42-{sig}@reply.example.fr"]) is None


def test_parse_ignores_foreign_domains_and_noise() -> None:
    """Addresses on other domains and non-token localparts are skipped, valid one wins."""
    address = rc.reply_address_for_log(7)
    assert rc.parse_reply_token(["leo@mail.example.fr", "contact@reply.example.fr", address]) == 7


def test_parse_handles_display_name_form() -> None:
    """RFC display-name form ``Name <addr>`` still parses."""
    address = rc.reply_address_for_log(7)
    assert rc.parse_reply_token([f"Léo Guillaume <{address}>"]) == 7


def test_parse_empty_inputs() -> None:
    """None / empty recipient lists parse to None rather than raising."""
    assert rc.parse_reply_token(None) is None
    assert rc.parse_reply_token([]) is None


def test_auto_reply_by_subject_french() -> None:
    """A French out-of-office subject is flagged as an autoresponder."""
    assert rc.is_auto_reply("Réponse automatique : Re: votre site", {}) is True


def test_auto_reply_by_auto_submitted_header() -> None:
    """``Auto-Submitted`` with any value except ``no`` marks an autoresponder."""
    assert rc.is_auto_reply("Re: votre site", {"Auto-Submitted": "auto-replied"}) is True
    assert rc.is_auto_reply("Re: votre site", {"Auto-Submitted": "no"}) is False


def test_auto_reply_by_precedence_header() -> None:
    """``Precedence: auto_reply`` marks an autoresponder."""
    assert rc.is_auto_reply("Re: votre site", {"Precedence": "auto_reply"}) is True


def test_human_reply_is_not_auto() -> None:
    """A plain human reply with ordinary headers is not flagged."""
    assert rc.is_auto_reply("Re: votre site", {"In-Reply-To": "<abc@mail.example.fr>"}) is False
