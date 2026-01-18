"""Background worker for SalonOS scheduled jobs.

This worker runs scheduled background jobs using APScheduler:
- Daily summary generation (21:45 IST)
- Nightly database backup (23:30 IST)
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
from apscheduler.executors.pool import ThreadPoolExecutor
import pytz

from app.jobs.scheduled import (
    generate_daily_summary_job,
    catchup_missing_summaries,
    nightly_backup_job,
    test_job,
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

    # Nightly Backup (23:30 IST)
    # Runs late at night for database backup
    scheduler.add_job(
        nightly_backup_job,
        trigger=CronTrigger(hour=23, minute=30, timezone=IST),
        id='nightly_backup',
        name='Nightly Database Backup',
        replace_existing=True,
        max_instances=1,
        misfire_grace_time=1800  # 30 minutes grace period
    )
    logger.info("✅ Scheduled: Nightly Backup (23:30 IST)")

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

    # Run catchup job immediately on startup
    logger.info("🔄 Running catchup job for missing summaries...")
    try:
        catchup_missing_summaries()
        logger.info("✅ Catchup job completed")
    except Exception as e:
        logger.error(f"❌ Catchup job failed: {str(e)}")

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
