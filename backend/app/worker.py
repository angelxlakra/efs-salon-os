"""
Placeholder worker for spec-01.
Will be implemented properly in spec-08 (Background Jobs & Events).
"""
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    logger.info("Worker placeholder started. Will be implemented in spec-08.")
    while True:
        time.sleep(60)
        logger.info("Worker heartbeat...")
        