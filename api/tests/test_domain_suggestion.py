"""Domain suggestion + availability: a logical, ideally-free .fr pre-fill for a prospect.

Covers the credential-free core: the business name drives the logical candidates (code logic
ranks first), Groq only enriches valid extras, and RDAP availability decides the pre-fill —
never claiming a domain is free without a 404 from the registry.
"""

import asyncio

import pytest

import services.domain.availability as availability_module
from services.domain import suggestion_service as suggestion_module
from services.domain.availability import is_fr_available
from services.domain.suggestion_service import DomainCandidate, domain_suggestion_service


class _FakeResponse:
    def __init__(self, status_code: int) -> None:
        self.status_code = status_code


class _FakeClient:
    """httpx.AsyncClient stand-in: yields a canned status, or raises a canned error."""

    def __init__(self, *, status: int | None, exc: Exception | None) -> None:
        self._status = status
        self._exc = exc

    async def __aenter__(self) -> "_FakeClient":
        return self

    async def __aexit__(self, *_exc: object) -> bool:
        return False

    async def get(self, _url: str) -> _FakeResponse:
        if self._exc is not None:
            raise self._exc
        assert self._status is not None
        return _FakeResponse(self._status)


def _patch_client(monkeypatch: pytest.MonkeyPatch, *, status: int | None = None, exc: Exception | None = None) -> None:
    monkeypatch.setattr(availability_module.httpx, "AsyncClient", lambda **_kw: _FakeClient(status=status, exc=exc))


class TestCandidateLabels:
    def test_builds_logical_variants_in_order(self) -> None:
        labels = domain_suggestion_service._candidate_labels("Chez Mimon", "Poitiers", "restaurant")
        assert labels == [
            "chezmimon",
            "chez-mimon",
            "chezmimon-poitiers",
            "chez-mimon-poitiers",
            "chezmimon-restaurant",
        ]

    def test_strips_accents_and_symbols(self) -> None:
        labels = domain_suggestion_service._candidate_labels("Café Créa+", None, None)
        assert labels == ["cafecrea", "cafe-crea"]

    def test_a_single_word_yields_one_label(self) -> None:
        # Compact and hyphenated collapse to the same string → deduped to one.
        assert domain_suggestion_service._candidate_labels("Tacosmaru", None, None) == ["tacosmaru"]


class TestAvailability:
    def test_404_means_available(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _patch_client(monkeypatch, status=404)
        assert asyncio.run(is_fr_available("tacos-maru.fr")) is True

    def test_200_means_taken(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _patch_client(monkeypatch, status=200)
        assert asyncio.run(is_fr_available("google.fr")) is False

    def test_unexpected_status_is_inconclusive(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _patch_client(monkeypatch, status=500)
        assert asyncio.run(is_fr_available("whatever.fr")) is None

    def test_network_error_is_inconclusive(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import httpx

        _patch_client(monkeypatch, exc=httpx.ConnectError("boom"))
        assert asyncio.run(is_fr_available("whatever.fr")) is None

    def test_non_fr_is_not_checked(self) -> None:
        assert asyncio.run(is_fr_available("example.com")) is None


class TestSuggest:
    @staticmethod
    def _run_suggest(monkeypatch: pytest.MonkeyPatch, *, availability: dict[str, bool | None], ai: list[str]):
        async def _fake_map(domains: list[str]) -> dict[str, bool | None]:
            return {d: availability.get(d) for d in domains}

        async def _fake_ai(*, business_name: str, city: str | None, category: str | None) -> list[str]:
            return ai

        monkeypatch.setattr(suggestion_module, "availability_map", _fake_map)
        monkeypatch.setattr(suggestion_module.llm_service, "suggest_domain_names", _fake_ai)
        return asyncio.run(domain_suggestion_service.suggest(name="Chez Mimon", city="Poitiers", category="restaurant"))

    def test_prefers_the_first_available_candidate(self, monkeypatch: pytest.MonkeyPatch) -> None:
        result = self._run_suggest(
            monkeypatch,
            availability={"chezmimon.fr": False, "chez-mimon.fr": True},
            ai=[],
        )
        assert result.suggested == "chez-mimon.fr"

    def test_falls_back_to_unknown_when_none_confirmed_free(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # Top logical taken, the rest could not be checked → pre-fill the first unknown.
        result = self._run_suggest(monkeypatch, availability={"chezmimon.fr": False}, ai=[])
        assert result.suggested == "chez-mimon.fr"
        assert result.candidates[0] == DomainCandidate(
            domain="chezmimon.fr", available=False, price_eur=pytest.approx(5.99)
        )

    def test_appends_only_valid_ai_labels(self, monkeypatch: pytest.MonkeyPatch) -> None:
        result = self._run_suggest(
            monkeypatch,
            availability={},
            ai=["mimonresto", "nom invalide !!"],
        )
        domains = [c.domain for c in result.candidates]
        assert "mimonresto.fr" in domains
        assert all("invalide" not in d for d in domains)
