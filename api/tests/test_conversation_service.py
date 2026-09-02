"""Unit tests for conversation helpers (subject building, HTML stripping, threading, intent)."""

from types import SimpleNamespace

from services import lead_scoring as ls
from services.conversation_service import (
    build_reply_subject,
    html_to_text,
    strip_quoted_reply,
    thread_headers_for,
)
from services.reply_intent_service import content_sha, normalize_verdict, replied_event_name


def test_strip_quoted_reply_removes_gmail_history() -> None:
    """Gmail « Le … a écrit : » and the quoted lines (+ tracking URL) are dropped."""
    raw = (
        "Bonjour,\n\n"
        "Merci pour votre proposition mais pour l'instant nous n'avons pas besoin de site.\n\n"
        "Bien cordialement\n\n"
        "Le lun. 31 août 2026 à 16:01, Léo Guillaume <leo@mail.dibodev.fr> a écrit :\n"
        "> Bonjour,\n"
        "> Le site est toujours en ligne : demo.dibodev.fr/x\n"
        "> <https://track.mail.dibodev.fr/CL0/https%3A%2F%2Fdemo...>\n"
    )
    trimmed = strip_quoted_reply(raw)
    assert "Merci pour votre proposition" in trimmed
    assert "Bien cordialement" in trimmed
    assert "a écrit" not in trimmed
    assert "track.mail.dibodev.fr" not in trimmed
    assert ">" not in trimmed


def test_strip_quoted_reply_handles_english_and_outlook() -> None:
    """English « … wrote: » and the Outlook underscore separator both cut the history."""
    english = "Thanks, not interested.\n\nOn Mon, 31 Aug 2026, Léo wrote:\n> original\n"
    assert strip_quoted_reply(english).strip() == "Thanks, not interested."
    outlook = "Pas intéressé.\n\n________________________________\nDe : Léo\n"
    assert strip_quoted_reply(outlook).strip() == "Pas intéressé."


def test_strip_quoted_reply_keeps_body_without_quote() -> None:
    """A reply with no quoted history is returned unchanged."""
    assert strip_quoted_reply("Ok, ça m'intéresse, rappelez-moi.") == "Ok, ça m'intéresse, rappelez-moi."


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
