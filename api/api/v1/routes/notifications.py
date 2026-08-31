"""
Web Push notification routes — VAPID key, subscribe/unsubscribe, test.
"""

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from core.config import settings
from core.database import get_db
from models.notification import Notification
from models.push_subscription import PushSubscription
from models.user import User
from schemas.notification import (
    NotificationListResponse,
    NotificationOut,
    PushSubscriptionCreate,
    PushSubscriptionDelete,
    TestNotificationResult,
    VapidKeyResponse,
)
from services import push_service
from services.auth_service import get_current_user

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("/vapid-key", response_model=VapidKeyResponse)
async def get_vapid_key(current_user: User = Depends(get_current_user)) -> Any:
    """
    Return the public VAPID key so the PWA can subscribe.

    Args:
        current_user: The authenticated user.

    Returns:
        The public key and whether push is configured server-side.
    """
    return VapidKeyResponse(
        public_key=settings.vapid_public_key,
        configured=push_service.is_configured(),
    )


@router.post("/subscribe", status_code=status.HTTP_204_NO_CONTENT)
async def subscribe(
    payload: PushSubscriptionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    """
    Register (or refresh) a browser push subscription for the current user.

    Args:
        payload: The browser PushSubscription.
        current_user: The authenticated user.
        db: Database session.
    """
    existing = db.query(PushSubscription).filter(PushSubscription.endpoint == payload.endpoint).first()
    if existing:
        existing.user_id = current_user.id
        existing.p256dh = payload.keys.p256dh
        existing.auth = payload.keys.auth
        existing.user_agent = payload.user_agent or ""
    else:
        db.add(
            PushSubscription(
                user_id=current_user.id,
                endpoint=payload.endpoint,
                p256dh=payload.keys.p256dh,
                auth=payload.keys.auth,
                user_agent=payload.user_agent or "",
            )
        )
    db.commit()


@router.post("/unsubscribe", status_code=status.HTTP_204_NO_CONTENT)
async def unsubscribe(
    payload: PushSubscriptionDelete,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    """
    Remove a browser push subscription for the current user.

    Args:
        payload: The endpoint to unregister.
        current_user: The authenticated user.
        db: Database session.
    """
    db.query(PushSubscription).filter(
        PushSubscription.endpoint == payload.endpoint,
        PushSubscription.user_id == current_user.id,
    ).delete(synchronize_session=False)
    db.commit()


@router.post("/test", response_model=TestNotificationResult)
async def test_notification(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    """
    Send a test notification now and report the delivery outcome. A non-zero ``failed`` with the
    push service's HTTP status pinpoints the break: a 403/400 is a VAPID/key problem on the server,
    while ``delivered`` with nothing on the phone points at an iOS setting (PWA not installed).

    Args:
        current_user: The authenticated user.
        db: Database session.

    Returns:
        Configuration flag, subscription count, delivered/failed counts and any failure detail.
    """
    subscriptions = db.query(PushSubscription).filter(PushSubscription.user_id == current_user.id).count()
    result = push_service.send_push(
        db,
        current_user.id,
        "DevLeadHunter",
        "Notification de test 🔔",
        "/dashboard",
    )
    return TestNotificationResult(
        configured=push_service.is_configured(),
        subscriptions=subscriptions,
        delivered=result.delivered,
        failed=result.failed,
        detail="; ".join(result.details)[:300] or None,
    )


@router.get("/history", response_model=NotificationListResponse)
async def history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = 20,
    before: int | None = None,
) -> Any:
    """
    Return a page of the current user's notification history (newest first).

    Args:
        current_user: The authenticated user.
        db: Database session.
        limit: Page size (clamped to 1..50).
        before: Return notifications with an id strictly below this (cursor for "load more").

    Returns:
        The page of notifications and the current unread count.
    """
    query = db.query(Notification).filter(Notification.user_id == current_user.id)
    if before:
        query = query.filter(Notification.id < before)
    rows = query.order_by(Notification.id.desc()).limit(min(max(limit, 1), 50)).all()
    unread_count = (
        db.query(Notification).filter(Notification.user_id == current_user.id, Notification.read_at.is_(None)).count()
    )
    items = [
        NotificationOut(
            id=row.id,
            category=row.category,
            level=row.level,
            title=row.title,
            body=row.body,
            url=row.url,
            read=row.read_at is not None,
            created_at=row.created_at,
        )
        for row in rows
    ]
    return NotificationListResponse(items=items, unread_count=unread_count)


@router.get("/{notification_id}", response_model=NotificationOut)
async def get_notification(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    """
    Return one notification of the current user (opened from a push tap).

    Args:
        notification_id: The notification to fetch.
        current_user: The authenticated user.
        db: Database session.

    Returns:
        The notification.

    Raises:
        HTTPException: 404 when the notification is unknown or owned by another user.
    """
    row = (
        db.query(Notification)
        .filter(Notification.id == notification_id, Notification.user_id == current_user.id)
        .first()
    )
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification introuvable")
    return NotificationOut(
        id=row.id,
        category=row.category,
        level=row.level,
        title=row.title,
        body=row.body,
        url=row.url,
        read=row.read_at is not None,
        created_at=row.created_at,
    )


@router.post("/read-all", status_code=status.HTTP_204_NO_CONTENT)
async def mark_all_read(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    """
    Mark every unread notification of the current user as read.

    Args:
        current_user: The authenticated user.
        db: Database session.
    """
    now = datetime.now(UTC).replace(tzinfo=None)
    db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.read_at.is_(None),
    ).update({Notification.read_at: now})
    db.commit()


@router.patch("/{notification_id}/read", status_code=status.HTTP_204_NO_CONTENT)
async def mark_read(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    """
    Mark a single notification of the current user as read.

    Args:
        notification_id: The notification to mark read.
        current_user: The authenticated user.
        db: Database session.
    """
    now = datetime.now(UTC).replace(tzinfo=None)
    db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.user_id == current_user.id,
        Notification.read_at.is_(None),
    ).update({Notification.read_at: now})
    db.commit()
