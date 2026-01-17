"""Idempotency service for preventing duplicate bill creation.

  This module uses Redis to track idempotency keys sent by clients.
  When a bill creation request includes an Idempotency-Key header,
  the service checks if that key was used before.

  If the key exists: Return the existing bill ID (no duplicate created)
  If the key is new: Allow bill creation and store the key

  Keys expire after 24 hours automatically.

  Example:
      # Client sends bill creation request
      POST /api/pos/bills
      Headers: Idempotency-Key: user123-1634567890

      # First request: Creates bill, stores key
      # Second request (same key): Returns existing bill
"""

from typing import Optional
import redis
from app.config import settings

class IdempotencyService:
    """Manage idempotency keys using Redis.

      Prevents duplicate bill creation by tracking request keys.
      Keys are stored with 24-hour TTL (time-to-live).

      Attributes:
          KEY_PREFIX: Redis key prefix ("idempotency:")
          TTL_SECONDS: Key expiration time (86400 = 24 hours)
    """

    KEY_PREFIX = "idempotency:"
    TTL_SECONDS = 86400

    def __init__(self):
        """Initialize Redis connection.

            Connects to Redis using URL from settings.
        """

        self.redis_client = redis.from_url(
            settings.redis_url,
            decode_responses=True
        )

    def check_key(self, key: str) -> Optional[str]:
        """Check if idempotency key was used before.

            Args:
                key: Idempotency key from request header.

            Returns:
                Optional[str]: Bill ID if key exists, None if new key.

            Example:
                >>> service = IdempotencyService()
                >>> service.check_key("user123-1634567890")
                None  # First time

                >>> service.store_key("user123-1634567890", "01BILL...")
                >>> service.check_key("user123-1634567890")
                "01BILL..."  # Returns existing bill ID
        """

        redis_key = f"{self.KEY_PREFIX}{key}"
        result = self.redis_client.get(redis_key)

        return result

    def store_key(self, key: str, bill_id: str) -> None:
        """Store idempotency key with associated bill ID.

            Keys expire after 24 hours automatically.

            Args:
                key: Idempotency key from request.
                bill_id: ID of the created bill.

            Example:
                >>> service = IdempotencyService()
                >>> service.store_key("user123-1634567890", "01BILL123...")
                # Key stored with 24hr TTL
        """

        redis_key = f"{self.KEY_PREFIX}{key}"
        self.redis_client.setex(redis_key, self.TTL_SECONDS, bill_id)

    def delete_key(self, key: str) -> None:
        """Delete idempotency key (optional cleanup).

            Normally not needed as keys expire automatically.
            Use for testing or manual cleanup.

            Args:
                key: Idempotency key to delete.
        """

        redis_key = f"{self.KEY_PREFIX}{key}"
        self.redis_client.delete(redis_key)
