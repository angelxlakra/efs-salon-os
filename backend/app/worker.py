"""Background worker for SalonOS scheduled jobs.

This worker runs scheduled background jobs using APScheduler:
- Daily summary generation (21:45 IST)
- Nightly database backup (22:00 IST)
- Catchup for missing summaries (on startup)

To run the worker:
    uv run python -m app.worker

Or in Docker:
    python -m app.worker
"""

import logging
import sys
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.executors.pool import ThreadPoolExecutor
import pytz

from app.config import settings

from app.jobs.scheduled import (
    generate_daily_summary_job,
    catchup_missing_summaries,
    catchup_missing_metrics,
    catchup_missing_backup,
    nightly_backup_job,
    generate_recurring_expenses_job,
    test_job,
    customer_sync_push_job,
    customer_sync_pull_job,
    central_heartbeat_job,
    metrics_push_job,
    transfer_poll_job,
    package_expiry_transitions_job,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

# Timezone for scheduler
IST = pytz.timezone('Asia/Kolkata')


def start_worker():
    """Initialize and start the background worker with scheduled jobs."""

    logger.info("=" * 60)
    logger.info("🚀 SalonOS Background Worker Starting...")
    logger.info("=" * 60)

    # Configure scheduler with thread pool
    executors = {
        'default': ThreadPoolExecutor(max_workers=3)
    }

    scheduler = BlockingScheduler(
        executors=executors,
        timezone=IST
    )

    # ============ Production Jobs ============

    # Daily Summary Generation (21:45 IST)
    # Runs after business hours to generate previous day's summary
    scheduler.add_job(
        generate_daily_summary_job,
        trigger=CronTrigger(hour=21, minute=45, timezone=IST),
        id='daily_summary',
        name='Daily Summary Generation',
        replace_existing=True,
        max_instances=1,
        misfire_grace_time=600  # 10 minutes grace period
    )
    logger.info("✅ Scheduled: Daily Summary Generation (21:45 IST)")

    # Recurring Expenses Generation (00:05 IST)
    # Runs early morning to create recurring expenses for the day
    scheduler.add_job(
        generate_recurring_expenses_job,
        trigger=CronTrigger(hour=0, minute=5, timezone=IST),
        id='recurring_expenses',
        name='Recurring Expenses Generation',
        replace_existing=True,
        max_instances=1,
        misfire_grace_time=300  # 5 minutes grace period
    )
    logger.info("✅ Scheduled: Recurring Expenses Generation (00:05 IST)")

    # Package Expiry Transitions (02:00 IST)
    # Bulk-marks ACTIVE sales with past expires_at as EXPIRED
    scheduler.add_job(
        package_expiry_transitions_job,
        trigger=CronTrigger(hour=2, minute=0, timezone=IST),
        id='package_expiry_transitions',
        name='Package Expiry Transitions',
        replace_existing=True,
        max_instances=1,
        misfire_grace_time=300  # 5 minutes grace period
    )
    logger.info("✅ Scheduled: Package Expiry Transitions (02:00 IST)")

    # Nightly Backup (22:00 IST)
    # Runs late at night for database backup
    scheduler.add_job(
        nightly_backup_job,
        trigger=CronTrigger(hour=22, minute=00, timezone=IST),
        id='nightly_backup',
        name='Nightly Database Backup',
        replace_existing=True,
        max_instances=1,
        misfire_grace_time=1800  # 30 minutes grace period
    )
    logger.info("✅ Scheduled: Nightly Backup (22:00 IST)")

    # Weekly Cloud Cleanup (Sunday 02:00 IST)
    # Deletes cloud backups older than backup_cloud_retention_days
    def _weekly_cloud_cleanup():
        from app.services.backup_service import BackupService
        from app.config import settings
        service = BackupService()
        service.cleanup_cloud(settings.backup_cloud_retention_days)

    scheduler.add_job(
        _weekly_cloud_cleanup,
        trigger=CronTrigger(day_of_week='sun', hour=2, minute=0, timezone=IST),
        id='cloud_cleanup',
        name='Weekly Cloud Backup Cleanup',
        replace_existing=True,
        max_instances=1,
        misfire_grace_time=3600  # 1 hour grace period
    )
    logger.info("✅ Scheduled: Weekly Cloud Cleanup (Sunday 02:00 IST)")

    # ============ Central Sync Jobs (only when enabled) ============

    if settings.central_sync_enabled:
        scheduler.add_job(
            customer_sync_push_job,
            trigger=IntervalTrigger(minutes=settings.central_sync_push_interval_minutes, timezone=IST),
            id='customer_sync_push',
            name='Customer Sync Push',
            replace_existing=True,
            max_instances=1,
            misfire_grace_time=60,
        )
        logger.info(f"✅ Scheduled: Customer Sync Push (every {settings.central_sync_push_interval_minutes} min)")

        scheduler.add_job(
            customer_sync_pull_job,
            trigger=IntervalTrigger(minutes=settings.central_sync_pull_interval_minutes, timezone=IST),
            id='customer_sync_pull',
            name='Customer Sync Pull',
            replace_existing=True,
            max_instances=1,
            misfire_grace_time=60,
        )
        logger.info(f"✅ Scheduled: Customer Sync Pull (every {settings.central_sync_pull_interval_minutes} min)")

        scheduler.add_job(
            central_heartbeat_job,
            trigger=IntervalTrigger(minutes=5, timezone=IST),
            id='central_heartbeat',
            name='Central Heartbeat',
            replace_existing=True,
            max_instances=1,
            misfire_grace_time=60,
        )
        logger.info("✅ Scheduled: Central Heartbeat (every 5 min)")

        scheduler.add_job(
            metrics_push_job,
            trigger=IntervalTrigger(minutes=settings.central_sync_metrics_push_interval_minutes, timezone=IST),
            id='metrics_push',
            name='Metrics Push to Central',
            replace_existing=True,
            max_instances=1,
            misfire_grace_time=60,
        )
        logger.info(f"✅ Scheduled: Metrics Push (every {settings.central_sync_metrics_push_interval_minutes} min)")

        scheduler.add_job(
            transfer_poll_job,
            trigger=IntervalTrigger(minutes=settings.central_transfer_poll_interval_minutes, timezone=IST),
            id='transfer_poll',
            name='Inventory Transfer Poll',
            replace_existing=True,
            max_instances=1,
            misfire_grace_time=120,
        )
        logger.info(f"✅ Scheduled: Transfer Poll (every {settings.central_transfer_poll_interval_minutes} min)")

        # Nightly catch-up push at 22:05 IST to handle any gaps from the day
        scheduler.add_job(
            customer_sync_push_job,
            trigger=CronTrigger(hour=22, minute=5, timezone=IST),
            id='customer_sync_catchup',
            name='Customer Sync Catch-up (Nightly)',
            replace_existing=True,
            max_instances=1,
            misfire_grace_time=1800,
        )
        logger.info("✅ Scheduled: Customer Sync Catch-up (22:05 IST nightly)")

    # ============ Development/Testing Jobs ============

    # Uncomment for testing scheduler (runs every 5 minutes)
    # scheduler.add_job(
    #     test_job,
    #     trigger=CronTrigger(minute='*/5', timezone=IST),
    #     id='test_job',
    #     name='Test Job (Every 5 minutes)',
    #     replace_existing=True
    # )
    # logger.info("✅ Scheduled: Test Job (Every 5 minutes)")

    # ============ Startup Jobs ============

    # Run catchup jobs immediately on startup
    logger.info("🔄 Running catchup job for missing summaries...")
    try:
        catchup_missing_summaries()
        logger.info("✅ Summary catchup completed")
    except Exception as e:
        logger.error(f"❌ Summary catchup failed: {str(e)}")

    logger.info("🔄 Running catchup job for missing cloud metrics...")
    try:
        catchup_missing_metrics()
        logger.info("✅ Metrics catchup completed")
    except Exception as e:
        logger.error(f"❌ Metrics catchup failed: {str(e)}")

    logger.info("🔄 Running catchup job for missing backup...")
    try:
        catchup_missing_backup()
        logger.info("✅ Backup catchup completed")
    except Exception as e:
        logger.error(f"❌ Backup catchup failed: {str(e)}")

    # ============ Start Scheduler ============

    logger.info("=" * 60)
    logger.info("🎯 Worker ready. Scheduler started.")
    logger.info("=" * 60)
    logger.info("")
    logger.info("Scheduled jobs:")
    for job in scheduler.get_jobs():
        logger.info(f"  - {job.name}: {job.trigger}")
    logger.info("")
    logger.info("Press Ctrl+C to stop worker")
    logger.info("=" * 60)

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("")
        logger.info("=" * 60)
        logger.info("🛑 Worker shutting down...")
        logger.info("=" * 60)
        scheduler.shutdown()
        logger.info("✅ Worker stopped cleanly")


if __name__ == "__main__":
    start_worker()
