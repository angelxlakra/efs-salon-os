#!/usr/bin/env python3
"""
Fix missing Staff profiles for users with STAFF role.

This script creates Staff profiles for any users with the STAFF role
who don't have a linked Staff profile.

Usage:
    python fix_staff_profiles.py
"""

from app.database import SessionLocal
from app.models.user import User, Staff, RoleEnum


def fix_staff_profiles():
    """Create Staff profiles for staff-role users without profiles."""
    db = SessionLocal()
    try:
        # Find all active staff-role users
        staff_users = db.query(User).join(User.role).filter(
            User.role.has(name=RoleEnum.STAFF),
            User.deleted_at.is_(None),
            User.is_active == True
        ).all()

        print(f"Found {len(staff_users)} staff-role users")

        fixed_count = 0
        for user in staff_users:
            # Check if Staff profile already exists
            existing_staff = db.query(Staff).filter(
                Staff.user_id == user.id
            ).first()

            if existing_staff:
                print(f"  ✓ {user.username} ({user.full_name}) - Staff profile exists")
            else:
                # Create Staff profile
                staff = Staff(
                    user_id=user.id,
                    display_name=user.full_name,
                    specialization=[],
                    is_active=True
                )
                db.add(staff)
                fixed_count += 1
                print(f"  ✅ {user.username} ({user.full_name}) - Staff profile created")

        if fixed_count > 0:
            db.commit()
            print(f"\n✅ Successfully created {fixed_count} Staff profile(s)")
        else:
            print("\n✓ All staff users already have Staff profiles")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    print("=" * 60)
    print("Staff Profile Fix Script")
    print("=" * 60)
    print()
    fix_staff_profiles()
    print()
    print("=" * 60)
    print("Done!")
    print("=" * 60)
