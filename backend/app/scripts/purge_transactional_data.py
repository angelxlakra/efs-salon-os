"""
Purge Transactional Data Script

This script removes all transactional/operational data from the system while
preserving master data (customers, staff, services, settings).

**DANGER**: This is a destructive operation. Always backup before running!

What gets DELETED:
- Bills (invoices)
- Bill items
- Payments
- Walk-ins
- Appointments
- Daily reconciliations
- Cash drawer records
- Day summaries
- Export logs
- Audit logs (optional)

What gets PRESERVED:
- Customers
- Users & Staff
- Services & Categories
- Service Addons
- Inventory (SKUs, Suppliers, Stock)
- Salon Settings
- Roles

Usage:
    docker compose exec api python -m app.scripts.purge_transactional_data

    # With confirmation prompt (safer):
    docker compose exec api python -m app.scripts.purge_transactional_data --interactive

    # Skip audit logs deletion:
    docker compose exec api python -m app.scripts.purge_transactional_data --keep-audit-logs

    # Dry run (show what would be deleted without actually deleting):
    docker compose exec api python -m app.scripts.purge_transactional_data --dry-run
"""

import sys
import argparse
from datetime import datetime
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.billing import Bill, BillItem, Payment
from app.models.appointment import Appointment, WalkIn
from app.models.reconciliation import DailyReconciliation
from app.models.accounting import CashDrawer, DaySummary, ExportLog
from app.models.audit import AuditLog, Event
from app.utils import IST


class TransactionalDataPurger:
    """Handles purging of transactional data with safety checks."""

    def __init__(self, db: Session, dry_run: bool = False, keep_audit_logs: bool = False):
        self.db = db
        self.dry_run = dry_run
        self.keep_audit_logs = keep_audit_logs
        self.deleted_counts = {}

    def count_records(self) -> dict:
        """Count records that will be deleted."""
        counts = {
            'payments': self.db.query(func.count(Payment.id)).scalar() or 0,
            'bill_items': self.db.query(func.count(BillItem.id)).scalar() or 0,
            'bills': self.db.query(func.count(Bill.id)).scalar() or 0,
            'walkins': self.db.query(func.count(WalkIn.id)).scalar() or 0,
            'appointments': self.db.query(func.count(Appointment.id)).scalar() or 0,
            'daily_reconciliations': self.db.query(func.count(DailyReconciliation.id)).scalar() or 0,
            'cash_drawers': self.db.query(func.count(CashDrawer.id)).scalar() or 0,
            'day_summaries': self.db.query(func.count(DaySummary.id)).scalar() or 0,
            'export_logs': self.db.query(func.count(ExportLog.id)).scalar() or 0,
        }

        if not self.keep_audit_logs:
            counts['audit_logs'] = self.db.query(func.count(AuditLog.id)).scalar() or 0
            counts['events'] = self.db.query(func.count(Event.id)).scalar() or 0

        return counts

    def delete_payments(self):
        """Delete all payment records."""
        count = self.db.query(Payment).delete()
        self.deleted_counts['payments'] = count
        print(f"  ✓ Deleted {count} payment record(s)")

    def delete_bill_items(self):
        """Delete all bill item records."""
        count = self.db.query(BillItem).delete()
        self.deleted_counts['bill_items'] = count
        print(f"  ✓ Deleted {count} bill item record(s)")

    def delete_bills(self):
        """Delete all bill/invoice records."""
        count = self.db.query(Bill).delete()
        self.deleted_counts['bills'] = count
        print(f"  ✓ Deleted {count} bill/invoice record(s)")

    def delete_walkins(self):
        """Delete all walk-in records."""
        count = self.db.query(WalkIn).delete()
        self.deleted_counts['walkins'] = count
        print(f"  ✓ Deleted {count} walk-in record(s)")

    def delete_appointments(self):
        """Delete all appointment records."""
        count = self.db.query(Appointment).delete()
        self.deleted_counts['appointments'] = count
        print(f"  ✓ Deleted {count} appointment record(s)")

    def delete_reconciliations(self):
        """Delete all daily reconciliation records."""
        count = self.db.query(DailyReconciliation).delete()
        self.deleted_counts['daily_reconciliations'] = count
        print(f"  ✓ Deleted {count} reconciliation record(s)")

    def delete_cash_drawers(self):
        """Delete all cash drawer records."""
        count = self.db.query(CashDrawer).delete()
        self.deleted_counts['cash_drawers'] = count
        print(f"  ✓ Deleted {count} cash drawer record(s)")

    def delete_day_summaries(self):
        """Delete all day summary records."""
        count = self.db.query(DaySummary).delete()
        self.deleted_counts['day_summaries'] = count
        print(f"  ✓ Deleted {count} day summary record(s)")

    def delete_export_logs(self):
        """Delete all export log records."""
        count = self.db.query(ExportLog).delete()
        self.deleted_counts['export_logs'] = count
        print(f"  ✓ Deleted {count} export log record(s)")

    def delete_audit_logs(self):
        """Delete all audit logs (optional)."""
        if self.keep_audit_logs:
            print("  ⊘ Skipping audit logs (--keep-audit-logs flag set)")
            return

        count_logs = self.db.query(AuditLog).delete()
        count_events = self.db.query(Event).delete()
        self.deleted_counts['audit_logs'] = count_logs
        self.deleted_counts['events'] = count_events
        print(f"  ✓ Deleted {count_logs} audit log record(s)")
        print(f"  ✓ Deleted {count_events} event record(s)")

    def purge_all(self):
        """Execute complete purge operation."""
        try:
            print("\n" + "=" * 60)
            print("PURGING TRANSACTIONAL DATA")
            print("=" * 60)

            if self.dry_run:
                print("\n⚠️  DRY RUN MODE - No data will be deleted\n")

            # Delete in correct order (respecting foreign key constraints)
            # Note: Walk-ins must be deleted BEFORE bills (FK: walkins.bill_id -> bills.id)
            print("\n1. Deleting Walk-ins...")
            self.delete_walkins()

            print("\n2. Deleting Appointments...")
            self.delete_appointments()

            print("\n3. Deleting Payments...")
            self.delete_payments()

            print("\n4. Deleting Bill Items...")
            self.delete_bill_items()

            print("\n5. Deleting Bills/Invoices...")
            self.delete_bills()

            print("\n6. Deleting Daily Reconciliations...")
            self.delete_reconciliations()

            print("\n7. Deleting Cash Drawer Records...")
            self.delete_cash_drawers()

            print("\n8. Deleting Day Summaries...")
            self.delete_day_summaries()

            print("\n9. Deleting Export Logs...")
            self.delete_export_logs()

            print("\n10. Deleting Audit Logs...")
            self.delete_audit_logs()

            if not self.dry_run:
                self.db.commit()
                print("\n" + "=" * 60)
                print("✅ PURGE COMPLETED SUCCESSFULLY")
                print("=" * 60)
            else:
                self.db.rollback()
                print("\n" + "=" * 60)
                print("ℹ️  DRY RUN COMPLETED (No changes made)")
                print("=" * 60)

            # Print summary
            print("\nSUMMARY:")
            total_deleted = sum(self.deleted_counts.values())
            for table, count in self.deleted_counts.items():
                print(f"  {table}: {count:,} records")
            print(f"\nTotal records deleted: {total_deleted:,}")

            return True

        except Exception as e:
            self.db.rollback()
            print(f"\n❌ ERROR: {str(e)}")
            print("Transaction rolled back. No data was deleted.")
            return False


def confirm_purge(counts: dict) -> bool:
    """Ask user for confirmation before purging."""
    print("\n" + "=" * 60)
    print("⚠️  WARNING: DESTRUCTIVE OPERATION")
    print("=" * 60)
    print("\nThe following records will be PERMANENTLY DELETED:\n")

    total = 0
    for table, count in counts.items():
        print(f"  • {table}: {count:,} records")
        total += count

    print(f"\n  TOTAL: {total:,} records will be deleted")

    print("\n" + "=" * 60)
    print("PRESERVED DATA (will NOT be deleted):")
    print("=" * 60)
    print("  ✓ Customers")
    print("  ✓ Users & Staff")
    print("  ✓ Services & Categories")
    print("  ✓ Service Addons")
    print("  ✓ Inventory (SKUs, Suppliers, Stock)")
    print("  ✓ Salon Settings")
    print("  ✓ Roles")

    print("\n" + "=" * 60)
    print("⚠️  IMPORTANT: Create a backup before proceeding!")
    print("=" * 60)
    print("\nBackup command:")
    print("  docker compose exec postgres pg_dump -U salon_user \\")
    print("    -Fc salon_db > backup_$(date +%Y%m%d_%H%M%S).dump")

    print("\n" + "=" * 60)
    response = input("\nType 'DELETE ALL DATA' to confirm (or anything else to cancel): ")
    return response.strip() == "DELETE ALL DATA"


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Purge transactional data from SalonOS",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument(
        '--interactive',
        action='store_true',
        help='Prompt for confirmation before deleting (recommended)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be deleted without actually deleting'
    )
    parser.add_argument(
        '--keep-audit-logs',
        action='store_true',
        help='Preserve audit logs and events'
    )
    parser.add_argument(
        '--yes',
        action='store_true',
        help='Skip confirmation (DANGEROUS - use with caution)'
    )

    args = parser.parse_args()

    # Create database session
    db = SessionLocal()

    try:
        # Create purger instance
        purger = TransactionalDataPurger(
            db=db,
            dry_run=args.dry_run,
            keep_audit_logs=args.keep_audit_logs
        )

        # Count records
        print("\nScanning database...")
        counts = purger.count_records()

        # Check if there's anything to delete
        total_records = sum(counts.values())
        if total_records == 0:
            print("\n✓ No transactional data found. Database is clean.")
            return 0

        # Confirmation (skip for dry-run or if --yes is set)
        if not args.dry_run and (args.interactive or not args.yes):
            if not confirm_purge(counts):
                print("\n❌ Operation cancelled by user.")
                return 1
        elif args.dry_run:
            # Show summary for dry run
            print("\n" + "=" * 60)
            print("DRY RUN - Preview Only")
            print("=" * 60)
            print("\nThe following would be deleted:\n")
            total = 0
            for table, count in counts.items():
                print(f"  • {table}: {count:,} records")
                total += count
            print(f"\n  TOTAL: {total:,} records")
            print("\nNo data will be deleted in dry-run mode.")
            print("=" * 60)

        # Execute purge
        success = purger.purge_all()

        # Print timestamp
        timestamp = datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S %Z")
        print(f"\nCompleted at: {timestamp}")

        return 0 if success else 1

    except KeyboardInterrupt:
        print("\n\n❌ Operation cancelled by user (Ctrl+C)")
        db.rollback()
        return 1

    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        db.rollback()
        return 1

    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
