"""
Prospect data models.
"""
from typing import Optional
from pydantic import BaseModel, Field, EmailStr
from enums.source import Source


class ProspectBase(BaseModel):
    """
    Base prospect model with common fields.
    
    Attributes:
        name: Business name (required)
        address: Street address (optional)
        city: City name (optional)
        phone: Phone number (optional)
        email: Email address (optional)
        website: Website URL (optional)
        category: Business category (required)
        source: Data source identifier (required)
        confidence: Confidence score between 1 and 4 (required)
    """
    
    name: str = Field(..., min_length=1, description="Business name")
    address: Optional[str] = Field(None, description="Street address")
    city: Optional[str] = Field(None, description="City name")
    phone: Optional[str] = Field(None, description="Phone number")
    email: Optional[EmailStr] = Field(None, description="Email address")
    website: Optional[str] = Field(None, description="Website URL")
    category: str = Field(..., description="Business category")
    source: Source = Field(..., description="Data source identifier")
    confidence: int = Field(..., ge=1, le=4, example=3, description="Confidence score 1-4")


class ProspectCreate(ProspectBase):
    """
    Model for creating a new prospect.
    Inherits all fields from ProspectBase.
    """
    pass


class ProspectUpdate(BaseModel):
    """
    Model for updating an existing prospect.
    
    All fields are optional to allow partial updates.
    """
    
    name: Optional[str] = Field(None, description="Business name")
    address: Optional[str] = Field(None, description="Street address")
    city: Optional[str] = Field(None, description="City name")
    phone: Optional[str] = Field(None, description="Phone number")
    email: Optional[EmailStr] = Field(None, description="Email address")
    website: Optional[str] = Field(None, description="Website URL")
    category: Optional[str] = Field(None, description="Business category")
    source: Optional[Source] = Field(None, description="Data source identifier")
    confidence: Optional[int] = Field(None, ge=1, le=4, description="Confidence score 1-4")


class Prospect(ProspectBase):
    """
    Complete prospect model with ID.
    
    Attributes:
        id: Unique prospect identifier
    """
    
    id: str = Field(..., description="Unique prospect identifier")
    
    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "id": "prospect_123",
                "name": "Le Bon Restaurant",
                "address": "123 Rue de la Paix",
                "city": "Paris",
                "email": "contact@bonrestaurant.fr",
                "website": "https://www.bonrestaurant.fr",
                "category": "restaurant",
                "source": "google",
                "confidence": 3,
                "phone": "+33123456789"
            }
        }
