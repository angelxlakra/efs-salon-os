"""Pydantic schemas for salon settings."""

from typing import Optional
from datetime import date, datetime
from pydantic import BaseModel, Field, field_validator, model_validator


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

    gst_registered: bool = False
    gst_effective_from: Optional[date] = None
    invoice_prefix_service: str = Field("SRV", min_length=1, max_length=10)
    invoice_prefix_product: str = Field("PRD", min_length=1, max_length=10)
    default_service_sac_code: str = Field("999721", min_length=4, max_length=8)
    default_product_hsn_code: str = Field("3305", min_length=4, max_length=8)

    receipt_header_text: Optional[str] = None
    receipt_footer_text: Optional[str] = None
    receipt_show_gstin: bool = True
    receipt_show_logo: bool = False

    logo_url: Optional[str] = Field(None, max_length=500)
    primary_color: Optional[str] = Field("#000000", max_length=7)

    invoice_prefix: str = Field("SAL", min_length=1, max_length=10)
    invoice_terms: Optional[str] = None

    daily_revenue_target_paise: int = Field(2000000, ge=0, description="Daily revenue target in paise (₹20,000 default)")
    daily_services_target: int = Field(25, ge=0, description="Daily services count target")

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

    @model_validator(mode='after')
    def validate_gst_mode(self):
        """GST registration requires a GSTIN; invoice series must be distinguishable."""
        if self.gst_registered and not (self.gstin and self.gstin.strip()):
            raise ValueError('GSTIN is required when GST registration is enabled')
        if self.invoice_prefix_service == self.invoice_prefix_product:
            raise ValueError('Service and product invoice prefixes must differ')
        return self


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

    gst_registered: Optional[bool] = None
    gst_effective_from: Optional[date] = None
    invoice_prefix_service: Optional[str] = Field(None, min_length=1, max_length=10)
    invoice_prefix_product: Optional[str] = Field(None, min_length=1, max_length=10)
    default_service_sac_code: Optional[str] = Field(None, min_length=4, max_length=8)
    default_product_hsn_code: Optional[str] = Field(None, min_length=4, max_length=8)

    receipt_header_text: Optional[str] = None
    receipt_footer_text: Optional[str] = None
    receipt_show_gstin: Optional[bool] = None
    receipt_show_logo: Optional[bool] = None

    logo_url: Optional[str] = Field(None, max_length=500)
    primary_color: Optional[str] = Field(None, max_length=7)

    invoice_prefix: Optional[str] = Field(None, min_length=1, max_length=10)
    invoice_terms: Optional[str] = None

    daily_revenue_target_paise: Optional[int] = Field(None, ge=0)
    daily_services_target: Optional[int] = Field(None, ge=0)


class SalonSettingsResponse(SalonSettingsBase):
    """Schema for salon settings response."""
    id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
