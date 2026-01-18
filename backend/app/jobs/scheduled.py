"""Scheduled jobs for SalonOS.

This module contains all scheduled background jobs that run automatically:
- Daily summary generation (21:45 IST)
- Nightly database backup (23:30 IST)
- Catchup for missing summaries (on startup)
"""

import logging
from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.services.accounting_service import AccountingService
from app.models.accounting import DaySummary
from app.utils import IST

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

    Scheduled to run at 23:30 IST every day.
    Creates PostgreSQL dump for disaster recovery.

    **Note**: This is a placeholder implementation.
    Full backup functionality requires Docker volume access and
    will be implemented in deployment configuration.

    The actual backup command would be:
        pg_dump -U salon_user -Fc salon_db > /backups/backup-YYYYMMDD.sql

    For now, this just logs that a backup would be performed.
    """
    logger.info("🔄 Nightly backup job triggered...")

    try:
        now = datetime.now(IST)
        backup_date = now.strftime("%Y%m%d")

        # In production, this would execute:
        # - pg_dump command via subprocess
        # - Upload to cloud storage (optional)
        # - Cleanup old backups (keep last 7 days local, 30 days cloud)

        logger.info(
            f"✅ Backup placeholder executed for {backup_date}. "
            f"Full implementation requires deployment configuration."
        )

    except Exception as e:
        logger.error(f"❌ Backup job failed: {str(e)}", exc_info=True)


def test_job():
    """Simple test job for development.

    This job runs every 5 minutes in development mode.
    Useful for testing the scheduler is working correctly.
    Should be removed or disabled in production.
    """
    now = datetime.now(IST)
    logger.info(f"🔔 Test job executed at {now.strftime('%H:%M:%S')}")
