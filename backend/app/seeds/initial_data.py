"""Initial seed data for SalonOS.

This script populates the database with:
- Roles (owner, receptionist, staff)
- Default owner user (username: owner, password: change_me_123)
- Sample service categories

Run with: uv run python -m app.seeds.initial_data
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy.orm import Session
import bcrypt

from app.database import SessionLocal
from app.models.user import Role, RoleEnum, User
from app.models.service import ServiceCategory


def seed_roles(db: Session):
    """Create the three system roles with their permissions."""
    print("Creating roles...")

    # Check if roles already exist
    existing_roles = db.query(Role).all()
    if existing_roles:
        print(f"  [INFO] Roles already exist ({len(existing_roles)} found). Skipping...")
        return {role.name.value: role for role in existing_roles}

    roles = {}

    # Owner role - full access
    owner_role = Role(
        name=RoleEnum.OWNER,
        description="Full system access - owner/manager",
        permissions={
            "billing": ["create", "read", "update", "refund"],
            "appointments": ["create", "read", "update", "delete"],
            "inventory": ["create", "read", "update", "approve"],
            "accounting": ["read", "export"],
            "users": ["create", "read", "update", "delete"],
            "settings": ["read", "update"],
            "reports": ["read", "export"],
        }
    )
    db.add(owner_role)
    roles["owner"] = owner_role

    # Receptionist role - front desk operations
    receptionist_role = Role(
        name=RoleEnum.RECEPTIONIST,
        description="Front desk operations - receptionist",
        permissions={
            "billing": ["create", "read", "update"],
            "appointments": ["create", "read", "update"],
            "customers": ["create", "read", "update"],
            "inventory": ["read", "request"],
            "reports": ["read"],
        }
    )
    db.add(receptionist_role)
    roles["receptionist"] = receptionist_role

    # Staff role - service providers
    staff_role = Role(
        name=RoleEnum.STAFF,
        description="Service providers - stylists/beauticians",
        permissions={
            "appointments": ["read", "update_own"],
            "bills": ["read_own"],
            "schedule": ["read_own"],
        }
    )
    db.add(staff_role)
    roles["staff"] = staff_role

    db.commit()
    print(f"  [OK] Created 3 roles: owner, receptionist, staff")

    return roles


def seed_owner_user(db: Session, roles):
    """Create the default owner user account."""
    print("Creating default owner user...")

    # Check if owner user already exists
    existing_owner = db.query(User).filter(User.username == "owner").first()
    if existing_owner:
        print("  [INFO] Owner user already exists. Skipping...")
        return existing_owner

    # Hash password using bcrypt directly
    password = "change_me_123"
    password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    owner_user = User(
        role_id=roles["owner"].id,
        username="owner",
        email="owner@salon.local",
        password_hash=password_hash,
        full_name="Salon Owner",
        is_active=True
    )
    db.add(owner_user)
    db.commit()

    print(f"  [OK] Created owner user (username: owner, password: change_me_123)")
    print(f"  [WARNING] IMPORTANT: Change the password immediately after first login!")

    return owner_user


def seed_service_categories(db: Session):
    """Create sample service categories."""
    print("Creating service categories...")

    # Check if categories already exist
    existing_categories = db.query(ServiceCategory).all()
    if existing_categories:
        print(f"  [INFO] Service categories already exist ({len(existing_categories)} found). Skipping...")
        return existing_categories

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
    """Main seeding function."""
    print("\n" + "=" * 60)
    print("SalonOS - Initial Data Seeding")
    print("=" * 60 + "\n")

    db = SessionLocal()

    try:
        # Seed roles
        roles = seed_roles(db)

        # Seed owner user
        owner_user = seed_owner_user(db, roles)

        # Seed service categories
        categories = seed_service_categories(db)

        print("\n" + "=" * 60)
        print("[SUCCESS] Seeding completed successfully!")
        print("=" * 60)
        print("\nSummary:")
        print(f"  - Roles: {len(roles)}")
        print(f"  - Users: 1 (owner)")
        print(f"  - Service Categories: {len(categories)}")
        print("\nDefault Login:")
        print("  Username: owner")
        print("  Password: change_me_123")
        print("  [WARNING] CHANGE THIS PASSWORD IMMEDIATELY!\n")

    except Exception as e:
        db.rollback()
        print(f"\n[ERROR] Error seeding data: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
