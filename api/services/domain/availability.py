"""``.fr`` domain availability via the AFNIC RDAP service (free, no API key).

RDAP answers ``404`` when a domain is not registered (so it is available) and ``200``
with the registration record when it is taken. The check is best-effort: any other
outcome (network error, unexpected status) returns ``None`` so the caller never claims a
domain is free without proof — a wrong "available" would send the operator to buy a name
that is actually taken.
"""

from __future__ import annotations

import asyncio
import logging

import httpx

logger = logging.getLogger(__name__)

_RDAP_FR_URL = "https://rdap.nic.fr/domain/{domain}"
_TIMEOUT_SECONDS = 6.0


async def is_fr_available(domain: str) -> bool | None:
    """Whether a ``.fr`` domain is free to register.

    Args:
        domain: A full ``.fr`` domain (e.g. ``"tacos-maru.fr"``); case-insensitive.

    Returns:
        ``True`` when available, ``False`` when already registered, ``None`` when the
        check is inconclusive (not a ``.fr``, network error, or an unexpected status).
    """
    name = (domain or "").strip().lower()
    if not name.endswith(".fr"):
        return None
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as client:
            response = await client.get(_RDAP_FR_URL.format(domain=name))
    except httpx.HTTPError as exc:
        logger.debug("RDAP availability check inconclusive for %s: %s", name, exc)
        return None
    if response.status_code == 404:
        return True
    if response.status_code == 200:
        return False
    logger.debug("RDAP returned unexpected status %s for %s", response.status_code, name)
    return None


async def availability_map(domains: list[str]) -> dict[str, bool | None]:
    """Resolve availability for several ``.fr`` domains in parallel.

    Args:
        domains: Full ``.fr`` domains to check.

    Returns:
        A mapping ``domain -> True/False/None`` (see :func:`is_fr_available`).
    """
    unique = list(dict.fromkeys(domains))
    results = await asyncio.gather(*(is_fr_available(domain) for domain in unique))
    return dict(zip(unique, results, strict=True))
