"""
Headful Storyblok login helper for the dedicated persistent profile (cascade step 2).

Mirrors the GoupixDex Amazon/Vinted/Cardmarket pattern: when no machine browser
session is available, the user signs in once in a visible window; the persistent
profile keeps the session and a small state file records it, so later background
captures start already authenticated.

Async (the sidecar is an async FastAPI app). Only login *state* is exposed; the
account token is never read or logged.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from services.storyblok_session_service import StoryblokSessionState, storyblok_session_service

logger = logging.getLogger(__name__)

_SPACES_URL = "https://app.storyblok.com/#/me/spaces"
_LOGIN_POLL_INTERVAL_SEC = 3.0
_LOGIN_POLL_MAX_SEC = 300.0


class StoryblokLoginHelper:
    """Own the visible login browser and report the dedicated-profile session state."""

    def __init__(self) -> None:
        self._playwright: Any = None
        self._context: Any = None
        self._poll_task: asyncio.Task | None = None
        self._lock = asyncio.Lock()

    @property
    def _is_open(self) -> bool:
        return self._context is not None

    async def open_login(self, executable_path: str | None = None) -> dict[str, Any]:
        """Open a visible Chromium on the Storyblok login, ready for the user to sign in.

        A background task then watches the window; as soon as it is authenticated it
        persists the state and closes the browser (flushing the profile to disk).
        """
        async with self._lock:
            if self._is_open:
                return {"opened": True, "already_open": True}
            from playwright.async_api import async_playwright

            profile_dir = storyblok_session_service.dedicated_profile_dir
            profile_dir.mkdir(parents=True, exist_ok=True)
            self._playwright = await async_playwright().start()
            self._context = await self._playwright.chromium.launch_persistent_context(
                str(profile_dir),
                headless=False,
                executable_path=executable_path,
                args=["--start-maximized", "--no-first-run", "--no-default-browser-check"],
            )
            page = self._context.pages[0] if self._context.pages else await self._context.new_page()
            await page.goto(_SPACES_URL, wait_until="domcontentloaded")
            self._poll_task = asyncio.create_task(self._poll_until_logged_in())
        return {"opened": True, "already_open": False}

    async def _poll_until_logged_in(self) -> None:
        """Watch the login window; persist + close as soon as it is authenticated."""
        loop = asyncio.get_event_loop()
        started = loop.time()
        try:
            while self._context is not None:
                if loop.time() - started > _LOGIN_POLL_MAX_SEC:
                    return
                await asyncio.sleep(_LOGIN_POLL_INTERVAL_SEC)
                if not await self._probe_authenticated():
                    continue
                storyblok_session_service.write_persisted_state(logged_in=True)
                logger.info("Storyblok dedicated-profile login detected — closing helper window")
                await self.close()
                return
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.debug("storyblok login poll: %s", exc)

    async def _probe_authenticated(self) -> bool:
        """True when the live window shows an authenticated Storyblok (no login form)."""
        if self._context is None:
            return False
        try:
            page = self._context.pages[0] if self._context.pages else None
            if page is None:
                return False
            has_password = await page.locator("input[type=password]").count() > 0
            url = (page.url or "").lower()
            return (not has_password) and "app.storyblok.com" in url and "login" not in url
        except Exception as exc:
            logger.debug("storyblok auth probe: %s", exc)
            return False

    async def close(self) -> None:
        """Shut the login window down and stop watching (idempotent)."""
        task = self._poll_task
        self._poll_task = None
        if task is not None and task is not asyncio.current_task():
            task.cancel()
            try:
                await asyncio.wait_for(task, timeout=3.0)
            except (TimeoutError, asyncio.CancelledError, Exception):
                pass
        if self._context is not None:
            try:
                await self._context.close()
            except Exception as exc:
                logger.debug("storyblok context close: %s", exc)
            self._context = None
        if self._playwright is not None:
            try:
                await self._playwright.stop()
            except Exception as exc:
                logger.debug("storyblok playwright stop: %s", exc)
            self._playwright = None

    async def state(self) -> dict[str, Any]:
        """Return the current connection state for the config UI.

        ``busy`` while the login window is open; otherwise the session service's
        read (``ready`` for a machine session or a recorded dedicated login).
        """
        if self._is_open:
            authed = await self._probe_authenticated()
            state: StoryblokSessionState = "ready" if authed else "busy"
            return {"state": state, "source": "dedicated-profile", "login_window_open": True}
        seed = storyblok_session_service.resolve_machine_seed()
        if seed is not None:
            return {"state": "ready", "source": seed.source, "login_window_open": False}
        persisted = storyblok_session_service.read_persisted_state()
        if persisted and persisted.get("logged_in"):
            return {"state": "ready", "source": "dedicated-profile", "login_window_open": False}
        return {"state": "needs_login", "source": None, "login_window_open": False}


storyblok_login_helper = StoryblokLoginHelper()
