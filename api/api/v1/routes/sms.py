"""
SMS routes — sender config, relance candidates + send, provider callbacks.

The SMS channel re-contacts prospects who ignored the cold email, pushing them
back to their demo. Sender config is per user (Paramètres → SMS) ; the smsmode
account is a single platform account. The DLR and STOP callbacks are public
(called by smsmode) — like the demo-events and Storyblok webhooks.
"""

from __future__ import annotations

import logging
from datetime import datetime

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
    SmsManualSendRequest,
    SmsMessageResponse,
    SmsMessagesResponse,
    SmsRelanceCandidateResponse,
    SmsSendResponse,
    SmsStatsResponse,
)
from services.auth_service import get_current_user
from services.notification_service import notification_service
from services.sms.dlr import (
    classify_dlr,
    dlr_message_id,
    dlr_ref_client,
    dlr_status_detail,
    dlr_status_value,
)
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
        provider_ready=bool(settings.smsmode_api_key),
    )


@router.put("/config", response_model=SmsConfigResponse)
async def update_sms_config(
    payload: SmsConfigUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SmsConfigResponse:
    """Set the current user's SMS sender (a configured sender turns the channel on)."""
    try:
        config = sms_config_service.upsert(db, current_user.id, sender=payload.sender)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return SmsConfigResponse(sender=config.sender, provider_ready=bool(settings.smsmode_api_key))


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
    refusal = sms_service.legal_window_refusal()
    if refusal:
        return SmsSendResponse(sent=False, reason=refusal)
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
    if sms_service.legal_window_refusal() is not None:
        return SmsBulkSendResponse(sent=0, skipped=len(candidates))
    sent = 0
    for candidate in candidates:
        if await sms_relance_service.send_relance(db, current_user.id, candidate):
            sent += 1
    return SmsBulkSendResponse(sent=sent, skipped=len(candidates) - sent)


@router.get("/messages", response_model=SmsMessagesResponse)
async def list_messages(
    limit: int = 500,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SmsMessagesResponse:
    """Return the current user's sent SMS (newest first) — the « Suivi des SMS » history."""
    rows = sms_service.list_messages(db, current_user.id, limit=limit)
    messages = [
        SmsMessageResponse(
            id=message.id,
            prospect_id=message.prospect_id,
            recipient_name=prospect_name or message.recipient_name,
            to_e164=message.to_e164,
            sender=message.sender,
            body=message.body,
            status=message.status,
            status_detail=message.status_detail,
            segments=message.segments,
            price_cents=message.price_cents,
            error=message.error,
            created_at=message.created_at,
            delivered_at=message.delivered_at,
        )
        for message, prospect_name in rows
    ]
    return SmsMessagesResponse(total=len(messages), messages=messages)


@router.get("/stats", response_model=SmsStatsResponse)
async def get_stats(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> SmsStatsResponse:
    """Return aggregate counters of the current user's SMS channel."""
    return SmsStatsResponse(**sms_service.stats(db, current_user.id))


@router.post("/send", response_model=SmsSendResponse)
async def send_manual_sms(
    payload: SmsManualSendRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SmsSendResponse:
    """Send one free-text SMS to a number (manual composer / self-test)."""
    config = sms_config_service.get(db, current_user.id)
    if config is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Configurez d'abord votre expéditeur dans Paramètres → Relance SMS.",
        )
    outcome = await sms_service.send_manual(
        db,
        user_id=current_user.id,
        config=config,
        to_raw=payload.to,
        text=payload.text,
        prospect_id=payload.prospect_id,
        recipient_name=payload.recipient_name,
    )
    return SmsSendResponse(sent=outcome.sent, reason=outcome.reason)


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
    if not isinstance(payload, dict):
        return {"status": "ignored"}
    message = _match_dlr_message(db, payload)
    if message is None:
        logger.info("SMS DLR unmatched: %s", str(payload)[:300])
        return {"status": "ok"}

    new_status = classify_dlr(dlr_status_value(payload))
    detail = dlr_status_detail(payload)
    previous_status = message.status
    if new_status == SmsStatus.DELIVERED.value:
        message.status = SmsStatus.DELIVERED.value
        message.delivered_at = datetime.utcnow()
    elif new_status == SmsStatus.FAILED.value:
        message.status = SmsStatus.FAILED.value
        message.error = detail or dlr_status_value(payload) or "Non délivré"
    if detail:
        message.status_detail = detail
    db.commit()
    # Notify only on a real transition, so a provider re-sending the same DLR never double-pings.
    if message.status != previous_status and message.status in {SmsStatus.DELIVERED.value, SmsStatus.FAILED.value}:
        await notification_service.notify_sms_event(
            db,
            user_id=message.user_id,
            event_name="sms_delivered" if message.status == SmsStatus.DELIVERED.value else "sms_failed",
            prospect_id=message.prospect_id,
            fallback_name=message.recipient_name or message.to_e164,
            detail=detail if message.status == SmsStatus.FAILED.value else None,
        )
    return {"status": "ok"}


def _match_dlr_message(db: Session, payload: dict[str, object]) -> SmsMessage | None:
    """Find the SMS a DLR refers to, by provider id then by our ``dlh-<id>`` ref.

    Args:
        db: Active database session.
        payload: The DLR JSON body.

    Returns:
        The matching SMS row, or ``None`` when neither key resolves.
    """
    message_id = dlr_message_id(payload)
    if message_id:
        matched = db.query(SmsMessage).filter(SmsMessage.provider_message_id == message_id).first()
        if matched is not None:
            return matched
    ref = dlr_ref_client(payload)
    if ref.startswith("dlh-"):
        try:
            row_id = int(ref[len("dlh-") :])
        except ValueError:
            return None
        return db.query(SmsMessage).filter(SmsMessage.id == row_id).first()
    return None


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
        await notification_service.notify_sms_event(
            db,
            user_id=last.user_id,
            event_name="sms_stop",
            prospect_id=last.prospect_id,
            fallback_name=last.recipient_name or phone_e164,
        )
    return {"status": "ok"}
