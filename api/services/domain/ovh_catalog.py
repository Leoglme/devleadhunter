"""Live ``.fr`` price from the OVH public order catalog (no API key needed).

Every ``.fr`` costs the same and the price is stable, so it is fetched once and cached for the
process lifetime. Falls back to the configured estimate when the catalog is unreachable or its
shape changed — the price is only a "before you buy" indicator, never a blocker.
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

_cache: dict[str, float] = {}


def extract_fr_create_price(catalog: dict[str, Any]) -> float | None:
    """Pull the ``.fr`` first-year (create-default, installation) price from a catalog payload.

    Args:
        catalog: The parsed ``/order/catalog/public/domain`` response.

    Returns:
        The first-year price in EUR (HT), or ``None`` when the ``.fr`` plan/pricing is absent.
    """
    for plan in catalog.get("plans", []):
        if not isinstance(plan, dict) or plan.get("planCode") != "fr":
            continue
        for pricing in plan.get("pricings", []):
            capacities = pricing.get("capacities") or []
            if pricing.get("mode") == "create-default" and "installation" in capacities:
                price = pricing.get("price")
                if isinstance(price, (int, float)):
                    return round(price / _PRICE_SCALE, 2)
    return None


async def fr_first_year_price_eur() -> float:
    """The OVH ``.fr`` first-year price (HT, EUR), live from the public catalog and cached.

    Returns:
        The live price, or ``settings.domain_fr_price_eur`` when the catalog is unreachable.
    """
    if "fr" in _cache:
        return _cache["fr"]
    price: float | None = None
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as client:
            response = await client.get(_CATALOG_URL, params={"ovhSubsidiary": settings.ovh_subsidiary})
            response.raise_for_status()
            price = extract_fr_create_price(response.json())
    except (httpx.HTTPError, ValueError) as exc:
        logger.debug("OVH catalog price fetch failed, using fallback: %s", exc)
    result = price if price is not None else settings.domain_fr_price_eur
    _cache["fr"] = result
    return result
