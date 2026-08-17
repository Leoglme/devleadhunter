"""
Tests for opening-hours cleaning: near a public holiday Google annotates the day ("samedi
(Assomption)") and adds an "hours may differ" disclaimer (sometimes as its own row), and two daily
ranges can be captured glued together. The cleaner strips the annotation and disclaimer, separates
the ranges, and keeps only real weekday rows.
"""

from services.templates import registry
from services.templates.site_content import _clean_opening_hours


def test_strips_holiday_annotation_disclaimer_and_splits_glued_ranges() -> None:
    rows = [
        {"day": "vendredi", "hours": "07:45–12:0014:00–18:00"},
        {"day": "samedi(Assomption)", "hours": "Fermé Les horaires peuvent être différents"},
        {"day": "dimanche", "hours": "Fermé"},
    ]
    assert _clean_opening_hours(rows) == [
        {"day": "vendredi", "hours": "07:45–12:00, 14:00–18:00"},
        {"day": "samedi", "hours": "Fermé"},
        {"day": "dimanche", "hours": "Fermé"},
    ]


def test_drops_rows_whose_day_is_not_a_real_weekday() -> None:
    rows = [
        {"day": "lundi", "hours": "08:00–19:00"},
        {"day": "Les horaires peuvent être différents", "hours": ""},
        {"day": "", "hours": "09:00–17:00"},
    ]
    assert [r["day"] for r in _clean_opening_hours(rows)] == ["lundi"]


def test_clean_hours_flow_through_the_generated_site() -> None:
    site = registry.build_site_content(
        template_id="barber",
        business_name="X",
        phone="0",
        email="x@y.fr",
        city="Tours",
        area="Tours",
        subtitle="",
        palette={"primary": "#000", "secondary": "#111", "accent": "#222"},
        enrichment={
            "opening_hours": [{"day": "samedi(Assomption)", "hours": "Fermé Les horaires peuvent être différents"}]
        },
    )
    assert site["openingHours"] == [{"day": "samedi", "hours": "Fermé"}]
