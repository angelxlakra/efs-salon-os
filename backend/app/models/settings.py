"""Salon settings model for configurable salon information."""

from sqlalchemy import Column, String, Text, Boolean
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

    def __repr__(self):
        return f"<SalonSettings {self.salon_name}>"
