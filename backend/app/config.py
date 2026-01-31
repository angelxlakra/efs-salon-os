"""Application configuration settings.

This module manages application settings loaded from environment variables
using Pydantic Settings for type validation and default values.
"""

from decimal import Decimal
import os
from typing import Optional
from urllib.parse import urlparse
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    All settings can be overridden by environment variables.
    For example, DATABASE_URL in .env will override the database_url field.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # Database
    database_url: str = "postgresql+psycopg://salon_user:change_me_123@postgres:5432/salon_db"

    # Redis - No default to force explicit configuration
    redis_url: str

    # Security
    secret_key: str = "CHANGE_THIS_SECRET_KEY_IN_PRODUCTION"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

    # Password Policy
    password_min_length: int = 8
    password_history_count: int = 3  # Number of old passwords to check
    bcrypt_rounds: int = 12  # Cost factor for bcrypt

    # Rate Limiting
    login_rate_limit_attempts: int = 5
    login_rate_limit_window_minutes: int = 1
    account_lockout_attempts: int = 10
    account_lockout_duration_minutes: int = 15

    # Application
    environment: str = "development"
    debug: bool = False
    timezone: str = "Asia/Kolkata"

    # Salon Information
    salon_name: str = "SalonOS"
    invoice_prefix: str = "SAL"
    salon_address: str = "123 Main Street, City, State"
    gstin: Optional[str] = None

    # Discount Settings
    receptionist_discount_limit: int = -1

    # Tax Settings
    gst_rate: Decimal = Decimal("0.18")

    # API
    api_prefix: str = "/api"
    cors_origins: str | list[str] = "http://salon.local,http://localhost:3000"

    @field_validator('cors_origins', mode='before')
    @classmethod
    def parse_cors_origins(cls, v):
        """Parse CORS_ORIGINS from comma-separated string or return list as-is."""
        if isinstance(v, str):
            # Split by comma and strip whitespace
            return [origin.strip() for origin in v.split(',') if origin.strip()]
        return v

    @field_validator('redis_url')
    @classmethod
    def validate_redis_url(cls, v: str) -> str:
        """Validate Redis URL format to prevent cryptic connection errors.

        Ensures the URL has:
        - Correct scheme (redis:// or rediss://)
        - Valid hostname
        - Valid port number (if specified)

        This catches configuration errors at startup with clear messages
        instead of cryptic "Port could not be cast to integer" errors.

        Args:
            v: Redis URL string

        Returns:
            str: Validated Redis URL

        Raises:
            ValueError: If URL format is invalid

        Example valid URLs:
            redis://redis:6379/0
            redis://:password@redis:6379/0
            rediss://redis:6380/0
        """
        if not v:
            raise ValueError(
                "REDIS_URL is required. "
                "Expected format: redis://[:password@]host:port/db"
            )

        try:
            parsed = urlparse(v)

            # Validate scheme
            if parsed.scheme not in ('redis', 'rediss'):
                raise ValueError(
                    f"Invalid Redis scheme '{parsed.scheme}'. "
                    f"Must be 'redis://' or 'rediss://'"
                )

            # Validate hostname
            if not parsed.hostname:
                raise ValueError(
                    "Missing Redis hostname. "
                    "URL must include host (e.g., redis://localhost:6379/0)"
                )

            # Validate port if specified
            if parsed.port is not None:
                if not (1 <= parsed.port <= 65535):
                    raise ValueError(
                        f"Invalid Redis port {parsed.port}. "
                        f"Port must be between 1 and 65535"
                    )

            return v

        except ValueError:
            # Re-raise our validation errors as-is
            raise
        except Exception as e:
            # Catch URL parsing errors
            raise ValueError(
                f"Invalid REDIS_URL format: {v}\n"
                f"Expected format: redis://[:password@]host:port/db\n"
                f"Parse error: {e}"
            )


# Create global settings instance
settings = Settings()
