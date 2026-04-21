"""Initial bulk customer sync — run once per store to push all existing customers to central.

This script bulk-pushes all existing customers by calling push_pending_customers()
in a loop until the batch returns zero new syncs. It is idempotent: customers
already synced (last_synced_to_central == updated_at) are skipped automatically.

Usage:
    python -m app.scripts.initial_customer_sync

Requirements:
    - CENTRAL_SYNC_ENABLED=true in environment / .env
    - CENTRAL_API_URL and CENTRAL_API_KEY must be set
    - Run from the backend/ directory (or ensure app package is on PYTHONPATH)

WARNING:
    This pushes ALL customers with a phone number to central. Run only once
    per store, or after confirming central_last_sync fields have been reset.
"""

import logging
import sys

from app.config import settings
from app.database import SessionLocal
from app.services.central_sync_service import CentralSyncService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MAX_BATCHES = 500


def main() -> None:
    if not settings.central_sync_enabled:
        logger.error(
            "CENTRAL_SYNC_ENABLED is false. "
            "Set it to true (and provide CENTRAL_API_URL / CENTRAL_API_KEY) "
            "before running this script."
        )
        sys.exit(1)

    logger.info("Starting initial customer sync to central: %s", settings.central_api_url)

    db = SessionLocal()
    try:
        service = CentralSyncService(db)
        total_pushed = 0

        try:
            batches = 0
            while True:
                batches += 1
                if batches > MAX_BATCHES:
                    logger.warning(
                        "MAX_BATCHES (%d) reached — stopping to prevent runaway loop. "
                        "Re-run the script to continue syncing remaining customers.",
                        MAX_BATCHES,
                    )
                    break
                result = service.push_pending_customers()
                batch_pushed = result.get("synced", 0)
                total_pushed += batch_pushed
                logger.info("Batch %d result: %s", batches, result)

                if batch_pushed == 0:
                    # No more pending customers — we are done
                    break

            logger.info("Initial sync complete. Total customers pushed: %d", total_pushed)

        finally:
            service.close()

    except Exception as exc:
        logger.error("Initial sync failed: %s", exc, exc_info=True)
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
