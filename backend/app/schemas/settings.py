"""Pydantic schemas for salon settings."""

from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field, field_validator


class SalonSettingsBase(BaseModel):
    """Base schema for salon settings."""
    salon_name: str = Field(..., min_length=1, max_length=255)
    salon_tagline: Optional[str] = Field(None, max_length=255)
    salon_address: str = Field(..., min_length=1)
    salon_city: Optional[str] = Field(None, max_length=100)
    salon_state: Optional[str] = Field(None, max_length=100)
    salon_pincode: Optional[str] = Field(None, max_length=20)

    contact_phone: Optional[str] = Field(None, max_length=20)
    contact_email: Optional[str] = Field(None, max_length=255)
    contact_website: Optional[str] = Field(None, max_length=255)

    gstin: Optional[str] = Field(None, max_length=15)
    pan: Optional[str] = Field(None, max_length=10)

    receipt_header_text: Optional[str] = None
    receipt_footer_text: Optional[str] = None
    receipt_show_gstin: bool = True
    receipt_show_logo: bool = False

    logo_url: Optional[str] = Field(None, max_length=500)
    primary_color: Optional[str] = Field("#000000", max_length=7)

    invoice_prefix: str = Field("SAL", min_length=1, max_length=10)
    invoice_terms: Optional[str] = None

    @field_validator('gstin')
    @classmethod
    def validate_gstin(cls, v):
        """Validate GSTIN format."""
        if v and len(v) != 15:
            raise ValueError('GSTIN must be 15 characters')
        return v

    @field_validator('pan')
    @classmethod
    def validate_pan(cls, v):
        """Validate PAN format."""
        if v and len(v) != 10:
            raise ValueError('PAN must be 10 characters')
        return v.upper() if v else v

    @field_validator('primary_color')
    @classmethod
    def validate_color(cls, v):
        """Validate hex color format."""
        if v and not v.startswith('#'):
            raise ValueError('Color must be in hex format (#RRGGBB)')
        if v and len(v) != 7:
            raise ValueError('Color must be 7 characters (#RRGGBB)')
        return v


class SalonSettingsUpdate(BaseModel):
    """Schema for updating salon settings (all fields optional)."""
    salon_name: Optional[str] = Field(None, min_length=1, max_length=255)
    salon_tagline: Optional[str] = Field(None, max_length=255)
    salon_address: Optional[str] = None
    salon_city: Optional[str] = Field(None, max_length=100)
    salon_state: Optional[str] = Field(None, max_length=100)
    salon_pincode: Optional[str] = Field(None, max_length=20)

    contact_phone: Optional[str] = Field(None, max_length=20)
    contact_email: Optional[str] = Field(None, max_length=255)
    contact_website: Optional[str] = Field(None, max_length=255)

    gstin: Optional[str] = Field(None, max_length=15)
    pan: Optional[str] = Field(None, max_length=10)

    receipt_header_text: Optional[str] = None
    receipt_footer_text: Optional[str] = None
    receipt_show_gstin: Optional[bool] = None
    receipt_show_logo: Optional[bool] = None

    logo_url: Optional[str] = Field(None, max_length=500)
    primary_color: Optional[str] = Field(None, max_length=7)

    invoice_prefix: Optional[str] = Field(None, min_length=1, max_length=10)
    invoice_terms: Optional[str] = None


class SalonSettingsResponse(SalonSettingsBase):
    """Schema for salon settings response."""
    id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
