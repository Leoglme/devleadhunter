"""The Storyblok session must read as valid only for a present AND unexpired token."""

from __future__ import annotations

import base64
import json
import time

from services.storyblok_session_service import StoryblokSessionSeed, _token_is_fresh


def _jwt(exp_offset_seconds: int) -> str:
    """A minimal unsigned JWT carrying only an ``exp`` claim ``exp_offset_seconds`` from now."""
    payload = base64.urlsafe_b64encode(json.dumps({"exp": int(time.time()) + exp_offset_seconds}).encode())
    return f"header.{payload.decode().rstrip('=')}.signature"


def test_fresh_token_is_valid() -> None:
    assert _token_is_fresh(_jwt(3600)) is True


def test_expired_token_is_not_valid() -> None:
    assert _token_is_fresh(_jwt(-10)) is False


def test_token_within_margin_is_not_valid() -> None:
    # Expires in 60s but the safety margin is 120s → treat as stale.
    assert _token_is_fresh(_jwt(60)) is False


def test_empty_token_is_not_valid() -> None:
    assert _token_is_fresh("") is False


def test_opaque_non_jwt_token_is_assumed_usable() -> None:
    # No decodable exp → presence is the only signal; the capture-time login-page
    # detection is the authoritative backstop.
    assert _token_is_fresh("opaque-non-jwt-token") is True


def test_seed_is_valid_mirrors_token_freshness() -> None:
    assert StoryblokSessionSeed(local_storage={"token": _jwt(3600)}).is_valid is True
    assert StoryblokSessionSeed(local_storage={"token": _jwt(-10)}).is_valid is False
    assert StoryblokSessionSeed(local_storage={}).is_valid is False
