"""SMS lifecycle status enumeration."""

from enum import Enum


class SmsStatus(str, Enum):
    """Lifecycle of an outbound SMS.

    Attributes:
        PENDING: Queued, not yet sent to the provider.
        SENT: Accepted by the provider (has a provider message id).
        DELIVERED: Provider DLR confirmed delivery to the handset.
        FAILED: Provider rejected it, or DLR reported a permanent failure.
    """

    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"
