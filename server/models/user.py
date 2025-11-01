"""
User model for authentication and authorization.
"""
from datetime import datetime
from typing import Optional, TYPE_CHECKING
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from core.database import Base
from enums.user_role import UserRole

if TYPE_CHECKING:
    from models.credit_transaction import CreditTransaction


class User(Base):
    """
    User model for authentication and authorization.
    
    Attributes:
        id: Unique identifier
        name: User's full name
        email: User's email address (unique)
        hashed_password: Hashed password
        role: User role (USER or ADMIN)
        is_active: Whether the user is active
        created_at: Timestamp when user was created
        updated_at: Timestamp when user was last updated
        credit_transactions: Relationship to credit transactions
    """
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), default=UserRole.USER.value, nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    updated_at: Mapped[Optional[datetime]] = mapped_column(onupdate=func.now(), nullable=True)
    
    # Relationship to credit transactions
    credit_transactions: Mapped[list["CreditTransaction"]] = relationship(
        "CreditTransaction",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        """String representation of the user."""
        return f"<User id={self.id} name={self.name} email={self.email} role={self.role}>"

