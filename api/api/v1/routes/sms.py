"""
SMS routes — sender config, relance candidates + send, provider callbacks.

The SMS channel re-contacts prospects who ignored the cold email, pushing them
back to their demo. Sender config is per user (Paramètres → SMS) ; the smsmode
account is a single platform account. The DLR and STOP callbacks are public
(called by smsmode) — like the demo-events and Storyblok webhooks.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from core.config import settings
from core.database import get_db
from enums.sms_status import SmsStatus
from models.sms_message import SmsMessage
from models.user import User
from schemas.sms import (
    SmsBulkSendResponse,
    SmsConfigResponse,
    SmsConfigUpdate,
    SmsRelanceCandidateResponse,
    SmsSendResponse,
)
from services.auth_service import get_current_user
from services.sms.phone_normalizer import to_e164_fr
from services.sms_config_service import sms_config_service
from services.sms_relance_service import sms_relance_service
from services.sms_service import sms_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sms", tags=["sms"])


@router.get("/config", response_model=SmsConfigResponse)
async def get_sms_config(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> SmsConfigResponse:
    """Return the current user's SMS sender configuration."""
    config = sms_config_service.get(db, current_user.id)
    return SmsConfigResponse(
        sender=config.sender if config else "",
        enabled=bool(config.enabled) if config else False,
        provider_ready=bool(settings.smsmode_api_key),
    )


@router.put("/config", response_model=SmsConfigResponse)
async def update_sms_config(
    payload: SmsConfigUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SmsConfigResponse:
    """Set the current user's SMS sender + enable flag."""
    try:
        config = sms_config_service.upsert(db, current_user.id, sender=payload.sender, enabled=payload.enabled)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return SmsConfigResponse(
        sender=config.sender, enabled=bool(config.enabled), provider_ready=bool(settings.smsmode_api_key)
    )


@router.get("/relance-candidates", response_model=list[SmsRelanceCandidateResponse])
async def list_relance_candidates(
    after_days: int = 30,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[SmsRelanceCandidateResponse]:
    """List prospects eligible for an SMS relance (unanswered email + mobile + live demo)."""
    candidates = sms_relance_service.find_candidates(db, current_user.id, after_days=after_days, limit=limit)
    return [
        SmsRelanceCandidateResponse(
            prospect_id=candidate.prospect.id,
            name=candidate.prospect.name,
            city=candidate.prospect.city,
            phone=candidate.prospect.phone,
            demo_url=candidate.demo_url,
            emailed_at=candidate.emailed_at,
        )
        for candidate in candidates
    ]


@router.post("/relance/{prospect_id}", response_model=SmsSendResponse)
async def send_relance(
    prospect_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SmsSendResponse:
    """Send a relance SMS to one eligible prospect."""
    candidates = sms_relance_service.find_candidates(db, current_user.id, limit=200)
    candidate = next((c for c in candidates if c.prospect.id == prospect_id), None)
    if candidate is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prospect non éligible à une relance SMS (déjà relancé, pas de mobile, ou pas de démo active).",
        )
    sent = await sms_relance_service.send_relance(db, current_user.id, candidate)
    return SmsSendResponse(sent=sent, reason=None if sent else "Envoi refusé par le provider")


@router.post("/relance", response_model=SmsBulkSendResponse)
async def send_relance_bulk(
    limit: int = 20,
    after_days: int = 30,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SmsBulkSendResponse:
    """Send relance SMS to the eligible prospects, up to *limit*."""
    candidates = sms_relance_service.find_candidates(db, current_user.id, after_days=after_days, limit=limit)
    sent = 0
    for candidate in candidates:
        if await sms_relance_service.send_relance(db, current_user.id, candidate):
            sent += 1
    return SmsBulkSendResponse(sent=sent, skipped=len(candidates) - sent)


@router.post("/callbacks/dlr", status_code=status.HTTP_200_OK)
async def receive_dlr_callback(request: Request, db: Session = Depends(get_db)) -> dict[str, str]:
    """Delivery-receipt callback from smsmode (public).

    Matches by ``messageId`` and updates the SMS status. Always answers 200 —
    even for an unknown id — so the provider does not retry in a loop.
    """
    try:
        payload = await request.json()
    except ValueError:
        return {"status": "ignored"}
    message_id = str(payload.get("messageId") or "").strip()
    if not message_id:
        return {"status": "ignored"}
    message = db.query(SmsMessage).filter(SmsMessage.provider_message_id == message_id).first()
    if message is None:
        logger.info("SMS DLR for unknown messageId %s", message_id)
        return {"status": "ok"}
    status_value = ""
    raw_status = payload.get("status")
    if isinstance(raw_status, dict):
        status_value = str(raw_status.get("value") or "").upper()
    if status_value in {"DELIVERED", "DELIVRED", "RECEIVED"}:
        message.status = SmsStatus.DELIVERED.value
    elif status_value in {"FAILED", "UNDELIVERED", "UNDELIVRED", "ERROR", "EXPIRED"}:
        message.status = SmsStatus.FAILED.value
        message.error = status_value
    db.commit()
    return {"status": "ok"}


@router.post("/callbacks/stop", status_code=status.HTTP_200_OK)
async def receive_stop_callback(request: Request, db: Session = Depends(get_db)) -> dict[str, str]:
    """STOP opt-out callback from smsmode (public).

    Adds the number to the sender's suppression list. The user is resolved from
    the last SMS sent to that number. Always answers 200.
    """
    try:
        payload = await request.json()
    except ValueError:
        return {"status": "ignored"}
    raw_number = str(payload.get("from") or payload.get("to") or payload.get("recipient") or "").strip()
    phone_e164 = to_e164_fr(raw_number) or (raw_number if raw_number.startswith("+") else None)
    if not phone_e164:
        return {"status": "ignored"}
    last = db.query(SmsMessage).filter(SmsMessage.to_e164 == phone_e164).order_by(SmsMessage.created_at.desc()).first()
    if last is not None:
        sms_service.suppress(db, last.user_id, phone_e164, reason="stop")
    return {"status": "ok"}
