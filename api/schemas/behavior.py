"""Pydantic schemas for prospect behaviour (demo tracking)."""

from typing import Any

from pydantic import BaseModel, Field


class ProspectBehaviorResponse(BaseModel):
    """Lead score + behaviour timeline for a prospect."""

    temperature: str
    score: int
    signals: dict[str, Any] = Field(default_factory=dict)
    timeline: list[dict[str, Any]] = Field(default_factory=list)
    has_data: bool
    tracking_configured: bool


class ProspectTemperaturesRequest(BaseModel):
    """Prospect ids to score in bulk."""

    prospect_ids: list[int] = Field(default_factory=list)


class ProspectTemperature(BaseModel):
    """Temperature + score for one prospect."""

    prospect_id: int
    temperature: str
    score: int


class ProspectTemperaturesResponse(BaseModel):
    """Bulk lead temperatures, one entry per prospect that has any activity."""

    items: list[ProspectTemperature] = Field(default_factory=list)


class BehaviorSummaryResponse(BaseModel):
    """AI (or rule-based) behaviour summary + relance advice."""

    summary: str


class PersonalizedFollowupResponse(BaseModel):
    """A behaviour-personalised follow-up draft."""

    subject: str
    body_html: str
