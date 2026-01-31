"""
Database Backup Script

Creates a timestamped backup of the SalonOS database.

This script is a Python wrapper around pg_dump that creates consistent,
timestamped backups with proper error handling and verification.

Backup Format: PostgreSQL custom format (.dump)
Location: /salon-data/backups/ (inside container)
Filename: salon_backup_YYYYMMDD_HHMMSS.dump

Usage:
    # From host machine (recommended):
    docker compose exec postgres pg_dump -U salon_user -Fc salon_db > backup_$(date +%Y%m%d_%H%M%S).dump

    # Using this script:
    docker compose exec api python -m app.scripts.backup_database

    # Specify custom output path:
    docker compose exec api python -m app.scripts.backup_database --output /backups/custom_name.dump

Restore:
    # Stop the application
    docker compose down

    # Restore from backup
    docker compose up -d postgres
    docker compose exec postgres pg_restore -U salon_user -d salon_db --clean backup.dump

    # Start application
    docker compose up -d
"""

import sys
import argparse
import subprocess
from datetime import datetime
from pathlib import Path

from app.config import settings
from app.utils import IST


def create_backup(output_path: str = None) -> bool:
    """Create database backup using pg_dump.

    Args:
        output_path: Optional custom output path. If not provided,
                    uses default timestamped name.

    Returns:
        True if backup successful, False otherwise
    """
    try:
        # Generate filename if not provided
        if not output_path:
            timestamp = datetime.now(IST).strftime("%Y%m%d_%H%M%S")
            output_path = f"/salon-data/backups/salon_backup_{timestamp}.dump"

        # Ensure backup directory exists
        backup_dir = Path(output_path).parent
        backup_dir.mkdir(parents=True, exist_ok=True)

        print("=" * 60)
        print("DATABASE BACKUP")
        print("=" * 60)
        print(f"\nDatabase: {settings.database_url.split('/')[-1]}")
        print(f"Output: {output_path}")
        print(f"Started: {datetime.now(IST).strftime('%Y-%m-%d %H:%M:%S %Z')}")
        print("\nCreating backup...")

        # Parse database connection details
        # Format: postgresql://user:pass@host:port/dbname
        db_url = settings.database_url
        parts = db_url.replace('postgresql://', '').split('@')
        user_pass = parts[0].split(':')
        host_port_db = parts[1].split('/')

        username = user_pass[0]
        password = user_pass[1] if len(user_pass) > 1 else ''
        host_port = host_port_db[0].split(':')
        host = host_port[0]
        port = host_port[1] if len(host_port) > 1 else '5432'
        database = host_port_db[1].split('?')[0]  # Remove query params

        # Build pg_dump command
        cmd = [
            'pg_dump',
            '-h', host,
            '-p', port,
            '-U', username,
            '-Fc',  # Custom format (compressed)
            '-f', output_path,
            database
        ]

        # Set password environment variable
        env = {'PGPASSWORD': password}

        # Execute pg_dump
        result = subprocess.run(
            cmd,
            env=env,
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            print(f"\n❌ Backup failed!")
            print(f"Error: {result.stderr}")
            return False

        # Verify backup file exists and has size
        backup_file = Path(output_path)
        if not backup_file.exists():
            print(f"\n❌ Backup file not found: {output_path}")
            return False

        file_size = backup_file.stat().st_size
        if file_size == 0:
            print(f"\n❌ Backup file is empty!")
            return False

        # Success
        size_mb = file_size / (1024 * 1024)
        print(f"\n✅ Backup completed successfully!")
        print(f"\nFile: {output_path}")
        print(f"Size: {size_mb:.2f} MB")
        print(f"Completed: {datetime.now(IST).strftime('%Y-%m-%d %H:%M:%S %Z')}")

        print("\n" + "=" * 60)
        print("RESTORE INSTRUCTIONS")
        print("=" * 60)
        print("\n1. Stop the application:")
        print("   docker compose down")
        print("\n2. Start only PostgreSQL:")
        print("   docker compose up -d postgres")
        print("\n3. Restore from backup:")
        print(f"   docker compose exec postgres pg_restore -U {username} \\")
        print(f"     -d {database} --clean {output_path}")
        print("\n4. Start application:")
        print("   docker compose up -d")
        print("=" * 60)

        return True

    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        return False


def list_backups(backup_dir: str = "/salon-data/backups") -> list:
    """List all backup files in the backup directory.

    Args:
        backup_dir: Directory to search for backups

    Returns:
        List of backup file paths
    """
    try:
        backup_path = Path(backup_dir)
        if not backup_path.exists():
            print(f"Backup directory not found: {backup_dir}")
            return []

        backups = sorted(
            backup_path.glob("salon_backup_*.dump"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )

        if not backups:
            print(f"No backup files found in {backup_dir}")
            return []

        print("\n" + "=" * 60)
        print("AVAILABLE BACKUPS")
        print("=" * 60)

        for i, backup in enumerate(backups, 1):
            size_mb = backup.stat().st_size / (1024 * 1024)
            mtime = datetime.fromtimestamp(backup.stat().st_mtime)
            print(f"\n{i}. {backup.name}")
            print(f"   Size: {size_mb:.2f} MB")
            print(f"   Created: {mtime.strftime('%Y-%m-%d %H:%M:%S')}")

        print("\n" + "=" * 60)

        return [str(b) for b in backups]

    except Exception as e:
        print(f"Error listing backups: {str(e)}")
        return []


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Create database backup for SalonOS",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument(
        '--output',
        '-o',
        help='Custom output path for backup file'
    )
    parser.add_argument(
        '--list',
        '-l',
        action='store_true',
        help='List available backups'
    )

    args = parser.parse_args()

    if args.list:
        list_backups()
        return 0

    success = create_backup(args.output)
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
