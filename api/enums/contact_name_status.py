"""Statuses of the decision-maker contact stored on a prospect enrichment."""

from enum import Enum


class ContactNameStatus(str, Enum):
    """How the TRUSTED contact name (contact_first/last_name) was established.

    Only trusted names feed « Bonjour {Prénom} » — a proposal never does.
    """

    AUTO = "auto"  # cascade output: primary source + geo confirmed
    CONFIRMED = "confirmed"  # a proposal the user explicitly confirmed
    MANUAL = "manual"  # typed by hand in the drawer


class ProposedContactState(str, Enum):
    """Lifecycle of the « à confirmer » name proposal shown in the drawer."""

    PENDING = "pending"  # waiting for the user's confirm / reject
    REJECTED = "rejected"  # rejected once — the same identity is never re-proposed
