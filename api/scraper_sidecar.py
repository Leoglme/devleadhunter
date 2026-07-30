"""Local scraping sidecar shipped inside the desktop app.

Google blocks datacenter IPs, so the browser-driven scraping (nodriver/Chrome)
must run on the USER's machine, with their residential IP — never on the VPS.
This module is the entrypoint the Tauri shell spawns: a minimal FastAPI app
exposing only the scraping endpoints that need a real browser.

It deliberately carries **no database and no background worker**: every endpoint
here is purely functional (scrape → return JSON), so the packaged binary needs
no credentials. Persisting the result stays the remote API's job.

Run: ``python scraper_sidecar.py --port 8765`` (Tauri passes the port and a
one-shot token; see ``web/src-tauri/src/scraper_sidecar.rs``).
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import multiprocessing
import os
import sys

import uvicorn
from fastapi import Depends, FastAPI, Header, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from core.win32_asyncio import ensure_proactor_event_loop
from models.prospect import (
    ProspectCreate,
    ProspectEnrichRequest,
    ProspectSearchSuggestion,
    ProspectSearchSuggestionsRequest,
)
from scrappers.chrome_provisioning import ensure_chrome, find_installed_chrome
from services.prospect_enrichment_service import prospect_enrichment_service

logger = logging.getLogger(__name__)

# État de l'approvisionnement Chrome, exposé par ``/health``.
_chrome_state: str = "unknown"
_chrome_path: str | None = None

# Le sidecar n'écoute que la boucle locale : il ne doit jamais être joignable
# depuis le réseau, même sur une machine partagée.
LOOPBACK_HOST = "127.0.0.1"

# Origines de la coquille Tauri (Windows/WebView2 sert l'app depuis tauri.localhost).
_ALLOWED_ORIGINS: list[str] = [
    "http://tauri.localhost",
    "https://tauri.localhost",
    "tauri://localhost",
    "http://localhost:1420",
]

app = FastAPI(
    title="DevLeadHunter — scraping sidecar",
    description="Local browser-driven scraping, executed on the user's machine.",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)


def require_sidecar_token(x_sidecar_token: str = Header(default="")) -> None:
    """Reject anything that does not carry the token Tauri generated at startup.

    Loopback alone is not enough: any local process — including a web page the
    user has open — could otherwise drive the scraper.

    Args:
        x_sidecar_token: Token sent by the desktop app on every call.

    Raises:
        HTTPException: 401 when the token is missing or wrong.
    """
    expected = os.environ.get("SIDECAR_TOKEN", "")
    if not expected or x_sidecar_token != expected:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Jeton sidecar invalide.")


@app.on_event("startup")
async def provision_chrome() -> None:
    """Make sure a Chrome is available, downloading one on first launch if needed.

    Runs in a worker thread so the sidecar answers ``/health`` immediately: the
    very first launch may spend minutes fetching Chrome for Testing, and the
    desktop app must be able to show that state rather than look frozen.
    """

    def _provision() -> None:
        global _chrome_state, _chrome_path
        try:
            _chrome_path = ensure_chrome()
            _chrome_state = "ready"
        except Exception as exc:
            _chrome_state = "unavailable"
            logger.exception("Chrome provisioning failed: %s", exc)

    if find_installed_chrome():
        _provision()
        return

    global _chrome_state
    _chrome_state = "installing"
    asyncio.get_running_loop().run_in_executor(None, _provision)


@app.get("/health")
async def health() -> dict[str, str]:
    """Liveness probe the desktop shell polls before routing any call.

    ``chrome`` is ``ready``, ``installing`` (first-launch download) or
    ``unavailable`` — the app surfaces it instead of failing on the first scrape.
    """
    return {"status": "ok", "chrome": _chrome_state, "chrome_path": _chrome_path or ""}


@app.post(
    "/scraper/search-suggestions",
    response_model=list[ProspectSearchSuggestion],
    dependencies=[Depends(require_sidecar_token)],
)
async def search_suggestions(request: ProspectSearchSuggestionsRequest) -> list[ProspectSearchSuggestion]:
    """Google Maps autocomplete for the « add a prospect » drawer.

    Args:
        request: Business name, optional city and result cap.

    Returns:
        The matching business suggestions.

    Raises:
        HTTPException: 400 when the search itself fails (Chrome, network, blocking).
    """
    try:
        return await prospect_enrichment_service.search_suggestions(
            query=request.query,
            city=request.city,
            max_results=request.max_results,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@app.post(
    "/scraper/enrich",
    response_model=ProspectCreate,
    dependencies=[Depends(require_sidecar_token)],
)
async def enrich(request: ProspectEnrichRequest) -> ProspectCreate:
    """Pre-fill a prospect from its Google Maps listing, without saving it.

    Args:
        request: Business name and/or Google Maps URL, optional city.

    Returns:
        The prospect draft the drawer displays.

    Raises:
        HTTPException: 400 when the listing cannot be read.
    """
    try:
        return await prospect_enrichment_service.enrich_from_google(
            business_name=request.business_name,
            google_maps_url=request.google_maps_url,
            city=request.city,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


def main() -> None:
    """Start the sidecar on the loopback port the desktop shell picked."""
    parser = argparse.ArgumentParser(description="DevLeadHunter local scraping sidecar")
    parser.add_argument("--port", type=int, default=int(os.environ.get("SIDECAR_PORT", "8765")))
    args = parser.parse_args()

    if sys.platform == "win32":
        # PyInstaller One-File respawns the process; without this it forks forever.
        multiprocessing.freeze_support()
        ensure_proactor_event_loop()

    logging.basicConfig(level=logging.INFO)
    logger.info("Scraping sidecar listening on http://%s:%s", LOOPBACK_HOST, args.port)
    uvicorn.run(app, host=LOOPBACK_HOST, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
