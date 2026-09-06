"""
Enum for the touch of the SMS sequence a template is written for.

Same split as the cold-email library: a first contact (prospects reached by SMS
first, a mobile but no email) and a follow-up (prospects who ignored the email)
are never interchangeable, so the library is filtered by category.
"""

from enum import Enum


class SmsTemplateCategory(str, Enum):
    """Which touch of the SMS sequence a template belongs to."""

    FIRST_CONTACT = "first_contact"
    FOLLOW_UP = "follow_up"
