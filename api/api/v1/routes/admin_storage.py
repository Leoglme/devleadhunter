"""
Admin routes to inspect and manage the Cloudflare R2 bucket.

Backs the dashboard « Stockage » page: list every object with its expiry
countdown, play/copy its public URL, delete it, purge expired ones, spot
R2 ↔ DB inconsistencies, and (in dev only) pull the prod bucket down.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from core.config import settings
from core.database import get_db
from models.demo_site import DemoSite
from models.prospect_db import ProspectDB
from models.prospect_enrichment import ProspectEnrichment
from models.user import User
from services.auth_service import require_admin
from services.r2_storage_service import r2_storage

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/storage", tags=["admin-storage"])

# Durée de vie des livrables liés à une démo (aligné sur le TTL des démos).
OBJECT_TTL_DAYS = 14


class StorageObject(BaseModel):
    """One object of the bucket, enriched with business context."""

    key: str
    kind: str  # website_video | website_thumbnail | presenter | support | prospect_photo | other
    size: int
    last_modified: datetime | None = None
    url: str
    slug: str | None = None
    prospect_name: str | None = None
    expires_in_days: int | None = None
    is_expired: bool = False


class StorageListResponse(BaseModel):
    """Bucket listing + totals."""

    bucket: str
    public_base_url: str
    items: list[StorageObject]
    total: int
    total_size: int


class StorageHealthResponse(BaseModel):
    """R2 ↔ database consistency report."""

    orphan_objects: list[str]
    missing_objects: list[str]
    expired_objects: list[str]


class StorageActionResponse(BaseModel):
    """Result of a mutating action."""

    deleted: int = 0
    copied: int = 0
    unchanged: int = 0
    message: str = ""


class DeleteObjectsRequest(BaseModel):
    """Payload for POST /admin/storage/delete-objects — the object keys to remove in one call."""

    keys: list[str]


def _classify(key: str) -> str:
    """Map an object key to a human category."""
    if key.startswith(r2_storage.VIDEOS_WEBSITES_PREFIX):
        return "website_video"
    if key.startswith(r2_storage.IMAGES_WEBSITES_PREFIX):
        return "website_thumbnail"
    if key.startswith(r2_storage.VIDEOS_PRESENTER_PREFIX):
        return "presenter"
    if key.startswith(r2_storage.IMAGES_SUPPORT_PREFIX):
        return "support"
    if key.startswith(r2_storage.IMAGES_PROSPECTS_PREFIX):
        return "prospect_photo"
    return "other"


def _slug_from_key(key: str) -> str | None:
    """Extract the demo slug carried by a website video/thumbnail key."""
    if _classify(key) not in ("website_video", "website_thumbnail"):
        return None
    return key.rsplit("/", 1)[-1].rsplit(".", 1)[0] or None


def _prospect_id_from_key(key: str) -> int | None:
    """Extract the prospect id carried by a rehosted photo key (``images/prospects/{id}/{hash}.jpg``)."""
    if not key.startswith(r2_storage.IMAGES_PROSPECTS_PREFIX):
        return None
    parts = key.split("/")
    return int(parts[2]) if len(parts) >= 4 and parts[2].isdigit() else None


def _referenced_prospect_photo_keys(db: Session) -> set[str]:
    """Collect every ``images/prospects/`` object key still referenced by an enrichment record.

    Compared by KEY (not full URL) so it holds regardless of the dev/prod public base URL. A prospect's
    ``photos`` list and its ``logo_url`` are the only places a rehosted photo is referenced.
    """
    prefix = r2_storage.IMAGES_PROSPECTS_PREFIX
    keys: set[str] = set()
    for photos, logo_url in db.query(ProspectEnrichment.photos, ProspectEnrichment.logo_url).all():
        for value in [*(photos or []), logo_url]:
            if not isinstance(value, str):
                continue
            index = value.find(prefix)
            if index != -1:
                keys.add(value[index:])
    return keys


def _ensure_configured() -> None:
    """Fail with a readable 503 when R2 is not configured."""
    if not r2_storage.is_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Stockage R2 non configuré (voir R2_* dans api/.env).",
        )


@router.get("", response_model=StorageListResponse)
async def list_storage_objects(
    prefix: str = "",
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> StorageListResponse:
    """
    List the bucket objects, newest first, with expiry and prospect context.

    Args:
        prefix: Optional key prefix filter (e.g. ``videos/websites/``).

    Returns:
        The bucket listing.
    """
    _ensure_configured()
    raw = await _list_async(prefix)

    slugs = {s for s in (_slug_from_key(item["key"]) for item in raw) if s}
    names_by_slug: dict[str, str] = {}
    if slugs:
        rows = (
            db.query(DemoSite.slug, ProspectDB.name)
            .outerjoin(ProspectDB, ProspectDB.id == DemoSite.prospect_id)
            .filter(DemoSite.slug.in_(slugs))
            .all()
        )
        names_by_slug = {slug: name for slug, name in rows if name}

    prospect_ids = {pid for pid in (_prospect_id_from_key(item["key"]) for item in raw) if pid}
    names_by_prospect_id: dict[int, str] = {}
    if prospect_ids:
        prospect_rows = db.query(ProspectDB.id, ProspectDB.name).filter(ProspectDB.id.in_(prospect_ids)).all()
        names_by_prospect_id = {pid: name for pid, name in prospect_rows if name}

    now = datetime.now(UTC)
    items: list[StorageObject] = []
    for entry in raw:
        key = entry["key"]
        kind = _classify(key)
        slug = _slug_from_key(key)
        expires_in: int | None = None
        is_expired = False
        # Seuls les livrables liés à une démo expirent ; le clip presenter, les pièces jointes support
        # et les photos de prospect (source durable des sites) sont permanents.
        if kind in ("website_video", "website_thumbnail") and entry["last_modified"]:
            deadline = entry["last_modified"] + timedelta(days=OBJECT_TTL_DAYS)
            expires_in = max(0, (deadline - now).days)
            is_expired = deadline <= now
        prospect_name = names_by_slug.get(slug or "")
        if kind == "prospect_photo":
            prospect_name = names_by_prospect_id.get(_prospect_id_from_key(key) or 0)
        items.append(
            StorageObject(
                key=key,
                kind=kind,
                size=entry["size"],
                last_modified=entry["last_modified"],
                url=r2_storage.public_url(key),
                slug=slug,
                prospect_name=prospect_name,
                expires_in_days=expires_in,
                is_expired=is_expired,
            )
        )

    items.sort(key=lambda o: o.last_modified or datetime.min.replace(tzinfo=UTC), reverse=True)
    return StorageListResponse(
        bucket=r2_storage.bucket_name(),
        public_base_url=settings.r2_public_base_url or "",
        items=items,
        total=len(items),
        total_size=sum(o.size for o in items),
    )


@router.get("/health", response_model=StorageHealthResponse)
async def storage_health(
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> StorageHealthResponse:
    """
    Report R2 ↔ DB inconsistencies — the proof that the 14-day cleanup works.

    Returns:
        Orphan objects, missing objects and expired leftovers.
    """
    _ensure_configured()
    from enums.demo_video_status import DemoVideoStatus

    objects = await _list_async(r2_storage.VIDEOS_WEBSITES_PREFIX)
    keys = {item["key"] for item in objects}

    ready_slugs = {
        slug
        for (slug,) in db.query(DemoSite.slug).filter(DemoSite.video_status == DemoVideoStatus.READY.value).all()
        if slug
    }
    expected = {r2_storage.website_video_key(slug) for slug in ready_slugs}

    now = datetime.now(UTC)
    expired = [
        item["key"]
        for item in objects
        if item["last_modified"] and item["last_modified"] + timedelta(days=OBJECT_TTL_DAYS) <= now
    ]

    return StorageHealthResponse(
        orphan_objects=sorted(keys - expected),
        missing_objects=sorted(expected - keys),
        expired_objects=sorted(expired),
    )


@router.delete("/object", response_model=StorageActionResponse)
async def delete_storage_object(
    key: str,
    _admin: User = Depends(require_admin),
) -> StorageActionResponse:
    """
    Delete one object from the bucket.

    Args:
        key: Full object key (query param so slashes need no escaping).

    Returns:
        How many objects were removed.
    """
    _ensure_configured()
    if not key.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Clé manquante.")
    await r2_storage.delete_async(key)
    return StorageActionResponse(deleted=1, message=f"{key} supprimé.")


@router.post("/delete-objects", response_model=StorageActionResponse)
async def delete_storage_objects(
    payload: DeleteObjectsRequest,
    _admin: User = Depends(require_admin),
) -> StorageActionResponse:
    """
    Delete several objects at once (the storage page's multi-selection).

    Args:
        payload: The object keys to remove; blank entries are ignored.

    Returns:
        How many objects were removed.
    """
    _ensure_configured()
    keys = [key for key in payload.keys if key.strip()]
    if not keys:
        return StorageActionResponse(deleted=0, message="Aucun fichier sélectionné.")
    import asyncio

    await asyncio.to_thread(r2_storage.delete_many, keys)
    return StorageActionResponse(deleted=len(keys), message=f"{len(keys)} fichier(s) supprimé(s).")


@router.post("/purge-expired", response_model=StorageActionResponse)
async def purge_expired_objects(
    _admin: User = Depends(require_admin),
) -> StorageActionResponse:
    """
    Delete every demo deliverable older than the TTL (video + thumbnail).

    Returns:
        How many objects were removed.
    """
    _ensure_configured()
    now = datetime.now(UTC)
    stale: list[str] = []
    for prefix in (
        r2_storage.VIDEOS_WEBSITES_PREFIX,
        r2_storage.IMAGES_WEBSITES_PREFIX,
    ):
        for item in await _list_async(prefix):
            if item["last_modified"] and item["last_modified"] + timedelta(days=OBJECT_TTL_DAYS) <= now:
                stale.append(item["key"])

    if stale:
        import asyncio

        await asyncio.to_thread(r2_storage.delete_many, stale)
    return StorageActionResponse(deleted=len(stale), message=f"{len(stale)} objet(s) expiré(s) supprimé(s).")


@router.post("/purge-orphan-prospect-photos", response_model=StorageActionResponse)
async def purge_orphan_prospect_photos(
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> StorageActionResponse:
    """
    Delete rehosted prospect photos that no enrichment record references any more.

    Deleting a prospect removes its photos inline and a re-enrichment reuses content-hash keys, but a
    replaced photo or an interrupted delete can leave an object behind. This reconciles the bucket
    against the enrichment table: every ``images/prospects/`` object whose key is referenced by no
    enrichment (``photos`` or ``logo_url``) is removed.

    Returns:
        How many orphan objects were removed.
    """
    _ensure_configured()
    referenced = _referenced_prospect_photo_keys(db)
    objects = await _list_async(r2_storage.IMAGES_PROSPECTS_PREFIX)
    orphans = [item["key"] for item in objects if item["key"] not in referenced]
    if orphans:
        import asyncio

        await asyncio.to_thread(r2_storage.delete_many, orphans)
    return StorageActionResponse(deleted=len(orphans), message=f"{len(orphans)} photo(s) orpheline(s) supprimée(s).")


@router.post("/sync-from-prod", response_model=StorageActionResponse)
async def sync_from_prod(
    _admin: User = Depends(require_admin),
) -> StorageActionResponse:
    """
    Mirror the production bucket into the dev one — **development only**.

    Incremental by design: copies only what is missing (server-side CopyObject,
    nothing transits through the API), deletes what disappeared upstream, and
    leaves identical objects untouched.

    Returns:
        Copied / deleted / unchanged counts.

    Raises:
        HTTPException: 403 when called on a production instance.
    """
    _ensure_configured()
    if settings.is_production:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="La synchronisation n'est disponible qu'en développement.",
        )

    import asyncio

    source_bucket = r2_storage.prod_bucket_name()
    target_bucket = r2_storage.bucket_name()
    if source_bucket == target_bucket:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Les buckets dev et prod sont identiques : synchronisation annulée.",
        )

    source = {i["key"]: i for i in await asyncio.to_thread(r2_storage.list_objects, "", bucket=source_bucket)}
    target = {i["key"]: i for i in await asyncio.to_thread(r2_storage.list_objects, "")}

    to_copy = [key for key, item in source.items() if key not in target or target[key]["etag"] != item["etag"]]
    to_delete = [key for key in target if key not in source]

    for key in to_copy:
        await asyncio.to_thread(r2_storage.copy_from_bucket, source_bucket, key)
    if to_delete:
        await asyncio.to_thread(r2_storage.delete_many, to_delete)

    unchanged = len(source) - len(to_copy)
    logger.info("[Storage] sync prod->dev: %d copied, %d deleted", len(to_copy), len(to_delete))
    return StorageActionResponse(
        copied=len(to_copy),
        deleted=len(to_delete),
        unchanged=unchanged,
        message=f"{len(to_copy)} copié(s), {len(to_delete)} supprimé(s), {unchanged} inchangé(s).",
    )


async def _list_async(prefix: str) -> list[dict[str, Any]]:
    """Run the blocking listing in a worker thread."""
    import asyncio

    return await asyncio.to_thread(r2_storage.list_objects, prefix)
