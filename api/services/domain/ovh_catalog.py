"""Live per-TLD domain price from the OVH public order catalog (no API key needed).

A TLD's price is stable, so each is fetched once and cached for the process lifetime. ``.fr`` falls
back to the configured estimate when the catalog is unreachable; a TLD OVH does not sell returns
``None`` (the UI then shows no price rather than a wrong one).
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from core.config import settings

logger = logging.getLogger(__name__)

_CATALOG_URL = "https://api.ovh.com/1.0/order/catalog/public/domain"
_TIMEOUT_SECONDS = 8.0
# OVH stores catalog prices as an integer scaled by 1e8 (499000000 → 4.99 €).
_PRICE_SCALE = 1e8

# tld -> first-year price in EUR (HT), or None when OVH does not sell it. Cached per process.
_cache: dict[str, float | None] = {}


def extract_create_price(catalog: dict[str, Any], tld: str) -> float | None:
    """Pull a TLD's first-year (create-default, installation) price from a catalog payload.

    Args:
        catalog: The parsed ``/order/catalog/public/domain`` response.
        tld: The TLD without a dot (e.g. ``"fr"``, ``"com"``).

    Returns:
        The first-year price in EUR (HT), or ``None`` when that TLD's plan/pricing is absent.
    """
    for plan in catalog.get("plans", []):
        if not isinstance(plan, dict) or plan.get("planCode") != tld:
            continue
        for pricing in plan.get("pricings", []):
            capacities = pricing.get("capacities") or []
            if pricing.get("mode") == "create-default" and "installation" in capacities:
                price = pricing.get("price")
                if isinstance(price, (int, float)):
                    return round(price / _PRICE_SCALE, 2)
    return None


def tld_of(domain: str) -> str:
    """The TLD (last label, no dot) of a domain — ``"tacos-maru.fr"`` → ``"fr"``."""
    return domain.strip().lower().rsplit(".", 1)[-1]


async def first_year_price_eur(tld: str) -> float | None:
    """The OVH first-year price (HT, EUR) for a TLD, live from the public catalog and cached.

    Args:
        tld: The TLD without a dot (e.g. ``"fr"``).

    Returns:
        The live price, ``settings.domain_fr_price_eur`` as a ``.fr`` fallback when the catalog is
        unreachable, or ``None`` when OVH does not sell the TLD.
    """
    tld = tld.lower().lstrip(".")
    if tld in _cache:
        return _cache[tld]
    price: float | None = None
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as client:
            response = await client.get(_CATALOG_URL, params={"ovhSubsidiary": settings.ovh_subsidiary})
            response.raise_for_status()
            price = extract_create_price(response.json(), tld)
    except (httpx.HTTPError, ValueError) as exc:
        logger.debug("OVH catalog price fetch failed for .%s, using fallback: %s", tld, exc)
    if price is None and tld == "fr":
        price = settings.domain_fr_price_eur
    _cache[tld] = price
    return price


async def price_for_domain(domain: str) -> float | None:
    """The OVH first-year price for a full domain, resolved from its TLD."""
    return await first_year_price_eur(tld_of(domain))
