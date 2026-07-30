"""Guarantee a usable Chrome on the end user's machine.

The desktop app must stay plug-and-play: someone who downloads it should never
have to install anything by hand. nodriver needs a real Chrome binary, so this
module finds the one already installed and, failing that, downloads a private
copy of Chrome for Testing next to the app's data.

The download is deliberate and one-shot: ~150 MB fetched once, kept under the
user's local app data, never touching the system Chrome or its profile.
"""

from __future__ import annotations

import io
import logging
import os
import platform
import shutil
import zipfile
from pathlib import Path
from urllib.request import urlopen

logger = logging.getLogger(__name__)

# Chrome for Testing: the only Chrome build Google publishes for automation.
_LATEST_STABLE_URL = "https://googlechromelabs.github.io/chrome-for-testing/last-known-good-versions.json"
_DOWNLOAD_TIMEOUT_SECONDS = 600

# Où l'utilisateur a le plus de chances d'avoir déjà Chrome installé.
_WINDOWS_CANDIDATES: tuple[str, ...] = (
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe",
)
_MACOS_CANDIDATES: tuple[str, ...] = (
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
)
_LINUX_BINARIES: tuple[str, ...] = ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser")


def app_data_dir() -> Path:
    """Per-user directory holding the app's private Chrome."""
    if platform.system() == "Windows":
        base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
    elif platform.system() == "Darwin":
        base = str(Path.home() / "Library" / "Application Support")
    else:
        base = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
    return Path(base) / "DevLeadHunter"


def find_installed_chrome() -> str | None:
    """Locate a Chrome already present on this machine.

    Returns:
        Absolute path to a usable Chrome, or ``None`` when none is installed.
    """
    configured = (os.environ.get("SCRAPER_CHROME_EXECUTABLE") or "").strip()
    if configured and Path(configured).is_file():
        return configured

    system = platform.system()
    if system == "Windows":
        for candidate in _WINDOWS_CANDIDATES:
            expanded = Path(os.path.expandvars(candidate))
            if expanded.is_file():
                return str(expanded)
    elif system == "Darwin":
        for candidate in _MACOS_CANDIDATES:
            if Path(candidate).is_file():
                return candidate
    else:
        for binary in _LINUX_BINARIES:
            found = shutil.which(binary)
            if found:
                return found

    return _managed_chrome_path()


def _managed_chrome_path() -> str | None:
    """Path of the Chrome this module downloaded previously, when still present."""
    root = app_data_dir() / "chrome"
    if not root.is_dir():
        return None
    names = ("chrome.exe", "Google Chrome for Testing", "chrome")
    for name in names:
        for found in root.rglob(name):
            if found.is_file():
                return str(found)
    return None


def _download_platform() -> str | None:
    """Chrome-for-Testing platform key matching this machine."""
    system = platform.system()
    is_64bit = platform.machine().endswith("64")
    if system == "Windows":
        return "win64" if is_64bit else "win32"
    if system == "Darwin":
        return "mac-arm64" if platform.machine() == "arm64" else "mac-x64"
    if system == "Linux":
        return "linux64" if is_64bit else None
    return None


def download_chrome_for_testing() -> str:
    """Fetch a private Chrome for Testing and return its executable path.

    Returns:
        Absolute path to the freshly downloaded Chrome.

    Raises:
        RuntimeError: The platform is unsupported, or the download/unpack failed.
    """
    target_platform = _download_platform()
    if not target_platform:
        raise RuntimeError(f"Plateforme non supportée pour le téléchargement de Chrome : {platform.platform()}")

    import json

    with urlopen(_LATEST_STABLE_URL, timeout=60) as response:
        versions = json.loads(response.read().decode("utf-8"))

    downloads = versions["channels"]["Stable"]["downloads"]["chrome"]
    url = next((entry["url"] for entry in downloads if entry["platform"] == target_platform), None)
    if not url:
        raise RuntimeError(f"Aucun build Chrome for Testing pour {target_platform}.")

    destination = app_data_dir() / "chrome"
    destination.mkdir(parents=True, exist_ok=True)
    logger.info("Downloading Chrome for Testing (%s) — this happens once", target_platform)

    with urlopen(url, timeout=_DOWNLOAD_TIMEOUT_SECONDS) as response:
        payload = response.read()
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        archive.extractall(destination)

    executable = _managed_chrome_path()
    if not executable:
        raise RuntimeError("Chrome téléchargé mais introuvable après décompression.")

    if platform.system() != "Windows":
        Path(executable).chmod(0o755)
    logger.info("Chrome for Testing ready at %s", executable)
    return executable


def ensure_chrome(*, allow_download: bool = True) -> str:
    """Return a usable Chrome path, downloading one only if none is installed.

    Args:
        allow_download: When False, never fetch — only report what is present.

    Returns:
        Absolute path to a usable Chrome.

    Raises:
        RuntimeError: No Chrome available and downloading is disabled or failed.
    """
    existing = find_installed_chrome()
    if existing:
        os.environ["SCRAPER_CHROME_EXECUTABLE"] = existing
        return existing

    if not allow_download:
        raise RuntimeError("Aucun Chrome détecté sur cette machine.")

    downloaded = download_chrome_for_testing()
    os.environ["SCRAPER_CHROME_EXECUTABLE"] = downloaded
    return downloaded
