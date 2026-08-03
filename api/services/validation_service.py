"""
Validation service for prospect data.
"""

import re
import unicodedata
from typing import ClassVar


class ValidationService:
    """
    Service for validating prospect data.

    This service provides utility methods for validating
    and checking prospect information such as websites,
    contact details, etc.
    """

    # Lowercase markers of a platform's OWN meta description scraped by mistake
    # (e.g. the Google Maps page meta instead of the business description).
    GENERIC_PLATFORM_DESCRIPTION_MARKERS: ClassVar[tuple[str, ...]] = (
        "google maps",
        "find local businesses",
        "view maps and get driving directions",
        "trouvez des commerces locaux",
        "consultez des plans et calculez des itinéraires",
    )

    # Tokens too common to prove a description talks about THIS business.
    _WEAK_MENTION_TOKENS: ClassVar[frozenset[str]] = frozenset(
        {"les", "des", "sur", "sous", "chez", "sarl", "sas", "eurl", "ets", "saint", "sainte"}
    )

    @staticmethod
    def is_valid_website(url: str | None) -> bool:
        """
        Check if a website URL is valid (not a social media platform).

        This method filters out social media URLs and determines
        if a URL points to a real business website.

        Args:
            url: Website URL to validate

        Returns:
            True if URL points to a valid business website, False otherwise

        Examples:
            >>> ValidationService.is_valid_website("https://www.example.com")
            True

            >>> ValidationService.is_valid_website("https://www.facebook.com/mybusiness")
            False

            >>> ValidationService.is_valid_website("http://example.fr")
            True
        """
        if not url:
            return False

        # Remove protocol if present
        url_clean = url.replace("http://", "").replace("https://", "").replace("www.", "").strip()

        # List of invalid domains (social media platforms)
        invalid_domains = [
            "facebook.com",
            "instagram.com",
            "twitter.com",
            "linkedin.com",
            "youtube.com",
            "pinterest.com",
            "tiktok.com",
            "snapchat.com",
        ]

        # Check if URL contains any invalid domain
        for domain in invalid_domains:
            if domain in url_clean:
                return False

        # Check if it's a real website (contains a dot and not just a domain name)
        if "." in url_clean and not url_clean.startswith("www."):
            # Basic validation: should have at least domain name
            parts = url_clean.split("/")
            domain = parts[0]

            # Domain should have at least one dot (e.g., example.com)
            if domain.count(".") >= 1:
                # Split domain and check parts
                domain_parts = domain.split(".")
                # Should have at least 2 parts (name and extension)
                if len(domain_parts) >= 2 and len(domain_parts[0]) > 0:
                    return True

        return False

    @staticmethod
    def _significant_tokens(text: str) -> set[str]:
        """
        Split a text into lowercase, accent-free tokens usable for matching.

        Args:
            text: Any human text (business name, city, description).

        Returns:
            Tokens of 3+ characters, minus the too-common ones.
        """
        decomposed = unicodedata.normalize("NFD", text.lower())
        without_accents = "".join(char for char in decomposed if unicodedata.category(char) != "Mn")
        tokens = set(re.findall(r"[a-z0-9]{3,}", without_accents))
        return tokens - ValidationService._WEAK_MENTION_TOKENS

    @classmethod
    def is_generic_platform_description(cls, description: str | None) -> bool:
        """
        Check whether a description is a platform's own boilerplate, not the business's.

        Real-world case: the Google Maps search page meta ("Find local businesses,
        view maps and get driving directions in Google Maps.") scraped as the
        prospect's description and displayed verbatim on his demo site.

        Args:
            description: Scraped description text.

        Returns:
            True when the text is platform boilerplate and must be dropped.
        """
        if not description:
            return False
        lowered = description.lower()
        return any(marker in lowered for marker in cls.GENERIC_PLATFORM_DESCRIPTION_MARKERS)

    @classmethod
    def description_mentions_business(
        cls,
        description: str,
        business_name: str | None,
        city: str | None,
    ) -> bool:
        """
        Check whether a description talks about the given business at all.

        Used on untrusted description sources (a page meta description): a text
        that names neither the business nor its city is about something else.
        With no name and no city to compare against, the check passes.

        Args:
            description: Scraped description text.
            business_name: Prospect business name.
            city: Prospect city.

        Returns:
            True when the description shares a significant token with the
            business name or the city.
        """
        expected_tokens = cls._significant_tokens(f"{business_name or ''} {city or ''}")
        if not expected_tokens:
            return True
        return bool(cls._significant_tokens(description) & expected_tokens)

    @staticmethod
    def is_valid_email(email: str | None) -> bool:
        """
        Check if an email address is valid.

        Args:
            email: Email address to validate

        Returns:
            True if email is valid, False otherwise
        """
        if not email:
            return False

        # Basic email pattern validation
        import re

        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        return bool(re.match(pattern, email))

    @staticmethod
    def normalize_phone(phone: str | None) -> str | None:
        """
        Normalize phone number format.

        Removes spaces, dashes, and other formatting characters
        to standardize phone number format.

        Args:
            phone: Phone number to normalize

        Returns:
            Normalized phone number or None if invalid
        """
        if not phone:
            return None

        # Remove common formatting characters
        normalized = phone.replace(" ", "").replace("-", "").replace(".", "").replace("(", "").replace(")", "")

        # Remove leading + if present
        if normalized.startswith("+"):
            normalized = normalized[1:]

        # Check if it's a valid phone number (at least 9 digits)
        if normalized and normalized.isdigit() and len(normalized) >= 9:
            return normalized

        return phone  # Return original if normalization failed

    @staticmethod
    def calculate_confidence_score(
        phone: str | None = None, address: str | None = None, email: str | None = None, website: str | None = None
    ) -> int:
        """
        Calculate confidence score based on data completeness.

        Score rules:
        - Base score: 1 (for name, category, source)
        - +1 if phone is present
        - +1 if address is present with street number
        - -1 if website is present and valid
        - +1 if email is present and valid
        - Maximum score: 4

        Args:
            phone: Phone number
            address: Full address
            email: Email address
            website: Website URL

        Returns:
            Confidence score from 1 to 4
        """
        score = 1  # Base score

        if phone and phone.strip():
            score += 1

        if address and address.strip() and any(c.isdigit() for c in address):
            score += 1

        if website and ValidationService.is_valid_website(website):
            score -= 1

        if email and ValidationService.is_valid_email(email):
            score += 1

        return min(max(score, 1), 4)


# Global service instance
validation_service = ValidationService()
