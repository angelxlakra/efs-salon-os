"""Verify package-related settings."""

from decimal import Decimal
from app.config import settings


def test_package_default_cancellation_fee_pct_is_20():
    assert settings.PACKAGE_DEFAULT_CANCELLATION_FEE_PCT == Decimal("20.00")
