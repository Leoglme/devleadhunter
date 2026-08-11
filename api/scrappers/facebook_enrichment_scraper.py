"""
Facebook page enrichment scraper.

Fallback for prospects that have NO Google listing but an active public Facebook
page — common among artisans who only ever set up a Facebook presence. It produces
the same ``EnrichmentData`` the Google scraper returns, so the rest of the pipeline
(``EnrichmentService._apply_data``, site-content mapping) is untouched.

Two Facebook specifics drive the design:

- **No stable CSS classes.** Facebook hashes and rotates every class name, so
  extraction is anchored on **stable French captions** ("Mobile", "Recommandé par
  X %", "… recommande …") and on ``a[href]`` / ``img[src]`` — never on class names.
- **Reviews are binary.** Facebook shows "recommends / doesn't recommend" plus a
  "Recommandé par X %" rate, not 1-5 stars. The rate is converted to a /5 rating so
  the data lines up with what Google yields (kept homogeneous on purpose).

Like the Google scraper it runs on the user's desktop (nodriver, residential IP) —
Facebook blocks datacenter IPs too. Everything is best-effort: a partial read still
returns whatever could be gathered. The text-parsing helpers are pure functions so
they can be unit-tested without a browser.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from scrappers.enrichment_scraper import EnrichmentData
from scrappers.nodriver_browser import NODRIVER_AVAILABLE, NodriverBrowser
from scrappers.nodriver_dom import NodriverDom
from scrappers.nodriver_executor import run_nodriver_task

logger = logging.getLogger(__name__)

# `\s` matches the thin/no-break spaces Facebook puts before « % », so « 96 % » / « 22 avis » parse verbatim.
_RECOMMEND_RE = re.compile(r"recommand[ée]?s?\s+par\s*(\d+)\s*%", re.IGNORECASE)
_REVIEWS_COUNT_RE = re.compile(r"\((\d[\d\s.,]*)\s*avis\)", re.IGNORECASE)
# Header line of a review block: "<Author> recommande <page>." / "… ne recommande pas …".
_REVIEW_HEADER_RE = re.compile(r"^(.+?)\s+(?:ne\s+)?recommande\b", re.IGNORECASE)
# A French date line ("27 septembre 2025") that sits between the header and the body.
_DATE_RE = re.compile(r"^\d{1,2}\s+\S+\s+\d{4}$")
_REVIEW_STOP_MARKERS: tuple[str, ...] = (
    "toutes les réactions",
    "toutes les reactions",
    "j'aime",
    "j’aime",
    "commenter",
    "partager",
    "répondre",
    "repondre",
)

# Dismiss the login gate + strip leftover overlays so the DOM behind (already loaded) stays readable; we only read.
_DISMISS_LOGIN_JS = r"""
(() => {
    let closed = false;
    for (const el of document.querySelectorAll('[aria-label="Fermer"], [aria-label="Close"]')) {
        try { el.click(); closed = true; break; } catch (e) {}
    }
    document.querySelectorAll('div[role="dialog"]').forEach((d) => { try { d.remove(); } catch (e) {} });
    try {
        document.body.style.overflow = 'visible';
        document.documentElement.style.overflow = 'visible';
    } catch (e) {}
    return closed;
})()
"""

# Read the « À propos » page in one round trip: title, panel text (parsed in Python), socials, website, photos.
_FB_ABOUT_JS = r"""
(() => {
    const out = { place_title: null, about_text: '', social: {}, website: null, photos: [] };
    const txt = (el) => (el ? (el.innerText || el.textContent || '').trim() : '');
    try { out.place_title = txt(document.querySelector('h1')) || null; } catch (e) {}
    try {
        const main = document.querySelector('div[role="main"]');
        out.about_text = (main ? main.innerText : (document.body ? document.body.innerText : '')) || '';
    } catch (e) { out.about_text = ''; }
    const unwrap = (href) => {
        const m = (href || '').match(/[?&]u=([^&]+)/);
        if (m) { try { return decodeURIComponent(m[1]); } catch (e) {} }
        return href || '';
    };
    const isSocial = (low) => ['facebook.com', 'instagram.com', 'tiktok.com', 'youtube.com',
        'linkedin.com', 'l.php', 'l.facebook'].some((needle) => low.includes(needle));
    try {
        const nets = { facebook: 'facebook.com/', instagram: 'instagram.com/',
            tiktok: 'tiktok.com/', youtube: 'youtube.com/', linkedin: 'linkedin.com/' };
        for (const a of document.querySelectorAll('a[href]')) {
            const href = unwrap(a.getAttribute('href'));
            const low = href.toLowerCase();
            for (const [net, needle] of Object.entries(nets)) {
                if (!out.social[net] && low.includes(needle)) out.social[net] = href;
            }
            if (!out.website && /^https?:\/\//i.test(href) && !isSocial(low)) out.website = href;
        }
    } catch (e) {}
    try {
        const seen = new Set();
        for (const img of document.querySelectorAll('img')) {
            const src = img.getAttribute('src') || '';
            if (!/scontent|fbcdn/i.test(src)) continue;
            if (seen.has(src)) continue;
            seen.add(src);
            out.photos.push(src);
            if (out.photos.length >= 20) break;
        }
    } catch (e) {}
    return out;
})()
"""

# Reviews tab: return the panel text; the review blocks are parsed in Python.
_FB_REVIEWS_JS = r"""
(() => {
    const main = document.querySelector('div[role="main"]');
    return { reviews_text: (main ? main.innerText : (document.body ? document.body.innerText : '')) || '' };
})()
"""


def _rating_from_pct(pct: int | None) -> float | None:
    """Convert a Facebook "recommended by X %" rate into a /5 rating (96 % → 4.8).

    Args:
        pct: Recommendation percentage (0-100), or None.

    Returns:
        The rating rounded to one decimal and clamped to [0, 5], or None.
    """
    if pct is None:
        return None
    return round(max(0.0, min(100.0, float(pct))) / 20.0, 1)


def _parse_about_stats(text: str) -> tuple[int | None, int | None]:
    """Extract the recommendation rate and review count from a Facebook panel text.

    Args:
        text: Visible text of the « À propos » / « Avis » panel.

    Returns:
        A ``(rating_pct, reviews_count)`` pair, each None when absent.
    """
    rating_match = _RECOMMEND_RE.search(text)
    count_match = _REVIEWS_COUNT_RE.search(text)
    rating_pct = int(rating_match.group(1)) if rating_match else None
    reviews_count = int(re.sub(r"\D", "", count_match.group(1))) if count_match else None
    return rating_pct, reviews_count


def _is_review_noise(line: str) -> bool:
    """True for lines that are not part of a review body (date, dot, reaction count)."""
    if line in {"·", "•", "…"}:
        return True
    if _DATE_RE.match(line):
        return True
    return line.replace(" ", "").isdigit()


def _is_review_stop(line: str) -> bool:
    """True when a line marks the end of a review body (reactions / action bar)."""
    lowered = line.lower()
    return any(marker in lowered for marker in _REVIEW_STOP_MARKERS)


def _parse_reviews(text: str) -> list[dict[str, Any]]:
    """Parse the reviews-tab text into ``{author, text, rating}`` rows.

    Each Facebook review reads "<Author> recommande <page>." then a date then the
    body, up to the "Toutes les réactions" marker. A recommendation maps to 5/5, a
    "ne recommande pas" to 2/5 (Facebook has no finer grain).

    Args:
        text: Visible text of the « Avis » panel.

    Returns:
        Up to 12 parsed reviews, in page order.
    """
    lines: list[str] = [line.strip() for line in text.splitlines() if line.strip()]
    reviews: list[dict[str, Any]] = []
    index = 0
    while index < len(lines) and len(reviews) < 12:
        header = _REVIEW_HEADER_RE.match(lines[index])
        if header is None:
            index += 1
            continue
        author: str = header.group(1).strip()
        recommends: bool = "ne recommande pas" not in lines[index].lower()
        body: list[str] = []
        cursor = index + 1
        while cursor < len(lines):
            line = lines[cursor]
            if _REVIEW_HEADER_RE.match(line) or _is_review_stop(line):
                break
            if not _is_review_noise(line):
                body.append(line)
            cursor += 1
        review_text: str = " ".join(body).strip()
        if author and review_text:
            reviews.append({"author": author, "text": review_text, "rating": 5 if recommends else 2})
        index = cursor if cursor > index else index + 1
    return reviews


class FacebookEnrichmentScraper:
    """Gathers proof data (rating, reviews, socials, photos) from a public Facebook page."""

    async def enrich(self, *, business_name: str, facebook_url: str) -> EnrichmentData:
        """Scrape a prospect's Facebook page into an ``EnrichmentData`` (source « facebook »).

        Args:
            business_name: Prospect name (logging only).
            facebook_url: Public Facebook page URL.

        Returns:
            The scraped enrichment; an empty « facebook » payload when nodriver is
            unavailable or the page could not be read.
        """
        if not NODRIVER_AVAILABLE:
            logger.warning("nodriver not available — Facebook enrichment skipped for %s", business_name)
            return EnrichmentData(source="facebook")

        async def task() -> EnrichmentData:
            return await self._enrich_nodriver(business_name, facebook_url)

        return await run_nodriver_task(task, timeout=150)

    async def _enrich_nodriver(self, business_name: str, facebook_url: str) -> EnrichmentData:
        """nodriver implementation: open the page, dismiss the login gate, extract."""
        browser = NodriverBrowser(ephemeral=True)
        try:
            tab = await browser.get_tab(self._about_url(facebook_url))
            await self._dismiss_login_gate(tab)
            if not await NodriverDom.wait_for_selector(tab, "h1", timeout_s=10.0):
                logger.info("Facebook enrichment: page not readable for %s", business_name)
                return EnrichmentData(source="facebook")
            dom = await self._extract_about(tab)
            reviews_text = await self._extract_reviews(tab, facebook_url)
            return self._build_from_raw(dom, reviews_text)
        except Exception as exc:
            logger.warning("Facebook enrichment failed for %s: %s", business_name, exc)
            return EnrichmentData(source="facebook")
        finally:
            await browser.close()

    @staticmethod
    def _base_url(facebook_url: str) -> str:
        """Normalize a Facebook page URL to its bare page root (no query, no trailing slash)."""
        base = facebook_url.strip()
        if not base.startswith("http"):
            base = f"https://{base}"
        return base.split("?")[0].rstrip("/")

    @classmethod
    def _about_url(cls, facebook_url: str) -> str:
        """The « À propos » sub-page URL (coordinates + general info)."""
        return f"{cls._base_url(facebook_url)}/about"

    @classmethod
    def _reviews_url(cls, facebook_url: str) -> str:
        """The « Avis » sub-page URL (recommendations)."""
        return f"{cls._base_url(facebook_url)}/reviews"

    async def _dismiss_login_gate(self, tab: Any) -> None:
        """Close the login modal and strip leftover overlays (best-effort)."""
        try:
            await NodriverDom.evaluate(tab, _DISMISS_LOGIN_JS, by_value=True)
        except Exception:
            pass

    async def _extract_about(self, tab: Any) -> dict[str, Any]:
        """Run the about-page extraction script once and coerce it to a dict."""
        raw = await NodriverDom.evaluate(tab, f"JSON.stringify({_FB_ABOUT_JS})", by_value=True)
        if not isinstance(raw, str):
            return {}
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}

    async def _extract_reviews(self, tab: Any, facebook_url: str) -> str:
        """Open the reviews tab and return its visible text (empty on failure)."""
        try:
            await NodriverDom.navigate(tab, self._reviews_url(facebook_url), sleep_s=1.2)
            await self._dismiss_login_gate(tab)
            raw = await NodriverDom.evaluate(tab, f"JSON.stringify({_FB_REVIEWS_JS})", by_value=True)
            if isinstance(raw, str):
                parsed = json.loads(raw)
                if isinstance(parsed, dict):
                    return str(parsed.get("reviews_text") or "")
        except Exception as exc:
            logger.info("Facebook reviews tab not readable: %s", exc)
        return ""

    @staticmethod
    def _build_from_raw(dom: dict[str, Any], reviews_text: str) -> EnrichmentData:
        """Coerce the raw about payload + reviews text into a typed ``EnrichmentData``."""
        about_text = str(dom.get("about_text") or "")
        rating_pct, reviews_count = _parse_about_stats(f"{about_text}\n{reviews_text}")
        social = {
            str(network): str(url)
            for network, url in (dom.get("social") or {}).items()
            if isinstance(url, str) and url.strip()
        }
        photos = [str(url) for url in dom.get("photos", []) if isinstance(url, str) and url.strip()]
        website = str(dom["website"]).strip() if dom.get("website") else None
        place_title = str(dom["place_title"]).strip() if dom.get("place_title") else None
        return EnrichmentData(
            source="facebook",
            rating=_rating_from_pct(rating_pct),
            reviews_count=reviews_count,
            website=website or None,
            photos=photos,
            reviews=_parse_reviews(reviews_text),
            social_links=social,
            place_title=place_title or None,
        )


facebook_enrichment_scraper = FacebookEnrichmentScraper()
