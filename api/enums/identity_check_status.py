"""Cross-source identity check of a prospect (registry vs Google Maps place)."""

from enum import Enum


class IdentityCheckStatus(str, Enum):
    """Outcome of comparing the two identity anchors of a prospect.

    The registry match (SIREN, siège) and the Maps place the enrichment was
    read from must designate the same business — a mismatch means one of them
    is a homonym and nothing should be trusted automatically.
    """

    COHERENT = "coherent"  # both anchors point at the same département
    CONFLICT = "conflict"  # anchors disagree — human arbitration required
