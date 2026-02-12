#!/usr/bin/env python3
"""
Validate and fix salon settings database.

This script checks if salon settings exist and ensures all required fields
have valid values. It will create settings if missing or fix NULL values.

Usage:
    python scripts/validate_settings.py
    # or via docker:
    docker compose exec api python scripts/validate_settings.py
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import SessionLocal
from app.models.settings import SalonSettings
from app.utils import generate_ulid


def validate_and_fix_settings():
    """Validate settings and fix any issues."""
    db = SessionLocal()

    try:
        print("🔍 Checking salon settings...")
        print("-" * 60)

        # Get or create settings
        settings = db.query(SalonSettings).first()

        if not settings:
            print("⚠️  No settings found. Creating default settings...")
            settings = SalonSettings(
                id=generate_ulid(),
                salon_name="My Salon",
                salon_address="123 Main Street",
                salon_city="Mumbai",
                salon_state="Maharashtra",
                salon_pincode="400001",
                contact_phone="+91 9876543210",
                contact_email="info@mysalon.com",
                gstin="27XXXXX1234X1ZX",
                invoice_prefix="SAL",
                daily_revenue_target_paise=2000000,  # ₹20,000
                daily_services_target=25,
                receipt_show_gstin=True,
                receipt_show_logo=False,
                primary_color="#000000"
            )
            db.add(settings)
            db.commit()
            db.refresh(settings)
            print("✅ Default settings created successfully!")
            print()
            print("⚠️  IMPORTANT: Please update these settings via the UI:")
            print("   - Salon name, address, and contact details")
            print("   - GSTIN and other tax information")
            print("   - Daily revenue and service targets")
            return True

        # Validate and fix existing settings
        print("✅ Settings record found")
        print()

        issues_fixed = []

        # Check required string fields
        required_strings = {
            'salon_name': 'My Salon',
            'salon_address': '123 Main Street',
            'invoice_prefix': 'SAL'
        }

        for field, default in required_strings.items():
            value = getattr(settings, field)
            if not value or value.strip() == '':
                setattr(settings, field, default)
                issues_fixed.append(f"Set {field} = '{default}'")

        # Check required integer fields with defaults
        required_ints = {
            'daily_revenue_target_paise': 2000000,  # ₹20,000
            'daily_services_target': 25
        }

        for field, default in required_ints.items():
            value = getattr(settings, field)
            if value is None:
                setattr(settings, field, default)
                issues_fixed.append(f"Set {field} = {default} (₹{default/100:,.2f})" if 'paise' in field else f"Set {field} = {default}")

        # Check boolean fields
        if settings.receipt_show_gstin is None:
            settings.receipt_show_gstin = True
            issues_fixed.append("Set receipt_show_gstin = True")

        if settings.receipt_show_logo is None:
            settings.receipt_show_logo = False
            issues_fixed.append("Set receipt_show_logo = False")

        # Check color field
        if not settings.primary_color or settings.primary_color == '':
            settings.primary_color = '#000000'
            issues_fixed.append("Set primary_color = '#000000'")

        # Commit fixes if any
        if issues_fixed:
            db.commit()
            print("🔧 Fixed the following issues:")
            for issue in issues_fixed:
                print(f"   ✓ {issue}")
            print()
        else:
            print("✅ All required fields are properly set")
            print()

        # Display current settings
        print("📋 Current Settings Summary:")
        print(f"   Salon Name: {settings.salon_name}")
        print(f"   Address: {settings.salon_address}")
        print(f"   City: {settings.salon_city or 'Not set'}")
        print(f"   Phone: {settings.contact_phone or 'Not set'}")
        print(f"   Email: {settings.contact_email or 'Not set'}")
        print(f"   GSTIN: {settings.gstin or 'Not set'}")
        print(f"   Invoice Prefix: {settings.invoice_prefix}")
        print(f"   Daily Revenue Target: ₹{settings.daily_revenue_target_paise / 100:,.2f}")
        print(f"   Daily Services Target: {settings.daily_services_target}")
        print()

        # Validation checks
        warnings = []

        if not settings.gstin or settings.gstin == '27XXXXX1234X1ZX':
            warnings.append("GSTIN not configured - update for tax compliance")

        if not settings.contact_phone or settings.contact_phone.startswith('+91 987'):
            warnings.append("Contact phone is default - update with real number")

        if not settings.contact_email or 'mysalon.com' in (settings.contact_email or ''):
            warnings.append("Contact email is default - update with real email")

        if settings.salon_name == 'My Salon':
            warnings.append("Salon name is default - update with your salon name")

        if warnings:
            print("⚠️  Warnings:")
            for warning in warnings:
                print(f"   • {warning}")
            print()
        else:
            print("✅ All settings look good!")
            print()

        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        db.close()


if __name__ == '__main__':
    print()
    print("=" * 60)
    print("  Salon Settings Validator")
    print("=" * 60)
    print()

    success = validate_and_fix_settings()

    print("=" * 60)
    if success:
        print("✅ Validation complete!")
    else:
        print("❌ Validation failed - check errors above")
        sys.exit(1)
    print()
