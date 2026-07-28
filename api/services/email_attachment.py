"""Shared email attachment value object.

Its own leaf module so the send paths (Resend, Gmail) and their callers
(``email_sending_service``, ``order_service``) can share it without importing
each other.
"""

from dataclasses import dataclass


@dataclass
class EmailAttachment:
    """A file attached to an outgoing email (e.g. an invoice PDF)."""

    filename: str
    content: bytes
    content_type: str = "application/pdf"
