"""
Facebook page exclusions — remember the pages the match filter rejected.

A Facebook search only proves a candidate usable AFTER the desktop enrichment
has read the page (email present, website or not). Rejected pages land here so
the next discovery for the same user skips them instead of paying another
enrichment for a page already known to be unusable.
"""

from __future__ import annotations

import logging

from sqlalchemy import and_
from sqlalchemy.orm import Session

from models.facebook_exclusion import FacebookPageExclusion

logger = logging.getLogger(__name__)


class FacebookExclusionService:
    """CRUD around :class:`FacebookPageExclusion`, scoped per user."""

    def add(self, db: Session, user_id: int, page_url: str, reason: str) -> None:
        """Record *page_url* as unusable for *user_id* (idempotent).

        Args:
            db: Active database session.
            user_id: Owner of the searches to filter.
            page_url: Canonical Facebook page URL.
            reason: ``no_email`` or ``has_website``.
        """
        url = (page_url or "").strip()[:512]
        if not url:
            return
        if self.is_excluded(db, user_id, url):
            return
        db.add(FacebookPageExclusion(user_id=user_id, page_url=url, reason=reason))
        db.commit()
        logger.info("Facebook exclusion recorded for user %s (%s): %s", user_id, reason, url)

    def is_excluded(self, db: Session, user_id: int, page_url: str) -> bool:
        """Whether *page_url* was already rejected for *user_id*.

        Args:
            db: Active database session.
            user_id: Owner of the searches to filter.
            page_url: Canonical Facebook page URL.

        Returns:
            ``True`` when the page must be skipped at discovery.
        """
        url = (page_url or "").strip()[:512]
        if not url:
            return False
        return (
            db.query(FacebookPageExclusion.id)
            .filter(and_(FacebookPageExclusion.user_id == user_id, FacebookPageExclusion.page_url == url))
            .first()
            is not None
        )


facebook_exclusion_service = FacebookExclusionService()
