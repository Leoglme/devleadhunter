"""
Facebook photos are captured in-browser at scrape time as base64 ``data:`` URIs (fbcdn URLs 403 on the
VPS). Those data URIs must survive generation — not dropped as "unrehostable" like raw fbcdn — and the
Storyblok upload decodes them instead of downloading.
"""

import base64

import pytest

from scrappers.facebook_enrichment_scraper import FacebookEnrichmentScraper
from services.storyblok_service import _decode_data_uri
from services.templates.site_content import _is_unrehostable_photo


class _FakeResponse:
    def __init__(self, status_code: int, content: bytes, content_type: str) -> None:
        self.status_code = status_code
        self.content = content
        self.headers = {"content-type": content_type}


class _FakeAsyncClient:
    def __init__(self, responses: dict[str, _FakeResponse]) -> None:
        self._responses = responses

    async def __aenter__(self) -> "_FakeAsyncClient":
        return self

    async def __aexit__(self, *_exc: object) -> bool:
        return False

    async def get(self, url: str, headers: dict | None = None) -> _FakeResponse:
        return self._responses[url]


class _FakeTab:
    async def evaluate(self, _js: str, **_kwargs: object) -> str:
        return "TestUA/1.0"


def test_decode_valid_data_uri() -> None:
    raw = b"\x89PNG\r\n\x1a\n some fake png bytes"
    uri = "data:image/png;base64," + base64.b64encode(raw).decode()
    content, content_type = _decode_data_uri(uri)
    assert content == raw
    assert content_type == "image/png"


def test_decode_defaults_mime_when_absent() -> None:
    uri = "data:;base64," + base64.b64encode(b"abc").decode()
    content, content_type = _decode_data_uri(uri)
    assert content == b"abc"
    assert content_type == "image/jpeg"


def test_decode_non_data_uri_returns_none() -> None:
    assert _decode_data_uri("https://example.com/x.jpg") == (None, "")
    assert _decode_data_uri("data:image/png,not-base64-no-marker") == (None, "")


def test_raw_fbcdn_is_dropped_but_captured_data_uri_passes() -> None:
    assert _is_unrehostable_photo("https://scontent-cdg4-3.xx.fbcdn.net/v/x.jpg?oh=1") is True
    assert _is_unrehostable_photo("data:image/jpeg;base64,AAAABBBB") is False


@pytest.mark.asyncio
async def test_rehost_downloads_valid_fbcdn_and_leaves_the_rest(monkeypatch) -> None:
    """A 200 image download becomes a data URI; a 403 stays a raw URL; non-fbcdn photos are untouched."""
    png = b"\x89PNG\r\n fake image bytes"
    ok_url = "https://scontent.xx.fbcdn.net/a.jpg?oh=1"
    forbidden_url = "https://scontent.xx.fbcdn.net/b.jpg?oh=2"
    google_url = "https://lh3.googleusercontent.com/x=s1600"
    responses = {
        ok_url: _FakeResponse(200, png, "image/jpeg"),
        forbidden_url: _FakeResponse(403, b"", "text/html"),
    }
    monkeypatch.setattr(
        "scrappers.facebook_enrichment_scraper.httpx.AsyncClient",
        lambda **_kwargs: _FakeAsyncClient(responses),
    )

    scraper = FacebookEnrichmentScraper()
    result = await scraper._rehost_fb_photos(_FakeTab(), [ok_url, forbidden_url, google_url])

    assert result[0] == "data:image/jpeg;base64," + base64.b64encode(png).decode("ascii")
    assert result[1] == forbidden_url  # 403 → kept as-is, generation will drop + fallback
    assert result[2] == google_url  # non-fbcdn → never touched
