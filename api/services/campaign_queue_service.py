"""
Campaign queue service — manages the cold-email send queue.

Responsibilities:
  - Enqueue initial (J1) and follow-up (J+N) emails when a campaign is launched.
  - A/B testing: split prospects 50/50 between variant A (campaign.template_id)
    and variant B (campaign.ab_template_id_b) at enqueue time.
  - Multiple follow-ups: after a J1 send, schedule all steps from
    ``campaign_follow_ups`` in order.  Falls back to the legacy
    ``follow_up_template_id`` if no ``campaign_follow_ups`` rows exist.
  - Skip sending to prospects who have unsubscribed or who already engaged
    (follow-ups only).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session, joinedload

from enums.demo_site_status import DemoSiteStatus
from enums.email_status import EmailStatus
from models.campaign import Campaign, CampaignStatus
from models.campaign_follow_up import CampaignFollowUp
from models.demo_site import DemoSite
from models.email_log import EmailLog
from models.email_queue import EmailQueue
from models.email_template import EmailTemplate
from models.prospect_db import ProspectDB
from services.email_sending_service import EmailSendingService
from services.email_variables import EmailVariables
from services.pricing_service import PricingService
from services.unsubscribe_service import unsubscribe_service

logger = logging.getLogger(__name__)

# Queue item status values
_STATUS_PENDING = "pending"
_STATUS_SENDING = "sending"
_STATUS_SENT = "sent"
_STATUS_SKIPPED = "skipped"
_STATUS_FAILED = "failed"


@dataclass
class EnqueueResult:
    """
    Outcome of enqueuing a campaign.

    Attributes:
        enqueued:         Number of J1 queue items added.
        skipped_no_demo:  Prospects skipped because their template uses
                          ``{lien_demo}`` but they have no active demo site.
                          Each entry is ``{"id": int, "name": str}``.
        skipped_no_video: Prospects skipped because their template uses
                          ``{lien_video}``/``{vignette_video}`` but their demo
                          has no generated prospection video.
    """

    enqueued: int = 0
    skipped_no_demo: list[dict[str, object]] = field(default_factory=list)
    skipped_no_video: list[dict[str, object]] = field(default_factory=list)


def _utcnow() -> datetime:
    """Return the current UTC time as a timezone-naive datetime (DB-compatible)."""
    return datetime.now(UTC).replace(tzinfo=None)


class CampaignQueueService:
    """Manages the ``email_queue`` table for rate-limited cold outreach."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def _purge_skipped_initial_items(self, campaign_id: int) -> int:
        """Delete initial queue items a pause cancelled (pending → skipped) so a resume re-enqueues them.

        A pause marks every pending send ``skipped`` (``cancel_campaign_queue``); those prospects were
        never emailed, yet ``already_queued`` would treat the leftover row as handled and drop them
        forever. Removing the stale rows lets the (re)launch rebuild a clean queue. Returns the count.
        """
        rows: list[EmailQueue] = list(
            self.db.execute(
                select(EmailQueue).where(
                    EmailQueue.campaign_id == campaign_id,
                    EmailQueue.queue_type == "initial",
                    EmailQueue.status == _STATUS_SKIPPED,
                )
            ).scalars()
        )
        for row in rows:
            self.db.delete(row)
        self.db.flush()
        return len(rows)

    def enqueue_campaign(
        self,
        campaign: Campaign,
        template_id: int,
        ab_template_id_b: int | None = None,
    ) -> EnqueueResult:
        """
        Populate the queue with J1 items for all prospects in the campaign.

        When ``ab_template_id_b`` is provided (A/B test mode), prospects are
        split 50/50: even-indexed prospects get variant A, odd-indexed get B.

        Each item is spaced ``campaign.send_delay_minutes`` apart so the worker
        can dispatch them without extra rate-limiting logic.  Emails are sent
        via the user's ResendConfig — no EmailAccount selection.

        Guard: a prospect is **not** enqueued when its assigned template uses the
        ``{lien_demo}`` placeholder but the prospect has no active demo site.
        This prevents sending a cold email with an empty demo link; such
        prospects are returned in ``skipped_no_demo`` so the operator can
        generate their sites and re-launch.

        Args:
            campaign:         The campaign whose prospects should be enqueued.
            template_id:      J1 template (variant A when A/B testing).
            ab_template_id_b: J1 template for variant B (A/B testing only).

        Returns:
            An :class:`EnqueueResult` with the enqueued count and the list of
            prospects skipped for lacking a demo site.
        """
        now = _utcnow()
        is_ab = ab_template_id_b is not None

        # Pre-load templates once to know whether each variant needs a demo link.
        template_a: EmailTemplate | None = self.db.get(EmailTemplate, template_id)
        template_b: EmailTemplate | None = self.db.get(EmailTemplate, ab_template_id_b) if ab_template_id_b else None
        uses_demo_a: bool = self._template_uses_demo_link(template_a)
        uses_demo_b: bool = self._template_uses_demo_link(template_b)
        uses_video_a: bool = self._template_uses_video(template_a)
        uses_video_b: bool = self._template_uses_video(template_b)

        # Append after the last pending slot so re-launching is safe.
        latest: datetime | None = self.db.execute(
            select(func.max(EmailQueue.scheduled_at)).where(
                EmailQueue.campaign_id == campaign.id,
                EmailQueue.status == _STATUS_PENDING,
            )
        ).scalar()

        # Drop initial items a pause cancelled (pending → skipped) so this (re)launch re-enqueues them.
        self._purge_skipped_initial_items(campaign.id)

        # Prospects with a live or sent initial item are never re-added.
        already_queued: set[int] = {
            row[0]
            for row in self.db.execute(
                select(EmailQueue.prospect_id).where(
                    EmailQueue.campaign_id == campaign.id,
                    EmailQueue.queue_type == "initial",
                )
            ).all()
        }

        result = EnqueueResult()

        # --- Pass 1: decide who gets enqueued (skip filters) -----------------
        to_enqueue: list[tuple[int, int, str | None]] = []  # (prospect_id, tpl_id, variant)
        for idx, prospect in enumerate(campaign.prospects):
            if prospect.id in already_queued:
                continue
            if unsubscribe_service.is_unsubscribed(self.db, prospect.email or ""):
                logger.debug("[Queue] Skipping unsubscribed prospect %d", prospect.id)
                continue

            if is_ab:
                variant = "A" if idx % 2 == 0 else "B"
                tpl_id = template_id if variant == "A" else ab_template_id_b
                uses_demo = uses_demo_a if variant == "A" else uses_demo_b
                uses_video = uses_video_a if variant == "A" else uses_video_b
            else:
                variant = None
                tpl_id = template_id
                uses_demo = uses_demo_a
                uses_video = uses_video_a

            # Guard: never enqueue an email that would ship an empty {lien_demo}.
            if uses_demo and not self._demo_link_for_prospect(prospect.id, campaign.user_id, variant):
                logger.info("[Queue] Skipping prospect %d — no active demo site for {lien_demo}", prospect.id)
                result.skipped_no_demo.append({"id": prospect.id, "name": prospect.name or ""})
                continue

            # Guard: a video-only template (no {lien_demo} fallback) still needs a
            # ready video and the campaign's video toggle on, else the email has no
            # content. A combo template ({lien_demo} + {vignette_video}) is never
            # skipped here — it degrades to the demo link when the video is missing
            # or the toggle is off (handled at dispatch).
            if uses_video and not uses_demo:
                has_video = campaign.include_video and bool(
                    self._video_for_prospect(prospect.id, campaign.user_id, variant)[0]
                )
                if not has_video:
                    logger.info("[Queue] Skipping prospect %d — video-only template, no video ready", prospect.id)
                    result.skipped_no_video.append({"id": prospect.id, "name": prospect.name or ""})
                    continue

            to_enqueue.append((prospect.id, tpl_id, variant))

        # --- Compute send slots (global send policy, or legacy spacing) ------
        slots: list[datetime] = self._schedule_slots(campaign, len(to_enqueue), now, latest)

        # --- Pass 2: create the queue rows ----------------------------------
        for (prospect_id, tpl_id, variant), slot in zip(to_enqueue, slots):
            self.db.add(
                EmailQueue(
                    user_id=campaign.user_id,
                    campaign_id=campaign.id,
                    prospect_id=prospect_id,
                    template_id=tpl_id,
                    email_account_id=None,
                    queue_type="initial",
                    ab_variant=variant,
                    follow_up_index=0,
                    scheduled_at=slot,
                    status=_STATUS_PENDING,
                )
            )
            result.enqueued += 1

        self.db.commit()
        logger.info(
            "[Queue] Enqueued %d J1 items for campaign %d (A/B=%s, %d skipped no-demo)",
            result.enqueued,
            campaign.id,
            is_ab,
            len(result.skipped_no_demo),
        )
        return result

    def _schedule_slots(
        self,
        campaign: Campaign,
        count: int,
        now: datetime,
        latest: datetime | None,
    ) -> list[datetime]:
        """
        Compute ``count`` send datetimes.

        When the user has a :class:`SendPolicy`, slots honour its weekday/hour
        window and daily cap (spread across days). Otherwise we keep the legacy
        behaviour: one email every ``campaign.send_delay_minutes``, no window.

        Args:
            campaign: The campaign being enqueued.
            count: Number of slots needed.
            now: Current UTC time.
            latest: Last pending scheduled slot of this campaign, if any.

        Returns:
            ``count`` ascending naive-UTC datetimes.
        """
        if count <= 0:
            return []

        from services.send_policy_service import send_policy_service

        # Take the policy path too when the campaign has its own daily cap (legacy path ignores it).
        policy_row = send_policy_service.get_policy(self.db, campaign.user_id)
        if policy_row is not None or campaign.max_emails_per_day is not None:
            resolved = send_policy_service.resolve(self.db, campaign.user_id)
            start = (
                latest + timedelta(minutes=resolved.spacing_minutes) if (latest is not None and latest > now) else now
            )
            seed_counts, occupied = send_policy_service.pending_schedule(self.db, campaign.user_id)
            return send_policy_service.next_send_slots(
                resolved,
                count,
                start_utc=start,
                seed_counts=seed_counts,
                occupied=occupied,
                per_campaign_cap=campaign.max_emails_per_day,
                campaign_seed_counts=send_policy_service.pending_campaign_counts_by_day(self.db, campaign.id),
            )

        delay = timedelta(minutes=max(campaign.send_delay_minutes, 1))
        start = latest + delay if (latest is not None and latest > now) else now
        return [start + delay * i for i in range(count)]

    async def process_next(self) -> bool:
        """
        Dispatch the next due queue item across all active campaigns.

        Returns:
            ``True`` if an item was processed, ``False`` if nothing was due.
        """
        now = _utcnow()

        item: EmailQueue | None = self.db.execute(
            select(EmailQueue)
            .join(Campaign, EmailQueue.campaign_id == Campaign.id)
            .where(
                and_(
                    EmailQueue.status == _STATUS_PENDING,
                    EmailQueue.scheduled_at <= now,
                    Campaign.status == CampaignStatus.ACTIVE.value,
                )
            )
            .order_by(EmailQueue.scheduled_at.asc())
            .limit(1)
        ).scalar_one_or_none()

        if item is None:
            return False

        # Claim the item immediately to prevent concurrent pick.
        item.status = _STATUS_SENDING
        self.db.commit()

        try:
            await self._dispatch(item)
        except Exception as exc:
            logger.error("[Queue] Unhandled error dispatching item %d: %s", item.id, exc)
            item.status = _STATUS_FAILED
            self.db.commit()

        return True

    @staticmethod
    def _template_uses_demo_link(template: EmailTemplate | None) -> bool:
        """
        Return True when a template references the ``{lien_demo}`` placeholder.

        Args:
            template: Template to inspect (subject + HTML body), or None.

        Returns:
            True if the rendered email would contain the demo link placeholder.
        """
        if template is None:
            return False
        haystack: str = f"{template.subject or ''} {template.body_html or ''}"
        return f"{{{EmailVariables.DEMO_LINK}}}" in haystack

    @staticmethod
    def _template_uses_video(template: EmailTemplate | None) -> bool:
        """
        Return True when a template references ``{lien_video}`` or
        ``{vignette_video}`` (either one requires a generated video).
        """
        if template is None:
            return False
        haystack: str = f"{template.subject or ''} {template.body_html or ''}"
        return f"{{{EmailVariables.VIDEO_LINK}}}" in haystack or f"{{{EmailVariables.VIDEO_THUMBNAIL}}}" in haystack

    def _active_demo_for_prospect(self, prospect_id: int, user_id: int) -> DemoSite | None:
        """Latest ACTIVE demo site of a prospect (or None)."""
        return self.db.execute(
            select(DemoSite)
            .where(
                DemoSite.prospect_id == prospect_id,
                DemoSite.user_id == user_id,
                DemoSite.status == DemoSiteStatus.ACTIVE.value,
            )
            .order_by(DemoSite.created_at.desc())
            .limit(1)
        ).scalar_one_or_none()

    def _demo_link_for_prospect(self, prospect_id: int, user_id: int, variant: str | None) -> str:
        """
        Resolve the ``{lien_demo}`` value: the prospect's active demo URL, with the
        A/B variant appended (``?v=A``) so PostHog can attribute the demo visit to
        the email variant. Returns "" when the prospect has no active demo.
        """
        site: DemoSite | None = self._active_demo_for_prospect(prospect_id, user_id)
        if not site or not site.demo_url:
            return ""
        url: str = site.demo_url
        if variant:
            url = f"{url}{'&' if '?' in url else '?'}v={variant}"
        return url

    def _video_for_prospect(self, prospect_id: int, user_id: int, variant: str | None) -> tuple[str, str]:
        """
        Resolve the ``{lien_video}``/``{vignette_video}`` values for a prospect.

        The player-page link carries the A/B variant (``?v=A``) so PostHog can
        attribute the video view to the email variant, like ``{lien_demo}``.

        Returns:
            ``(player page URL, thumbnail URL)`` — both "" when the prospect's active demo has no generated video.
        """
        from services.demo_video_service import has_ready_video, public_thumbnail_url, video_page_url

        site: DemoSite | None = self._active_demo_for_prospect(prospect_id, user_id)
        if not site or not has_ready_video(site):
            return "", ""
        url: str = video_page_url(site.slug)
        if variant:
            url = f"{url}{'&' if '?' in url else '?'}v={variant}"
        return url, public_thumbnail_url(site.slug)

    async def _dispatch(self, item: EmailQueue) -> None:
        """
        Render and send the email for a single queue item, then schedule follow-ups.

        Args:
            item: The queue item to process.
        """
        prospect: ProspectDB = item.prospect
        template: EmailTemplate = item.template
        campaign: Campaign = item.campaign

        # Guard: prospect may have unsubscribed after being enqueued.
        if not prospect.email or unsubscribe_service.is_unsubscribed(self.db, prospect.email):
            logger.info("[Queue] Skipping unsubscribed prospect %d", prospect.id)
            item.status = _STATUS_SKIPPED
            self.db.commit()
            return

        # Follow-up guard: skip if the prospect already engaged.
        if item.queue_type == "followup":
            engaged: int = (
                self.db.execute(
                    select(func.count()).where(
                        EmailLog.campaign_id == item.campaign_id,
                        EmailLog.prospect_id == str(item.prospect_id),
                        EmailLog.status.in_(
                            [
                                EmailStatus.OPENED.value,
                                EmailStatus.CLICKED.value,
                            ]
                        ),
                    )
                ).scalar()
                or 0
            )
            if engaged > 0:
                logger.info("[Queue] Follow-up skipped — prospect %d already engaged", prospect.id)
                item.status = _STATUS_SKIPPED
                self.db.commit()
                return

        # Guard (defense in depth): never send an email whose template needs
        # {lien_demo} when the prospect has no active demo site — e.g. the demo
        # expired between enqueue and dispatch.
        uses_demo: bool = self._template_uses_demo_link(template)
        demo_link: str = self._demo_link_for_prospect(prospect.id, item.user_id, item.ab_variant)
        if uses_demo and not demo_link:
            logger.info("[Queue] Skipping send for prospect %d — no active demo site for {lien_demo}", prospect.id)
            item.status = _STATUS_SKIPPED
            self.db.commit()
            return

        if uses_demo and demo_link:
            demo_site = self._active_demo_for_prospect(prospect.id, item.user_id)
            if demo_site is not None and demo_site.demo_link_sent_at is None:
                from services.demo_site_service import demo_site_service

                try:
                    await demo_site_service.ensure_storyblok_space_for_outreach(self.db, demo_site)
                except Exception:
                    logger.warning(
                        "[Queue] Storyblok outreach swap failed for prospect %d — sending anyway",
                        prospect.id,
                        exc_info=True,
                    )

        # Video: attach it only when the template uses it AND the campaign's video
        # toggle is on. A video-only template (no {lien_demo} fallback) with no
        # usable video has nothing to say and is skipped; a combo template just
        # degrades to its demo link (empty vignette).
        uses_video: bool = self._template_uses_video(template)
        video_link, video_thumbnail_url = "", ""
        if uses_video and campaign.include_video:
            video_link, video_thumbnail_url = self._video_for_prospect(prospect.id, item.user_id, item.ab_variant)
        if uses_video and not uses_demo and not video_link:
            logger.info("[Queue] Skipping send for prospect %d — video-only template, no video ready", prospect.id)
            item.status = _STATUS_SKIPPED
            self.db.commit()
            return

        # Build personalisation variables ({salutation}/{prenom}/{nom} come from
        # the resolved decision-maker — never the company name).
        sale_price_cents: int = PricingService.sale_price_cents(self.db, item.user_id)
        variables: dict[str, str] = EmailVariables.build_for_prospect(
            self.db, prospect, demo_link, video_link, video_thumbnail_url, sale_price_cents=sale_price_cents
        )

        email_service = EmailSendingService(self.db)
        subject: str = email_service.replace_variables(template.subject, variables)
        body_html: str = email_service.replace_variables(template.body_html, variables)

        # Behaviour-personalised follow-up (additive — keeps the rendered template
        # as the base and falls back to it if there is no behaviour data / LLM).
        if item.queue_type == "followup" and getattr(campaign, "behavior_personalized_followups", False):
            try:
                from services.behavior_service import behavior_service

                personalized = await behavior_service.draft_personalized_followup(
                    self.db,
                    item.user_id,
                    prospect,
                    base_subject=subject,
                    base_body_html=body_html,
                )
                subject = personalized.get("subject", subject) or subject
                body_html = personalized.get("body_html", body_html) or body_html
            except Exception as exc:
                logger.warning("[Queue] Behaviour personalisation failed for prospect %d: %s", prospect.id, exc)

        # Append the signature LAST so it survives the LLM personalisation above.
        from services.email_signatures import render_signature_html

        body_html += render_signature_html(self.db, template.signature_id, variables, user_id=item.user_id)

        result: dict = await email_service.send_via_user_identity(
            user_id=item.user_id,
            recipient_email=prospect.email,
            recipient_name=prospect.name,
            subject=subject,
            body_html=body_html,
            prospect_id=str(prospect.id),
            campaign_id=str(item.campaign_id),
            ab_variant=item.ab_variant,
        )

        item.email_log_id = result.get("email_log_id")
        item.status = _STATUS_SENT if result.get("success") else _STATUS_FAILED
        self.db.commit()

        # Schedule follow-ups after a successful J1 send.
        if item.queue_type == "initial" and result.get("success"):
            self._schedule_follow_ups(item)

    def _demo_link_outlives(self, j1_item: EmailQueue, template_id: int | None, scheduled_at: datetime) -> bool:
        """
        Whether a follow-up may be queued, i.e. its demo link will still be alive.

        A demo site dies ``DEMO_SITE_TTL_DAYS`` after its demo link is **first emailed**
        to the prospect (``demo_link_sent_at``). Before that send the site stays live
        so batches can be generated ahead of a slow outreach cadence.

        The refusal is recorded as a ``skipped`` queue row so the campaign page shows
        why the sequence stopped, instead of the follow-up silently never existing.

        Args:
            j1_item: The J1 whose follow-up is being scheduled.
            template_id: Template of the follow-up step.
            scheduled_at: When that follow-up would leave.

        Returns:
            True when the follow-up can be queued.
        """
        template: EmailTemplate | None = self.db.get(EmailTemplate, template_id) if template_id else None
        if not self._template_uses_demo_link(template):
            return True

        site: DemoSite | None = self._active_demo_for_prospect(j1_item.prospect_id, j1_item.user_id)
        expires_at: datetime | None = site.expires_at if site else None
        if expires_at is not None and expires_at.tzinfo is not None:
            expires_at = expires_at.replace(tzinfo=None)
        if expires_at is not None and expires_at > scheduled_at:
            return True

        logger.warning(
            "[Queue] Follow-up skipped for prospect %d — demo site expires %s, before the follow-up on %s",
            j1_item.prospect_id,
            expires_at.isoformat() if expires_at else "never (no active site)",
            scheduled_at.isoformat(),
        )
        self.db.add(
            EmailQueue(
                user_id=j1_item.user_id,
                campaign_id=j1_item.campaign_id,
                prospect_id=j1_item.prospect_id,
                template_id=template_id,
                email_account_id=None,
                queue_type="followup",
                ab_variant=j1_item.ab_variant,
                follow_up_index=j1_item.follow_up_index + 1,
                scheduled_at=scheduled_at,
                status=_STATUS_SKIPPED,
                skip_reason="Site démo expiré avant la relance",
            )
        )
        self.db.commit()
        return False

    def _schedule_follow_ups(self, j1_item: EmailQueue) -> None:
        """
        Create EmailQueue rows for all follow-up steps after a J1 success.

        Uses ``campaign_follow_ups`` rows when they exist; falls back to the
        legacy ``follow_up_template_id`` / ``follow_up_delay_days`` fields.

        Args:
            j1_item: The just-sent J1 queue item.
        """
        campaign: Campaign = j1_item.campaign

        # Prefer the new multi-step follow-up table.
        follow_ups: list[CampaignFollowUp] = (
            self.db.execute(
                select(CampaignFollowUp)
                .where(CampaignFollowUp.campaign_id == campaign.id)
                .order_by(CampaignFollowUp.position.asc())
            )
            .scalars()
            .all()
        )

        from services.send_policy_service import send_policy_service

        resolved = send_policy_service.resolve(self.db, campaign.user_id)
        sent_at: datetime = _utcnow()

        if not follow_ups:
            # Legacy fallback: single follow-up fields on the campaign.
            if campaign.follow_up_template_id:
                follow_up_at = send_policy_service.follow_up_slot(
                    resolved, sent_at, campaign.follow_up_delay_days or None
                )
                if not self._demo_link_outlives(j1_item, campaign.follow_up_template_id, follow_up_at):
                    return
                self.db.add(
                    EmailQueue(
                        user_id=j1_item.user_id,
                        campaign_id=j1_item.campaign_id,
                        prospect_id=j1_item.prospect_id,
                        template_id=campaign.follow_up_template_id,
                        email_account_id=None,
                        queue_type="followup",
                        ab_variant=j1_item.ab_variant,
                        follow_up_index=1,
                        scheduled_at=follow_up_at,
                        status=_STATUS_PENDING,
                    )
                )
                self.db.commit()
            return

        # Each step waits its own delay, counted in sending days from the J1 send.
        elapsed_days: int = 0
        for step in follow_ups:
            elapsed_days += max(1, step.delay_days)
            step_at: datetime = send_policy_service.follow_up_slot(resolved, sent_at, elapsed_days)
            if not self._demo_link_outlives(j1_item, step.template_id, step_at):
                break
            self.db.add(
                EmailQueue(
                    user_id=j1_item.user_id,
                    campaign_id=j1_item.campaign_id,
                    prospect_id=j1_item.prospect_id,
                    template_id=step.template_id,
                    email_account_id=None,
                    queue_type="followup",
                    ab_variant=j1_item.ab_variant,
                    follow_up_index=step.position,
                    scheduled_at=step_at,
                    status=_STATUS_PENDING,
                )
            )
        self.db.commit()
        logger.info(
            "[Queue] Scheduled %d follow-up(s) for prospect %d",
            len(follow_ups),
            j1_item.prospect_id,
        )

    async def send_followup_now(
        self,
        campaign: Campaign,
        prospect_id: int,
        template_id: int,
    ) -> dict:
        """
        Immediately dispatch a follow-up email for a specific prospect,
        bypassing the scheduled queue.  Sends via the user's active identity
        (Resend or Gmail).

        Args:
            campaign:    The parent campaign.
            prospect_id: Target prospect ID.
            template_id: Template to use.

        Returns:
            Result dict from ``EmailSendingService.send_via_user_identity``.
        """
        prospect: ProspectDB | None = self.db.get(ProspectDB, prospect_id)
        template: EmailTemplate | None = self.db.get(EmailTemplate, template_id)

        if not prospect or not prospect.email:
            return {"success": False, "error": "Prospect introuvable ou sans email"}
        if not template:
            return {"success": False, "error": "Template introuvable"}

        video_link, video_thumbnail_url = "", ""
        if self._template_uses_video(template) and campaign.include_video:
            video_link, video_thumbnail_url = self._video_for_prospect(prospect_id, campaign.user_id, None)
        variables: dict[str, str] = EmailVariables.build_for_prospect(
            self.db,
            prospect,
            self._demo_link_for_prospect(prospect_id, campaign.user_id, None),
            video_link,
            video_thumbnail_url,
            sale_price_cents=PricingService.sale_price_cents(self.db, campaign.user_id),
        )

        email_service = EmailSendingService(self.db)
        subject = email_service.replace_variables(template.subject, variables)
        body_html = email_service.replace_variables(template.body_html, variables)

        from services.email_signatures import render_signature_html

        body_html += render_signature_html(self.db, template.signature_id, variables, user_id=campaign.user_id)

        return await email_service.send_via_user_identity(
            user_id=campaign.user_id,
            recipient_email=prospect.email,
            recipient_name=prospect.name,
            subject=subject,
            body_html=body_html,
            prospect_id=str(prospect_id),
            campaign_id=str(campaign.id),
        )

    def cancel_campaign_queue(self, campaign_id: int) -> int:
        """
        Cancel all pending items for a campaign (pause / cancel).

        Returns:
            Number of items cancelled.
        """
        items: list[EmailQueue] = (
            self.db.execute(
                select(EmailQueue).where(
                    EmailQueue.campaign_id == campaign_id,
                    EmailQueue.status == _STATUS_PENDING,
                )
            )
            .scalars()
            .all()
        )

        for item in items:
            item.status = _STATUS_SKIPPED
        self.db.commit()
        logger.info("[Queue] Cancelled %d pending items for campaign %d", len(items), campaign_id)
        return len(items)

    def get_pending_count(self, campaign_id: int) -> int:
        """Return the number of pending items in the queue for a campaign."""
        return (
            self.db.execute(
                select(func.count()).where(
                    EmailQueue.campaign_id == campaign_id,
                    EmailQueue.status == _STATUS_PENDING,
                )
            ).scalar()
            or 0
        )

    def next_send_at_by_campaign(self, campaign_ids: list[int]) -> dict[int, datetime]:
        """
        Return the earliest still-pending send time per campaign.

        One grouped query for every id, so the campaigns list can show a
        « prochain envoi » without an N+1.

        Args:
            campaign_ids: Campaigns to look up.

        Returns:
            Mapping of campaign id → earliest pending ``scheduled_at``. Campaigns
            with no pending item are absent from the map.
        """
        if not campaign_ids:
            return {}
        rows = self.db.execute(
            select(EmailQueue.campaign_id, func.min(EmailQueue.scheduled_at))
            .where(
                EmailQueue.campaign_id.in_(campaign_ids),
                EmailQueue.status == _STATUS_PENDING,
            )
            .group_by(EmailQueue.campaign_id)
        ).all()
        return {campaign_id: scheduled_at for campaign_id, scheduled_at in rows if scheduled_at is not None}

    def count_upcoming_sends(self, user_id: int, *, days: int = 7) -> int:
        """
        Count a user's pending sends scheduled within the next ``days`` days.

        Args:
            user_id: Owner of the queue items.
            days:    Size of the forward window (default 7).

        Returns:
            The number of pending items scheduled in ``[now, now + days)``.
        """
        now = _utcnow()
        return (
            self.db.execute(
                select(func.count()).where(
                    EmailQueue.user_id == user_id,
                    EmailQueue.status == _STATUS_PENDING,
                    EmailQueue.scheduled_at >= now,
                    EmailQueue.scheduled_at < now + timedelta(days=days),
                )
            ).scalar()
            or 0
        )

    def get_queue_items(
        self,
        campaign_id: int,
        *,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[EmailQueue]:
        """Return queue items ordered by ``scheduled_at``."""
        stmt = select(EmailQueue).where(EmailQueue.campaign_id == campaign_id)
        if status is not None:
            stmt = stmt.where(EmailQueue.status == status)
        return self.db.execute(stmt.order_by(EmailQueue.scheduled_at.asc()).limit(limit).offset(offset)).scalars().all()

    def _active_demos_by_prospect(self, prospect_ids: list[int], user_id: int) -> dict[int, DemoSite]:
        """
        Map each prospect to its latest ACTIVE demo site in a single query (no N+1).

        Args:
            prospect_ids: Prospects to resolve a site for.
            user_id:      Owner of the demo sites.

        Returns:
            ``prospect_id → DemoSite`` for prospects that have an active site.
        """
        unique_ids: list[int] = list({pid for pid in prospect_ids if pid is not None})
        if not unique_ids:
            return {}
        rows: list[DemoSite] = (
            self.db.execute(
                select(DemoSite)
                .where(
                    DemoSite.prospect_id.in_(unique_ids),
                    DemoSite.user_id == user_id,
                    DemoSite.status == DemoSiteStatus.ACTIVE.value,
                )
                .order_by(DemoSite.created_at.desc())
            )
            .scalars()
            .all()
        )
        by_prospect: dict[int, DemoSite] = {}
        for site in rows:
            # Rows come newest-first, so the first seen per prospect is the latest active site.
            if site.prospect_id is not None and site.prospect_id not in by_prospect:
                by_prospect[site.prospect_id] = site
        return by_prospect

    def build_forecast(self, user_id: int, start: datetime, days: int) -> list[dict[str, object]]:
        """
        Build the week-ahead send forecast across all of a user's campaigns.

        Returns every queue item scheduled in ``[start, start + days)`` that is still pending,
        plus items that were skipped for a stated reason (e.g. a demo site that expired before a
        follow-up) so the operator sees why a send will not go out. Each item carries the link the
        email will contain — today the prospect's active demo URL, with the A/B variant appended
        for tracking, exactly as the prospect receives it — and the demo site's review sign-off.

        Args:
            user_id: Owner of the queue.
            start:   Window start (naive UTC).
            days:    Window width in days.

        Returns:
            Forecast rows ordered by ``scheduled_at``, one dict per queue item.
        """
        end: datetime = start + timedelta(days=days)
        items: list[EmailQueue] = (
            self.db.execute(
                select(EmailQueue)
                .options(joinedload(EmailQueue.prospect), joinedload(EmailQueue.campaign))
                .where(
                    EmailQueue.user_id == user_id,
                    EmailQueue.scheduled_at >= start,
                    EmailQueue.scheduled_at < end,
                    or_(
                        EmailQueue.status == _STATUS_PENDING,
                        and_(EmailQueue.status == _STATUS_SKIPPED, EmailQueue.skip_reason.isnot(None)),
                    ),
                )
                .order_by(EmailQueue.scheduled_at.asc())
            )
            .scalars()
            .all()
        )

        demos: dict[int, DemoSite] = self._active_demos_by_prospect([i.prospect_id for i in items], user_id)

        forecast: list[dict[str, object]] = []
        for item in items:
            site: DemoSite | None = demos.get(item.prospect_id)
            link: str = ""
            if site and site.demo_url:
                link = site.demo_url
                if item.ab_variant:
                    link = f"{link}{'&' if '?' in link else '?'}v={item.ab_variant}"
            prospect = item.prospect
            campaign = item.campaign
            forecast.append(
                {
                    "queue_id": item.id,
                    "scheduled_at": item.scheduled_at.isoformat(),
                    "campaign_id": item.campaign_id,
                    "campaign_name": campaign.name if campaign else "",
                    "prospect_id": item.prospect_id,
                    "prospect_name": prospect.name if prospect else None,
                    "prospect_email": prospect.email if prospect else None,
                    "prospect_city": prospect.city if prospect else None,
                    "prospect_category": prospect.category if prospect else "",
                    "queue_type": item.queue_type,
                    "follow_up_index": item.follow_up_index,
                    "ab_variant": item.ab_variant,
                    "status": item.status,
                    "skip_reason": item.skip_reason,
                    "link": link or None,
                    "link_kind": "website" if link else None,
                    "demo_site_id": site.id if site else None,
                    "site_reviewed_at": site.site_reviewed_at.isoformat() if site and site.site_reviewed_at else None,
                }
            )
        return forecast
