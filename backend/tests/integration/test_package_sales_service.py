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


def test_create_sale_snapshots_max_redemptions_and_initialises_remaining(
    db_session, service_factory, customer_factory, test_user,
):
    """When a PackageDefinitionItem has max_redemptions, the PackageSaleItem
    stores max_redemptions (snapshotted) and remaining = max_redemptions.
    For uncapped items, both columns stay null."""
    from datetime import datetime, timezone
    from app.models.billing import Bill, BillStatus, BillType
    from app.models.package import (
        PackageDefinition, PackageDefinitionItem, PackageDefinitionStatus,
        EntitlementType, Shareability,
    )
    from app.services.package_sales_service import create_sale
    from decimal import Decimal

    svc_a = service_factory(base_price=100000)
    svc_b = service_factory(base_price=50000)
    customer = customer_factory()

    pkg = PackageDefinition(
        name="Royal", status=PackageDefinitionStatus.PUBLISHED,
        entitlement_type=EntitlementType.COUNTED, total_sessions=12,
        shareability=Shareability.OWNER_ONLY, validity_days=180,
        auto_apply=True, cancellation_fee_pct=Decimal("20.00"),
        created_by_user_id=test_user.id,
    )
    pkg.items = [
        PackageDefinitionItem(
            service_id=svc_a.id, quantity=1, unit_price_paise=100000,
            locked=False, display_order=0, max_redemptions=3,
        ),
        PackageDefinitionItem(
            service_id=svc_b.id, quantity=1, unit_price_paise=50000,
            locked=False, display_order=1, max_redemptions=None,
        ),
    ]
    db_session.add(pkg)
    db_session.flush()

    bill = Bill(
        customer_id=customer.id, subtotal=150000, discount_amount=0,
        tax_amount=27000, cgst_amount=13500, sgst_amount=13500,
        total_amount=177000, rounded_total=177000, rounding_adjustment=0,
        status=BillStatus.POSTED, bill_type=BillType.NORMAL,
        created_by=test_user.id,
    )
    db_session.add(bill)
    db_session.flush()

    sale = create_sale(
        db_session, package_definition_id=pkg.id, bill_id=bill.id,
        customer_id=customer.id, selling_staff_id=None,
    )
    by_svc = {it.service_id: it for it in sale.items}
    assert by_svc[svc_a.id].max_redemptions == 3
    assert by_svc[svc_a.id].remaining == 3
    assert by_svc[svc_b.id].max_redemptions is None
    assert by_svc[svc_b.id].remaining is None
