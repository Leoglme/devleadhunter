"""
Facebook photos are captured in-browser at scrape time as base64 ``data:`` URIs (fbcdn URLs 403 on the
VPS). Those data URIs must survive generation — not dropped as "unrehostable" like raw fbcdn — and the
Storyblok upload decodes them instead of downloading.
"""

import base64
import json

import pytest

from scrappers.facebook_enrichment_scraper import FacebookEnrichmentScraper, _dedupe_photos
from services.storyblok_service import _decode_data_uri
from services.templates.site_content import _is_unrehostable_photo


def test_dedupe_keeps_data_uris_alongside_fbcdn() -> None:
    """The build-time dedup must not drop rehosted ``data:`` photos: they carry no ``scontent`` host,
    so the old asset filter silently stripped every captured photo (FB-only prospect rendered empty).
    """
    data_uri = "data:image/jpeg;base64," + base64.b64encode(b"fake-bytes").decode("ascii")
    fbcdn = "https://scontent-cdg4-2.xx.fbcdn.net/v/t39.30808-6/123456_abc_n.jpg?oh=1"
    icon = "https://static.xx.fbcdn.net/rsrc.php/y.png"

    result = _dedupe_photos([data_uri, fbcdn, icon])

    assert data_uri in result  # rehosted photo survives
    assert any("fbcdn.net/v/t39" in p for p in result)  # real fbcdn survives
    assert icon not in result  # static asset still filtered


def test_dedupe_drops_duplicate_data_uris() -> None:
    """Identical captured photos (same bytes) collapse to a single entry."""
    data_uri = "data:image/jpeg;base64," + base64.b64encode(b"same").decode("ascii")
    assert _dedupe_photos([data_uri, data_uri]) == [data_uri]


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
async def test_rehost_maps_captured_data_uris_and_leaves_the_rest(monkeypatch) -> None:
    """The single awaited evaluate returns a JSON string: fbcdn→data URI, uncaptured fbcdn stays raw, non-fbcdn untouched."""
    ok_url = "https://scontent.xx.fbcdn.net/a.jpg?oh=1"
    missed_url = "https://scontent.xx.fbcdn.net/b.jpg?oh=2"
    google_url = "https://lh3.googleusercontent.com/x=s1600"
    data_uri = "data:image/jpeg;base64," + base64.b64encode(b"fake").decode("ascii")

    async def fake_evaluate(_tab: object, _js: str, **_kwargs: object) -> str:
        return json.dumps({ok_url: data_uri})

    monkeypatch.setattr("scrappers.facebook_enrichment_scraper.NodriverDom.evaluate", fake_evaluate)

    scraper = FacebookEnrichmentScraper()
    result = await scraper._rehost_fb_photos(object(), [ok_url, missed_url, google_url])

    assert result[0] == data_uri
    assert result[1] == missed_url  # fbcdn not captured → left raw (generation drops + fallback)
    assert result[2] == google_url  # non-fbcdn → never touched
