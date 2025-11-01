"""
User model for authentication and authorization.
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import Column, Integer, String, Boolean, Enum, DateTime
from sqlalchemy.sql import func

from core.database import Base
from enums.user_role import UserRole


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
    """
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    email = Column(String(255), nullable=False, unique=True, index=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), default=UserRole.USER, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)
    
    def __repr__(self) -> str:
        """String representation of the user."""
        return f"<User id={self.id} name={self.name} email={self.email} role={self.role}>"

