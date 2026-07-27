"""
Cumulative email-log counters shared by campaign stats, email list stats, etc.

Each funnel step includes every log that reached at least that step (an opened
email is also counted as sent and delivered), so rates never exceed 100 %.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import case, func, or_
from sqlalchemy.orm import Session

from enums.email_status import EmailStatus
from models.email_log import EmailLog

_POST_SEND_STATUSES: tuple[str, ...] = (
    EmailStatus.SENT.value,
    EmailStatus.DELIVERED.value,
    EmailStatus.DELIVERY_DELAYED.value,
    EmailStatus.OPENED.value,
    EmailStatus.CLICKED.value,
    EmailStatus.BOUNCED.value,
    EmailStatus.COMPLAINED.value,
)


def _sent_marker() -> or_:
    return or_(EmailLog.sent_at.isnot(None), EmailLog.status.in_(_POST_SEND_STATUSES))


def _delivered_marker() -> or_:
    return or_(
        EmailLog.delivered_at.isnot(None),
        EmailLog.status.in_((EmailStatus.DELIVERED.value, EmailStatus.OPENED.value, EmailStatus.CLICKED.value)),
    )


def _opened_marker() -> or_:
    return or_(
        EmailLog.opened_at.isnot(None),
        EmailLog.status.in_((EmailStatus.OPENED.value, EmailStatus.CLICKED.value)),
    )


def _clicked_marker() -> or_:
    return or_(EmailLog.clicked_at.isnot(None), EmailLog.status == EmailStatus.CLICKED.value)


def _bounced_marker() -> or_:
    return or_(EmailLog.bounced_at.isnot(None), EmailLog.status == EmailStatus.BOUNCED.value)


def _failed_marker() -> or_:
    return or_(EmailLog.failed_at.isnot(None), EmailLog.status == EmailStatus.FAILED.value)


@dataclass(frozen=True)
class EmailLogCounts:
    """Raw cumulative counters for one scoped set of email logs."""

    sent: int
    delivered: int
    opened: int
    clicked: int
    bounced: int
    failed: int


@dataclass(frozen=True)
class EmailEngagementRates:
    """Derived percentage rates from :class:`EmailLogCounts`."""

    delivery_rate: float
    open_rate: float
    click_rate: float


def aggregate_email_log_counts(db: Session, *filters: object) -> EmailLogCounts:
    """Sum cumulative counters for logs matching ``filters``.

    Args:
        db: SQLAlchemy session.
        *filters: Extra ``EmailLog`` filter clauses (e.g. user / campaign scope).

    Returns:
        Cumulative sent / delivered / opened / clicked / bounced / failed counts.
    """
    row = (
        db.query(
            func.sum(case((_sent_marker(), 1), else_=0)),
            func.sum(case((_delivered_marker(), 1), else_=0)),
            func.sum(case((_opened_marker(), 1), else_=0)),
            func.sum(case((_clicked_marker(), 1), else_=0)),
            func.sum(case((_bounced_marker(), 1), else_=0)),
            func.sum(case((_failed_marker(), 1), else_=0)),
        )
        .filter(*filters)
        .one()
    )
    sent, delivered, opened, clicked, bounced, failed = (int(value or 0) for value in row)
    return EmailLogCounts(
        sent=sent,
        delivered=delivered,
        opened=opened,
        clicked=clicked,
        bounced=bounced,
        failed=failed,
    )


def _rate(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round(numerator * 100.0 / denominator, 2)


def _capped_rate(numerator: int, denominator: int) -> float:
    return min(_rate(numerator, denominator), 100.0)


def compute_engagement_rates(counts: EmailLogCounts) -> EmailEngagementRates:
    """Compute delivery / open / click rates from cumulative counters."""
    return EmailEngagementRates(
        delivery_rate=_rate(counts.delivered, counts.sent),
        open_rate=_capped_rate(counts.opened, counts.delivered),
        click_rate=_capped_rate(counts.clicked, counts.opened),
    )
