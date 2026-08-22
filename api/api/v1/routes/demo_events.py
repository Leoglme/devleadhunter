"""
Public ingestion endpoint for live demo / video behavioural events.

The demo-host (a separate domain) beacons a prospect's key actions here so the
owner gets a real-time mobile push. Unauthenticated by design — the demo-host has
no user session; the slug resolves to its owning user. Unknown slugs are ignored.
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from core.database import get_db
from enums.demo_site_status import DemoSiteStatus
from models.demo_site import DemoSite
from schemas.notification import DemoEventIn
from services.notification_service import notification_service

router = APIRouter(prefix="/demo-events", tags=["demo-events"])


@router.post("", status_code=status.HTTP_204_NO_CONTENT)
async def ingest_demo_event(payload: DemoEventIn, db: Session = Depends(get_db)) -> None:
    """
    Receive a behavioural event from a live demo/video page and notify the owner.

    Args:
        payload: The beaconed event (slug + event name + optional context).
        db: Database session.
    """
    site = db.execute(
        select(DemoSite).where(
            DemoSite.slug == payload.demo_slug,
            DemoSite.status != DemoSiteStatus.DELETED.value,
        )
    ).scalar_one_or_none()
    if site is None:
        return
    await notification_service.notify_demo_event(
        db,
        user_id=site.user_id,
        prospect_id=site.prospect_id,
        event_name=payload.event,
        fallback_name=site.slug,
        label=payload.label,
        host=payload.host,
        seconds=payload.seconds,
        max_scroll=payload.max_scroll,
    )
