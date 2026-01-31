"""
System Reset Script

This script:
1. Purges all database tables EXCEPT 'salon_settings'.
2. Re-seeds system roles.
3. Creates a new owner user 'Angel Lakra' with the provided mobile number.

**DANGER**: This is a highly destructive operation. Use with extreme caution.
"""

import sys
from pathlib import Path
import argparse
from sqlalchemy import text
from sqlalchemy.orm import Session

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.database import SessionLocal, Base, engine
from app.models.user import Role, RoleEnum, User
from app.auth.password import PasswordHandler
from app.seeds.initial_data import seed_roles

def purge_database(db: Session, keep_tables=["salon_settings", "alembic_version"]):
    """Purge all data from all tables except specified ones."""
    print("Purging database...")
    
    # Get all tables in dependency order
    tables = Base.metadata.sorted_tables
    
    # For PostgreSQL, we might need TRUNCATE CASCADE, but SQLAlchemy delete() works
    # if we follow the correct order (reverse dependency order).
    
    for table in reversed(tables):
        if table.name in keep_tables:
            print(f"  [SKIP] Keeping {table.name}")
            continue
            
        print(f"  [DELETE] Purging {table.name}...")
        try:
            db.execute(table.delete())
        except Exception as e:
            print(f"  [ERROR] Failed to purge {table.name}: {e}")
            raise
    
    db.commit()
    print("  [OK] Database purged.")

def create_admin_user(db: Session):
    """Create the new owner user."""
    print("\nCreating owner user 'Angel Lakra'...")
    
    # Ensure roles exist first
    roles = seed_roles(db)
    owner_role = roles.get("owner")
    
    if not owner_role:
        owner_role = db.query(Role).filter(Role.name == RoleEnum.OWNER).first()
    
    if not owner_role:
        raise Exception("Failed to find or create 'owner' role.")
    
    # Check if user already exists (shouldn't after purge, but safe check)
    existing_user = db.query(User).filter(User.username == "angel").first()
    if existing_user:
        print("  [INFO] User 'angel' already exists. Updating...")
        user = existing_user
    else:
        user = User()
        db.add(user)

    password = "Angel1204"
    password_hash = PasswordHandler.hash_password(password)
    
    user.role_id = owner_role.id
    user.username = "angel"
    user.email = "ngellakra@gmail.com"
    user.password_hash = password_hash
    user.full_name = "Angel Lakra"
    user.phone = "7903449486"
    user.is_active = True
    
    db.commit()
    
    print(f"  [OK] Created owner user: Angel Lakra")
    print(f"  [INFO] Username: angel")
    print(f"  [INFO] Password: {password}")
    print(f"  [INFO] Mobile: 7903449486")
    print(f"  [WARNING] PLEASE CHANGE THE PASSWORD IMMEDIATELY AFTER LOGIN!")

def main():
    parser = argparse.ArgumentParser(description="Purge DB except settings and create owner user")
    parser.add_argument("--yes", action="store_true", help="Skip confirmation")
    args = parser.parse_args()
    
    if not args.yes:
        print("\n" + "!" * 60)
        print("CRITICAL WARNING: DESTRUCTIVE OPERATION")
        print("THIS WILL DELETE ALL DATA EXCEPT SALON SETTINGS")
        print("!" * 60 + "\n")
        confirm = input("Are you absolutely sure you want to proceed? (Type 'YES' to confirm): ")
        if confirm != 'YES':
            print("Aborted.")
            return

    db = SessionLocal()
    try:
        purge_database(db)
        create_admin_user(db)
        print("\n" + "=" * 60)
        print("[SUCCESS] System reset complete.")
        print("=" * 60)
    except Exception as e:
        db.rollback()
        print(f"\n[ERROR] {e}")
        # import traceback
        # traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    main()
