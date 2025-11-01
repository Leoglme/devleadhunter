"""
User Pydantic schemas for request/response validation.
"""
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field

from enums.user_role import UserRole


class UserBase(BaseModel):
    """
    Base user schema with common fields.
    
    Attributes:
        name: User's full name
        email: User's email address
        role: User role
    """
    name: str = Field(..., min_length=1, max_length=255, description="User's full name")
    email: EmailStr = Field(..., description="User's email address")
    role: UserRole = Field(default=UserRole.USER, description="User role")


class UserCreate(UserBase):
    """
    Schema for creating a new user.
    
    Attributes:
        password: User's password
    """
    password: str = Field(..., min_length=6, max_length=100, description="User's password")


class UserUpdate(BaseModel):
    """
    Schema for updating user information.
    
    Attributes:
        name: User's full name
        email: User's email address
    """
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="User's full name")
    email: Optional[EmailStr] = Field(None, description="User's email address")


class UserResponse(UserBase):
    """
    Schema for user response.
    
    Attributes:
        id: User's unique identifier
        is_active: Whether the user is active
        created_at: Timestamp when user was created
        updated_at: Timestamp when user was last updated
    """
    id: int
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        """Pydantic configuration."""
        from_attributes = True


class UserLogin(BaseModel):
    """
    Schema for user login.
    
    Attributes:
        email: User's email address
        password: User's password
    """
    email: EmailStr = Field(..., description="User's email address")
    password: str = Field(..., min_length=1, description="User's password")


class Token(BaseModel):
    """
    Schema for authentication token.
    
    Attributes:
        access_token: JWT access token
        token_type: Token type (usually 'bearer')
    """
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """
    Schema for token data.
    
    Attributes:
        email: User's email from token
    """
    email: Optional[str] = None

