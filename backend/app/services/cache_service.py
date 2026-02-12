"""Redis-based caching service for application data.

This module provides a synchronous Redis client for caching:
- Settings (salon configuration)
- Catalog data (services, categories)
- Dashboard metrics (aggregated reports)
- Any frequently-accessed, slowly-changing data

Example:
    from app.services.cache_service import cache

    # Set with 1 hour TTL
    cache.set("settings:salon", settings_dict, ttl=3600)

    # Get
    cached = cache.get("settings:salon")

    # Invalidate pattern
    cache.delete_pattern("catalog:*")
"""

import json
import logging
from typing import Optional, Any
import redis
from app.config import settings

logger = logging.getLogger(__name__)


class CacheService:
    """Synchronous Redis cache manager.

    Provides simple key-value caching with:
    - Automatic JSON serialization
    - TTL support
    - Pattern-based deletion
    - Connection pooling
    - Lazy connection initialization
    """

    def __init__(self):
        """Initialize cache service (connection happens lazily)."""
        self._redis = None

    @property
    def redis(self) -> redis.Redis:
        """Get Redis client, connecting if needed."""
        if self._redis is None:
            try:
                self._redis = redis.Redis.from_url(
                    settings.redis_url,
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=5,
                    retry_on_timeout=True,
                    health_check_interval=30,
                )
                self._redis.ping()
                logger.info("Cache service connected to Redis")
            except redis.ConnectionError as e:
                logger.error(f"Failed to connect to Redis: {e}")
                raise
            except Exception as e:
                logger.error(f"Redis initialization error: {e}")
                raise ValueError(f"Invalid Redis configuration: {e}")
        return self._redis

    def get(self, key: str) -> Optional[str]:
        """Get value from cache."""
        try:
            return self.redis.get(key)
        except redis.RedisError as e:
            logger.error(f"Cache get error for key '{key}': {e}")
            return None

    def get_json(self, key: str) -> Optional[Any]:
        """Get value from cache and deserialize JSON."""
        value = self.get(key)
        if value is None:
            return None
        try:
            return json.loads(value)
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error for key '{key}': {e}")
            return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache with optional TTL."""
        try:
            if not isinstance(value, str):
                value = json.dumps(value, default=str)
            if ttl:
                result = self.redis.setex(key, ttl, value)
            else:
                result = self.redis.set(key, value)
            return bool(result)
        except (redis.RedisError, TypeError, json.JSONDecodeError) as e:
            logger.error(f"Cache set error for key '{key}': {e}")
            return False

    def delete(self, key: str) -> bool:
        """Delete a single key from cache."""
        try:
            count = self.redis.delete(key)
            return count > 0
        except redis.RedisError as e:
            logger.error(f"Cache delete error for key '{key}': {e}")
            return False

    def delete_pattern(self, pattern: str) -> int:
        """Delete all keys matching a pattern."""
        try:
            keys = self.redis.keys(pattern)
            if keys:
                return self.redis.delete(*keys)
            return 0
        except redis.RedisError as e:
            logger.error(f"Cache delete_pattern error for pattern '{pattern}': {e}")
            return 0

    def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        try:
            return bool(self.redis.exists(key))
        except redis.RedisError as e:
            logger.error(f"Cache exists error for key '{key}': {e}")
            return False


# Singleton instance
cache = CacheService()
