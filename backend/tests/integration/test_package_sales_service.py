"""Integration tests for package_sales_service.create_sale."""

import pytest
from datetime import timedelta
from decimal import Decimal

from app.models.package import (
    PackageSaleStatus,
    EntitlementType,
    Shareability,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _call_create_sale(db_session, pkg, bill, customer, selling_staff_id=None):
    """Thin wrapper so all tests share the same import path."""
    from app.services.package_sales_service import create_sale
    return create_sale(
        db=db_session,
        package_definition_id=pkg.id,
        bill_id=bill.id,
        customer_id=customer.id,
        selling_staff_id=selling_staff_id,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestCreateSaleCountedSnapshots:
    """COUNTED entitlement: sessions_remaining mirrors total_sessions."""

    def test_create_sale_counted_snapshots_correctly(
        self,
        db_session,
        customer_factory,
        service_factory,
        package_definition_factory,
        bill_factory,
    ):
        customer = customer_factory()
        svc = service_factory(base_price=75000)
        pkg = package_definition_factory(
            services=[svc],
            entitlement_type=EntitlementType.COUNTED,
            total_sessions=10,
            validity_days=180,
        )
        bill = bill_factory(customer_id=customer.id)

        sale = _call_create_sale(db_session, pkg, bill, customer)

        assert sale.status == PackageSaleStatus.ACTIVE
        assert sale.sessions_remaining == 10
        assert sale.total_sessions_snapshot == 10
        # expires_at should be ~180 days after sold_at (allow 5-second clock drift)
        delta = sale.expires_at - sale.sold_at
        assert abs(delta - timedelta(days=180)) < timedelta(seconds=5)
        # Items
        assert len(sale.items) == len(pkg.items)
        assert sale.items[0].snapshot_unit_price_paise == svc.base_price
        assert sale.items[0].snapshot_gst_rate_pct == Decimal("0")


class TestCreateSaleUnlimited:
    """UNLIMITED entitlement: sessions_remaining and total_sessions_snapshot are None."""

    def test_create_sale_unlimited_has_null_sessions(
        self,
        db_session,
        customer_factory,
        service_factory,
        package_definition_factory,
        bill_factory,
    ):
        customer = customer_factory()
        svc = service_factory(base_price=30000)
        pkg = package_definition_factory(
            services=[svc],
            entitlement_type=EntitlementType.UNLIMITED,
            total_sessions=None,
            validity_days=90,
        )
        bill = bill_factory(customer_id=customer.id)

        sale = _call_create_sale(db_session, pkg, bill, customer)

        assert sale.sessions_remaining is None
        assert sale.total_sessions_snapshot is None
        assert sale.status == PackageSaleStatus.ACTIVE


class TestCreateSaleNotFound:
    """Unknown package_definition_id raises ValueError."""

    def test_create_sale_unknown_definition_raises(
        self,
        db_session,
        customer_factory,
        bill_factory,
    ):
        from app.services.package_sales_service import create_sale

        customer = customer_factory()
        bill = bill_factory(customer_id=customer.id)

        with pytest.raises(ValueError, match="not found"):
            create_sale(
                db=db_session,
                package_definition_id="NONEXISTENT00000000000000",
                bill_id=bill.id,
                customer_id=customer.id,
                selling_staff_id=None,
            )


class TestCreateSaleMultiItem:
    """Multi-item definition: one PackageSaleItem created per PackageDefinitionItem."""

    def test_create_sale_multi_item_definition(
        self,
        db_session,
        customer_factory,
        service_factory,
        package_definition_factory,
        bill_factory,
    ):
        customer = customer_factory()
        svc1 = service_factory(base_price=50000)
        svc2 = service_factory(base_price=80000)
        pkg = package_definition_factory(
            services=[svc1, svc2],
            entitlement_type=EntitlementType.COUNTED,
            total_sessions=5,
            validity_days=60,
        )
        bill = bill_factory(customer_id=customer.id)

        sale = _call_create_sale(db_session, pkg, bill, customer)

        assert len(sale.items) == 2

        # Build lookup by service_id for order-independent assertions
        items_by_service = {item.service_id: item for item in sale.items}

        assert svc1.id in items_by_service
        assert items_by_service[svc1.id].snapshot_unit_price_paise == svc1.base_price

        assert svc2.id in items_by_service
        assert items_by_service[svc2.id].snapshot_unit_price_paise == svc2.base_price
