"""Verify package-related settings."""

from decimal import Decimal
from app.config import settings


def test_package_default_cancellation_fee_pct_default():
    assert settings.package_default_cancellation_fee_pct == Decimal("20.00")
