"""
Facebook photos are captured in-browser at scrape time as base64 ``data:`` URIs (fbcdn URLs 403 on the
VPS). Those data URIs must survive generation — not dropped as "unrehostable" like raw fbcdn — and the
Storyblok upload decodes them instead of downloading.
"""

import base64
import json

import pytest

from scrappers.facebook_enrichment_scraper import FacebookEnrichmentScraper
from services.storyblok_service import _decode_data_uri
from services.templates.site_content import _is_unrehostable_photo


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
    """The in-browser capture maps fbcdn URLs to data URIs; an uncaptured fbcdn stays raw; non-fbcdn is untouched."""
    ok_url = "https://scontent.xx.fbcdn.net/a.jpg?oh=1"
    missed_url = "https://scontent.xx.fbcdn.net/b.jpg?oh=2"
    google_url = "https://lh3.googleusercontent.com/x=s1600"
    data_uri = "data:image/jpeg;base64," + base64.b64encode(b"fake").decode("ascii")

    calls = {"n": 0}

    async def fake_evaluate(_tab: object, _js: str, **_kwargs: object) -> object:
        calls["n"] += 1
        if calls["n"] == 1:
            return True  # the fire-and-forget start script
        return json.dumps({ok_url: data_uri})  # a poll returns the captured map

    async def instant_sleep(_seconds: float) -> None:
        return None

    monkeypatch.setattr("scrappers.facebook_enrichment_scraper.NodriverDom.evaluate", fake_evaluate)
    monkeypatch.setattr("scrappers.facebook_enrichment_scraper.asyncio.sleep", instant_sleep)

    scraper = FacebookEnrichmentScraper()
    result = await scraper._rehost_fb_photos(object(), [ok_url, missed_url, google_url])

    assert result[0] == data_uri
    assert result[1] == missed_url  # fbcdn not captured → left raw (generation drops + fallback)
    assert result[2] == google_url  # non-fbcdn → never touched
