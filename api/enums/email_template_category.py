"""
Enum for the step of the sequence an email template is written for.

Stored as a plain string in a ``String`` column, following the Order/DemoSite
convention. It drives the tabs of the templates page: a first email and a
follow-up are never interchangeable, so mixing them in one list is misleading.
"""

from enum import Enum


class EmailTemplateCategory(str, Enum):
    """Which step of the cold-email sequence a template belongs to."""

    FIRST_EMAIL = "first_email"
    FOLLOW_UP = "follow_up"
