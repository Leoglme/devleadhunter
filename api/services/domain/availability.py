"""Domain availability via RDAP — ``.fr`` through AFNIC, other TLDs through the rdap.org bootstrap.

RDAP answers ``404`` when a domain is not registered (available) and ``200`` with the record when
it is taken. The check is best-effort: any other outcome (network error, unexpected status, no RDAP
server for the TLD) returns ``None`` so the caller never claims a domain is free without proof.
"""

from __future__ import annotations

import asyncio
import logging

import httpx

logger = logging.getLogger(__name__)

_TIMEOUT_SECONDS = 6.0
# .fr has a reliable authoritative RDAP; everything else goes through the IANA bootstrap redirector.
_AFNIC_RDAP = "https://rdap.nic.fr/domain/{domain}"
_BOOTSTRAP_RDAP = "https://rdap.org/domain/{domain}"


def _rdap_url(domain: str) -> str:
    """The RDAP query URL for a domain (AFNIC for .fr, the bootstrap redirector otherwise)."""
    return (_AFNIC_RDAP if domain.endswith(".fr") else _BOOTSTRAP_RDAP).format(domain=domain)


async def is_available(domain: str) -> bool | None:
    """Whether a domain is free to register.

    Args:
        domain: A full domain (e.g. ``"tacos-maru.fr"`` or ``"tacos-maru.com"``); case-insensitive.

    Returns:
        ``True`` when available, ``False`` when already registered, ``None`` when the check is
        inconclusive (no dot, network error, no RDAP server, or an unexpected status).
    """
    name = (domain or "").strip().lower()
    if "." not in name:
        return None
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS, follow_redirects=True) as client:
            response = await client.get(_rdap_url(name))
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
    """Resolve availability for several domains in parallel.

    Args:
        domains: Full domains to check.

    Returns:
        A mapping ``domain -> True/False/None`` (see :func:`is_available`).
    """
    unique = list(dict.fromkeys(domains))
    results = await asyncio.gather(*(is_available(domain) for domain in unique))
    return dict(zip(unique, results, strict=True))
