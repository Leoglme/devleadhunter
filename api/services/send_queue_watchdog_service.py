"""Watchdog that alerts when the cold-email send queue stops draining."""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select

from core.database import SessionLocal
from models.campaign import Campaign, CampaignStatus
from models.email_queue import EmailQueue
from services.notification_service import notification_service

logger = logging.getLogger(__name__)

_STATUS_PENDING: str = "pending"

# A due item should be dispatched within a worker tick (60s); this much lag means the queue is stuck.
_OVERDUE_ALERT_MINUTES: int = 20
_CHECK_INTERVAL_SECONDS: int = 300


class SendQueueWatchdog:
    """Detects a stalled send queue and notifies admins, whatever the root cause."""

    async def check_and_alert(self) -> int:
        """
        Alert when active-campaign emails are overdue and still unsent.

        The email queue worker dispatches every due item within a tick, so a pending item on an
        active campaign that is overdue by more than ``_OVERDUE_ALERT_MINUTES`` means the worker is
        no longer draining the queue (crash-looping tick, dead task, stuck process…). Any such case
        raises a single admin notification, collapsed by tag so it is not repeated every check.

        Returns:
            The number of overdue-pending items found (0 when the queue is healthy).
        """
        cutoff: datetime = datetime.now(UTC).replace(tzinfo=None) - timedelta(minutes=_OVERDUE_ALERT_MINUTES)

        db = SessionLocal()
        try:
            row = db.execute(
                select(func.count(), func.min(EmailQueue.scheduled_at))
                .join(Campaign, EmailQueue.campaign_id == Campaign.id)
                .where(
                    EmailQueue.status == _STATUS_PENDING,
                    EmailQueue.scheduled_at <= cutoff,
                    Campaign.status == CampaignStatus.ACTIVE.value,
                )
            ).one()
        finally:
            db.close()

        overdue_count: int = row[0] or 0
        if overdue_count == 0:
            return 0

        earliest: datetime | None = row[1]
        earliest_label: str = earliest.strftime("%d/%m %H:%M UTC") if earliest else "?"
        logger.error(
            "[SendQueueWatchdog] %d overdue pending email(s), oldest scheduled %s — queue not draining",
            overdue_count,
            earliest_label,
        )
        await notification_service.notify_error(
            context="File d'envoi bloquée",
            message=(
                f"{overdue_count} mail(s) en retard non envoyés (le plus ancien prévu {earliest_label}). "
                "Le worker d'envoi ne draine plus la file."
            ),
            tag="send-queue-stuck",
        )
        return overdue_count


send_queue_watchdog = SendQueueWatchdog()


async def run_send_queue_watchdog_loop() -> None:
    """Check the send queue health on a fixed interval, forever (errors never stop the loop)."""
    logger.info(
        "[SendQueueWatchdog] Started — interval=%ds, overdue threshold=%dmin",
        _CHECK_INTERVAL_SECONDS,
        _OVERDUE_ALERT_MINUTES,
    )
    while True:
        try:
            await send_queue_watchdog.check_and_alert()
        except Exception as exc:
            logger.warning("[SendQueueWatchdog] check failed: %s", exc)
        await asyncio.sleep(_CHECK_INTERVAL_SECONDS)
