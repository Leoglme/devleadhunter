"""
Scraped Google reviews arrive as truncated previews: hard newlines inside, and a trailing expand-link
label ("… Plus" in FR, "More"/"Mehr"… elsewhere). Both read badly on the generated site, so the
generation step collapses whitespace and strips the read-more marker — without a re-enrichment.
"""

from services.templates.site_content import _clean_review_text


def test_strips_trailing_ellipsis_plus_marker() -> None:
    assert _clean_review_text("un food truck coréen comme celui-ci ici 🇰🇷 … Plus") == (
        "un food truck coréen comme celui-ci ici 🇰🇷"
    )


def test_strips_bare_plus_after_punctuation() -> None:
    assert _clean_review_text("nous venons chaque semaine! Plus") == "nous venons chaque semaine!"


def test_strips_english_more_marker() -> None:
    assert _clean_review_text("Great haircut and friendly staff More") == "Great haircut and friendly staff"


def test_collapses_inner_newlines() -> None:
    assert _clean_review_text("Délicieux !\n\nÀ recommander") == "Délicieux ! À recommander"


def test_keeps_a_legit_lowercase_plus() -> None:
    # Only the capitalised UI label is a marker; an ordinary "plus" must survive.
    assert _clean_review_text("le sourire en plus") == "le sourire en plus"


def test_empty_stays_empty() -> None:
    assert _clean_review_text("") == ""
    assert _clean_review_text("   \n  ") == ""
