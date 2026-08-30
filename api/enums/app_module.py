"""Activatable modules of the DevLeadHunter tool (a multi-module house)."""

from enum import Enum


class AppModule(str, Enum):
    """A tool module a user can run."""

    WEBSITES = "websites"  # module 1 — the base product, always active
    APPLE_WALLET = "apple_wallet"  # module 2 — loyalty cards


# Modules every user always has — never toggled off.
BASE_MODULES: frozenset[str] = frozenset({AppModule.WEBSITES.value})
