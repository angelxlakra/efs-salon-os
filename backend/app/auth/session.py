"""Session management with Redis.

This module provides Redis-backed session storage for refresh tokens,
token blacklisting, and rate limiting for authentication endpoints.
"""

from datetime import timedelta
from typing import Optional
import redis.asyncio as redis
from app.config import settings
from app.auth.jwt import JWTHandler


class SessionManager:
    """Manage user sessions and tokens in Redis.

    Handles:
    - Refresh token storage and validation
    - Access token blacklisting
    - Rate limiting for login attempts
    - Account lockout tracking
    """

    def __init__(self):
        """Initialize Redis connection."""
        self.redis = redis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True
        )

    async def close(self):
        """Close Redis connection."""
        await self.redis.close()

    # ========== Refresh Token Management ==========

    async def store_refresh_token(
        self,
        user_id: str,
        jti: str,
        token: str,
        device_id: Optional[str] = None
    ):
        """Store refresh token in Redis.

        Args:
            user_id: The user's ID.
            jti: JWT token ID (unique identifier).
            token: The refresh token string.
            device_id: Optional device identifier.

        Example:
            >>> await session_manager.store_refresh_token(
            ...     user_id="01HXX...",
            ...     jti="01HYY...",
            ...     token="eyJhbGc...",
            ...     device_id="reception_001"
            ... )
        """
        key = f"refresh_token:{user_id}:{jti}"

        data = {
            "token": token,
            "device_id": device_id or "unknown",
            "created_at": str(int(timedelta().total_seconds()))
        }

        # Store token data
        await self.redis.hset(key, mapping=data)

        # Set expiration
        await self.redis.expire(
            key,
            timedelta(days=JWTHandler.REFRESH_TOKEN_EXPIRE_DAYS)
        )

    async def validate_refresh_token(
        self,
        user_id: str,
        jti: str
    ) -> bool:
        """Check if refresh token exists and is valid.

        Args:
            user_id: The user's ID.
            jti: JWT token ID.

        Returns:
            bool: True if token exists in Redis, False otherwise.

        Example:
            >>> is_valid = await session_manager.validate_refresh_token(
            ...     user_id="01HXX...",
            ...     jti="01HYY..."
            ... )
        """
        key = f"refresh_token:{user_id}:{jti}"
        return await self.redis.exists(key) > 0

    async def revoke_refresh_token(self, user_id: str, jti: str):
        """Revoke a specific refresh token.

        Args:
            user_id: The user's ID.
            jti: JWT token ID to revoke.

        Example:
            >>> await session_manager.revoke_refresh_token(
            ...     user_id="01HXX...",
            ...     jti="01HYY..."
            ... )
        """
        key = f"refresh_token:{user_id}:{jti}"
        await self.redis.delete(key)

    async def revoke_all_user_tokens(self, user_id: str):
        """Revoke all refresh tokens for a user.

        Used for logout from all devices.

        Args:
            user_id: The user's ID.

        Example:
            >>> await session_manager.revoke_all_user_tokens("01HXX...")
        """
        pattern = f"refresh_token:{user_id}:*"
        cursor = 0

        # Scan and delete all matching keys
        while True:
            cursor, keys = await self.redis.scan(
                cursor=cursor,
                match=pattern,
                count=100
            )

            if keys:
                await self.redis.delete(*keys)

            if cursor == 0:
                break

    # ========== Access Token Blacklist ==========

    async def blacklist_access_token(self, jti: str, expires_in: int):
        """Add access token to blacklist.

        Blacklisted tokens are rejected even if not expired.
        The blacklist entry expires when the token would expire anyway.

        Args:
            jti: JWT token ID.
            expires_in: Seconds until token expires.

        Example:
            >>> await session_manager.blacklist_access_token(
            ...     jti="01HYY...",
            ...     expires_in=900  # 15 minutes
            ... )
        """
        key = f"blacklist:{jti}"
        await self.redis.setex(key, expires_in, "1")

    async def is_token_blacklisted(self, jti: str) -> bool:
        """Check if access token is blacklisted.

        Args:
            jti: JWT token ID.

        Returns:
            bool: True if token is blacklisted.

        Example:
            >>> is_blacklisted = await session_manager.is_token_blacklisted("01HYY...")
        """
        key = f"blacklist:{jti}"
        return await self.redis.exists(key) > 0

    # ========== Rate Limiting ==========

    async def check_login_rate_limit(self, identifier: str) -> bool:
        """Check if login attempts exceed rate limit.

        Args:
            identifier: IP address or username to track.

        Returns:
            bool: True if within rate limit, False if exceeded.

        Example:
            >>> allowed = await session_manager.check_login_rate_limit("192.168.1.100")
            >>> if not allowed:
            ...     raise HTTPException(status_code=429, detail="Too many attempts")
        """
        key = f"login_rate:{identifier}"
        current = await self.redis.get(key)

        if current is None:
            # First attempt, set counter
            await self.redis.setex(
                key,
                timedelta(minutes=settings.login_rate_limit_window_minutes),
                "1"
            )
            return True

        attempts = int(current)
        if attempts >= settings.login_rate_limit_attempts:
            return False

        # Increment counter
        await self.redis.incr(key)
        return True

    async def increment_failed_login(self, username: str):
        """Increment failed login counter for account lockout.

        Args:
            username: The username attempting to login.

        Example:
            >>> await session_manager.increment_failed_login("owner")
        """
        key = f"failed_login:{username}"
        current = await self.redis.get(key)

        if current is None:
            await self.redis.setex(
                key,
                timedelta(minutes=settings.account_lockout_duration_minutes),
                "1"
            )
        else:
            await self.redis.incr(key)

    async def reset_failed_login(self, username: str):
        """Reset failed login counter after successful login.

        Args:
            username: The username that logged in successfully.

        Example:
            >>> await session_manager.reset_failed_login("owner")
        """
        key = f"failed_login:{username}"
        await self.redis.delete(key)

    async def is_account_locked(self, username: str) -> bool:
        """Check if account is locked due to failed attempts.

        Args:
            username: The username to check.

        Returns:
            bool: True if account is locked.

        Example:
            >>> is_locked = await session_manager.is_account_locked("owner")
            >>> if is_locked:
            ...     raise HTTPException(status_code=403, detail="Account locked")
        """
        key = f"failed_login:{username}"
        current = await self.redis.get(key)

        if current is None:
            return False

        attempts = int(current)
        return attempts >= settings.account_lockout_attempts

    # ========== Device Management ==========

    async def get_user_devices(self, user_id: str) -> list:
        """Get all active devices for a user.

        Args:
            user_id: The user's ID.

        Returns:
            list: List of device IDs with active sessions.

        Example:
            >>> devices = await session_manager.get_user_devices("01HXX...")
            >>> print(devices)
            ['reception_001', 'mobile_app']
        """
        pattern = f"refresh_token:{user_id}:*"
        devices = []
        cursor = 0

        while True:
            cursor, keys = await self.redis.scan(
                cursor=cursor,
                match=pattern,
                count=100
            )

            for key in keys:
                device_id = await self.redis.hget(key, "device_id")
                if device_id and device_id not in devices:
                    devices.append(device_id)

            if cursor == 0:
                break

        return devices


# Create global session manager instance
session_manager = SessionManager()
