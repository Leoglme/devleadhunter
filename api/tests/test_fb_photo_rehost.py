"""
Facebook photos are captured in-browser at scrape time as base64 ``data:`` URIs (fbcdn URLs 403 on the
VPS). Those data URIs must survive generation — not dropped as "unrehostable" like raw fbcdn — and the
Storyblok upload decodes them instead of downloading.
"""

import base64

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
