"""Integration tests for package_catalog_service.py."""

import pytest
from decimal import Decimal
from app.services.package_catalog_service import (
    create_definition, publish, archive, soft_delete, update_definition,
)
from app.schemas.package import (
    PackageDefinitionCreate, PackageDefinitionItemCreate, DiscountInput,
    PackageDefinitionUpdate,
)
from app.models.package import PackageDefinitionStatus, EntitlementType, Shareability


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_service(db_session, name_suffix=""):
    from app.models.service import Service, ServiceCategory
    cat = ServiceCategory(
        name=f"Cat{name_suffix}", display_order=1, is_active=True
    )
    db_session.add(cat)
    db_session.flush()
    svc = Service(
        category_id=cat.id,
        name=f"Service{name_suffix}",
        base_price=100000,
        duration_minutes=30,
        is_active=True,
        display_order=1,
    )
    db_session.add(svc)
    db_session.flush()
    return svc


def _counted_payload(items, discount=None):
    return PackageDefinitionCreate(
        name="Test Pack",
        entitlement_type=EntitlementType.COUNTED,
        total_sessions=5,
        validity_days=90,
        shareability=Shareability.OWNER_ONLY,
        items=items,
        discount=discount,
    )


# ---------------------------------------------------------------------------
# create_definition
# ---------------------------------------------------------------------------

def test_create_with_discount_distribution(db_session, user_factory):
    """create_definition applies percentage discount to item prices."""
    svc1 = _make_service(db_session, "A")
    svc2 = _make_service(db_session, "B")
    user = user_factory()
    payload = _counted_payload(
        items=[
            PackageDefinitionItemCreate(service_id=svc1.id, quantity=1, unit_price_paise=200000),
            PackageDefinitionItemCreate(service_id=svc2.id, quantity=1, unit_price_paise=200000),
        ],
        discount=DiscountInput(mode="pct", value=Decimal("20")),
    )
    pkg = create_definition(db_session, payload, user.id)
    assert pkg.status == PackageDefinitionStatus.DRAFT
    # 20% off 200000 = 160000 per item
    assert all(i.unit_price_paise == 160000 for i in pkg.items)


def test_create_without_discount(db_session, user_factory):
    """create_definition without discount preserves original prices."""
    svc = _make_service(db_session, "C")
    user = user_factory()
    payload = _counted_payload(
        items=[
            PackageDefinitionItemCreate(service_id=svc.id, quantity=1, unit_price_paise=150000),
        ],
    )
    pkg = create_definition(db_session, payload, user.id)
    assert pkg.status == PackageDefinitionStatus.DRAFT
    assert pkg.items[0].unit_price_paise == 150000


def test_create_flat_discount(db_session, user_factory):
    """create_definition applies flat discount across unlocked items."""
    svc = _make_service(db_session, "D")
    user = user_factory()
    payload = _counted_payload(
        items=[
            PackageDefinitionItemCreate(service_id=svc.id, quantity=1, unit_price_paise=300000),
        ],
        discount=DiscountInput(mode="flat", value=Decimal("50000")),
    )
    pkg = create_definition(db_session, payload, user.id)
    assert pkg.items[0].unit_price_paise == 250000


# ---------------------------------------------------------------------------
# publish
# ---------------------------------------------------------------------------

def test_publish_from_draft(db_session, user_factory):
    """publish() transitions DRAFT -> PUBLISHED."""
    svc = _make_service(db_session, "E")
    user = user_factory()
    payload = _counted_payload(
        items=[PackageDefinitionItemCreate(service_id=svc.id, quantity=1, unit_price_paise=100000)],
    )
    pkg = create_definition(db_session, payload, user.id)
    assert pkg.status == PackageDefinitionStatus.DRAFT

    result = publish(db_session, pkg.id)
    assert result.status == PackageDefinitionStatus.PUBLISHED


def test_publish_only_from_draft_raises(db_session, user_factory):
    """publish() on a non-DRAFT package raises ValueError."""
    svc = _make_service(db_session, "F")
    user = user_factory()
    payload = _counted_payload(
        items=[PackageDefinitionItemCreate(service_id=svc.id, quantity=1, unit_price_paise=100000)],
    )
    pkg = create_definition(db_session, payload, user.id)
    publish(db_session, pkg.id)  # now PUBLISHED
    with pytest.raises(ValueError, match="draft"):
        publish(db_session, pkg.id)  # second publish should fail


# ---------------------------------------------------------------------------
# archive
# ---------------------------------------------------------------------------

def test_archive_published(db_session, user_factory):
    """archive() sets status to ARCHIVED on a published package."""
    svc = _make_service(db_session, "G")
    user = user_factory()
    payload = _counted_payload(
        items=[PackageDefinitionItemCreate(service_id=svc.id, quantity=1, unit_price_paise=100000)],
    )
    pkg = create_definition(db_session, payload, user.id)
    publish(db_session, pkg.id)

    result = archive(db_session, pkg.id)
    assert result.status == PackageDefinitionStatus.ARCHIVED


# ---------------------------------------------------------------------------
# soft_delete
# ---------------------------------------------------------------------------

def test_soft_delete_allowed_when_no_active_sales(db_session, user_factory):
    """soft_delete() succeeds when no active PackageSales exist."""
    svc = _make_service(db_session, "H")
    user = user_factory()
    payload = _counted_payload(
        items=[PackageDefinitionItemCreate(service_id=svc.id, quantity=1, unit_price_paise=100000)],
    )
    pkg = create_definition(db_session, payload, user.id)

    soft_delete(db_session, pkg.id)
    db_session.refresh(pkg)
    assert pkg.deleted_at is not None


def test_soft_delete_blocked_when_active_sales(
    db_session, user_factory,
):
    """soft_delete() raises ValueError when active PackageSales exist."""
    svc = _make_service(db_session, "I")
    user = user_factory()
    payload = _counted_payload(
        items=[PackageDefinitionItemCreate(service_id=svc.id, quantity=1, unit_price_paise=100000)],
    )
    pkg = create_definition(db_session, payload, user.id)
    publish(db_session, pkg.id)

    from app.models.customer import Customer
    customer = Customer(
        first_name="Block", last_name="Test", phone="9000000001",
        total_visits=0, total_spent=0,
    )
    db_session.add(customer)
    db_session.flush()

    # Create an active sale referencing this definition's id directly
    from datetime import datetime, timedelta, timezone
    from decimal import Decimal as D
    from app.models.billing import Bill, BillStatus, BillType
    from app.models.package import PackageSale, PackageSaleStatus, EntitlementType, Shareability
    from app.models.user import User

    bill = Bill(
        customer_id=customer.id,
        subtotal=100000,
        discount_amount=0,
        tax_amount=18000,
        cgst_amount=9000,
        sgst_amount=9000,
        total_amount=118000,
        rounded_total=118000,
        rounding_adjustment=0,
        status=BillStatus.POSTED,
        bill_type=BillType.NORMAL,
        created_by=user.id,
    )
    db_session.add(bill)
    db_session.flush()

    sale = PackageSale(
        bill_id=bill.id,
        package_definition_id=pkg.id,
        customer_id=customer.id,
        sold_at=datetime.now(timezone.utc),
        expires_at=datetime.now(timezone.utc) + timedelta(days=90),
        entitlement_type_snapshot=EntitlementType.COUNTED,
        shareability_snapshot=Shareability.OWNER_ONLY,
        cancellation_fee_pct_snapshot=D("20.00"),
        total_sessions_snapshot=5,
        sessions_remaining=5,
        status=PackageSaleStatus.ACTIVE,
    )
    db_session.add(sale)
    db_session.flush()

    with pytest.raises(ValueError, match="active sales"):
        soft_delete(db_session, pkg.id)


# ---------------------------------------------------------------------------
# update_definition
# ---------------------------------------------------------------------------

def test_update_definition_replaces_items(db_session, user_factory):
    """update_definition clears old items and re-inserts new ones."""
    svc1 = _make_service(db_session, "J")
    svc2 = _make_service(db_session, "K")
    user = user_factory()
    payload = _counted_payload(
        items=[PackageDefinitionItemCreate(service_id=svc1.id, quantity=1, unit_price_paise=100000)],
    )
    pkg = create_definition(db_session, payload, user.id)
    original_id = pkg.items[0].id

    update_payload = PackageDefinitionUpdate(
        name="Updated Pack",
        entitlement_type=EntitlementType.COUNTED,
        total_sessions=5,
        validity_days=90,
        shareability=Shareability.OWNER_ONLY,
        items=[
            PackageDefinitionItemCreate(service_id=svc2.id, quantity=2, unit_price_paise=200000),
        ],
    )
    updated = update_definition(db_session, pkg.id, update_payload, user.id)
    assert updated.name == "Updated Pack"
    assert len(updated.items) == 1
    assert updated.items[0].service_id == svc2.id
    assert updated.items[0].quantity == 2
    # Old item must be gone
    assert updated.items[0].id != original_id


def test_update_definition_not_found_raises(db_session, user_factory):
    """update_definition raises ValueError for unknown id."""
    user = user_factory()
    svc = _make_service(db_session, "L")
    update_payload = PackageDefinitionUpdate(
        name="Ghost",
        entitlement_type=EntitlementType.COUNTED,
        total_sessions=5,
        validity_days=90,
        shareability=Shareability.OWNER_ONLY,
        items=[PackageDefinitionItemCreate(service_id=svc.id, quantity=1, unit_price_paise=100000)],
    )
    with pytest.raises(ValueError, match="not found"):
        update_definition(db_session, "00000000000000000000000000", update_payload, user.id)
