"""Clear all services and categories from the catalog.

This script removes:
- All services
- All service categories

⚠️  WARNING: This will delete all catalog data. Use with caution!

Run with: docker compose exec api python -m app.seeds.clear_catalog
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.service import Service, ServiceCategory


def clear_services(db: Session):
    """Delete all services."""
    print("Clearing services...")

    services_count = db.query(Service).count()
    if services_count == 0:
        print("  [INFO] No services found. Skipping...")
        return 0

    db.query(Service).delete()
    db.commit()

    print(f"  [OK] Deleted {services_count} services")
    return services_count


def clear_categories(db: Session):
    """Delete all service categories."""
    print("Clearing service categories...")

    categories_count = db.query(ServiceCategory).count()
    if categories_count == 0:
        print("  [INFO] No categories found. Skipping...")
        return 0

    db.query(ServiceCategory).delete()
    db.commit()

    print(f"  [OK] Deleted {categories_count} categories")
    return categories_count


def main():
    """Main clearing function."""
    print("\n" + "=" * 60)
    print("SalonOS - Clear Catalog Data")
    print("=" * 60)
    print("\n⚠️  WARNING: This will delete ALL services and categories!")
    print("This action cannot be undone.\n")

    # Confirmation prompt (commented out for Docker exec usage)
    # response = input("Are you sure you want to continue? (yes/no): ")
    # if response.lower() != "yes":
    #     print("Operation cancelled.")
    #     sys.exit(0)

    db = SessionLocal()

    try:
        # Clear services first (due to foreign key constraints)
        services_deleted = clear_services(db)

        # Clear categories
        categories_deleted = clear_categories(db)

        print("\n" + "=" * 60)
        print("[SUCCESS] Catalog cleared successfully!")
        print("=" * 60)
        print("\nSummary:")
        print(f"  - Services deleted: {services_deleted}")
        print(f"  - Categories deleted: {categories_deleted}")
        print("\nYou can now add new categories and services.\n")

    except Exception as e:
        db.rollback()
        print(f"\n[ERROR] Error clearing catalog: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
