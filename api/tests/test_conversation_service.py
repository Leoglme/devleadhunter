"""Unit tests for conversation helpers (subject building, HTML stripping, threading, intent)."""

from types import SimpleNamespace

from services import lead_scoring as ls
from services.conversation_service import build_reply_subject, html_to_text, thread_headers_for
from services.reply_intent_service import content_sha, normalize_verdict, replied_event_name


def test_reply_subject_adds_single_re_prefix() -> None:
    """Re: is added once, never stacked on an existing Re:/RE:/Fwd: chain."""
    assert build_reply_subject("Votre site") == "Re: Votre site"
    assert build_reply_subject("Re: Votre site") == "Re: Votre site"
    assert build_reply_subject("RE: fwd: Votre site") == "Re: Votre site"
    assert build_reply_subject(None) == "Re:"


def test_html_to_text_strips_tags_and_scripts() -> None:
    """Tags vanish, script/style content vanishes entirely, entities unescape."""
    raw = "<style>p{color:red}</style><p>Bonjour &amp; merci</p><script>alert(1)</script><div>À bientôt</div>"
    text = html_to_text(raw)
    assert "Bonjour & merci" in text
    assert "À bientôt" in text
    assert "alert" not in text
    assert "color" not in text
    assert "<" not in text


def test_html_to_text_preserves_line_structure() -> None:
    """Block-level closings become newlines so the reply stays readable."""
    text = html_to_text("<p>Ligne 1</p><p>Ligne 2</p>")
    assert text == "Ligne 1\nLigne 2"


def test_thread_headers_require_message_id() -> None:
    """No Message-ID on the reply → no threading headers (never empty strings)."""
    with_id = thread_headers_for(SimpleNamespace(message_id="<abc@x>"))
    assert with_id == {"In-Reply-To": "<abc@x>", "References": "<abc@x>"}
    assert thread_headers_for(SimpleNamespace(message_id=None)) is None


def test_reply_signal_scores_and_heats() -> None:
    """A single human reply outweighs opens and flips the lead to hot."""
    opened_only = ls.compute([], email={"sent": 1, "opened": 1})
    replied = ls.compute([], email={"sent": 1, "opened": 1, "replied": 1})
    assert replied["score"] > opened_only["score"]
    assert replied["temperature"] == "hot"
    assert opened_only["temperature"] != "hot"


def test_negative_reply_cools_the_lead() -> None:
    """A « pas intéressé » must never read as hot — it demotes the score instead."""
    negative = ls.compute([], email={"sent": 1, "opened": 1, "negative_replies": 1})
    assert negative["temperature"] == "cold"
    # A later positive reply cancels the demotion: the conversation restarted.
    recovered = ls.compute([], email={"sent": 1, "opened": 1, "negative_replies": 1, "replied": 1})
    assert recovered["temperature"] == "hot"


def test_normalize_verdict_tolerates_decoration() -> None:
    """Decorated model output still resolves to the closed intent set."""
    assert normalize_verdict("interested") == "interested"
    assert normalize_verdict(" NOT_INTERESTED. ") == "not_interested"
    assert normalize_verdict("not-interested") == "not_interested"
    assert normalize_verdict("Verdict : unsubscribe") == "unsubscribe"
    assert normalize_verdict("je ne sais pas") is None
    assert normalize_verdict(None) is None


def test_content_sha_is_whitespace_insensitive() -> None:
    """The dedup hash ignores whitespace and case so twin replies share one verdict."""
    assert content_sha("Pas  intéressé\nmerci") == content_sha("pas intéressé merci")
    assert content_sha("Oui") != content_sha("Non")


def test_replied_event_name_by_intent() -> None:
    """Notification event varies with the verdict; unknown verdicts stay neutral."""
    assert replied_event_name("interested") == "email_replied_interested"
    assert replied_event_name("not_interested") == "email_replied_negative"
    assert replied_event_name("unsubscribe") == "email_replied_negative"
    assert replied_event_name("question") == "email_replied"
    assert replied_event_name(None) == "email_replied"
