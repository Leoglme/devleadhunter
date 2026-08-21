"""
Facebook photos are captured at scrape time as base64 ``data:`` URIs (their signed fbcdn URLs expire
within days), then moved to permanent R2 storage when the enrichment is persisted. Those data URIs must
survive generation — not dropped as "unrehostable" like raw fbcdn — and the Storyblok upload decodes
them instead of downloading.
"""

import base64

import httpx
import pytest

from scrappers.facebook_enrichment_scraper import FacebookEnrichmentScraper, _dedupe_photos, _upgrade_fb_photo_url
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


def test_upgrade_fb_photo_url_drops_ctp_for_full_size() -> None:
    """An fbcdn grid thumbnail (ctp=s206x206) upgrades to full size by dropping the ctp param, keeping
    the stp/cstp transforms and the oh signature intact (verified live: 206² → 1440²)."""
    thumb = (
        "https://scontent-cdg4-1.xx.fbcdn.net/v/t51.82787-15/723187010_x_n.webp"
        "?stp=dst-jpg_tt6&cstp=mx1440x1440&ctp=s206x206&_nc_cat=108"
        "&oh=00_AQHtJIgS0M7Jc3XNQqongV3yCnY23h7jYrejthTY8aWFnQ&oe=6A8BD291"
    )
    upgraded = _upgrade_fb_photo_url(thumb)

    assert "ctp=" not in upgraded  # display-size param dropped → full size
    assert "cstp=mx1440x1440" in upgraded  # max-size hint kept
    assert "stp=dst-jpg_tt6" in upgraded  # transform kept
    assert "oh=00_AQHtJIgS0M7Jc3XNQqongV3yCnY23h7jYrejthTY8aWFnQ" in upgraded  # signature untouched


def test_upgrade_fb_photo_url_leaves_non_fbcdn_untouched() -> None:
    """A Google (or any non-fbcdn) URL is returned unchanged."""
    google = "https://lh3.googleusercontent.com/gps-cs-s/ABC=s1600"
    assert _upgrade_fb_photo_url(google) == google


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
    """fbcdn photos become their captured data URI; an uncaptured fbcdn stays raw; a non-fbcdn URL is
    never even downloaded."""
    ok_url = "https://scontent.xx.fbcdn.net/a.jpg?oh=1"
    missed_url = "https://scontent.xx.fbcdn.net/b.jpg?oh=2"
    google_url = "https://lh3.googleusercontent.com/x=s1600"
    data_uri = "data:image/jpeg;base64," + base64.b64encode(b"fake").decode("ascii")

    async def fake_download(urls: list[str]) -> dict[str, str]:
        assert google_url not in urls  # only fbcdn targets are downloaded
        return {ok_url: data_uri}

    monkeypatch.setattr(FacebookEnrichmentScraper, "_download_as_data_uris", staticmethod(fake_download))

    scraper = FacebookEnrichmentScraper()
    result = await scraper._rehost_fb_photos([ok_url, missed_url, google_url])

    assert result[0] == data_uri
    assert result[1] == missed_url  # fbcdn not captured → left raw (generation drops + fallback)
    assert result[2] == google_url  # non-fbcdn → never touched


class _FakeResponse:
    """Minimal stand-in for an ``httpx.Response`` in the download test."""

    def __init__(self, status_code: int, content: bytes = b"", content_type: str = "image/jpeg") -> None:
        self.status_code = status_code
        self.content = content
        self.headers = {"content-type": content_type}


class _FakeClient:
    """Async-context httpx client that serves canned responses (or raises for an unknown URL)."""

    def __init__(self, responses: dict[str, _FakeResponse]) -> None:
        self._responses = responses

    async def __aenter__(self) -> "_FakeClient":
        return self

    async def __aexit__(self, *_exc: object) -> bool:
        return False

    async def get(self, url: str) -> _FakeResponse:
        response = self._responses.get(url)
        if response is None:
            raise httpx.ConnectError("no route")
        return response


@pytest.mark.asyncio
async def test_download_as_data_uris_captures_only_real_images(monkeypatch) -> None:
    """A 200 image becomes a data URI; a dead link, an oversized body and a non-image are all skipped."""
    ok_url = "https://scontent.xx.fbcdn.net/a.jpg?oh=1"
    dead_url = "https://scontent.xx.fbcdn.net/b.jpg?oh=2"
    huge_url = "https://scontent.xx.fbcdn.net/c.jpg?oh=3"
    html_url = "https://scontent.xx.fbcdn.net/d.jpg?oh=4"
    responses = {
        ok_url: _FakeResponse(200, b"real-image-bytes", "image/jpeg"),
        dead_url: _FakeResponse(404),
        huge_url: _FakeResponse(200, b"x" * (3_500_001), "image/jpeg"),
        html_url: _FakeResponse(200, b"<html>login</html>", "text/html"),
    }
    monkeypatch.setattr(
        "scrappers.facebook_enrichment_scraper.httpx.AsyncClient",
        lambda *args, **kwargs: _FakeClient(responses),
    )

    captured = await FacebookEnrichmentScraper._download_as_data_uris([ok_url, dead_url, huge_url, html_url])

    assert captured[ok_url] == "data:image/jpeg;base64," + base64.b64encode(b"real-image-bytes").decode("ascii")
    assert dead_url not in captured  # non-200 skipped
    assert huge_url not in captured  # over the size guard
    assert html_url not in captured  # not an image
