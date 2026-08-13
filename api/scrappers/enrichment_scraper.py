"""
Prospect enrichment scraper (Google Maps place details).

Deliberately separate from the prospect *search* scrapers: this runs only on
demand (enrichment button / before site generation), so discovery stays fast.
It reuses the shared nodriver infrastructure but never touches the search
scrapers' code paths.

The DOM selectors target Google Maps place panels and are best-effort: every
extraction step is isolated so a partial failure still returns whatever data
could be gathered. Selectors may need tuning over time against live Maps.
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field
from typing import Any

from scrappers import scrape_signals
from scrappers.google_scraper import GoogleScraper
from scrappers.nodriver_browser import NODRIVER_AVAILABLE, NodriverBrowser
from scrappers.nodriver_dom import NodriverDom
from scrappers.nodriver_executor import run_nodriver_task
from scrappers.osm_enrichment import enrich_from_osm
from scrappers.resilient_extract import parse_ld_json_blocks
from services.validation_service import validation_service

logger = logging.getLogger(__name__)


@dataclass
class EnrichmentData:
    """Structured rich data gathered for a prospect."""

    source: str = "google"
    logo_url: str | None = None
    rating: float | None = None
    reviews_count: int | None = None
    description: str | None = None
    website: str | None = None
    photos: list[str] = field(default_factory=list)
    reviews: list[dict[str, Any]] = field(default_factory=list)
    opening_hours: list[dict[str, str]] = field(default_factory=list)
    services: list[str] = field(default_factory=list)
    social_links: dict[str, str] = field(default_factory=dict)
    # Contact emails discovered while enriching (e.g. from the linked Facebook page) — folded into the
    # prospect's multi-email list. Usually empty from Google Maps, which rarely exposes an email.
    emails: list[str] = field(default_factory=list)
    # Identity of the Maps place the data was ACTUALLY read from — lets the
    # service reject a homonym's listing instead of silently absorbing it.
    # None on payloads from older desktop sidecars (identity check skipped).
    place_title: str | None = None
    place_city: str | None = None
    place_postal_code: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dict (matches the ProspectEnrichment columns)."""
        return {
            "source": self.source,
            "logo_url": self.logo_url,
            "rating": self.rating,
            "reviews_count": self.reviews_count,
            "description": self.description,
            "website": self.website,
            "photos": self.photos,
            "reviews": self.reviews,
            "opening_hours": self.opening_hours,
            "services": self.services,
            "social_links": self.social_links,
            "emails": self.emails,
            "place_title": self.place_title,
            "place_city": self.place_city,
            "place_postal_code": self.place_postal_code,
        }


# JS executed in the place page to gather everything in one round trip.
_EXTRACT_JS = r"""
(() => {
    const out = {
        rating: null, reviews_count: null, description: null, website: null,
        photos: [], reviews: [], opening_hours: [], ld: [], social: {},
        place_title: null
    };
    const txt = (el) => (el ? (el.innerText || el.textContent || '').trim() : '');

    // Title of the place panel — the name of the business the page is REALLY about.
    try {
        out.place_title = txt(document.querySelector('h1')) || null;
    } catch (e) {}

    // JSON-LD (schema.org) — the most stable anchor; parsed in Python as a fallback
    // for description / rating / reviews_count when the DOM selectors miss.
    try {
        out.ld = Array.from(document.querySelectorAll('script[type="application/ld+json"]'))
            .map(s => s.textContent || '').filter(Boolean);
    } catch (e) {}

    // Social profile links present anywhere on the panel.
    try {
        const nets = { facebook: 'facebook.com/', instagram: 'instagram.com/', linkedin: 'linkedin.com/', tiktok: 'tiktok.com/', youtube: 'youtube.com/' };
        document.querySelectorAll('a[href]').forEach((a) => {
            const href = a.getAttribute('href') || '';
            for (const [net, needle] of Object.entries(nets)) {
                if (!out.social[net] && href.toLowerCase().includes(needle)) out.social[net] = href;
            }
        });
    } catch (e) {}

    // Rating + reviews count (F7nice block: "4,9  (132)")
    try {
        const block = document.querySelector('div.F7nice');
        if (block) {
            const blockTxt = txt(block);
            const ratingM = blockTxt.match(/(\d+[.,]\d+)/);
            if (ratingM) { const r = parseFloat(ratingM[1].replace(',', '.')); if (!isNaN(r)) out.rating = r; }
            const aria = block.querySelector('[aria-label]');
            const ariaTxt = aria ? (aria.getAttribute('aria-label') || '') : '';
            // The count lives in parentheses ("(132)") — take it first; fall back to
            // the aria-label ("132 avis"). The old code only matched the aria form.
            let n = null;
            const parenM = blockTxt.match(/\(([\d\s.,  ]+)\)/);
            if (parenM) n = parseInt(parenM[1].replace(/[^\d]/g, ''), 10);
            if (n === null || isNaN(n)) {
                const ariaM = ariaTxt.match(/([\d][\d\s.,  ]*)\s*(avis|reviews|review)/i);
                if (ariaM) n = parseInt(ariaM[1].replace(/[^\d]/g, ''), 10);
            }
            if (n !== null && !isNaN(n)) out.reviews_count = n;
        }
    } catch (e) {}

    // Description / about (meta description as fallback)
    try {
        const meta = document.querySelector('meta[name="description"], meta[property="og:description"]');
        if (meta) out.description = (meta.getAttribute('content') || '').trim() || null;
    } catch (e) {}

    // Website link on the panel (data-item-id="authority", a stable semantic hook):
    // a real site means the prospect is NOT a « no website » target — surfaced so the
    // enrichment can double-check what the search scrapers may have missed.
    try {
        const site = document.querySelector('a[data-item-id="authority"]');
        const href = site ? (site.getAttribute('href') || '') : '';
        if (href && !/google\.[a-z.]+\/maps/i.test(href)) out.website = href.trim() || null;
    } catch (e) {}

    // Photos (large googleusercontent images, deduplicated)
    try {
        const seen = new Set();
        document.querySelectorAll('img').forEach((img) => {
            let src = img.getAttribute('src') || '';
            if (!src || src.indexOf('googleusercontent') === -1) return;
            // keep only reasonably large images (skip tiny avatars)
            if (/=s\d{1,2}-/.test(src) || /=w\d{1,2}-/.test(src)) return;
            // normalize size to a large variant
            src = src.replace(/=w\d+-h\d+.*$/, '=w1200-h800').replace(/=s\d+.*$/, '=s1200');
            if (!seen.has(src)) { seen.add(src); out.photos.push(src); }
        });
        out.photos = out.photos.slice(0, 20);
    } catch (e) {}

    // Opening hours (table rows: day + hours, then div-based fallback)
    try {
        const pushHour = (day, hours) => {
            if (!day || !hours || day.length >= 24 || hours.length >= 48) return;
            const key = day.toLowerCase();
            if (out.opening_hours.some((row) => row.day.toLowerCase() === key)) return;
            out.opening_hours.push({ day, hours });
        };
        document.querySelectorAll('table tr').forEach((tr) => {
            const cells = tr.querySelectorAll('td, th');
            if (cells.length >= 2) pushHour(txt(cells[0]), txt(cells[1]));
        });
        if (out.opening_hours.length < 5) {
            document.querySelectorAll('[role="row"], li').forEach((row) => {
                const parts = txt(row).split('\\n').map((p) => p.trim()).filter(Boolean);
                if (parts.length >= 2) pushHour(parts[0], parts.slice(1).join(' '));
            });
        }
        out.opening_hours = out.opening_hours.slice(0, 7);
    } catch (e) {}

    // Reviews snippets present in the panel
    try {
        const blocks = document.querySelectorAll('div.jftiEf, div[data-review-id]');
        blocks.forEach((b) => {
            const author = txt(b.querySelector('.d4r55, .TSUbDb'));
            const text = txt(b.querySelector('.wiI7pd, .MyEned'));
            const ratingEl = b.querySelector('[aria-label*="étoile"], [aria-label*="star"], .kvMYJc');
            let rating = null;
            if (ratingEl) {
                const m = (ratingEl.getAttribute('aria-label') || '').match(/([\d.,]+)/);
                if (m) rating = parseFloat(m[1].replace(',', '.'));
            }
            // « Réponse du propriétaire » — the owner's reply, often signed with a
            // first name (fuels the decision-maker resolution). Selector-free:
            // detected via the localized marker inside the block's inner text.
            let ownerResponse = null;
            try {
                const full = b.innerText || '';
                const marker = full.includes('Réponse du propriétaire')
                    ? 'Réponse du propriétaire'
                    : (full.includes('Response from the owner') ? 'Response from the owner' : null);
                if (marker) {
                    ownerResponse = full.split(marker)[1].replace(/^[\\s:.-]+/, '').trim().slice(0, 400) || null;
                }
            } catch (e) {}
            if (text) out.reviews.push({ author: author || 'Client', text, rating, owner_response: ownerResponse });
        });
        out.reviews = out.reviews.slice(0, 12);
    } catch (e) {}

    return out;
})()
"""

# Lightweight readiness probe — wave-2 hydration (review count + weekly hours).
_HYDRATION_READY_JS = r"""
(() => {
    const txt = (el) => (el ? (el.innerText || el.textContent || '').trim() : '');
    let hasReviewCount = false;
    const block = document.querySelector('div.F7nice');
    if (block) {
        const blockTxt = txt(block);
        hasReviewCount = /\([\d\s.,]+/.test(blockTxt);
        if (!hasReviewCount) {
            const aria = block.querySelector('[aria-label]');
            const ariaTxt = aria ? (aria.getAttribute('aria-label') || '') : '';
            hasReviewCount = /\d+\s*(avis|reviews|review)/i.test(ariaTxt);
        }
    }
    let hourRowCount = 0;
    document.querySelectorAll('table tr').forEach((tr) => {
        const cells = tr.querySelectorAll('td, th');
        if (cells.length >= 2 && txt(cells[0]) && txt(cells[1])) hourRowCount++;
    });
    let hasReviewsTab = false;
    for (const el of document.querySelectorAll('[role="tab"], button, [role="button"]')) {
        const label = txt(el).toLowerCase();
        if (label === 'avis' || label.startsWith('avis ') || label.includes('reviews')) {
            hasReviewsTab = true;
            break;
        }
    }
    return { hasReviewCount, hourRowCount, hasReviewsTab };
})()
"""

# Expand the weekly hours table before extraction. We deliberately DO NOT open the reviews
# tab: clicking it now triggers Google's ReviewsService, which demands a sign-in (auth wall)
# and dead-ends the scrape (browser lands on accounts.google.com and closes). Reviews are read
# straight from the main place panel instead — fewer of them, but no wall.
_PREPARE_PANEL_JS = r"""
(() => {
    const txt = (el) => (el ? (el.innerText || el.textContent || el.getAttribute('aria-label') || '').trim() : '');
    const clickNeedle = (needles) => {
        for (const el of document.querySelectorAll('button, [role="tab"], [role="button"], div[role="button"]')) {
            const label = txt(el).toLowerCase();
            if (needles.some((needle) => label.includes(needle))) {
                el.click();
                return true;
            }
        }
        return false;
    };
    return {
        hours: clickNeedle(['horaire', 'hours', 'opening']),
    };
})()
"""

_ENRICHMENT_MAX_ATTEMPTS: int = 4
_ENRICHMENT_POLL_INTERVAL_S: float = 1.5
_ENRICHMENT_MIN_HOUR_ROWS: int = 5


class EnrichmentScraper:
    """Gathers rich Google Maps place data for a single prospect."""

    async def enrich(
        self,
        *,
        business_name: str,
        city: str | None = None,
        google_maps_url: str | None = None,
        facebook_url: str | None = None,
    ) -> EnrichmentData:
        """Fetch enrichment for a business: Google Maps (rich) + OpenStreetMap (stable gap-filler).

        Google is the primary source (photos, reviews, rating); OpenStreetMap fills the fields
        Google is weak/blocked on (opening hours, social links, description) via a plain HTTP API.
        OSM runs even when nodriver is unavailable, so enrichment degrades gracefully instead of
        returning nothing. With no Google listing but a Facebook page, the read is delegated to the
        Facebook scraper instead — Google wins whenever its URL is present.
        """
        # No Google listing to anchor on → read the Facebook page instead (many artisans only have one).
        if not (google_maps_url or "").strip() and (facebook_url or "").strip():
            from scrappers.facebook_enrichment_scraper import facebook_enrichment_scraper

            return await facebook_enrichment_scraper.enrich(
                business_name=business_name, facebook_url=facebook_url or ""
            )

        data = EnrichmentData()
        if NODRIVER_AVAILABLE:

            async def task() -> EnrichmentData:
                return await self._enrich_nodriver(business_name, city, google_maps_url)

            data = await run_nodriver_task(task, timeout=180)
        else:
            logger.warning("nodriver not available — Google enrichment skipped, OSM only")

        # Complementary OpenStreetMap enrichment (plain HTTP, no browser, never blocked).
        try:
            osm = await enrich_from_osm(business_name, city)
        except Exception as exc:
            logger.info("OSM enrichment failed for %s: %s", business_name, exc)
            osm = {}
        self._merge_osm(data, osm)

        # Complementary Facebook read: the Maps listing often links a Facebook page that carries
        # opening hours / social links / a contact email Google doesn't expose. Prefer the FB URL
        # found on THIS listing; fall back to the one stored on the prospect (same business), so a
        # manually-added FB page still enriches even when Google links only Instagram or is walled.
        facebook_url = self._facebook_url_from_data(data) or (facebook_url or "").strip() or None
        if facebook_url and NODRIVER_AVAILABLE:
            try:
                from scrappers.facebook_enrichment_scraper import facebook_enrichment_scraper

                facebook = await facebook_enrichment_scraper.enrich(
                    business_name=business_name, facebook_url=facebook_url
                )
                self._merge_facebook(data, facebook)
            except Exception as exc:
                logger.info("Facebook complementary enrichment failed for %s: %s", business_name, exc)

        return data

    @staticmethod
    def _facebook_url_from_data(data: EnrichmentData) -> str | None:
        """Return a Facebook page URL discovered on the Maps listing (a social link, or the "website"
        link when it points to ``facebook.com``), or None."""
        candidate = (data.social_links or {}).get("facebook")
        if not candidate and "facebook.com/" in (data.website or "").lower():
            candidate = data.website
        candidate = (candidate or "").strip()
        return candidate or None

    @staticmethod
    def _merge_facebook(data: EnrichmentData, facebook: EnrichmentData) -> None:
        """Fill gaps in the Google-sourced data with the linked Facebook page (Google wins where present)."""
        if not data.opening_hours and facebook.opening_hours:
            data.opening_hours = facebook.opening_hours
        if facebook.social_links:
            data.social_links = {**facebook.social_links, **(data.social_links or {})}
        if not data.description and facebook.description:
            data.description = facebook.description
        if facebook.emails:
            data.emails = [*data.emails, *facebook.emails]
        if "facebook" not in data.source:
            data.source = f"{data.source}+facebook"

    @staticmethod
    def _merge_osm(data: EnrichmentData, osm: dict[str, Any]) -> None:
        """Fill gaps in the Google-sourced data with OSM's stable fields (Google wins where present)."""
        if not osm:
            return
        if not data.opening_hours and isinstance(osm.get("opening_hours"), list):
            data.opening_hours = osm["opening_hours"]
        if isinstance(osm.get("social_links"), dict) and osm["social_links"]:
            data.social_links = {**osm["social_links"], **(data.social_links or {})}
        if not data.description and osm.get("description"):
            data.description = str(osm["description"]).strip() or None
        if data.source == "google":
            data.source = "google+osm"

    async def _enrich_nodriver(
        self,
        business_name: str,
        city: str | None,
        google_maps_url: str | None,
    ) -> EnrichmentData:
        """nodriver implementation: open the place panel and extract rich data."""
        browser = NodriverBrowser(ephemeral=True)
        try:
            if google_maps_url and GoogleScraper.is_maps_url(google_maps_url):
                url = GoogleScraper.normalize_maps_url(google_maps_url)
            else:
                query = GoogleScraper.build_business_query(business_name, city)
                url = f"https://www.google.com/maps/search/{query}"

            tab = await browser.get_tab(url)
            await GoogleScraper.accept_cookies(tab)
            await GoogleScraper.accept_web_modal(tab)

            # If we landed on a results feed, open the first place.
            current = NodriverDom.tab_url(tab)
            if "/maps/place/" not in current:
                opened = await NodriverDom.evaluate(
                    tab,
                    """
                    (() => {
                        const link = document.querySelector("div[role='feed'] a[href*='/maps/place/']");
                        if (link) { link.removeAttribute('target'); link.click(); return true; }
                        return false;
                    })()
                    """,
                    by_value=True,
                )
                if opened is True:
                    await asyncio.sleep(1.0)

            if not await NodriverDom.wait_for_selector(tab, "h1", timeout_s=12.0):
                logger.info("Enrichment: place panel not found for %s", business_name)
                try:
                    page_html = await NodriverDom.evaluate(tab, "document.documentElement.outerHTML", by_value=True)
                except Exception:
                    page_html = None
                scrape_signals.note_block(
                    "enrichment",
                    reason="place panel not found (blocked/consent)",
                    html=page_html if isinstance(page_html, str) else None,
                )
                return EnrichmentData()

            await self._wait_for_maps_hydration(tab)
            return await self._extract_with_retries(tab, business_name=business_name, city=city)
        except Exception as exc:
            logger.warning("Enrichment scrape failed for %s: %s", business_name, exc)
            return EnrichmentData()
        finally:
            await browser.close()

    async def _wait_for_maps_hydration(self, tab: Any, *, timeout_s: float = 18.0) -> None:
        """Wait until Google Maps wave-2 data (review count / weekly hours) appears."""
        deadline = asyncio.get_running_loop().time() + timeout_s
        while asyncio.get_running_loop().time() < deadline:
            status = await self._read_hydration_status(tab)
            # Weekly hours are the reliable wave-2 signal; the review count is a bonus that some
            # listings (new places, food trucks) never render, so we no longer block on it.
            if status.get("hourRowCount", 0) >= _ENRICHMENT_MIN_HOUR_ROWS:
                return
            await asyncio.sleep(0.5)

    async def _read_hydration_status(self, tab: Any) -> dict[str, Any]:
        """Return the current hydration markers from the place panel."""
        raw = await NodriverDom.evaluate(tab, f"JSON.stringify({_HYDRATION_READY_JS})", by_value=True)
        if not isinstance(raw, str):
            return {}
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}

    async def _prepare_panel_for_extraction(self, tab: Any) -> None:
        """Expand hours, open the reviews tab, and scroll lazy-loaded content."""
        try:
            await NodriverDom.evaluate(tab, _PREPARE_PANEL_JS, by_value=True)
            await asyncio.sleep(0.8)
        except Exception:
            pass

        try:
            for _ in range(6):
                await NodriverDom.scroll_element(tab, "div[role='main']", 1400)
                await asyncio.sleep(0.45)
        except Exception:
            pass

    async def _extract_raw(self, tab: Any) -> dict[str, Any]:
        """Run the in-page extraction script once."""
        raw = await NodriverDom.evaluate(tab, f"JSON.stringify({_EXTRACT_JS})", by_value=True)
        if not isinstance(raw, str):
            return {}
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}

    @staticmethod
    def _is_extraction_ready(data: EnrichmentData) -> bool:
        """True when wave-2 data looks complete enough to stop retrying.

        Weekly hours are the reliable signal; the review count is optional (new places and food
        trucks often have none), so we don't burn extra attempts waiting for a count that never comes.
        """
        return len(data.opening_hours) >= _ENRICHMENT_MIN_HOUR_ROWS

    @staticmethod
    def _merge_attempt_data(current: EnrichmentData, incoming: EnrichmentData) -> EnrichmentData:
        """Keep the richest fields seen across extraction attempts."""
        merged_reviews: list[dict[str, Any]] = list(current.reviews)
        seen_reviews: set[str] = {
            str(review.get("text") or review.get("author") or "").strip().lower()
            for review in merged_reviews
            if isinstance(review, dict)
        }
        for review in incoming.reviews:
            if not isinstance(review, dict):
                continue
            key: str = str(review.get("text") or review.get("author") or "").strip().lower()
            if not key or key in seen_reviews:
                continue
            merged_reviews.append(review)
            seen_reviews.add(key)

        merged_photos: list[str] = [url for url in current.photos if url]
        seen_photos: set[str] = set(merged_photos)
        for url in incoming.photos:
            if url and url not in seen_photos:
                merged_photos.append(url)
                seen_photos.add(url)

        merged_hours: list[dict[str, str]] = current.opening_hours
        if len(incoming.opening_hours) > len(merged_hours):
            merged_hours = incoming.opening_hours

        return EnrichmentData(
            source=incoming.source or current.source,
            logo_url=incoming.logo_url or current.logo_url,
            rating=incoming.rating if incoming.rating is not None else current.rating,
            reviews_count=incoming.reviews_count if incoming.reviews_count is not None else current.reviews_count,
            description=incoming.description or current.description,
            website=incoming.website or current.website,
            photos=merged_photos[:20],
            reviews=merged_reviews[:12],
            opening_hours=merged_hours,
            services=incoming.services or current.services,
            social_links={**(current.social_links or {}), **(incoming.social_links or {})},
            place_title=incoming.place_title or current.place_title,
            place_city=incoming.place_city or current.place_city,
            place_postal_code=incoming.place_postal_code or current.place_postal_code,
        )

    async def _extract_with_retries(
        self,
        tab: Any,
        *,
        business_name: str,
        city: str | None,
    ) -> EnrichmentData:
        """Poll extraction until wave-2 hydration is complete or attempts are exhausted."""
        best: EnrichmentData = EnrichmentData()
        for attempt in range(_ENRICHMENT_MAX_ATTEMPTS):
            await self._prepare_panel_for_extraction(tab)
            raw = await self._extract_raw(tab)
            candidate = self._build_from_raw(raw, business_name=business_name, city=city)
            best = self._merge_attempt_data(best, candidate)
            if self._is_extraction_ready(best):
                logger.info("Enrichment ready for %s after %s attempt(s)", business_name, attempt + 1)
                return best
            if attempt + 1 < _ENRICHMENT_MAX_ATTEMPTS:
                logger.info(
                    "Enrichment incomplete for %s (attempt %s/%s) — retrying",
                    business_name,
                    attempt + 1,
                    _ENRICHMENT_MAX_ATTEMPTS,
                )
                await asyncio.sleep(_ENRICHMENT_POLL_INTERVAL_S)
        logger.info(
            "Enrichment for %s finished with partial data after %s attempts",
            business_name,
            _ENRICHMENT_MAX_ATTEMPTS,
        )
        return best

    @staticmethod
    def _build_from_raw(
        data: dict[str, Any],
        *,
        business_name: str | None = None,
        city: str | None = None,
    ) -> EnrichmentData:
        """Coerce the raw JS payload into a typed EnrichmentData.

        DOM selectors first, then JSON-LD (schema.org) as a stable fallback for
        description / rating / reviews_count when the obfuscated classes miss.
        ``business_name`` / ``city`` gate the meta-description fallback: it is the
        PAGE's meta, trustworthy only when it actually names the business.
        """
        if not isinstance(data, dict):
            return EnrichmentData()

        def _as_float(value: Any) -> float | None:
            try:
                return float(value) if value is not None else None
            except (TypeError, ValueError):
                return None

        def _as_int(value: Any) -> int | None:
            try:
                return int(value) if value is not None else None
            except (TypeError, ValueError):
                return None

        photos = [str(p) for p in data.get("photos", []) if isinstance(p, str)]
        reviews = [r for r in data.get("reviews", []) if isinstance(r, dict)]
        hours = [h for h in data.get("opening_hours", []) if isinstance(h, dict)]
        social = {str(k): str(v) for k, v in (data.get("social") or {}).items() if isinstance(v, str) and v.strip()}
        website = (str(data["website"]).strip() if data.get("website") else None) or None

        # JSON-LD fallback (Google Maps place pages sometimes ship schema.org data).
        business = parse_ld_json_blocks(data.get("ld"))

        rating = _as_float(data.get("rating"))
        if rating is None and business:
            rating = _as_float(business.get("rating"))

        reviews_count = _as_int(data.get("reviews_count"))
        if reviews_count is None and business:
            reviews_count = _as_int(business.get("reviews_count"))

        dom_description = (str(data["description"]).strip() if data.get("description") else None) or None
        # The DOM value is the page's meta description: on a place deep link it names
        # the business, on a search/consent page it's Google's own boilerplate.
        if dom_description and (
            validation_service.is_generic_platform_description(dom_description)
            or not validation_service.description_mentions_business(dom_description, business_name, city)
        ):
            logger.info("Enrichment: dropping irrelevant meta description %r", dom_description[:80])
            dom_description = None

        description = dom_description
        if business and business.get("description"):
            # Prefer a JSON-LD description over the meta description fallback.
            ld_description = str(business["description"]).strip()
            if ld_description and not validation_service.is_generic_platform_description(ld_description):
                description = ld_description

        place_title = (str(data["place_title"]).strip() if data.get("place_title") else None) or None
        if place_title is None and business and business.get("name"):
            place_title = str(business["name"]).strip() or None

        return EnrichmentData(
            source="google",
            rating=rating,
            reviews_count=reviews_count,
            description=description,
            website=website,
            photos=photos,
            reviews=reviews,
            opening_hours=hours,
            social_links=social,
            place_title=place_title,
            place_city=(str(business["city"]).strip() or None) if business and business.get("city") else None,
            place_postal_code=(
                (str(business["postal_code"]).strip() or None) if business and business.get("postal_code") else None
            ),
        )


enrichment_scraper = EnrichmentScraper()
