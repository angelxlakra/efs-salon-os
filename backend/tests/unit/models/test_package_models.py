"""Smoke test: model classes exist with expected columns."""

from app.models.package import (
    EntitlementType,
    PackageDefinition,
    PackageDefinitionItem,
    PackageDefinitionStatus,
    PackageExpiryExtension,
    PackageRedemptionAudit,
    PackageSale,
    PackageSaleItem,
    PackageSaleStatus,
    Shareability,
)


def test_package_definition_model_shape():
    assert hasattr(PackageDefinition, "name")
    assert hasattr(PackageDefinition, "status")
    assert hasattr(PackageDefinition, "entitlement_type")
    assert hasattr(PackageDefinition, "shareability")
    assert hasattr(PackageDefinition, "validity_days")
    assert hasattr(PackageDefinition, "auto_apply")
    assert hasattr(PackageDefinition, "cancellation_fee_pct")
    assert hasattr(PackageDefinition, "total_sessions")
    assert hasattr(PackageDefinition, "items")  # relationship


def test_enum_values():
    assert PackageDefinitionStatus.DRAFT.value == "draft"
    assert PackageDefinitionStatus.PUBLISHED.value == "published"
    assert PackageDefinitionStatus.ARCHIVED.value == "archived"
    assert EntitlementType.COUNTED.value == "counted"
    assert EntitlementType.UNLIMITED.value == "unlimited"
    assert Shareability.OWNER_ONLY.value == "owner_only"
    assert Shareability.SHARED.value == "shared"


def test_package_definition_item_shape():
    assert hasattr(PackageDefinitionItem, "package_definition_id")
    assert hasattr(PackageDefinitionItem, "service_id")
    assert hasattr(PackageDefinitionItem, "quantity")
    assert hasattr(PackageDefinitionItem, "unit_price_paise")
    assert hasattr(PackageDefinitionItem, "locked")
    assert hasattr(PackageDefinitionItem, "display_order")


def test_package_sale_model_shape():
    assert hasattr(PackageSale, "bill_id")
    assert hasattr(PackageSale, "package_definition_id")
    assert hasattr(PackageSale, "customer_id")
    assert hasattr(PackageSale, "selling_staff_id")
    assert hasattr(PackageSale, "sold_at")
    assert hasattr(PackageSale, "expires_at")
    assert hasattr(PackageSale, "entitlement_type_snapshot")
    assert hasattr(PackageSale, "shareability_snapshot")
    assert hasattr(PackageSale, "cancellation_fee_pct_snapshot")
    assert hasattr(PackageSale, "total_sessions_snapshot")
    assert hasattr(PackageSale, "sessions_remaining")
    assert hasattr(PackageSale, "status")
    assert hasattr(PackageSale, "refunded_at")
    assert hasattr(PackageSale, "refund_bill_id")
    assert hasattr(PackageSale, "items")


def test_package_sale_status_enum():
    assert PackageSaleStatus.ACTIVE.value == "active"
    assert PackageSaleStatus.EXPIRED.value == "expired"
    assert PackageSaleStatus.REFUNDED.value == "refunded"
    assert PackageSaleStatus.EXHAUSTED.value == "exhausted"


def test_package_sale_item_shape():
    assert hasattr(PackageSaleItem, "package_sale_id")
    assert hasattr(PackageSaleItem, "package_definition_item_id")
    assert hasattr(PackageSaleItem, "service_id")
    assert hasattr(PackageSaleItem, "quantity")
    assert hasattr(PackageSaleItem, "snapshot_unit_price_paise")
    assert hasattr(PackageSaleItem, "snapshot_gst_rate_pct")
    assert hasattr(PackageSaleItem, "locked")
    assert hasattr(PackageSaleItem, "sale")


def test_package_sale_compound_indexes():
    """Verify the three required compound indexes are declared."""
    index_columns = set()
    for arg in PackageSale.__table_args__:
        if hasattr(arg, "columns"):
            cols = tuple(c.key for c in arg.columns)
            index_columns.add(cols)
    assert ("customer_id", "status") in index_columns
    assert ("expires_at", "status") in index_columns
    assert ("selling_staff_id", "sold_at") in index_columns


def test_package_redemption_audit_shape():
    assert hasattr(PackageRedemptionAudit, "package_sale_id")
    assert hasattr(PackageRedemptionAudit, "bill_item_id")
    assert hasattr(PackageRedemptionAudit, "package_sale_item_id")
    assert hasattr(PackageRedemptionAudit, "redeemed_for_customer_id")
    assert hasattr(PackageRedemptionAudit, "performed_by_user_id")
    assert hasattr(PackageRedemptionAudit, "redeemed_at")
    assert hasattr(PackageRedemptionAudit, "session_number")
    assert hasattr(PackageRedemptionAudit, "notes")


def test_package_expiry_extension_shape():
    assert hasattr(PackageExpiryExtension, "package_sale_id")
    assert hasattr(PackageExpiryExtension, "previous_expires_at")
    assert hasattr(PackageExpiryExtension, "new_expires_at")
    assert hasattr(PackageExpiryExtension, "performed_by_user_id")
    assert hasattr(PackageExpiryExtension, "extended_at")
    assert hasattr(PackageExpiryExtension, "reason")


def test_package_redemption_audit_indexes():
    """Verify the required compound index on PackageRedemptionAudit."""
    index_columns = set()
    for arg in PackageRedemptionAudit.__table_args__:
        if hasattr(arg, "columns"):
            cols = tuple(c.key for c in arg.columns)
            index_columns.add(cols)
    assert ("redeemed_for_customer_id", "redeemed_at") in index_columns


def test_package_expiry_extension_forward_constraint():
    """Verify the forward-in-time CheckConstraint is declared."""
    constraint_names = set()
    for arg in PackageExpiryExtension.__table_args__:
        if hasattr(arg, "name"):
            constraint_names.add(arg.name)
    assert "ck_package_extend_forward_in_time" in constraint_names


def test_package_definition_item_max_redemptions_defaults_null(db_session, test_user, service_factory):
    """A definition item without max_redemptions stores NULL."""
    from app.models.package import (
        PackageDefinition, PackageDefinitionItem, EntitlementType, Shareability,
        PackageDefinitionStatus,
    )
    from decimal import Decimal
    svc = service_factory()
    pkg = PackageDefinition(
        name="t", status=PackageDefinitionStatus.DRAFT,
        entitlement_type=EntitlementType.COUNTED, total_sessions=5,
        shareability=Shareability.OWNER_ONLY, validity_days=30,
        auto_apply=True, cancellation_fee_pct=Decimal("20.00"),
        created_by_user_id=test_user.id,
    )
    db_session.add(pkg)
    db_session.flush()
    item = PackageDefinitionItem(
        package_definition_id=pkg.id,
        service_id=svc.id,
        quantity=1, unit_price_paise=10000, locked=False, display_order=0,
    )
    db_session.add(item)
    db_session.flush()
    assert item.max_redemptions is None


def test_package_definition_item_max_redemptions_rejects_zero(db_session, test_user, service_factory):
    """The CHECK constraint rejects max_redemptions=0."""
    import pytest
    from sqlalchemy.exc import IntegrityError
    from app.models.package import (
        PackageDefinition, PackageDefinitionItem, EntitlementType, Shareability,
        PackageDefinitionStatus,
    )
    from decimal import Decimal
    svc = service_factory()
    pkg = PackageDefinition(
        name="t", status=PackageDefinitionStatus.DRAFT,
        entitlement_type=EntitlementType.COUNTED, total_sessions=5,
        shareability=Shareability.OWNER_ONLY, validity_days=30,
        auto_apply=True, cancellation_fee_pct=Decimal("20.00"),
        created_by_user_id=test_user.id,
    )
    db_session.add(pkg)
    db_session.flush()
    item = PackageDefinitionItem(
        package_definition_id=pkg.id,
        service_id=svc.id,
        quantity=1, unit_price_paise=10000, locked=False, display_order=0,
        max_redemptions=0,
    )
    db_session.add(item)
    with pytest.raises(IntegrityError):
        db_session.flush()
    db_session.rollback()


def test_package_sale_item_remaining_must_match_cap_presence(
    db_session, test_user, service_factory, customer_factory, bill_factory,
    package_definition_factory,
):
    """remaining must be NULL iff max_redemptions is NULL."""
    import pytest
    from sqlalchemy.exc import IntegrityError
    from decimal import Decimal
    from datetime import datetime, timedelta, timezone
    from app.models.package import (
        PackageSale, PackageSaleItem, PackageSaleStatus, EntitlementType, Shareability,
    )
    from app.models.billing import BillStatus, BillType
    from app.models.billing import Bill

    svc = service_factory()
    customer = customer_factory()
    defn = package_definition_factory(services=[svc])
    bill = Bill(
        customer_id=customer.id,
        subtotal=10000,
        discount_amount=0,
        tax_amount=0,
        cgst_amount=0,
        sgst_amount=0,
        total_amount=10000,
        rounded_total=10000,
        rounding_adjustment=0,
        status=BillStatus.POSTED,
        bill_type=BillType.NORMAL,
        created_by=test_user.id,
    )
    db_session.add(bill)
    db_session.flush()

    sale = PackageSale(
        bill_id=bill.id,
        package_definition_id=defn.id,
        customer_id=customer.id,
        sold_at=datetime.now(timezone.utc),
        expires_at=datetime.now(timezone.utc) + timedelta(days=90),
        entitlement_type_snapshot=EntitlementType.COUNTED,
        shareability_snapshot=Shareability.OWNER_ONLY,
        cancellation_fee_pct_snapshot=Decimal("20.00"),
        total_sessions_snapshot=10,
        sessions_remaining=10,
        status=PackageSaleStatus.ACTIVE,
    )
    db_session.add(sale)
    db_session.flush()

    bad = PackageSaleItem(
        package_sale_id=sale.id,
        package_definition_item_id=defn.items[0].id,
        service_id=svc.id,
        quantity=1, snapshot_unit_price_paise=10000,
        snapshot_gst_rate_pct=Decimal("0"), locked=False, display_order=0,
        max_redemptions=3, remaining=None,
    )
    db_session.add(bad)
    with pytest.raises(IntegrityError):
        db_session.flush()
    db_session.rollback()
