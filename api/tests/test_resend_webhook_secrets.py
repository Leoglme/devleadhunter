"""Unit tests for multi-tenant Resend webhook secret resolution."""

from types import SimpleNamespace

import pytest

import api.v1.routes.webhooks as wh


class _FakeExecute:
    def __init__(self, config: object | None) -> None:
        self._config = config

    def scalar_one_or_none(self) -> object | None:
        return self._config


class _FakeDB:
    def __init__(self, config: object | None) -> None:
        self._config = config

    def execute(self, *_args: object, **_kwargs: object) -> _FakeExecute:
        return _FakeExecute(self._config)


def test_webhook_secrets_prefers_user_secret_then_platform(monkeypatch: pytest.MonkeyPatch) -> None:
    """User secret is listed before the platform fallback."""
    email_log = SimpleNamespace(user_id=42)
    monkeypatch.setattr(wh, "_find_email_log_for_payload", lambda db, data: email_log)
    monkeypatch.setattr(wh.encryption_service, "decrypt", lambda value: "whsec_user")
    monkeypatch.setattr(wh.settings, "resend_webhook_secret", "whsec_platform")

    secrets = wh._webhook_secrets_for_payload(
        _FakeDB(SimpleNamespace(webhook_secret="enc_user")),
        {"email_id": "msg_1"},
    )

    assert secrets == ["whsec_user", "whsec_platform"]


def test_webhook_secrets_falls_back_to_platform_when_no_email_log(monkeypatch: pytest.MonkeyPatch) -> None:
    """Orphan events still verify against the platform secret."""
    monkeypatch.setattr(wh, "_find_email_log_for_payload", lambda db, data: None)
    monkeypatch.setattr(wh.settings, "resend_webhook_secret", "whsec_platform")

    secrets = wh._webhook_secrets_for_payload(None, {})

    assert secrets == ["whsec_platform"]


def test_verify_signature_accepts_any_candidate_secret() -> None:
    """A valid signature for any candidate secret passes verification."""
    import base64
    import hashlib
    import hmac

    body = b'{"type":"email.sent"}'
    svix_id = "msg_123"
    svix_timestamp = "1700000000"
    secret = "whsec_" + "a" * 32
    signed_content = f"{svix_id}.{svix_timestamp}.".encode() + body

    digest = hmac.new(base64.b64decode("a" * 32), signed_content, hashlib.sha256).digest()
    signature = f"v1,{base64.b64encode(digest).decode()}"

    assert wh._verify_signature(body, svix_id, svix_timestamp, signature, ["wrong", secret]) is True
    assert wh._verify_signature(body, svix_id, svix_timestamp, signature, ["wrong"]) is False
