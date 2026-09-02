"""Unit tests for push notification on conversation reply send."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

import services.email_sending_service as sending
from enums.sending_provider import SendingProvider
from models.campaign_follow_up import CampaignFollowUp  # noqa: F401
from models.payment_account import PaymentAccount  # noqa: F401
from services.email_sending_service import EmailSendingService


class _FakeDB:
    def __init__(self) -> None:
        self.added: list[object] = []

    def add(self, row: object) -> None:
        self.added.append(row)

    def commit(self) -> None:
        return None

    def refresh(self, row: object) -> None:
        row.id = 42


class _RecordingResend:
    async def send_email(self, **kwargs: object) -> dict:
        return {"message_id": "msg_1", "provider": "resend"}


def test_conversation_reply_triggers_confirmation_notification(monkeypatch: pytest.MonkeyPatch) -> None:
    """A drawer answer notifies the operator without emitting a funnel email_sent event."""
    monkeypatch.setattr(
        sending,
        "resolve_sending_identity",
        lambda _db, _user_id: SimpleNamespace(
            provider=SendingProvider.RESEND.value,
            gmail_account=None,
            from_email="leo@mail.dibodev.fr",
            from_name="Léo",
            resend_api_key="re_test",
        ),
    )
    monkeypatch.setattr(sending.unsubscribe_service, "is_unsubscribed", lambda _db, _email: False)

    notified: list[str] = []

    async def record_notify(_db, **kwargs: object) -> None:
        notified.append(str(kwargs.get("event_name")))

    funnel_called = {"value": False}

    async def record_funnel(**_kwargs: object) -> None:
        funnel_called["value"] = True

    monkeypatch.setattr(sending.notification_service, "notify_email_event", record_notify)

    service = EmailSendingService(_FakeDB())
    service.resend_service = _RecordingResend()
    monkeypatch.setattr(service, "_mark_prospect_contacted", lambda _prospect_id: None)
    monkeypatch.setattr(service, "_capture_email_sent", record_funnel)

    result = asyncio.run(
        service.send_via_user_identity(
            user_id=1,
            recipient_email="prospect@example.fr",
            subject="Re: Site",
            body_html="<p>Ok</p>",
            prospect_id="99",
            is_conversation_reply=True,
            bcc=["leo@mail.dibodev.fr"],
        )
    )

    assert result["success"] is True
    assert notified == ["email_conversation_reply_sent"]
    assert funnel_called["value"] is False
