"""Scheduled jobs for SalonOS.

This module contains all scheduled background jobs that run automatically:
- Daily summary generation (21:45 IST)
- Nightly database backup (23:30 IST)
- Catchup for missing summaries (on startup)
"""

from pathlib import Path
from app.jobs.utils import parse_database_url
import subprocess
import os
import time
from app.config import settings
import logging
from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.services.accounting_service import AccountingService
from app.models.accounting import DaySummary
from app.models.expense import Expense, ExpenseStatus, RecurrenceType
from app.utils import IST, generate_ulid

logger = logging.getLogger(__name__)


def generate_daily_summary_job():
    """Generate daily summary for yesterday.

    Scheduled to run at 21:45 IST every day.
    Creates final summary for the previous day's business.

    This job:
    - Runs after business hours (salon closes around 20:00-21:00)
    - Aggregates all yesterday's transactions
    - Marks the summary as final (is_final=True)
    - Logs success/failure for monitoring
    """
    db = SessionLocal()
    logger.info("Starting daily summary generation job...")

    try:
        # Calculate yesterday's date in IST
        now = datetime.now(IST)
        yesterday = (now - timedelta(days=1)).date()

        logger.info(f"Generating daily summary for {yesterday}")

        # Create accounting service
        service = AccountingService(db)

        # Generate summary with is_final=True
        summary = service.generate_daily_summary(
            target_date=yesterday,
            generated_by=None,  # System-generated
            is_final=True
        )

        # Push metrics to cloud
        from app.services.backup_service import BackupService
        backup_service = BackupService()
        backup_service.push_daily_metrics(summary)

        logger.info(
            f"✅ Daily summary generated successfully for {yesterday}: "
            f"₹{summary.net_revenue_rupees:.2f} net revenue"
        )

    except Exception as e:
        logger.error(f"❌ Failed to generate daily summary: {str(e)}", exc_info=True)
        raise

    finally:
        db.close()


def catchup_missing_summaries():
    """Generate missing daily summaries on startup.

    This job runs once when the worker starts up.
    It checks for any days that don't have a summary and generates them.

    This ensures:
    - No gaps in financial reporting
    - Recovery from downtime or missed jobs
    - Historical data completeness
    """
    db = SessionLocal()
    logger.info("Checking for missing daily summaries...")

    try:
        # Get the earliest bill date
        from app.models.billing import Bill

        earliest_bill = db.query(Bill).order_by(Bill.created_at).first()

        if not earliest_bill:
            logger.info("No bills found, skipping catchup")
            return

        # Start from earliest bill date
        start_date = earliest_bill.created_at.date()
        today = datetime.now(IST).date()

        # Don't generate for today (it's still in progress)
        end_date = today - timedelta(days=1)

        # Get all existing summaries
        existing_summaries = db.query(DaySummary.summary_date).filter(
            DaySummary.summary_date >= start_date,
            DaySummary.summary_date <= end_date
        ).all()

        existing_dates = {s.summary_date for s in existing_summaries}

        # Find missing dates
        missing_dates = []
        current_date = start_date

        while current_date <= end_date:
            if current_date not in existing_dates:
                missing_dates.append(current_date)
            current_date += timedelta(days=1)

        if not missing_dates:
            logger.info("✅ No missing summaries found")
            return

        logger.info(f"Found {len(missing_dates)} missing summaries, generating...")

        service = AccountingService(db)

        for missing_date in missing_dates:
            try:
                summary = service.generate_daily_summary(
                    target_date=missing_date,
                    generated_by=None,
                    is_final=True
                )
                logger.info(f"✅ Generated summary for {missing_date}: ₹{summary.net_revenue_rupees:.2f}")

            except Exception as e:
                logger.error(f"❌ Failed to generate summary for {missing_date}: {str(e)}")
                # Continue with next date even if one fails

        logger.info(f"✅ Catchup complete: generated {len(missing_dates)} summaries")

    except Exception as e:
        logger.error(f"❌ Catchup job failed: {str(e)}", exc_info=True)

    finally:
        db.close()


def nightly_backup_job():
    """Perform nightly database backup.

      Scheduled to run at 22:00 IST every day.
      Creates a compressed PostgreSQL dump to /backups/ and uploads to cloud if configured.
      """
    logger.info("🔄 Nightly backup job triggered...")
    
    # CONFIGS
    BACKUP_DIR = Path("/backups")
    MIN_FILE_SIZE_BYTES = 1024  # 1KB

    try:
        # 1. Ensure backup directory exists
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)

        # 2. Parse DATABASE_URL into components pg_dump understands
        db_info = parse_database_url(settings.database_url)

        # 3. Build the output filename
        now = datetime.now(IST)
        timestamp = now.strftime("%Y%m%d_%H%M%S")
        filename = f"{settings.branch_id}_{timestamp}.dump"
        filepath = BACKUP_DIR / filename

        logger.info(f"Starting pg_dump to {filepath}...")
        start_time = time.time()

        # 4. Set up environment with PGPASSWORD
        env = os.environ.copy()
        env["PGPASSWORD"] = db_info["password"] or ""

        # 5. Run pg_dump
        result = subprocess.run(
            [
                "pg_dump",
                "-h",
                db_info["host"],
                "-p",
                str(db_info["port"]),
                 "-U",
                db_info["user"],
                "-Fc",
                "-d",
                db_info["dbname"],
                "-f",
                str(filepath)
            ],
            env=env,
            capture_output=True,
            text=True,
            timeout=600
            )

        duration = time.time() - start_time

        # 6. Check if pg_dump succeeded
        if result.returncode != 0:
            logger.error(f"pg_dump failed (exit {result.returncode})")
            logger.debug(f"pg_dump stderr (truncated): {(result.stderr or '')[:200]}")
            if filepath.exists():
                filepath.unlink()
            return
        
        # 7. Verify the dump file
        if not filepath.exists() or filepath.stat().st_size < MIN_FILE_SIZE_BYTES:
            logger.error(f"Backup file missing or too small: {filepath}")
            return

        file_size_mb = filepath.stat().st_size / (1024 * 1024)
        logger.info(
              f"Backup completed: {filename} "
              f"({file_size_mb:.1f} MB in {duration:.1f}s)"
          )
        
        # 8. Clean up old local backups
        _cleanup_old_backups(BACKUP_DIR, settings.backup_retention_days)

        # 9. Upload to cloud (if configured)
        from app.services.backup_service import BackupService
        backup_service = BackupService()
        backup_service.upload_to_cloud(filepath)

    except subprocess.TimeoutExpired:
        logger.error("pg_dump timed out after 600s")
    except Exception as e:
        logger.error(f"❌ Backup job failed: {str(e)}", exc_info=True)


def generate_recurring_expenses_job():
    """Generate recurring expense entries.

    Scheduled to run daily at 00:05 IST (12:05 AM).
    Creates expense entries for recurring expenses (rent, salaries, etc.).

    This job:
    - Runs early morning to prepare for the new business day
    - Checks all recurring expense templates
    - Creates new expense entries based on recurrence type
    - Auto-approves if template doesn't require approval
    """
    db = SessionLocal()
    logger.info("Starting recurring expense generation job...")

    try:
        now = datetime.now(IST)
        today = now.date()

        # Get all active recurring expense templates
        recurring_expenses = db.query(Expense).filter(
            Expense.is_recurring == True,
            Expense.status == ExpenseStatus.APPROVED,
            Expense.parent_expense_id.is_(None)  # Only templates, not instances
        ).all()

        if not recurring_expenses:
            logger.info("No recurring expenses found")
            return

        logger.info(f"Found {len(recurring_expenses)} recurring expense templates")

        expenses_created = 0

        for template in recurring_expenses:
            try:
                # Check if we should create an expense today
                should_create = False

                if template.recurrence_type == RecurrenceType.DAILY:
                    should_create = True

                elif template.recurrence_type == RecurrenceType.WEEKLY:
                    # Check if today matches the weekday of the template date
                    should_create = today.weekday() == template.expense_date.weekday()

                elif template.recurrence_type == RecurrenceType.MONTHLY:
                    # Check if today is the same day of month
                    should_create = today.day == template.expense_date.day

                elif template.recurrence_type == RecurrenceType.QUARTERLY:
                    # Check if today is the first day of a quarter and matches template day
                    is_quarter_start = today.month in [1, 4, 7, 10] and today.day == 1
                    should_create = is_quarter_start and template.expense_date.day == 1

                elif template.recurrence_type == RecurrenceType.YEARLY:
                    # Check if today matches month and day of template
                    should_create = (
                        today.month == template.expense_date.month and
                        today.day == template.expense_date.day
                    )

                if not should_create:
                    continue

                # Check if expense already exists for today
                existing = db.query(Expense).filter(
                    Expense.parent_expense_id == template.id,
                    Expense.expense_date == today
                ).first()

                if existing:
                    logger.info(f"Expense already exists for template {template.id} on {today}")
                    continue

                # Create new expense instance
                new_expense = Expense(
                    id=generate_ulid(),
                    category=template.category,
                    amount=template.amount,
                    expense_date=today,
                    description=f"{template.description} (Auto-generated)",
                    vendor_name=template.vendor_name,
                    invoice_number=template.invoice_number,
                    notes=f"Auto-generated from recurring template on {today}",
                    is_recurring=False,  # Instance, not template
                    recurrence_type=None,
                    parent_expense_id=template.id,
                    staff_id=template.staff_id,
                    status=ExpenseStatus.APPROVED if not template.requires_approval else ExpenseStatus.PENDING,
                    requires_approval=template.requires_approval,
                    recorded_by=template.recorded_by,
                    recorded_at=now,
                    approved_by=template.recorded_by if not template.requires_approval else None,
                    approved_at=now if not template.requires_approval else None
                )

                db.add(new_expense)
                expenses_created += 1

                logger.info(
                    f"✅ Created expense: {template.category.value} - "
                    f"₹{template.amount / 100:.2f} for {today}"
                )

            except Exception as e:
                logger.error(
                    f"❌ Failed to create expense from template {template.id}: {str(e)}",
                    exc_info=True
                )
                # Continue with next template even if one fails

        db.commit()

        if expenses_created > 0:
            logger.info(f"✅ Recurring expense generation complete: created {expenses_created} expense(s)")
        else:
            logger.info("No recurring expenses needed for today")

    except Exception as e:
        logger.error(f"❌ Recurring expense job failed: {str(e)}", exc_info=True)
        db.rollback()

    finally:
        db.close()

def _cleanup_old_backups(backup_dir: Path, retention_days: int):
    """Delete local backup files older than retention_days."""

    cutoff = datetime.now(IST) - timedelta(days=retention_days)
    removed = 0
    for f in backup_dir.glob("*.dump"):
        # Get file modification time and compare to cutoff
        file_mtime = datetime.fromtimestamp(f.stat().st_mtime, tz=IST)
        if file_mtime < cutoff:
            f.unlink()
            removed += 1
            logger.info(f"Deleted old backup: {f.name}")
    
    if removed:
          logger.info(f"Cleaned up {removed} old backup(s)")


def catchup_missing_metrics():
    """Push metrics for any recent DaySummary that is missing from cloud storage.

    Runs once on worker startup (after catchup_missing_summaries).
    Checks the last 14 days of local DaySummary records against the
    cloud metrics prefix and uploads any that are absent.

    Capped at 14 days to avoid flooding B2 after prolonged downtime.
    """
    from app.services.backup_service import BackupService

    backup_service = BackupService()

    if not backup_service.cloud_enabled:
        logger.debug("Metrics catchup skipped — cloud not configured")
        return

    db = SessionLocal()
    logger.info("Checking for missing cloud metrics...")

    try:
        today = datetime.now(IST).date()
        start_date = today - timedelta(days=14)

        # Get local summaries for the last 14 days
        summaries = (
            db.query(DaySummary)
            .filter(
                DaySummary.summary_date >= start_date,
                DaySummary.summary_date < today,
                DaySummary.is_final == True,
            )
            .all()
        )

        if not summaries:
            logger.info("No recent summaries to catch up")
            return

        # List existing cloud metrics to find gaps
        s3 = backup_service._get_s3_client()
        prefix = f"{settings.branch_id}/metrics/"

        existing_keys: set[str] = set()
        try:
            response = s3.list_objects_v2(
                Bucket=settings.backup_s3_bucket,
                Prefix=prefix,
            )
            if "Contents" in response:
                existing_keys = {obj["Key"] for obj in response["Contents"]}
        except Exception as e:
            logger.warning(f"Could not list cloud metrics: {e}")
            return

        pushed = 0
        for summary in summaries:
            expected_key = f"{prefix}{summary.summary_date}.json"
            if expected_key not in existing_keys:
                if backup_service.push_daily_metrics(summary):
                    pushed += 1

        if pushed:
            logger.info(f"✅ Metrics catchup: pushed {pushed} missing metric(s)")
        else:
            logger.info("✅ All recent metrics already in cloud")

    except Exception as e:
        logger.error(f"❌ Metrics catchup failed: {str(e)}", exc_info=True)

    finally:
        db.close()


def test_job():
    """Simple test job for development.

    This job runs every 5 minutes in development mode.
    Useful for testing the scheduler is working correctly.
    Should be removed or disabled in production.
    """
    now = datetime.now(IST)
    logger.info(f"🔔 Test job executed at {now.strftime('%H:%M:%S')}")
