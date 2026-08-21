"""Pre-swap Storyblok spaces before scheduled outreach emails."""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

from enums.campaign_status import CampaignStatus
from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from core.config import settings
from enums.demo_site_status import DemoSiteStatus
from models.campaign import Campaign
from models.demo_site import DemoSite
from models.email_queue import EmailQueue
from models.email_template import EmailTemplate
from services.campaign_queue_service import CampaignQueueService
from services.demo_site_service import demo_site_service

logger = logging.getLogger(__name__)

_STATUS_PENDING: str = "pending"


class StoryblokPreswapService:
    """Warm-swaps expiring Storyblok spaces ahead of scheduled demo outreach."""

    async def run_preswap_pass(self, db: Session) -> int:
        """
        Swap Storyblok spaces that would expire during the upcoming demo TTL window.

        Returns:
            Number of demo sites swapped during this pass.
        """
        now: datetime = datetime.now(UTC)
        lead: timedelta = timedelta(minutes=settings.storyblok_preswap_lead_minutes)
        window_end: datetime = now + lead

        rows: list[tuple[EmailQueue, EmailTemplate]] = list(
            db.execute(
                select(EmailQueue, EmailTemplate)
                .join(Campaign, EmailQueue.campaign_id == Campaign.id)
                .join(EmailTemplate, EmailQueue.template_id == EmailTemplate.id)
                .where(
                    and_(
                        EmailQueue.status == _STATUS_PENDING,
                        EmailQueue.scheduled_at > now,
                        EmailQueue.scheduled_at <= window_end,
                        Campaign.status == CampaignStatus.ACTIVE.value,
                    )
                )
                .order_by(EmailQueue.scheduled_at.asc())
            ).all()
        )

        swapped: int = 0
        seen_site_ids: set[int] = set()

        for item, template in rows:
            if not CampaignQueueService._template_uses_demo_link(template):
                continue

            site: DemoSite | None = self._active_demo_for_prospect(db, item.prospect_id, item.user_id)
            if site is None or site.id in seen_site_ids:
                continue
            if site.demo_link_sent_at is not None:
                continue
            if not demo_site_service.needs_storyblok_space_swap(site, now):
                continue

            seen_site_ids.add(site.id)
            try:
                if await demo_site_service.swap_storyblok_space_for_outreach(db, site):
                    swapped += 1
            except Exception:
                logger.warning(
                    "Storyblok pre-swap failed for demo site %s (queue item %s)",
                    site.id,
                    item.id,
                    exc_info=True,
                )

        if swapped:
            logger.info("[StoryblokPreswap] Swapped %d demo site space(s)", swapped)
        return swapped

    @staticmethod
    def _active_demo_for_prospect(db: Session, prospect_id: int, user_id: int) -> DemoSite | None:
        return db.execute(
            select(DemoSite)
            .where(
                DemoSite.prospect_id == prospect_id,
                DemoSite.user_id == user_id,
                DemoSite.status == DemoSiteStatus.ACTIVE.value,
            )
            .order_by(DemoSite.created_at.desc())
            .limit(1)
        ).scalar_one_or_none()


storyblok_preswap_service = StoryblokPreswapService()
