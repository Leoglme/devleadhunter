"""The Google-Maps extraction retry loop must stop early once the parse plateaus — a rating is
parsed but the hour count stays frozen below the 5-row "ready" threshold. Otherwise a food-truck
(open a few days) or a partial-panel load burns all 4 attempts (~20s), the reappeared grid delay.
"""

import asyncio

import pytest

from scrappers.enrichment_scraper import EnrichmentData, EnrichmentScraper


@pytest.mark.asyncio
async def test_extract_retries_plateau_stops_before_exhausting_attempts(monkeypatch) -> None:
    scraper = EnrichmentScraper()
    prepare_calls = {"n": 0}

    async def fake_prepare(_tab: object) -> None:
        prepare_calls["n"] += 1

    async def fake_extract_raw(_tab: object) -> dict:
        return {}

    def fake_build(_raw: dict, *, business_name: str, city: str | None) -> EnrichmentData:
        # Flaky panel: a rating parses, but only one hour row (never reaches the 5-row ready threshold).
        return EnrichmentData(rating=5.0, opening_hours=[{"day": "Ven", "hours": "18h-23h"}])

    async def fake_sleep(_s: float) -> None:
        return None

    monkeypatch.setattr(scraper, "_prepare_panel_for_extraction", fake_prepare)
    monkeypatch.setattr(scraper, "_extract_raw", fake_extract_raw)
    monkeypatch.setattr(scraper, "_build_from_raw", fake_build)
    monkeypatch.setattr(asyncio, "sleep", fake_sleep)

    data = await scraper._extract_with_retries(object(), business_name="Tasty", city="Poitiers")

    # Attempt 1 sets the baseline; attempt 2 sees the frozen count + a rating → plateau exit. Never 4.
    assert prepare_calls["n"] == 2
    assert data.rating == 5.0


@pytest.mark.asyncio
async def test_extract_retries_returns_immediately_when_hours_complete(monkeypatch) -> None:
    """A full weekly-hours parse is ``ready`` on the first attempt — no plateau needed."""
    scraper = EnrichmentScraper()
    prepare_calls = {"n": 0}

    async def fake_prepare(_tab: object) -> None:
        prepare_calls["n"] += 1

    async def fake_extract_raw(_tab: object) -> dict:
        return {}

    def fake_build(_raw: dict, *, business_name: str, city: str | None) -> EnrichmentData:
        return EnrichmentData(rating=5.0, opening_hours=[{"day": d, "hours": "9h-18h"} for d in "LMMJVSD"])

    monkeypatch.setattr(scraper, "_prepare_panel_for_extraction", fake_prepare)
    monkeypatch.setattr(scraper, "_extract_raw", fake_extract_raw)
    monkeypatch.setattr(scraper, "_build_from_raw", fake_build)

    await scraper._extract_with_retries(object(), business_name="Garage", city="Niort")

    assert prepare_calls["n"] == 1
