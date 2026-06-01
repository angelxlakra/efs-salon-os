"""Smoke test: model classes exist with expected columns."""

from app.models.package import (
    PackageDefinition,
    PackageDefinitionItem,
    PackageDefinitionStatus,
    EntitlementType,
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
