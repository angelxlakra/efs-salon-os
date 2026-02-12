"""Salon settings model for configurable salon information."""

from sqlalchemy import Column, String, Text, Boolean, Integer
from app.database import Base
from app.models.base import TimestampMixin, ULIDMixin


class SalonSettings(Base, ULIDMixin, TimestampMixin):
    """
    Salon configuration settings.

    Stores salon-wide settings like business information,
    receipt customization, and branding.

    Should only have one record (singleton pattern).
    """
    __tablename__ = "salon_settings"

    # Business Information
    salon_name = Column(String(255), nullable=False, default="SalonOS")
    salon_tagline = Column(String(255), nullable=True)
    salon_address = Column(Text, nullable=False)
    salon_city = Column(String(100), nullable=True)
    salon_state = Column(String(100), nullable=True)
    salon_pincode = Column(String(20), nullable=True)

    # Contact Information
    contact_phone = Column(String(20), nullable=True)
    contact_email = Column(String(255), nullable=True)
    contact_website = Column(String(255), nullable=True)

    # Tax Information
    gstin = Column(String(15), nullable=True)  # GST Identification Number
    pan = Column(String(10), nullable=True)     # PAN Card Number

    # Receipt Customization
    receipt_header_text = Column(Text, nullable=True)  # Custom header message
    receipt_footer_text = Column(Text, nullable=True)  # Custom footer message
    receipt_show_gstin = Column(Boolean, default=True)
    receipt_show_logo = Column(Boolean, default=False)

    # Branding
    logo_url = Column(String(500), nullable=True)  # Path to logo image
    primary_color = Column(String(7), nullable=True, default="#000000")  # Hex color

    # Invoice Settings
    invoice_prefix = Column(String(10), nullable=False, default="SAL")
    invoice_terms = Column(Text, nullable=True)  # Terms and conditions

    # Dashboard Goals
    daily_revenue_target_paise = Column(Integer, nullable=False, default=2000000)  # Default ₹20,000
    daily_services_target = Column(Integer, nullable=False, default=25)  # Default 25 services

    def __repr__(self):
        return f"<SalonSettings {self.salon_name}>"

    def to_dict(self):
        """Convert settings to dictionary for caching."""
        return {
            "id": self.id,
            "salon_name": self.salon_name,
            "salon_tagline": self.salon_tagline,
            "salon_address": self.salon_address,
            "salon_city": self.salon_city,
            "salon_state": self.salon_state,
            "salon_pincode": self.salon_pincode,
            "contact_phone": self.contact_phone,
            "contact_email": self.contact_email,
            "contact_website": self.contact_website,
            "gstin": self.gstin,
            "pan": self.pan,
            "receipt_header_text": self.receipt_header_text,
            "receipt_footer_text": self.receipt_footer_text,
            "receipt_show_gstin": self.receipt_show_gstin,
            "receipt_show_logo": self.receipt_show_logo,
            "logo_url": self.logo_url,
            "primary_color": self.primary_color,
            "invoice_prefix": self.invoice_prefix,
            "invoice_terms": self.invoice_terms,
            "daily_revenue_target_paise": self.daily_revenue_target_paise,
            "daily_services_target": self.daily_services_target,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
