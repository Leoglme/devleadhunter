"""Unit tests for inbox copy forwarding of captured prospect replies."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from services import reply_inbox_forward_service as rif
from services.sending_identity import SendingIdentity


@pytest.fixture
def identity() -> SendingIdentity:
    return SendingIdentity(
        provider="resend",
        from_email="leo@mail.dibodev.fr",
        from_name="Léo Guillaume",
        resend_api_key="re_test",
    )


def test_inbox_copy_address_uses_from_email(identity: SendingIdentity, monkeypatch: pytest.MonkeyPatch) -> None:
    """Without override, inbox copies go to the user's sending address."""
    monkeypatch.setattr(rif.settings, "reply_inbox_forward_to", "", raising=False)
    assert rif.inbox_copy_address(identity) == "leo@mail.dibodev.fr"


def test_inbox_copy_address_honours_global_override(identity: SendingIdentity, monkeypatch: pytest.MonkeyPatch) -> None:
    """REPLY_INBOX_FORWARD_TO overrides per-user from_email."""
    monkeypatch.setattr(rif.settings, "reply_inbox_forward_to", "Contact@Dibodev.Fr", raising=False)
    assert rif.inbox_copy_address(identity) == "contact@dibodev.fr"


def test_wrap_forward_html_includes_prospect_and_body() -> None:
    """The Gmail copy prefixes context and keeps the prospect's words."""
    reply = SimpleNamespace(
        from_email="prospect@example.fr",
        subject="Re: votre site",
        body_html=None,
        body_text="Merci mais non merci.",
    )
    html = rif._wrap_forward_html(reply)  # noqa: SLF001
    assert "prospect@example.fr" in html
    assert "Re: votre site" in html
    assert "Merci mais non merci." in html
    assert "DevLeadHunter" in html
