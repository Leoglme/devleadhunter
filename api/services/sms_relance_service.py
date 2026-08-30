"""Find prospects eligible for an SMS relance, and send it.

The SMS channel is a RELANCE, never a cold first touch: a prospect qualifies
only when they were emailed a while ago and did NOT react (no human open, no
click, no reply), still have a live demo to point at, own a mobile, and have not
already been texted or opted out. This keeps the SMS squarely a « second touch »
— more natural and more defensible than a cold SMS.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from enums.demo_site_status import DemoSiteStatus
from models.demo_site import DemoSite
from models.email_log import EmailLog
from models.prospect_db import ProspectDB
from models.sms_message import SmsMessage
from services.decision_maker.greeting import build_greeting
from services.demo_site_service import demo_site_service
from services.email_variables import EmailVariables
from services.sms.phone_normalizer import is_mobile_fr, to_e164_fr
from services.sms_config_service import sms_config_service
from services.sms_service import sms_service

logger = logging.getLogger(__name__)

# A prospect qualifies for a relance this many *calendar* days after the email.
DEFAULT_RELANCE_AFTER_DAYS: int = 30


class SmsRelanceCandidate:
    """A prospect eligible for an SMS relance, with the demo link to push."""

    def __init__(self, *, prospect: ProspectDB, demo_url: str, emailed_at: datetime) -> None:
        self.prospect = prospect
        self.demo_url = demo_url
        self.emailed_at = emailed_at


class SmsRelanceService:
    """Select relance-eligible prospects and send their SMS."""

    def find_candidates(
        self,
        db: Session,
        user_id: int,
        *,
        after_days: int = DEFAULT_RELANCE_AFTER_DAYS,
        limit: int = 50,
    ) -> list[SmsRelanceCandidate]:
        """Return the user's prospects eligible for an SMS relance.

        Args:
            db: Active database session.
            user_id: Owner.
            after_days: Minimum age (days) of the unanswered email.
            limit: Max candidates to return.

        Returns:
            Eligible candidates, oldest email first.
        """
        cutoff = datetime.utcnow() - timedelta(days=after_days)
        # Emails sent before the cutoff that got NO human reaction.
        unreacted = (
            select(EmailLog.prospect_id, func.min(EmailLog.sent_at).label("emailed_at"))
            .where(
                EmailLog.user_id == user_id,
                EmailLog.prospect_id.isnot(None),
                EmailLog.sent_at.isnot(None),
                EmailLog.sent_at <= cutoff,
                EmailLog.opened_at.is_(None),
                EmailLog.clicked_at.is_(None),
                EmailLog.replied_at.is_(None),
            )
            .group_by(EmailLog.prospect_id)
            .subquery()
        )
        # Prospects already texted (any status) — never text twice in v1.
        already_texted = select(SmsMessage.prospect_id).where(SmsMessage.user_id == user_id).subquery()

        rows = db.execute(
            select(ProspectDB, unreacted.c.emailed_at)
            .join(unreacted, unreacted.c.prospect_id == ProspectDB.id)
            .where(
                ProspectDB.user_id == user_id,
                ProspectDB.phone.isnot(None),
                ProspectDB.id.notin_(select(already_texted.c.prospect_id)),
            )
            .order_by(unreacted.c.emailed_at.asc())
            .limit(limit * 3)  # over-fetch: mobile/demo/suppression filters trim below
        ).all()

        candidates: list[SmsRelanceCandidate] = []
        for prospect, emailed_at in rows:
            if not is_mobile_fr(prospect.phone):
                continue
            to_e164 = to_e164_fr(prospect.phone)
            if to_e164 and sms_service.is_suppressed(db, user_id, to_e164):
                continue
            demo_url = self._live_demo_url(db, user_id, prospect.id)
            if not demo_url:
                continue
            candidates.append(SmsRelanceCandidate(prospect=prospect, demo_url=demo_url, emailed_at=emailed_at))
            if len(candidates) >= limit:
                break
        return candidates

    def _live_demo_url(self, db: Session, user_id: int, prospect_id: int) -> str | None:
        """Public URL of the prospect's live demo, or ``None`` when there is none."""
        site = (
            db.query(DemoSite)
            .filter(
                DemoSite.user_id == user_id,
                DemoSite.prospect_id == prospect_id,
                DemoSite.status == DemoSiteStatus.ACTIVE.value,
                DemoSite.slug.isnot(None),
            )
            .order_by(DemoSite.created_at.desc())
            .first()
        )
        if site is None or not site.slug:
            return None
        return demo_site_service.demo_url_for_slug(site.slug)

    async def send_relance(self, db: Session, user_id: int, candidate: SmsRelanceCandidate) -> bool:
        """Send the relance SMS for one candidate.

        Args:
            db: Active database session.
            user_id: Sender.
            candidate: The eligible candidate.

        Returns:
            ``True`` when the SMS was accepted by the provider.
        """
        config = sms_config_service.get(db, user_id)
        if config is None:
            return False
        first, last, gender = EmailVariables.resolved_contact(db, candidate.prospect.id)
        greeting = build_greeting(first, last, gender)
        outcome = await sms_service.send_to_prospect(
            db,
            user_id=user_id,
            prospect=candidate.prospect,
            config=config,
            demo_url=candidate.demo_url,
            greeting=greeting,
        )
        return outcome.sent


sms_relance_service = SmsRelanceService()
