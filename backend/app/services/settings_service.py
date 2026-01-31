"""Service for managing salon settings."""

from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from app.models.settings import SalonSettings


class SettingsService:
    """Service for managing salon settings (singleton pattern)."""

    @staticmethod
    def get_settings(db: Session) -> Optional[SalonSettings]:
        """
        Get salon settings.

        Returns the first (and should be only) settings record.

        Args:
            db: Database session

        Returns:
            SalonSettings or None if not initialized
        """
        return db.query(SalonSettings).first()

    @staticmethod
    def get_or_create_settings(db: Session) -> SalonSettings:
        """
        Get existing settings or create default settings.

        Args:
            db: Database session

        Returns:
            SalonSettings instance
        """
        settings = SettingsService.get_settings(db)

        if not settings:
            # Create default settings
            settings = SalonSettings(
                salon_name="SalonOS",
                salon_address="123 Main Street, City, State",
                salon_city="City",
                salon_state="State",
                contact_phone="+91 98765 43210",
                invoice_prefix="SAL",
                receipt_show_gstin=True,
                receipt_show_logo=False,
                primary_color="#000000"
            )
            db.add(settings)
            db.commit()
            db.refresh(settings)

        return settings

    @staticmethod
    def update_settings(
        db: Session,
        updates: Dict[str, Any]
    ) -> SalonSettings:
        """
        Update salon settings.

        Args:
            db: Database session
            updates: Dictionary of fields to update

        Returns:
            Updated SalonSettings instance

        Raises:
            ValueError: If settings not found
        """
        settings = SettingsService.get_or_create_settings(db)

        # Update only provided fields
        for field, value in updates.items():
            if hasattr(settings, field) and value is not None:
                setattr(settings, field, value)

        db.commit()
        db.refresh(settings)

        return settings

    @staticmethod
    def reset_to_defaults(db: Session) -> SalonSettings:
        """
        Reset settings to default values.

        Args:
            db: Database session

        Returns:
            Reset SalonSettings instance
        """
        settings = SettingsService.get_or_create_settings(db)

        # Reset to defaults
        settings.salon_name = "SalonOS"
        settings.salon_tagline = None
        settings.salon_address = "123 Main Street, City, State"
        settings.salon_city = "City"
        settings.salon_state = "State"
        settings.salon_pincode = None
        settings.contact_phone = "+91 98765 43210"
        settings.contact_email = None
        settings.contact_website = None
        settings.gstin = None
        settings.pan = None
        settings.receipt_header_text = None
        settings.receipt_footer_text = None
        settings.receipt_show_gstin = True
        settings.receipt_show_logo = False
        settings.logo_url = None
        settings.primary_color = "#000000"
        settings.invoice_prefix = "SAL"
        settings.invoice_terms = None

        db.commit()
        db.refresh(settings)

        return settings
