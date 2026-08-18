"""Status of the demo site client's collaboration on its Storyblok space."""

from enum import Enum


class StoryblokCollaboratorStatus(str, Enum):
    """
    Where the client stands on the Storyblok CMS handover.

    Persisted on ``demo_sites.storyblok_collaborator_status`` (NULL until first
    observed). ``UNKNOWN`` is a transient read failure — callers keep the previous
    value rather than overwriting a known state with it.
    """

    NOT_INVITED = "not_invited"
    PENDING = "pending"
    JOINED = "joined"
    UNKNOWN = "unknown"
