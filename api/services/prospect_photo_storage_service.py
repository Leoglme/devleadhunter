"""Rehost a prospect's enrichment photos onto permanent R2 storage.

Facebook photos are served from ``fbcdn.net`` on **signed URLs that expire within days**, so a demo
site generated a few days after the scrape would fetch a dead link. The desktop scraper captures those
photos as base64 ``data:`` URIs while the links are still fresh (residential IP); this service turns
those data URIs into permanent R2 objects, so the enrichment record stores light, never-expiring URLs
that every later generation (and re-generation) can reuse.

Non-``data:`` URLs (a Google photo, an already-rehosted R2 URL) are passed through untouched: only the
transient captured bytes need a durable home. Everything is best-effort — a rehost failure returns the
original value so enrichment never breaks over a storage hiccup.
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import logging
import re

from services.r2_storage_service import r2_storage

logger = logging.getLogger(__name__)

# Guard against a pathological payload — the scraper already caps a single photo at 3.5 MB.
_MAX_PHOTO_BYTES = 8 * 1024 * 1024
# Bound the concurrent uploads so a large gallery never opens dozens of R2 connections at once.
_UPLOAD_CONCURRENCY = 4

_DATA_URI_RE = re.compile(r"^data:(image/[a-zA-Z0-9.+-]+);base64,(.+)$", re.DOTALL)
# Explicit extension per image MIME — ``mimetypes.guess_extension`` is platform-dependent
# (it can return ``.jpe`` for JPEG), and the key extension is user-visible in the storage page.
_EXTENSION_BY_MIME: dict[str, str] = {
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
    "image/avif": ".avif",
}


class ProspectPhotoStorageService:
    """Moves captured enrichment photos to R2 and cleans them up when a prospect is deleted."""

    @staticmethod
    def _decode_data_uri(value: str) -> tuple[bytes, str, str] | None:
        """Decode a base64 image ``data:`` URI into its bytes, MIME type and file extension.

        Args:
            value: A candidate photo string (any non-data-URI returns None).

        Returns:
            A ``(bytes, content_type, extension)`` tuple, or None when the value is not a decodable
            base64 image data URI or exceeds the size guard.
        """
        match = _DATA_URI_RE.match(value.strip()) if isinstance(value, str) else None
        if not match:
            return None
        content_type = match.group(1).lower()
        try:
            data = base64.b64decode(match.group(2), validate=False)
        except (ValueError, TypeError):
            return None
        if not data or len(data) > _MAX_PHOTO_BYTES:
            return None
        extension = _EXTENSION_BY_MIME.get(content_type, ".jpg")
        return data, content_type, extension

    async def rehost_one(self, prospect_id: int, photo: str) -> str:
        """Rehost a single photo to R2 when it is a captured data URI, else return it unchanged.

        Args:
            prospect_id: Owner prospect — folders the object and scopes later cleanup.
            photo: A photo value from the enrichment (data URI, http(s) URL, or already an R2 URL).

        Returns:
            The permanent R2 URL when the photo was a rehostable data URI, otherwise the original value
            (also on any storage failure — rehosting never breaks enrichment).
        """
        decoded = self._decode_data_uri(photo)
        if decoded is None or not r2_storage.is_configured():
            return photo
        data, content_type, extension = decoded
        digest = hashlib.sha1(data).hexdigest()[:16]
        key = r2_storage.prospect_photo_key(prospect_id, digest, extension)
        try:
            return await r2_storage.upload_bytes_async(key, data, content_type)
        except Exception as exc:  # storage hiccup must never fail the enrichment
            logger.warning("Prospect photo rehost failed for prospect_id=%s (%s): %s", prospect_id, key, exc)
            return photo

    async def rehost_photos(self, prospect_id: int, photos: list[str]) -> list[str]:
        """Rehost every captured data-URI photo of a prospect to R2, preserving order.

        Args:
            prospect_id: Owner prospect.
            photos: The enrichment photo list (mixed data URIs / URLs).

        Returns:
            The same list with each rehostable data URI replaced by its permanent R2 URL.
        """
        if not photos:
            return photos
        semaphore = asyncio.Semaphore(_UPLOAD_CONCURRENCY)

        async def _bounded(photo: str) -> str:
            async with semaphore:
                return await self.rehost_one(prospect_id, photo)

        return list(await asyncio.gather(*(_bounded(photo) for photo in photos)))

    async def delete_for_prospect(self, prospect_id: int) -> int:
        """Delete every R2 photo owned by a prospect (called when the prospect is deleted).

        Args:
            prospect_id: Prospect whose photos must be purged.

        Returns:
            The number of objects deleted (0 when R2 is unconfigured or the prospect had none).
        """
        if not r2_storage.is_configured():
            return 0
        prefix = r2_storage.prospect_photos_prefix(prospect_id)
        try:
            objects = await asyncio.to_thread(r2_storage.list_objects, prefix)
            keys = [entry["key"] for entry in objects]
            if keys:
                await asyncio.to_thread(r2_storage.delete_many, keys)
            return len(keys)
        except Exception as exc:  # cleanup is best-effort — never block a prospect deletion
            logger.warning("Prospect photo cleanup failed for prospect_id=%s: %s", prospect_id, exc)
            return 0


prospect_photo_storage = ProspectPhotoStorageService()
