"""The email tracking page must explain, in French, why a send failed — and whether it's our fault.

``EmailFailureExplainer`` classifies a failure from its status + raw provider reason; the unsubscribe
footer must survive a strip/re-add roundtrip so a resend to a corrected address gets a fresh link.
"""

from services.email_failure_explainer import EmailFailureExplainer
from services.unsubscribe_service import unsubscribe_service


def test_invalid_recipient_bounce_is_flagged_expected() -> None:
    explanation = EmailFailureExplainer.explain(
        "bounced", "The email couldn't be delivered because the recipient address doesn't exist"
    )
    assert explanation is not None
    assert explanation.category == "invalid_recipient"
    assert explanation.is_expected is True


def test_failed_status_without_reason_is_a_sending_error() -> None:
    explanation = EmailFailureExplainer.explain("failed", None)
    assert explanation is not None
    assert explanation.category == "sending_error"
    assert explanation.is_expected is False


def test_complained_status_is_a_spam_complaint() -> None:
    explanation = EmailFailureExplainer.explain("complained", None)
    assert explanation is not None
    assert explanation.category == "spam_complaint"


def test_delivered_email_has_no_failure_explanation() -> None:
    assert EmailFailureExplainer.explain("delivered", None) is None
    assert EmailFailureExplainer.explain("opened", None) is None


def test_unmatched_bounce_reason_is_kept_in_the_detail() -> None:
    explanation = EmailFailureExplainer.explain("bounced", "554 weird provider message")
    assert explanation is not None
    assert explanation.category == "undeliverable"
    assert "554 weird provider message" in explanation.reason


def test_unsubscribe_footer_survives_a_strip_and_readd_roundtrip() -> None:
    body = "<html><body><p>Hello</p></body></html>"
    with_footer = unsubscribe_service.add_unsubscribe_footer(body, "https://x/unsub?t=old")
    stripped = unsubscribe_service.strip_unsubscribe_footer(with_footer)
    assert "se désabonner" not in stripped.lower()
    assert stripped == body
    # Re-adding for a new recipient yields the new link, not the old one.
    readded = unsubscribe_service.add_unsubscribe_footer(stripped, "https://x/unsub?t=new")
    assert "t=new" in readded
    assert "t=old" not in readded
