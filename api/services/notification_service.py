"""
Notification builder — turns business events (email, demo, sale) into mobile push
notifications and delivers them through ``push_service``.

Best-effort by design: every method swallows its own errors so a notification
failure can never break the request (webhook, send, sale) that triggered it.
"""

import asyncio
import logging
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from core.config import settings
from core.database import SessionLocal
from enums.demo_site_status import DemoSiteStatus
from enums.user_role import UserRole
from models.demo_site import DemoSite
from models.email_log import EmailLog
from models.order import Order
from models.prospect_db import ProspectDB
from models.push_subscription import PushSubscription
from models.user import User
from services import push_service
from services.posthog_service import posthog_service

logger = logging.getLogger(__name__)

# Deep link opened when a prospect-related notification is tapped.
_PROSPECTS_URL = "/dashboard/my-prospects"

# Email lifecycle event → (title template, body template). ``{prospect}`` is filled
# with the prospect's business name, ``{subject}`` with the email subject. An event
# absent from this map is not notified.
_EMAIL_EVENT_NOTIFS: dict[str, tuple[str, str]] = {
    "email_sent": ("📤 Mail envoyé à {prospect}", "{subject}"),
    "email_delivered": ("✅ Mail livré à {prospect}", "{subject}"),
    "email_opened": ("👀 {prospect} a ouvert ton mail", "{subject}"),
    "email_clicked": ("🖱️ {prospect} a cliqué ton lien", "{subject}"),
    "email_bounced": ("⛔ Bounce — {prospect}", "Adresse rejetée, bascule en cours"),
    "email_complained": ("🚩 {prospect} t'a marqué en spam", ""),
    "email_failed": ("❌ Échec d'envoi — {prospect}", "{subject}"),
    "email_delivery_delayed": ("⏳ Livraison retardée — {prospect}", "{subject}"),
    "email_suppressed": ("🚫 Mail supprimé — {prospect}", "Adresse supprimée"),
}

# Live demo / video event → (title template, body template). ``{prospect}`` is the
# prospect name; ``{label}`` / ``{host}`` / ``{seconds}`` / ``{max_scroll}`` fill from
# the beacon. Only notify-worthy events are listed (section views and scroll depth are
# covered by the end-of-visit ``demo_time_on_page`` summary).
_DEMO_EVENT_NOTIFS: dict[str, tuple[str, str]] = {
    "demo_opened": ("🌐 {prospect} est sur sa démo", "En ce moment"),
    "demo_engaged": ("🔥 Visite qualifiée — {prospect}", "Prospect engagé"),
    "demo_cta_click": ("👉 {prospect} a cliqué « {label} »", ""),
    "demo_phone_click": ("📞 {prospect} a cliqué ton numéro", ""),
    "demo_contact_click": ("✉️ {prospect} a cliqué ton mail de contact", ""),
    "demo_outbound_click": ("🔗 {prospect} a cliqué un lien externe", "{host}"),
    "demo_time_on_page": ("👀 Visite de {prospect}", "{seconds}s · scroll {max_scroll}%"),
    "demo_video_opened": ("🎬 {prospect} a ouvert ta vidéo", ""),
    "demo_video_play": ("▶️ {prospect} lance ta vidéo", ""),
    "demo_video_complete": ("✅ {prospect} a vu ta vidéo en entier", ""),
    "demo_video_replay": ("🔁 {prospect} revoit ta vidéo", ""),
}


class NotificationService:
    """Builds and sends mobile push notifications from business events."""

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
    ) -> None:
        """
        Push a mobile notification for an email lifecycle event.

        Args:
            db: Active database session (used to resolve the prospect's name).
            user_id: Owner of the email — the notification recipient.
            event_name: Underscore event name (e.g. ``email_opened``).
            recipient_email: Recipient address, used as a name fallback.
            prospect_id: Prospect id, when the email targets a saved prospect.
            subject: Email subject, shown in the notification body.
            email_log_id: EmailLog id, tags the email's events so they collapse into one notification.
        """
        try:
            mapping = _EMAIL_EVENT_NOTIFS.get(event_name)
            if mapping is None:
                return
            title_template, body_template = mapping
            prospect_name = self._resolve_prospect_name(db, prospect_id, recipient_email)
            title = title_template.format(prospect=prospect_name)
            body = body_template.format(subject=subject or "")
            tag = f"email-{email_log_id}" if email_log_id else None
            await push_service.notify(user_id, title, body, _PROSPECTS_URL, tag)
        except Exception as exc:
            logger.warning("notify_email_event failed (log=%s): %s", email_log_id, exc)

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
    ) -> None:
        """
        Push a mobile notification for a live demo/video behavioural event.

        Args:
            db: Active database session (used to resolve the prospect's name).
            user_id: Owner of the demo — the notification recipient.
            prospect_id: Prospect the demo belongs to.
            event_name: Beaconed event name (e.g. ``demo_cta_click``).
            fallback_name: Name shown when the prospect can't be resolved (e.g. the slug).
            label: CTA label, for ``demo_cta_click``.
            host: External host, for ``demo_outbound_click``.
            seconds: Engaged seconds, for the end-of-visit summary.
            max_scroll: Max scroll depth (%), for the end-of-visit summary.
        """
        try:
            mapping = _DEMO_EVENT_NOTIFS.get(event_name)
            if mapping is None:
                return
            title_template, body_template = mapping
            prospect_name = self._resolve_prospect_name(db, prospect_id, fallback_name)
            title = title_template.format(prospect=prospect_name, label=label or "")
            body = body_template.format(
                host=host or "",
                seconds=seconds if seconds is not None else 0,
                max_scroll=max_scroll if max_scroll is not None else 0,
            )
            await push_service.notify(user_id, title, body, _PROSPECTS_URL)
        except Exception as exc:
            logger.warning("notify_demo_event failed (event=%s): %s", event_name, exc)

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
        Push a mobile notification when a prospect pays — the funnel's final step.

        Args:
            db: Active database session (used to resolve the prospect's name).
            user_id: Owner of the sale — the notification recipient.
            prospect_id: Prospect who paid, when known.
            amount_cents: Order amount in cents.
            currency: ISO currency code (e.g. ``eur``).
            fallback_name: Name shown when the prospect can't be resolved.
            order_id: Order id, tags the notification.
        """
        try:
            prospect_name = self._resolve_prospect_name(db, prospect_id, fallback_name)
            amount = self._format_amount(amount_cents, currency)
            await push_service.notify(
                user_id,
                f"💰 VENTE — {prospect_name}",
                amount,
                "/dashboard/orders",
                f"sale-{order_id}",
            )
        except Exception as exc:
            logger.warning("notify_sale failed (order=%s): %s", order_id, exc)

    async def notify_error(self, *, context: str, message: str, tag: str | None = None) -> None:
        """
        Push a system-error notification to every active admin.

        Args:
            context: Short label of where the error happened (e.g. the request path).
            message: Error detail, truncated in the notification body.
            tag: Optional tag to collapse repeated occurrences of the same error.
        """
        db = SessionLocal()
        try:
            admins = db.query(User).filter(User.role == UserRole.ADMIN.value, User.is_active.is_(True)).all()
            title = f"🛠️ Erreur — {context}"[:120]
            body = message[:200]
            for admin in admins:
                await push_service.notify(admin.id, title, body, "/dashboard", tag)
        except Exception as exc:
            logger.warning("notify_error failed (context=%s): %s", context, exc)
        finally:
            db.close()

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
                await push_service.notify(user_id, "📊 Récap du jour", body, "/dashboard", "daily-recap")
        except Exception as exc:
            logger.warning("send_daily_recap failed: %s", exc)
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
    """Fire the daily recap once a day at the configured UTC hour (never crashes the loop)."""
    while True:
        now = datetime.utcnow()
        target = now.replace(hour=settings.daily_recap_hour_utc, minute=0, second=0, microsecond=0)
        if target <= now:
            target += timedelta(days=1)
        await asyncio.sleep((target - now).total_seconds())
        try:
            await notification_service.send_daily_recap()
        except Exception as exc:
            logger.warning("daily recap loop error: %s", exc)
