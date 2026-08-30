"""User module model — which activatable modules a user has turned on."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from core.database import Base


class UserModule(Base):
    """A user's activation state for one tool module.

    Only non-base modules get a row: the base module (websites) is always active.
    Scoped to the user like everything else in the product.

    Attributes:
        user_id: Owner of the activation.
        module: The module value (see :class:`~enums.app_module.AppModule`).
        is_active: Whether the module is currently on.
        activated_at: When it was last activated.
    """

    __tablename__ = "user_modules"
    __table_args__ = (UniqueConstraint("user_id", "module", name="uq_user_modules_user_module"),)

    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    module: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    activated_at: Mapped[datetime | None] = mapped_column(nullable=True)

    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime | None] = mapped_column(onupdate=func.now(), nullable=True)

    def __repr__(self) -> str:
        """String representation of the user module."""
        return f"<UserModule user_id={self.user_id} module={self.module} active={self.is_active}>"
