"""
Notification builder — turns business events (email, demo, sale, system) into
mobile push notifications AND a persisted in-app log, per user.

Every notification is **persisted first** (attributed to a user, kept ~90 days),
then pushed best-effort — so the in-app history stays complete even when no device
receives the push (not subscribed, app closed, offline). Best-effort throughout:
a notification failure never breaks the request that raised it.

Notification shape: the title is ``{emoji} {prospect}`` and the action lives in the
body, so the essential info stays visible on iOS without expanding the notification.
"""

import asyncio
import logging
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from core.config import settings
from core.database import SessionLocal
from enums.demo_site_status import DemoSiteStatus
from enums.user_role import is_platform_admin
from models.demo_site import DemoSite
from models.email_log import EmailLog
from models.notification import Notification
from models.order import Order
from models.prospect_db import ProspectDB
from models.push_subscription import PushSubscription
from models.user import User
from services import push_service
from services.posthog_service import posthog_service

logger = logging.getLogger(__name__)

# Deep links opened when a notification is tapped.
_PROSPECTS_URL = "/dashboard/my-prospects"
_ORDERS_URL = "/dashboard/orders"
_DASHBOARD_URL = "/dashboard"

# In-app notification log retention.
_RETENTION_DAYS = 90

# Email lifecycle event → (emoji, level, body). Title = "{emoji} {prospect}", so the
# action (body) stays visible on iOS without expanding the notification.
_EMAIL_EVENT_NOTIFS: dict[str, tuple[str, str, str]] = {
    "email_sent": ("📤", "info", "Mail envoyé"),
    "email_delivered": ("✅", "info", "Mail livré"),
    "email_opened": ("👀", "success", "A ouvert ton mail"),
    "email_clicked": ("🖱️", "success", "A cliqué le lien du mail"),
    "email_bounced": ("⛔", "warning", "Mail rejeté (bounce) — bascule en cours"),
    "email_complained": ("🚩", "warning", "T'a marqué en spam"),
    "email_failed": ("❌", "error", "Échec d'envoi"),
    "email_delivery_delayed": ("⏳", "warning", "Livraison retardée"),
    "email_suppressed": ("🚫", "warning", "Mail supprimé (suppression)"),
    "email_replied": ("💬", "success", "T'a répondu !"),
    "email_replied_interested": ("🎯", "success", "T'a répondu — intéressé !"),
    "email_replied_negative": ("🙅", "warning", "T'a répondu — pas intéressé"),
}

# Live demo / video event → (emoji, level, body). Same title convention.
_DEMO_EVENT_NOTIFS: dict[str, tuple[str, str, str]] = {
    "demo_opened": ("🌐", "success", "Vient d'ouvrir sa démo"),
    # Banner « Ce site vous plaît ? » submitted — the strongest demo signal there is.
    "demo_lead": ("🙋", "success", "Est intéressé par son site !"),
    "demo_engaged": ("🔥", "success", "Visite qualifiée — prospect engagé"),
    "demo_cta_click": ("👉", "success", "A cliqué « {label} »"),
    "demo_phone_click": ("📞", "success", "A cliqué ton numéro"),
    "demo_contact_click": ("✉️", "success", "A cliqué ton mail de contact"),
    "demo_outbound_click": ("🔗", "info", "A cliqué un lien externe : {host}"),
    "demo_time_on_page": ("👀", "info", "Visite : {seconds}s · {max_scroll}% lu"),
    "demo_video_opened": ("🎬", "success", "A ouvert ta vidéo"),
    "demo_video_play": ("▶️", "success", "Lance ta vidéo"),
    "demo_video_complete": ("✅", "success", "A vu ta vidéo en entier"),
    "demo_video_replay": ("🔁", "success", "Revoit ta vidéo"),
}


class NotificationService:
    """Raises business notifications: persist per user, then push best-effort."""

    async def notify_email_event(
        self,
        db: Session,
        *,
        user_id: int,
        event_name: str,
        recipient_email: str,
        prospect_id: int | None = None,
        subject: str | None = None,
        email_log_id: int | None = None,
        open_count: int = 1,
    ) -> None:
        """
        Raise a notification for an email lifecycle event.

        Args:
            db: Active database session (to resolve the prospect's name).
            user_id: Owner of the email — the notification recipient.
            event_name: Underscore event name (e.g. ``email_opened``).
            recipient_email: Recipient address, used as a name fallback.
            prospect_id: Prospect id, when the email targets a saved prospect.
            subject: Email subject, appended to the body on opens/clicks.
            email_log_id: EmailLog id, tags the email's events so the push collapses.
            open_count: Running count of human opens; >1 turns the open into a reopen cue.
        """
        mapping = _EMAIL_EVENT_NOTIFS.get(event_name)
        if mapping is None:
            return
        emoji, level, body = mapping
        prospect_name = self._resolve_prospect_name(db, prospect_id, recipient_email)
        if event_name == "email_opened" and open_count > 1:
            emoji, body = "🔁", f"A rouvert ton mail ({open_count}×)"
        if subject and event_name in (
            "email_opened",
            "email_clicked",
            "email_replied",
            "email_replied_interested",
            "email_replied_negative",
        ):
            body = f"{body} : « {subject} »"
        tag = f"email-{email_log_id}" if email_log_id else None
        await self._dispatch(
            user_id=user_id,
            category="email",
            level=level,
            title=f"{emoji} {prospect_name}",
            body=body,
            url=_PROSPECTS_URL,
            tag=tag,
        )

    async def notify_demo_event(
        self,
        db: Session,
        *,
        user_id: int,
        prospect_id: int | None,
        event_name: str,
        fallback_name: str,
        label: str | None = None,
        host: str | None = None,
        seconds: int | None = None,
        max_scroll: int | None = None,
        message: str | None = None,
    ) -> None:
        """
        Raise a notification for a live demo/video behavioural event.

        Args:
            db: Active database session (to resolve the prospect's name).
            user_id: Owner of the demo — the notification recipient.
            prospect_id: Prospect the demo belongs to.
            event_name: Beaconed event name (e.g. ``demo_cta_click``).
            fallback_name: Name shown when the prospect can't be resolved (e.g. the slug).
            label: CTA label, for ``demo_cta_click``.
            host: External host, for ``demo_outbound_click``.
            seconds: Engaged seconds, for the end-of-visit summary.
            max_scroll: Max scroll depth (%), for the end-of-visit summary.
            message: Free text left by the prospect, for ``demo_lead``.
        """
        mapping = _DEMO_EVENT_NOTIFS.get(event_name)
        if mapping is None:
            return
        emoji, level, body_template = mapping
        prospect_name = self._resolve_prospect_name(db, prospect_id, fallback_name)
        body = body_template.format(
            label=label or "",
            host=host or "",
            seconds=seconds if seconds is not None else 0,
            max_scroll=max_scroll if max_scroll is not None else 0,
        )
        if event_name == "demo_lead" and (message or "").strip():
            excerpt = message.strip()[:160]
            body = f"{body} « {excerpt} »"
        await self._dispatch(
            user_id=user_id,
            category="demo",
            level=level,
            title=f"{emoji} {prospect_name}",
            body=body,
            url=_PROSPECTS_URL,
        )

    async def notify_sale(
        self,
        db: Session,
        *,
        user_id: int,
        prospect_id: int | None,
        amount_cents: int,
        currency: str,
        fallback_name: str,
        order_id: int,
    ) -> None:
        """
        Raise a notification when a prospect pays — the funnel's final step.

        Args:
            db: Active database session (to resolve the prospect's name).
            user_id: Owner of the sale — the notification recipient.
            prospect_id: Prospect who paid, when known.
            amount_cents: Order amount in cents.
            currency: ISO currency code (e.g. ``eur``).
            fallback_name: Name shown when the prospect can't be resolved.
            order_id: Order id, tags the notification.
        """
        prospect_name = self._resolve_prospect_name(db, prospect_id, fallback_name)
        amount = self._format_amount(amount_cents, currency)
        await self._dispatch(
            user_id=user_id,
            category="sale",
            level="success",
            title=f"💰 {prospect_name}",
            body=f"A payé {amount}",
            url=_ORDERS_URL,
            tag=f"sale-{order_id}",
        )

    async def notify_error(self, *, context: str, message: str, tag: str | None = None) -> None:
        """
        Raise a system-error notification for every active admin.

        Args:
            context: Short label of where the error happened (e.g. the request path).
            message: Error detail, truncated in the body.
            tag: Optional tag to collapse repeated occurrences of the same error.
        """
        db = SessionLocal()
        try:
            admins = db.query(User).filter(User.is_active.is_(True)).all()
            admin_ids = [admin.id for admin in admins if is_platform_admin(admin.role)]
        except Exception as exc:
            logger.warning("notify_error admin lookup failed (context=%s): %s", context, exc)
            admin_ids = []
        finally:
            db.close()
        for admin_id in admin_ids:
            await self._dispatch(
                user_id=admin_id,
                category="system",
                level="error",
                title="🛠️ Erreur serveur",
                body=f"{context} — {message}"[:200],
                url=_DASHBOARD_URL,
                tag=tag,
            )

    async def send_daily_recap(self) -> None:
        """Send each subscribed user their daily activity recap — sent even when everything is zero."""
        db = SessionLocal()
        try:
            day_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            user_ids = [row[0] for row in db.query(PushSubscription.user_id).distinct().all()]
            for user_id in user_ids:
                sent = db.query(EmailLog).filter(EmailLog.user_id == user_id, EmailLog.sent_at >= day_start).count()
                delivered = (
                    db.query(EmailLog).filter(EmailLog.user_id == user_id, EmailLog.delivered_at >= day_start).count()
                )
                opened = db.query(EmailLog).filter(EmailLog.user_id == user_id, EmailLog.opened_at >= day_start).count()
                clicked = (
                    db.query(EmailLog).filter(EmailLog.user_id == user_id, EmailLog.clicked_at >= day_start).count()
                )
                sales = (
                    db.query(Order)
                    .filter(Order.user_id == user_id, Order.paid_at >= day_start, Order.deleted_at.is_(None))
                    .count()
                )
                slugs = [
                    row[0]
                    for row in db.query(DemoSite.slug)
                    .filter(
                        DemoSite.user_id == user_id,
                        DemoSite.status != DemoSiteStatus.DELETED.value,
                        DemoSite.slug.isnot(None),
                    )
                    .all()
                ]
                visits = await posthog_service.count_demo_visits_since(slugs, day_start)
                body = (
                    f"{sent} mails · {delivered} livrés · {opened} ouverts · {clicked} clics · "
                    f"{visits['pageviews']} visites ({visits['engaged']} qualifiées) · {sales} vente(s)"
                )
                await self._dispatch(
                    user_id=user_id,
                    category="recap",
                    level="info",
                    title="📊 Récap du jour",
                    body=body,
                    url=_DASHBOARD_URL,
                    tag="daily-recap",
                )
        except Exception as exc:
            logger.warning("send_daily_recap failed: %s", exc)
        finally:
            db.close()

    async def _dispatch(
        self,
        *,
        user_id: int,
        category: str,
        level: str,
        title: str,
        body: str,
        url: str,
        tag: str | None = None,
    ) -> None:
        """
        Persist a notification (guaranteed) then push it to the user's devices (best-effort).

        Args:
            user_id: Recipient.
            category: Domain (email / demo / sale / system / recap).
            level: Visual level (info / success / warning / error).
            title: Notification title.
            body: Notification body.
            url: In-app deep link opened on tap.
            tag: Optional push tag (collapses same-tag notifications on the device).
        """
        await asyncio.to_thread(self._persist, user_id, category, level, title, body, url)
        await push_service.notify(user_id, title, body, url, tag)

    @staticmethod
    def _persist(user_id: int, category: str, level: str, title: str, body: str, url: str) -> None:
        """
        Store a notification in the in-app log (own session; never raises).

        Args:
            user_id: Recipient.
            category: Domain.
            level: Visual level.
            title: Notification title.
            body: Notification body.
            url: Deep link.
        """
        db = SessionLocal()
        try:
            db.add(
                Notification(
                    user_id=user_id,
                    category=category,
                    level=level,
                    title=title,
                    body=body,
                    url=url,
                )
            )
            db.commit()
        except Exception as exc:
            logger.warning("notification persist failed (user=%s): %s", user_id, exc)
        finally:
            db.close()

    @staticmethod
    def purge_old(days: int = _RETENTION_DAYS) -> None:
        """
        Delete notifications older than ``days`` (in-app log retention).

        Args:
            days: Retention window in days.
        """
        db = SessionLocal()
        try:
            cutoff = datetime.utcnow() - timedelta(days=days)
            db.query(Notification).filter(Notification.created_at < cutoff).delete(synchronize_session=False)
            db.commit()
        except Exception as exc:
            logger.warning("notification purge failed: %s", exc)
        finally:
            db.close()

    @staticmethod
    def _resolve_prospect_name(db: Session, prospect_id: int | None, fallback: str) -> str:
        """
        Return the prospect's business name, falling back to a provided label.

        Args:
            db: Active database session.
            prospect_id: Prospect id, when known.
            fallback: Name used when no prospect name is found (recipient address or slug).

        Returns:
            A non-empty display name for the notification.
        """
        if prospect_id:
            prospect = db.query(ProspectDB).filter(ProspectDB.id == prospect_id).first()
            if prospect and prospect.name:
                return prospect.name
        return fallback or "Prospect"

    @staticmethod
    def _format_amount(amount_cents: int, currency: str) -> str:
        """
        Format a cents amount into a short human label (e.g. ``500 €``).

        Args:
            amount_cents: Amount in cents.
            currency: ISO currency code.

        Returns:
            The formatted amount with its currency symbol.
        """
        symbols = {"eur": "€", "usd": "$", "gbp": "£"}
        symbol = symbols.get(currency.lower(), currency.upper())
        amount = amount_cents / 100
        text = f"{amount:.0f}" if amount == int(amount) else f"{amount:.2f}"
        return f"{text} {symbol}"


notification_service = NotificationService()


async def run_daily_recap_loop() -> None:
    """Fire the daily recap + purge old notifications, once a day at the configured UTC hour."""
    while True:
        now = datetime.utcnow()
        target = now.replace(hour=settings.daily_recap_hour_utc, minute=0, second=0, microsecond=0)
        if target <= now:
            target += timedelta(days=1)
        await asyncio.sleep((target - now).total_seconds())
        try:
            await notification_service.send_daily_recap()
            notification_service.purge_old()
        except Exception as exc:
            logger.warning("daily recap loop error: %s", exc)
