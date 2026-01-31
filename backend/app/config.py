"""Application configuration settings.

This module manages application settings loaded from environment variables
using Pydantic Settings for type validation and default values.
"""

from decimal import Decimal
import os
from typing import Optional
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

    # Redis
    redis_url: str = "redis://redis:6379/0"

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


# Create global settings instance
settings = Settings()
