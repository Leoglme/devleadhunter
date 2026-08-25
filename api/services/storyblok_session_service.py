"""
Resolve a usable Storyblok editor session on the machine where the sidecar runs.

The Storyblok Visual Editor is only reachable while authenticated as the space
owner (Léo). No per-space password exists (clients self-serve via an emailed
invite), so the sidecar must borrow an existing owner session from the desktop.

Cascade (decided with Léo, 2026-08-25):
  1. Reuse a browser session already on the machine — Storyblok keeps its auth
     JWT in the ``app.storyblok.com`` localStorage (key ``token``), not in a
     cookie, so we read it from the Firefox profile on disk (read-only copy to
     dodge the file lock) and inject it into a headless browser.
  2. Fall back to a dedicated persistent profile the app owns — the GoupixDex
     pattern (Amazon/Vinted/Cardmarket): the user signs in once via a headful
     window, the profile keeps the session, and a state file records it.
  3. If neither yields a session, the caller skips the editor sequence.

This module only *reads* sessions and reports state; the actual browser probing
and the editor capture live in ``storyblok_editor_clip_service`` (it owns
Playwright). Values (tokens) are never logged.
"""

from __future__ import annotations

import glob
import json
import logging
import os
import shutil
import sqlite3
import tempfile
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

logger = logging.getLogger(__name__)

StoryblokSessionState = Literal["ready", "needs_login", "busy", "unknown"]

# Storyblok stores its auth in localStorage; only these keys are pure-ASCII and
# needed. Firefox encodes other blobs in a way that corrupts on a naive read and
# crashes Storyblok's JSON.parse, so we never inject them — the app rebuilds them.
_SAFE_LOCALSTORAGE_KEYS: tuple[str, ...] = ("token", "d0_session")

_STORYBLOK_LS_ORIGIN_DIR = "https+++app.storyblok.com"
_SESSION_STATE_FILE = "storyblok-session.json"


@dataclass
class StoryblokSessionSeed:
    """Everything needed to authenticate a fresh browser context to Storyblok.

    ``local_storage`` is injected on ``app.storyblok.com`` before its SPA boots;
    ``cookies`` are the (accessory) storyblok cookies. ``source`` is a short label
    for diagnostics ("firefox:<profile>" / "dedicated-profile").
    """

    local_storage: dict[str, str]
    cookies: list[dict] = field(default_factory=list)
    source: str = ""

    @property
    def has_token(self) -> bool:
        """True when the auth token is present (necessary, not sufficient — it may be expired)."""
        return bool(self.local_storage.get("token"))


class StoryblokSessionService:
    """Read reusable Storyblok owner sessions from the desktop and track their state."""

    def __init__(self, dedicated_profile_dir: Path | None = None) -> None:
        self._dedicated_profile_dir = dedicated_profile_dir or self.default_dedicated_profile_dir()

    # ── Machine browser session (cascade step 1) ─────────────────────────────

    def resolve_machine_seed(self) -> StoryblokSessionSeed | None:
        """Best Storyblok session found in the machine's browsers, or ``None``.

        Only Firefox is read today (Léo's browser); the return shape is browser
        agnostic so Chrome/Edge can be added without touching callers.
        """
        for profile in self._firefox_profiles_with_storyblok():
            seed = self._read_firefox_seed(profile)
            if seed and seed.has_token:
                logger.info("Storyblok machine session found (source=%s)", seed.source)
                return seed
        return None

    def _firefox_profiles_with_storyblok(self) -> list[Path]:
        """Firefox profile dirs that hold an ``app.storyblok.com`` localStorage store."""
        base = os.path.expandvars(r"%APPDATA%\Mozilla\Firefox\Profiles")
        if not os.path.isdir(base):
            return []
        matches: list[Path] = []
        for entry in sorted(glob.glob(os.path.join(base, "*"))):
            ls = Path(entry) / "storage" / "default" / _STORYBLOK_LS_ORIGIN_DIR / "ls" / "data.sqlite"
            if ls.is_file():
                matches.append(Path(entry))
        return matches

    def _read_firefox_seed(self, profile_dir: Path) -> StoryblokSessionSeed | None:
        """Extract the auth localStorage + storyblok cookies from one Firefox profile."""
        local_storage = self._read_firefox_localstorage(profile_dir)
        if not local_storage.get("token"):
            return None
        cookies = self._read_firefox_cookies(profile_dir)
        return StoryblokSessionSeed(
            local_storage=local_storage,
            cookies=cookies,
            source=f"firefox:{profile_dir.name}",
        )

    def _read_firefox_localstorage(self, profile_dir: Path) -> dict[str, str]:
        """Read the safe (ASCII, auth) localStorage keys for ``app.storyblok.com``."""
        ls = profile_dir / "storage" / "default" / _STORYBLOK_LS_ORIGIN_DIR / "ls" / "data.sqlite"
        items: dict[str, str] = {}
        try:
            copied = self._copy_locked(ls)
            connection = sqlite3.connect(copied)
            try:
                for key, value in connection.execute("SELECT key, value FROM data"):
                    if key not in _SAFE_LOCALSTORAGE_KEYS:
                        continue
                    text = value.decode("ascii", "ignore") if isinstance(value, bytes) else str(value)
                    if text and "�" not in text:
                        items[key] = text
            finally:
                connection.close()
        except (OSError, sqlite3.Error) as exc:
            logger.debug("Firefox localStorage read failed for %s: %s", profile_dir.name, exc)
        return items

    def _read_firefox_cookies(self, profile_dir: Path) -> list[dict]:
        """Read storyblok cookies from the profile as Playwright-ready session cookies."""
        same_site = {0: "None", 1: "Lax", 2: "Strict"}
        cookies: list[dict] = []
        try:
            copied = self._copy_locked(profile_dir / "cookies.sqlite")
            connection = sqlite3.connect(copied)
            try:
                rows = connection.execute(
                    "SELECT host, name, value, path, isSecure, isHttpOnly, sameSite "
                    "FROM moz_cookies WHERE host LIKE '%storyblok%'"
                )
                for host, name, value, path, is_secure, is_http, ss in rows:
                    cookies.append(
                        {
                            "name": name,
                            "value": value,
                            "domain": host,
                            "path": path or "/",
                            "expires": -1,
                            "httpOnly": bool(is_http),
                            "secure": bool(is_secure),
                            "sameSite": same_site.get(ss, "Lax"),
                        }
                    )
            finally:
                connection.close()
        except (OSError, sqlite3.Error) as exc:
            logger.debug("Firefox cookies read failed for %s: %s", profile_dir.name, exc)
        return cookies

    @staticmethod
    def _copy_locked(path: Path) -> str:
        """Copy a (possibly locked) SQLite file to temp so we never touch the live DB."""
        destination = os.path.join(tempfile.gettempdir(), "sb_" + path.name)
        shutil.copy2(path, destination)
        return destination

    # ── Dedicated persistent profile (cascade step 2, GoupixDex pattern) ─────

    @staticmethod
    def default_dedicated_profile_dir() -> Path:
        """App-owned Storyblok browser profile (kept between runs so login persists)."""
        base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
        return Path(base) / "DevLeadHunter" / "storyblok-profile"

    @property
    def dedicated_profile_dir(self) -> Path:
        """The persistent profile directory used by the login helper and clip capture."""
        return self._dedicated_profile_dir

    def read_persisted_state(self) -> dict | None:
        """Return the last recorded dedicated-profile session info, or ``None``."""
        path = self._dedicated_profile_dir / _SESSION_STATE_FILE
        if not path.is_file():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            logger.debug("read_persisted_state: %s", exc)
            return None
        return data if isinstance(data, dict) else None

    def write_persisted_state(self, *, logged_in: bool, email: str | None = None) -> None:
        """Persist the dedicated-profile login state next to the profile (best-effort)."""
        path = self._dedicated_profile_dir / _SESSION_STATE_FILE
        payload = {
            "logged_in": logged_in,
            "email": email,
            "last_seen": datetime.now(UTC).isoformat(),
        }
        try:
            self._dedicated_profile_dir.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        except OSError as exc:
            logger.warning("write_persisted_state: %s", exc)

    # ── State summary for the UI ─────────────────────────────────────────────

    def state(self) -> StoryblokSessionState:
        """Best-effort connection state without launching a browser.

        ``ready`` when a machine session token is present OR the dedicated profile
        last recorded a login; ``needs_login`` otherwise. A live probe (which can
        also return ``busy``) is done by the clip service when it actually runs.
        """
        if self.resolve_machine_seed() is not None:
            return "ready"
        persisted = self.read_persisted_state()
        if persisted and persisted.get("logged_in"):
            return "ready"
        return "needs_login"


storyblok_session_service = StoryblokSessionService()
