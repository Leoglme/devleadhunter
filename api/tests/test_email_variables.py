"""Unit tests for `{lien_demo}` rendering.

The demo link MUST be a real ``<a>`` anchor: Resend's click tracking only rewrites
``href`` attributes, so a bare URL in the body was never wrapped and every click went
untracked. These tests lock the anchor rendering so the tracking gap cannot silently
reappear.
"""

from __future__ import annotations

from services.email_variables import EmailVariables


def test_build_demo_link_html_wraps_url_in_anchor() -> None:
    """A demo URL renders as an anchor carrying the exact href (so Resend can wrap it)."""
    html = EmailVariables.build_demo_link_html("https://demo.dibodev.fr/tacos-maru?v=A")
    assert html.startswith("<a ")
    assert 'href="https://demo.dibodev.fr/tacos-maru?v=A"' in html
    assert "voir votre site" in html
    assert html.endswith("</a>")


def test_build_demo_link_html_accepts_custom_text() -> None:
    """The visible call-to-action text can be overridden by the caller."""
    html = EmailVariables.build_demo_link_html("https://demo.dibodev.fr/x", text="le comparer")
    assert ">le comparer</a>" in html


def test_build_demo_link_html_empty_when_no_link() -> None:
    """No demo link renders empty (the queue guard skips demo-less prospects)."""
    assert EmailVariables.build_demo_link_html("") == ""
