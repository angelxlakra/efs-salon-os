"""Validate package schemas: required fields, validation rules, serialization."""

import pytest
from decimal import Decimal
from pydantic import ValidationError
from app.schemas.package import (
    PackageDefinitionCreate, PackageDefinitionItemCreate, DiscountInput,
    PackageDefinitionResponse, PackageSaleResponse, RefundRequest,
    ExtendExpiryRequest, RedemptionEligibilityRequest,
)


def test_definition_create_minimal_counted():
    obj = PackageDefinitionCreate(
        name="Test",
        entitlement_type="counted",
        total_sessions=10,
        validity_days=180,
        shareability="owner_only",
        items=[PackageDefinitionItemCreate(
            service_id="01HXYZ0000000000000000ABCD",
            quantity=1,
            unit_price_paise=50000,
        )],
    )
    assert obj.total_sessions == 10


def test_definition_create_rejects_counted_without_sessions():
    with pytest.raises(ValidationError):
        PackageDefinitionCreate(
            name="Test", entitlement_type="counted", validity_days=180,
            shareability="owner_only",
            items=[PackageDefinitionItemCreate(
                service_id="01HXYZ0000000000000000ABCD",
                quantity=1, unit_price_paise=50000,
            )],
        )


def test_definition_create_rejects_unlimited_with_sessions():
    with pytest.raises(ValidationError):
        PackageDefinitionCreate(
            name="Test", entitlement_type="unlimited", total_sessions=10,
            validity_days=30, shareability="owner_only",
            items=[PackageDefinitionItemCreate(
                service_id="01HXYZ0000000000000000ABCD",
                quantity=1, unit_price_paise=50000,
            )],
        )


def test_definition_create_fee_pct_range():
    with pytest.raises(ValidationError):
        PackageDefinitionCreate(
            name="Test", entitlement_type="counted", total_sessions=5,
            validity_days=180, shareability="owner_only",
            cancellation_fee_pct=Decimal("150"),
            items=[PackageDefinitionItemCreate(
                service_id="01HXYZ0000000000000000ABCD",
                quantity=1, unit_price_paise=50000,
            )],
        )


def test_discount_input_modes():
    DiscountInput(mode="pct", value=Decimal("20"))
    DiscountInput(mode="flat", value=Decimal("500"))
    DiscountInput(mode="final", value=Decimal("4500"))
    with pytest.raises(ValidationError):
        DiscountInput(mode="invalid", value=Decimal("10"))


def test_refund_request_requires_reason():
    with pytest.raises(ValidationError):
        RefundRequest(payment_method="cash", reason="")


def test_extend_expiry_request_requires_reason():
    with pytest.raises(ValidationError):
        ExtendExpiryRequest(
            new_expires_at="2027-01-01T00:00:00+00:00",
            reason="",
        )
