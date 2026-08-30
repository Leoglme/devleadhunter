"""SMS API schemas — config, relance candidates, provider callbacks."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class SmsConfigResponse(BaseModel):
    """The user's SMS sender configuration."""

    sender: str = ""
    enabled: bool = False
    provider_ready: bool = Field(default=False, description="Whether the platform smsmode key is configured")


class SmsConfigUpdate(BaseModel):
    """Payload to set the SMS sender configuration."""

    sender: str = Field(default="", max_length=11)
    enabled: bool = False


class SmsRelanceCandidateResponse(BaseModel):
    """A prospect eligible for an SMS relance."""

    prospect_id: int
    name: str
    city: str | None = None
    phone: str | None = None
    demo_url: str
    emailed_at: datetime


class SmsSendResponse(BaseModel):
    """Outcome of a relance send."""

    sent: bool
    reason: str | None = None


class SmsBulkSendResponse(BaseModel):
    """Outcome of a bulk relance send."""

    sent: int
    skipped: int


class SmsDlrCallback(BaseModel):
    """smsmode delivery-receipt callback (subset we use)."""

    messageId: str | None = None
    refClient: str | None = None

    class Status(BaseModel):
        """Nested status object."""

        value: str | None = None

    status: Status | None = None
