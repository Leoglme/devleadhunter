"""Unit tests for conversation replies — signature append and inbox BCC."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

import services.conversation_service as conv
from services.conversation_service import ConversationService


@pytest.fixture
def db() -> MagicMock:
    session = MagicMock()
    session.get.side_effect = _get_side_effect
    session.execute.return_value.scalars.return_value.all.return_value = []
    return session


def _get_side_effect(_model: type, pk: int) -> SimpleNamespace | None:
    if pk == 10:
        return SimpleNamespace(
            id=10,
            user_id=1,
            email_log_id=5,
            prospect_id=99,
            from_email="prospect@example.fr",
            subject="Re: Site web",
            message_id="<msg@prospect>",
            handled_at=None,
        )
    if pk == 5:
        return SimpleNamespace(id=5, user_id=1, subject="Site web")
    return None


def test_send_reply_appends_signature_and_bcc(db: MagicMock, monkeypatch: pytest.MonkeyPatch) -> None:
    """Drawer answers include the default signature and a BCC inbox copy."""
    monkeypatch.setattr(conv, "render_default_signature_html", lambda _db, _uid: "<div>Sig</div>")
    monkeypatch.setattr(
        conv,
        "resolve_sending_identity",
        lambda _db, _uid: SimpleNamespace(
            from_email="leo@mail.dibodev.fr",
            from_name="Léo",
            resend_api_key="re_test",
        ),
    )
    monkeypatch.setattr(conv, "inbox_copy_address", lambda _identity: "leo@mail.dibodev.fr")

    captured: dict = {}

    async def fake_send(**kwargs: object) -> dict:
        captured.update(kwargs)
        return {"success": True}

    mock_sending = MagicMock()
    mock_sending.send_via_user_identity = AsyncMock(side_effect=fake_send)
    monkeypatch.setattr(conv, "EmailSendingService", lambda _db: mock_sending)

    service = ConversationService()
    result = asyncio.run(service.send_reply(db, user_id=1, reply_id=10, body_html="<p>Merci</p>"))

    assert result["success"] is True
    assert captured["body_html"] == "<p>Merci</p><div>Sig</div>"
    assert captured["bcc"] == ["leo@mail.dibodev.fr"]
    assert captured["is_conversation_reply"] is True
    assert captured["recipient_email"] == "prospect@example.fr"
