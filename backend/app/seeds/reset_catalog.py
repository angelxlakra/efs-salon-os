"""Reset catalog by clearing and re-seeding service categories.

This script:
1. Deletes all services
2. Deletes all service categories
3. Re-creates default service categories

⚠️  WARNING: This will delete all catalog data and recreate defaults!

Run with: docker compose exec api python -m app.seeds.reset_catalog
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.service import Service, ServiceCategory


def clear_catalog(db: Session):
    """Clear all services and categories."""
    print("Clearing existing catalog...")

    # Delete services first
    services_count = db.query(Service).count()
    if services_count > 0:
        db.query(Service).delete()
        print(f"  [OK] Deleted {services_count} services")

    # Delete categories
    categories_count = db.query(ServiceCategory).count()
    if categories_count > 0:
        db.query(ServiceCategory).delete()
        print(f"  [OK] Deleted {categories_count} categories")

    db.commit()


def seed_categories(db: Session):
    """Create default service categories."""
    print("Creating default service categories...")

    categories = [
        ServiceCategory(
            name="Haircut & Styling",
            description="Hair cutting and styling services",
            display_order=1,
            is_active=True
        ),
        ServiceCategory(
            name="Hair Color & Treatment",
            description="Hair coloring, highlights, and treatment services",
            display_order=2,
            is_active=True
        ),
        ServiceCategory(
            name="Facial & Skin Care",
            description="Facial treatments and skin care services",
            display_order=3,
            is_active=True
        ),
        ServiceCategory(
            name="Spa & Massage",
            description="Spa treatments and massage services",
            display_order=4,
            is_active=True
        ),
        ServiceCategory(
            name="Makeup",
            description="Makeup services for all occasions",
            display_order=5,
            is_active=True
        ),
        ServiceCategory(
            name="Nail Care",
            description="Manicure, pedicure, and nail art",
            display_order=6,
            is_active=True
        ),
    ]

    db.add_all(categories)
    db.commit()

    print(f"  [OK] Created {len(categories)} service categories")
    return categories


def main():
    """Main reset function."""
    print("\n" + "=" * 60)
    print("SalonOS - Reset Catalog (Clear + Re-seed)")
    print("=" * 60)
    print("\n⚠️  WARNING: This will delete ALL catalog data and recreate defaults!")
    print("This action cannot be undone.\n")

    db = SessionLocal()

    try:
        # Clear existing data
        clear_catalog(db)

        # Re-seed categories
        categories = seed_categories(db)

        print("\n" + "=" * 60)
        print("[SUCCESS] Catalog reset successfully!")
        print("=" * 60)
        print("\nSummary:")
        print(f"  - Service Categories: {len(categories)}")
        print("\nYou can now add services to these categories.\n")

    except Exception as e:
        db.rollback()
        print(f"\n[ERROR] Error resetting catalog: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
