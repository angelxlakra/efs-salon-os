"""Application configuration settings.

This module manages application settings loaded from environment variables
using Pydantic Settings for type validation and default values.
"""

from decimal import Decimal
import os
from typing import Optional
from urllib.parse import urlparse
from pydantic_settings import BaseSettings, SettingsConfigDict
import re
from pydantic import field_validator, model_validator


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

    # Backup Configs
    branch_id: str = "default"
    backup_retention_days: int = 7

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

    # Packages
    # Percent as a whole number (e.g., 20.00 = 20%), NOT a fraction.
    # Diverges from gst_rate which stores 0.18 — preserved for operator readability
    # in env var overrides (PACKAGE_DEFAULT_CANCELLATION_FEE_PCT=15.00).
    package_default_cancellation_fee_pct: Decimal = Decimal("20.00")

    # API
    api_prefix: str = "/api"
    cors_origins: str | list[str] = "http://localhost:3000"

    # Central Sync
    central_sync_enabled: bool = False
    central_api_url: str = ""
    central_api_key: str = ""
    central_sync_push_interval_minutes: int = 1
    central_sync_pull_interval_minutes: int = 10
    central_sync_metrics_push_interval_minutes: int = 5
    central_transfer_poll_interval_minutes: int = 15
    central_other_stores_json: str = "[]"

    # Cloud Backup (S3-compatible — works with B2, AWS S3, MinIO)
    backup_s3_endpoint: Optional[str] = None
    backup_s3_bucket: Optional[str] = None
    backup_s3_access_key: Optional[str] = None
    backup_s3_secret_key: Optional[str] = None
    backup_s3_region: Optional[str] = "us-west-004"
    backup_cloud_retention_days: int = 90

    @field_validator('branch_id')
    @classmethod
    def validate_branch_id(cls, v: str) -> str:
        """Ensure branch_id is safe for use in file paths and S3 keys."""
        if not re.match(r'^[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}$', v):
            raise ValueError(
                f"branch_id must be alphanumeric with hyphens/underscores, "
                f"1-64 chars, got: {v!r}"
            )
        return v

    @field_validator('cors_origins', mode='before')
    @classmethod
    def parse_cors_origins(cls, v):
        """Parse CORS_ORIGINS from comma-separated string or return list as-is."""
        if isinstance(v, str):
            # Split by comma and strip whitespace
            return [origin.strip() for origin in v.split(',') if origin.strip()]
        return v

    @model_validator(mode='after')
    def validate_central_sync_settings(self) -> 'Settings':
        """When central sync is enabled, URL and API key must be non-empty."""
        if self.central_sync_enabled:
            if not self.central_api_url or not self.central_api_url.strip():
                raise ValueError(
                    "CENTRAL_API_URL must be set when CENTRAL_SYNC_ENABLED=true"
                )
            if not self.central_api_key or not self.central_api_key.strip():
                raise ValueError(
                    "CENTRAL_API_KEY must be set when CENTRAL_SYNC_ENABLED=true"
                )
        return self

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
