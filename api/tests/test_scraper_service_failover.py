"""Unit tests for the scraper-service source ordering (failover chain + isolated sources)."""

import asyncio
from collections.abc import Callable

from enums.source import Source
from models.prospect import ProspectCreate
from scrappers.base_scraper import BaseScraper
from services.scrape_progress import ScrapeProgressReporter
from services.scraper_service import ScraperService


class _StubScraper(BaseScraper):
    """Registration-only scraper — ordering tests never call :meth:`scrape`."""

    async def scrape(
        self,
        category: str,
        city: str,
        max_results: int = 50,
        *,
        only_without_website: bool = True,
        progress: ScrapeProgressReporter | None = None,
        should_stop: Callable[[], bool] | None = None,
    ) -> list[ProspectCreate]:
        return []


def _service_with(*sources: Source) -> ScraperService:
    """Build a service with one stub scraper registered per source."""
    service = ScraperService()
    for source in sources:
        asyncio.run(service.add_scraper(_StubScraper(source)))
    return service


_ALL_SOURCES = (Source.GOOGLE, Source.PAGESJAUNES, Source.BRIGHTDATA, Source.OSM, Source.FACEBOOK)


class TestOrderedCandidates:
    def test_generic_search_never_includes_facebook(self) -> None:
        service = _service_with(*_ALL_SOURCES)
        candidates, is_specific = service._ordered_candidates(None)
        assert [c.source.value for c in candidates] == ["google", "pagesjaunes", "brightdata", "osm"]
        assert is_specific is False

    def test_all_filter_never_includes_facebook(self) -> None:
        service = _service_with(*_ALL_SOURCES)
        candidates, _ = service._ordered_candidates("all")
        assert "facebook" not in [c.source.value for c in candidates]

    def test_explicit_facebook_runs_alone(self) -> None:
        service = _service_with(*_ALL_SOURCES)
        candidates, is_specific = service._ordered_candidates("facebook")
        assert [c.source.value for c in candidates] == ["facebook"]
        assert is_specific is True

    def test_explicit_generic_source_still_cascades(self) -> None:
        service = _service_with(*_ALL_SOURCES)
        candidates, is_specific = service._ordered_candidates("pagesjaunes")
        assert [c.source.value for c in candidates] == ["pagesjaunes", "google", "brightdata", "osm"]
        assert is_specific is True
