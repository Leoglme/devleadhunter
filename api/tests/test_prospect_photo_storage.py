"""
A prospect's captured Facebook photos (base64 ``data:`` URIs) are rehosted to permanent R2 storage when
the enrichment is persisted, so the record holds durable URLs instead of fbcdn links that expire in days.
Non-data-URI values (Google photos, already-R2 URLs) pass through untouched, and everything is
best-effort so a storage hiccup never breaks enrichment.
"""

import base64

import httpx
import pytest

from api.v1.routes.admin_storage import _classify, _prospect_id_from_key
from services.prospect_photo_storage_service import ProspectPhotoStorageService, prospect_photo_storage
from services.r2_storage_service import r2_storage


def _jpeg_data_uri(content: bytes) -> str:
    return "data:image/jpeg;base64," + base64.b64encode(content).decode("ascii")


class _FakeResponse:
    """Minimal stand-in for an ``httpx.Response`` in the download tests."""

    def __init__(self, status_code: int, content: bytes = b"", content_type: str = "image/jpeg") -> None:
        self.status_code = status_code
        self.content = content
        self.headers = {"content-type": content_type}


class _FakeClient:
    """Async-context httpx client serving canned responses (or raising for an unknown URL)."""

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


def test_decode_valid_jpeg_data_uri() -> None:
    raw = b"jpeg-bytes"
    decoded = ProspectPhotoStorageService._decode_data_uri(_jpeg_data_uri(raw))
    assert decoded is not None
    data, content_type, extension = decoded
    assert data == raw
    assert content_type == "image/jpeg"
    assert extension == ".jpg"


def test_decode_png_extension() -> None:
    decoded = ProspectPhotoStorageService._decode_data_uri("data:image/png;base64," + base64.b64encode(b"x").decode())
    assert decoded is not None
    assert decoded[2] == ".png"


def test_decode_rejects_non_data_uri() -> None:
    assert ProspectPhotoStorageService._decode_data_uri("https://x/y.jpg") is None
    assert ProspectPhotoStorageService._decode_data_uri("data:text/plain;base64,AAAA") is None


def test_decode_rejects_oversized(monkeypatch) -> None:
    monkeypatch.setattr("services.prospect_photo_storage_service._MAX_PHOTO_BYTES", 4)
    uri = "data:image/jpeg;base64," + base64.b64encode(b"toolong").decode()
    assert ProspectPhotoStorageService._decode_data_uri(uri) is None


@pytest.mark.asyncio
async def test_rehost_one_passes_through_non_data_uri(monkeypatch) -> None:
    monkeypatch.setattr(r2_storage, "is_configured", lambda: True)
    url = "https://lh3.googleusercontent.com/x=s1600"
    assert await prospect_photo_storage.rehost_one(29, url) == url


@pytest.mark.asyncio
async def test_rehost_one_passes_through_when_r2_unconfigured(monkeypatch) -> None:
    monkeypatch.setattr(r2_storage, "is_configured", lambda: False)
    uri = _jpeg_data_uri(b"bytes")
    assert await prospect_photo_storage.rehost_one(29, uri) == uri


@pytest.mark.asyncio
async def test_rehost_one_uploads_data_uri(monkeypatch) -> None:
    uploaded: dict[str, object] = {}
    monkeypatch.setattr(r2_storage, "is_configured", lambda: True)
    monkeypatch.setattr(
        r2_storage, "prospect_photo_key", lambda pid, digest, ext: f"images/prospects/{pid}/{digest}{ext}"
    )

    async def fake_upload(key: str, data: bytes, content_type: str) -> str:
        uploaded.update({"key": key, "data": data, "content_type": content_type})
        return f"https://cdn.example/{key}"

    monkeypatch.setattr(r2_storage, "upload_bytes_async", fake_upload)

    result = await prospect_photo_storage.rehost_one(29, _jpeg_data_uri(b"abc"))

    assert result == f"https://cdn.example/{uploaded['key']}"
    assert str(uploaded["key"]).startswith("images/prospects/29/")
    assert str(uploaded["key"]).endswith(".jpg")
    assert uploaded["data"] == b"abc"
    assert uploaded["content_type"] == "image/jpeg"


@pytest.mark.asyncio
async def test_rehost_photos_preserves_order_and_mixes(monkeypatch) -> None:
    monkeypatch.setattr(r2_storage, "is_configured", lambda: True)
    monkeypatch.setattr(r2_storage, "prospect_photo_key", lambda pid, digest, ext: f"k/{pid}/{digest}{ext}")

    async def fake_upload(key: str, data: bytes, content_type: str) -> str:
        return f"https://cdn/{key}"

    monkeypatch.setattr(r2_storage, "upload_bytes_async", fake_upload)

    google = "https://lh3.googleusercontent.com/x"
    result = await prospect_photo_storage.rehost_photos(29, [_jpeg_data_uri(b"one"), google, _jpeg_data_uri(b"two")])

    assert result[0].startswith("https://cdn/k/29/")
    assert result[1] == google
    assert result[2].startswith("https://cdn/k/29/")
    assert result[0] != result[2]  # different bytes → different content-hash keys


@pytest.mark.asyncio
async def test_rehost_one_survives_upload_failure(monkeypatch) -> None:
    monkeypatch.setattr(r2_storage, "is_configured", lambda: True)
    monkeypatch.setattr(r2_storage, "prospect_photo_key", lambda pid, digest, ext: "k")

    async def boom(key: str, data: bytes, content_type: str) -> str:
        raise RuntimeError("R2 down")

    monkeypatch.setattr(r2_storage, "upload_bytes_async", boom)
    uri = _jpeg_data_uri(b"z")
    assert await prospect_photo_storage.rehost_one(29, uri) == uri  # best-effort → original value kept


@pytest.mark.asyncio
async def test_delete_for_prospect_deletes_listed_keys(monkeypatch) -> None:
    monkeypatch.setattr(r2_storage, "is_configured", lambda: True)
    monkeypatch.setattr(r2_storage, "prospect_photos_prefix", lambda pid: f"images/prospects/{pid}/")
    monkeypatch.setattr(
        r2_storage, "list_objects", lambda prefix: [{"key": prefix + "a.jpg"}, {"key": prefix + "b.jpg"}]
    )
    deleted: dict[str, object] = {}
    monkeypatch.setattr(r2_storage, "delete_many", lambda keys: deleted.update({"keys": keys}))

    count = await prospect_photo_storage.delete_for_prospect(29)

    assert count == 2
    assert deleted["keys"] == ["images/prospects/29/a.jpg", "images/prospects/29/b.jpg"]


@pytest.mark.asyncio
async def test_rehost_one_downloads_and_stores_fbcdn_url(monkeypatch) -> None:
    fbcdn = "https://scontent-cdg4-1.xx.fbcdn.net/v/t39.30808-6/123_abc_n.jpg?oh=1&oe=2"
    monkeypatch.setattr(r2_storage, "is_configured", lambda: True)
    monkeypatch.setattr(
        r2_storage, "prospect_photo_key", lambda pid, digest, ext: f"images/prospects/{pid}/{digest}{ext}"
    )
    monkeypatch.setattr(
        "services.prospect_photo_storage_service.httpx.AsyncClient",
        lambda *args, **kwargs: _FakeClient({fbcdn: _FakeResponse(200, b"real-tacos-bytes", "image/jpeg")}),
    )

    async def fake_upload(key: str, data: bytes, content_type: str) -> str:
        return f"https://cdn/{key}"

    monkeypatch.setattr(r2_storage, "upload_bytes_async", fake_upload)

    result = await prospect_photo_storage.rehost_one(29, fbcdn)

    assert result.startswith("https://cdn/images/prospects/29/")
    assert result.endswith(".jpg")


@pytest.mark.asyncio
async def test_rehost_one_never_downloads_a_google_url(monkeypatch) -> None:
    google = "https://lh3.googleusercontent.com/gps-cs-s/ABC=s1600"
    monkeypatch.setattr(r2_storage, "is_configured", lambda: True)

    def boom(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("a non-fbcdn URL must never be downloaded")

    monkeypatch.setattr("services.prospect_photo_storage_service.httpx.AsyncClient", boom)
    assert await prospect_photo_storage.rehost_one(29, google) == google


@pytest.mark.asyncio
async def test_rehost_one_keeps_fbcdn_when_download_fails(monkeypatch) -> None:
    dead = "https://scontent.xx.fbcdn.net/v/dead.jpg?oh=1"
    monkeypatch.setattr(r2_storage, "is_configured", lambda: True)
    monkeypatch.setattr(
        "services.prospect_photo_storage_service.httpx.AsyncClient",
        lambda *args, **kwargs: _FakeClient({dead: _FakeResponse(403)}),
    )
    assert await prospect_photo_storage.rehost_one(29, dead) == dead


def test_classify_recognises_prospect_photos() -> None:
    assert _classify("images/prospects/29/abc123.jpg") == "prospect_photo"
    assert _classify("images/websites/some-slug.jpg") == "website_thumbnail"
    assert _classify("videos/websites/some-slug.mp4") == "website_video"


def test_prospect_id_from_key() -> None:
    assert _prospect_id_from_key("images/prospects/29/abc.jpg") == 29
    assert _prospect_id_from_key("images/prospects/not-a-number/abc.jpg") is None
    assert _prospect_id_from_key("images/websites/slug.jpg") is None
