"""Per-user SMS configuration — the alphanumeric sender + enable flag."""

from __future__ import annotations

import re

from sqlalchemy.orm import Session

from models.sms_config import SmsConfig

# Alphanumeric sender: letters/digits/spaces, 3–11 chars, at least one letter
# (French A2P rule; a purely numeric sender is not a valid alphanumeric OADC).
_SENDER_RE: re.Pattern[str] = re.compile(r"^(?=.*[A-Za-z])[A-Za-z0-9 ]{3,11}$")


class SmsConfigService:
    """Read/write a user's SMS sender identity."""

    def get(self, db: Session, user_id: int) -> SmsConfig | None:
        """Return the user's SMS config, or ``None`` when never set.

        Args:
            db: Active database session.
            user_id: Owner.

        Returns:
            The config row, or ``None``.
        """
        return db.query(SmsConfig).filter(SmsConfig.user_id == user_id).first()

    @staticmethod
    def is_valid_sender(sender: str) -> bool:
        """Whether *sender* is a valid French alphanumeric sender id.

        Args:
            sender: Candidate sender.

        Returns:
            ``True`` when 3–11 chars, alphanumeric/space, with at least one letter.
        """
        return bool(_SENDER_RE.match(sender or ""))

    def upsert(self, db: Session, user_id: int, *, sender: str, enabled: bool) -> SmsConfig:
        """Create or update the user's SMS config.

        Args:
            db: Active database session.
            user_id: Owner.
            sender: Alphanumeric sender id.
            enabled: Whether the SMS channel is on.

        Returns:
            The persisted config.

        Raises:
            ValueError: When *sender* is invalid (and the channel is enabled).
        """
        cleaned = (sender or "").strip()
        if enabled and not self.is_valid_sender(cleaned):
            raise ValueError("Expéditeur invalide : 3 à 11 caractères, lettres/chiffres, au moins une lettre.")
        config = self.get(db, user_id)
        if config is None:
            config = SmsConfig(user_id=user_id)
            db.add(config)
        config.sender = cleaned
        config.enabled = enabled
        db.commit()
        db.refresh(config)
        return config


sms_config_service = SmsConfigService()
