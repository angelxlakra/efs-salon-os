"""Smoke test: model classes exist with expected columns."""

from app.models.package import (
    EntitlementType,
    PackageDefinition,
    PackageDefinitionItem,
    PackageDefinitionStatus,
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
