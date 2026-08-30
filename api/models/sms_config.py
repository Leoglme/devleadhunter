"""Per-user SMS sending configuration.

The smsmode account is a single platform account; what varies per user is the
**alphanumeric sender** (≤11 chars, e.g. « Dibodev »), configured here the same
way the email sending identity is configured per user. No API key is stored: the
key is a platform-level secret injected server-side.
"""

from datetime import datetime

from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from core.database import Base


class SmsConfig(Base):
    """A user's SMS sender identity + enable flag.

    Attributes:
        id: Unique identifier (auto-increment)
        user_id: Owner of the configuration (one row per user)
        sender: Alphanumeric sender id shown on the prospect's phone (≤11 chars)
        enabled: Whether the user opted the SMS channel on
        created_at: Creation timestamp
        updated_at: Last-update timestamp
    """

    __tablename__ = "sms_configs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, unique=True, index=True)
    sender: Mapped[str] = mapped_column(String(11), nullable=False, default="")
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime | None] = mapped_column(onupdate=func.now(), nullable=True)
