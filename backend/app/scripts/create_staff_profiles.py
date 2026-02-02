"""
Script to create staff profiles for existing users who don't have one.

This script:
1. Finds all users with role 'staff' or 'receptionist' who don't have a Staff profile
2. Creates Staff profiles for them using their full name as display_name
3. Sets them as active

Usage:
    cd backend
    python -m app.scripts.create_staff_profiles
"""

from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.user import User, Staff, RoleEnum
from app.models.base import generate_ulid


def create_missing_staff_profiles(db: Session) -> dict:
    """Create staff profiles for users who don't have one.

    Args:
        db: Database session

    Returns:
        dict: Summary of created profiles
    """
    # Find users who should have staff profiles but don't
    users_without_profiles = db.query(User).outerjoin(Staff).filter(
        User.deleted_at.is_(None),
        User.is_active == True,
        Staff.id.is_(None)  # No staff profile exists
    ).all()

    created_count = 0
    skipped_count = 0
    results = []

    for user in users_without_profiles:
        # Create staff profile for staff and receptionist roles
        if user.role.name in [RoleEnum.STAFF, RoleEnum.RECEPTIONIST]:
            # Extract first name from full name
            first_name = user.full_name.split()[0] if user.full_name else user.username

            staff_profile = Staff(
                id=generate_ulid(),
                user_id=user.id,
                display_name=first_name,
                specialization=[],
                is_active=True
            )
            db.add(staff_profile)
            created_count += 1
            results.append({
                'user_id': user.id,
                'username': user.username,
                'full_name': user.full_name,
                'role': user.role.name.value,
                'staff_id': staff_profile.id
            })
            print(f"✓ Created staff profile for {user.role.name.value}: {user.full_name} ({user.username})")
        else:
            skipped_count += 1
            print(f"⊘ Skipped {user.role.name.value}: {user.full_name} ({user.username})")

    if created_count > 0:
        db.commit()
        print(f"\n✓ Successfully created {created_count} staff profiles")
    else:
        print("\n⊘ No staff profiles needed to be created")

    if skipped_count > 0:
        print(f"⊘ Skipped {skipped_count} users (owners don't need staff profiles)")

    return {
        'created': created_count,
        'skipped': skipped_count,
        'profiles': results
    }


def main():
    """Main function to run the script."""
    print("=" * 60)
    print("Creating Staff Profiles for Existing Users")
    print("=" * 60)
    print()

    db = SessionLocal()
    try:
        result = create_missing_staff_profiles(db)

        print("\n" + "=" * 60)
        print("Summary:")
        print("=" * 60)
        print(f"Created: {result['created']}")
        print(f"Skipped: {result['skipped']}")
        print()

        if result['profiles']:
            print("Created Staff Profiles:")
            for profile in result['profiles']:
                print(f"  - {profile['full_name']} ({profile['role']})")
                print(f"    Username: {profile['username']}")
                print(f"    Staff ID: {profile['staff_id']}")
                print()

    except Exception as e:
        print(f"\n✗ Error: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
