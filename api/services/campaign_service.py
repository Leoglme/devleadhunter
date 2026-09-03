"""
Campaign service for managing email campaigns.
"""

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

from models.campaign import Campaign, CampaignStatus
from models.email_log import EmailLog
from models.prospect_db import ProspectDB
from schemas.campaign import (
    CampaignCreate,
    CampaignStats,
    CampaignUpdate,
    CampaignVariantStats,
)
from services.activity_log_service import CATEGORY_CAMPAIGN, STATUS_INFO, activity_log_service
from services.email_log_stats import aggregate_email_log_counts, compute_engagement_rates

# Campaign status → French verb for the activity feed.
_CAMPAIGN_STATUS_VERBS: dict[str, str] = {
    CampaignStatus.ACTIVE.value: "activée",
    CampaignStatus.PAUSED.value: "mise en pause",
    CampaignStatus.COMPLETED.value: "terminée",
    CampaignStatus.CANCELLED.value: "annulée",
    CampaignStatus.DRAFT.value: "repassée en brouillon",
}


class CampaignService:
    """Service for campaign management."""

    def create_campaign(self, db: Session, user_id: int, campaign_data: CampaignCreate) -> Campaign:
        """
        Create a new campaign.

        Args:
            db: Database session
            user_id: ID of the user creating the campaign
            campaign_data: Campaign creation data

        Returns:
            Created campaign
        """
        # Create campaign
        campaign = Campaign(
            user_id=user_id,
            name=campaign_data.name,
            description=campaign_data.description,
            status=campaign_data.status or CampaignStatus.DRAFT.value,
            template_id=campaign_data.template_id,
            ab_template_id_b=campaign_data.ab_template_id_b,
            send_delay_minutes=campaign_data.send_delay_minutes,
            max_emails_per_day=campaign_data.max_emails_per_day,
        )

        # Add prospects if provided
        if campaign_data.prospect_ids:
            prospects = (
                db.query(ProspectDB)
                .filter(ProspectDB.id.in_(campaign_data.prospect_ids), ProspectDB.user_id == user_id)
                .all()
            )
            campaign.prospects = prospects

        db.add(campaign)
        db.commit()
        db.refresh(campaign)

        activity_log_service.record(
            category=CATEGORY_CAMPAIGN,
            action="campaign_created",
            status=STATUS_INFO,
            title=f"Campagne créée · {campaign.name}",
            user_id=user_id,
            entity_type="campaign",
            entity_id=campaign.id,
        )

        return campaign

    def get_campaign(self, db: Session, campaign_id: int, user_id: int) -> Campaign | None:
        """
        Get a campaign by ID.

        Args:
            db: Database session
            campaign_id: Campaign ID
            user_id: ID of the user requesting the campaign

        Returns:
            Campaign if found and owned by user, None otherwise
        """
        campaign = (
            db.query(Campaign)
            .options(
                joinedload(Campaign.prospects),
                joinedload(Campaign.follow_ups),
            )
            .filter(Campaign.id == campaign_id, Campaign.user_id == user_id)
            .first()
        )

        return campaign

    def list_campaigns(
        self, db: Session, user_id: int, skip: int = 0, limit: int = 100, status: str | None = None
    ) -> tuple[list[Campaign], int]:
        """
        List campaigns for a user.

        Args:
            db: Database session
            user_id: ID of the user
            skip: Number of records to skip
            limit: Maximum number of records to return
            status: Filter by status (optional)

        Returns:
            Tuple of (campaigns list, total count)
        """
        query = db.query(Campaign).filter(Campaign.user_id == user_id)

        if status:
            query = query.filter(Campaign.status == status)

        total = query.count()
        campaigns = query.order_by(Campaign.created_at.desc()).offset(skip).limit(limit).all()

        return campaigns, total

    def update_campaign(
        self, db: Session, campaign_id: int, user_id: int, campaign_data: CampaignUpdate
    ) -> Campaign | None:
        """
        Update a campaign.

        Args:
            db: Database session
            campaign_id: Campaign ID
            user_id: ID of the user updating the campaign
            campaign_data: Campaign update data

        Returns:
            Updated campaign if found and owned by user, None otherwise
        """
        campaign = self.get_campaign(db, campaign_id, user_id)
        if not campaign:
            return None

        # Update fields
        previous_status = campaign.status
        update_data = campaign_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(campaign, field, value)

        db.commit()
        db.refresh(campaign)

        if campaign.status != previous_status:
            verb = _CAMPAIGN_STATUS_VERBS.get(campaign.status, campaign.status)
            activity_log_service.record(
                category=CATEGORY_CAMPAIGN,
                action="campaign_status_changed",
                status=STATUS_INFO,
                title=f"Campagne {verb} · {campaign.name}",
                user_id=user_id,
                entity_type="campaign",
                entity_id=campaign.id,
            )

        return campaign

    def delete_campaign(self, db: Session, campaign_id: int, user_id: int) -> bool:
        """
        Delete a campaign.

        Args:
            db: Database session
            campaign_id: Campaign ID
            user_id: ID of the user deleting the campaign

        Returns:
            True if deleted, False if not found
        """
        campaign = self.get_campaign(db, campaign_id, user_id)
        if not campaign:
            return False

        campaign_name = campaign.name
        deleted_id = campaign.id
        db.delete(campaign)
        db.commit()

        activity_log_service.record(
            category=CATEGORY_CAMPAIGN,
            action="campaign_deleted",
            status=STATUS_INFO,
            title=f"Campagne supprimée · {campaign_name}",
            user_id=user_id,
            entity_type="campaign",
            entity_id=deleted_id,
        )

        return True

    def add_prospects_to_campaign(
        self, db: Session, campaign_id: int, user_id: int, prospect_ids: list[int]
    ) -> Campaign | None:
        """
        Add prospects to a campaign.

        Args:
            db: Database session
            campaign_id: Campaign ID
            user_id: ID of the user
            prospect_ids: List of prospect IDs to add

        Returns:
            Updated campaign if found, None otherwise

        Raises:
            HTTPException: If prospects not found or not owned by user
        """
        campaign = self.get_campaign(db, campaign_id, user_id)
        if not campaign:
            return None

        # Get prospects
        prospects = db.query(ProspectDB).filter(ProspectDB.id.in_(prospect_ids), ProspectDB.user_id == user_id).all()

        if len(prospects) != len(prospect_ids):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Some prospects not found or not owned by user"
            )

        # Get existing prospect IDs
        existing_ids = {p.id for p in campaign.prospects}

        # Add only new prospects
        for prospect in prospects:
            if prospect.id not in existing_ids:
                campaign.prospects.append(prospect)

        db.commit()
        db.refresh(campaign)

        return campaign

    def remove_prospect_from_campaign(
        self, db: Session, campaign_id: int, user_id: int, prospect_id: int
    ) -> Campaign | None:
        """
        Remove a prospect from a campaign.

        Args:
            db: Database session
            campaign_id: Campaign ID
            user_id: ID of the user
            prospect_id: Prospect ID to remove

        Returns:
            Updated campaign if found, None otherwise
        """
        campaign = self.get_campaign(db, campaign_id, user_id)
        if not campaign:
            return None

        # Find and remove prospect
        for i, prospect in enumerate(campaign.prospects):
            if prospect.id == prospect_id:
                campaign.prospects.pop(i)
                break

        db.commit()
        db.refresh(campaign)

        return campaign

    def get_campaign_stats(self, db: Session, campaign_id: int, user_id: int) -> CampaignStats | None:
        """
        Get statistics for a campaign.

        Args:
            db: Database session
            campaign_id: Campaign ID
            user_id: ID of the user

        Returns:
            Campaign statistics if campaign found, None otherwise
        """
        campaign = self.get_campaign(db, campaign_id, user_id)
        if not campaign:
            return None

        # Count prospects
        total_prospects = len(campaign.prospects)

        counts = aggregate_email_log_counts(
            db,
            EmailLog.campaign_id == campaign_id,
            EmailLog.user_id == user_id,
        )
        rates = compute_engagement_rates(counts)

        # A/B breakdown (only when campaign has a B variant)
        ab_stats: list[CampaignVariantStats] | None = None
        if campaign.ab_template_id_b:
            ab_stats = []
            for variant in ("A", "B"):
                variant_counts = aggregate_email_log_counts(
                    db,
                    EmailLog.campaign_id == campaign_id,
                    EmailLog.user_id == user_id,
                    EmailLog.ab_variant == variant,
                )
                variant_rates = compute_engagement_rates(variant_counts)
                ab_stats.append(
                    CampaignVariantStats(
                        variant=variant,
                        sent=variant_counts.sent,
                        delivered=variant_counts.delivered,
                        opened=variant_counts.opened,
                        clicked=variant_counts.clicked,
                        replied=variant_counts.replied,
                        open_rate=variant_rates.open_rate,
                        click_rate=variant_rates.click_rate,
                        reply_rate=variant_rates.reply_rate,
                    )
                )

        return CampaignStats(
            campaign_id=campaign_id,
            total_prospects=total_prospects,
            total_emails_sent=counts.sent,
            emails_delivered=counts.delivered,
            emails_opened=counts.opened,
            emails_clicked=counts.clicked,
            emails_replied=counts.replied,
            emails_bounced=counts.bounced,
            emails_failed=counts.failed,
            delivery_rate=rates.delivery_rate,
            open_rate=rates.open_rate,
            click_rate=rates.click_rate,
            reply_rate=rates.reply_rate,
            ab_stats=ab_stats,
        )


# Singleton instance
campaign_service = CampaignService()
