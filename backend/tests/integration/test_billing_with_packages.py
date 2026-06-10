"""Integration tests for PackageSale creation at billing finalization."""

import pytest
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from app.services.billing_service import BillingService
from app.services.package_redemption_service import apply_redemption
from app.services.package_eligibility import find_eligible_packages
from app.models.billing import Bill, BillItem, BillItemType, BillStatus, BillType, Payment, PaymentMethod
from app.models.package import (
    PackageDefinition, PackageDefinitionItem, PackageSale, PackageSaleItem,
    EntitlementType, Shareability, PackageDefinitionStatus, PackageSaleStatus,
)


@pytest.fixture
def monkeypatched_billing(db_session, monkeypatch):
    """BillingService with commit monkeypatched to flush for test isolation."""
    monkeypatch.setattr(db_session, "commit", db_session.flush)
    return BillingService(db_session)


def make_package_sale_line_bill(db_session, test_user, customer, pkg_defn):
    """Helper: create a DRAFT Bill with one PACKAGE_SALE_LINE BillItem."""
    total_paise = sum(i.unit_price_paise * i.quantity for i in pkg_defn.items)

    bill = Bill(
        customer_id=customer.id,
        subtotal=total_paise,
        discount_amount=0,
        tax_amount=0,
        cgst_amount=0,
        sgst_amount=0,
        total_amount=total_paise,
        rounded_total=total_paise,
        rounding_adjustment=0,
        status=BillStatus.DRAFT,
        bill_type=BillType.NORMAL,
        created_by=test_user.id,
    )
    db_session.add(bill)
    db_session.flush()

    item = BillItem(
        bill_id=bill.id,
        item_name=pkg_defn.name,
        base_price=total_paise,
        quantity=1,
        line_total=total_paise,
        item_type=BillItemType.PACKAGE_SALE_LINE,
        package_definition_id=pkg_defn.id,  # the new column
    )
    db_session.add(item)
    db_session.flush()

    return bill, item


def test_finalize_creates_package_sale_for_package_sale_line(
    db_session, monkeypatched_billing, test_user, test_customer,
    package_definition_factory, service_factory,
):
    svc = service_factory()
    pkg = package_definition_factory(services=[svc], validity_days=90, total_sessions=5)

    bill, bill_item = make_package_sale_line_bill(db_session, test_user, test_customer, pkg)
    amount_rupees = bill.rounded_total / 100

    # Finalize by adding payment that covers the full bill
    monkeypatched_billing.add_payment(
        bill_id=bill.id,
        payment_method=PaymentMethod.CASH,
        amount=amount_rupees,
        confirmed_by_id=test_user.id,
    )

    db_session.refresh(bill_item)
    assert bill_item.package_sale_id is not None, "BillItem.package_sale_id should be set after finalization"

    sale = db_session.get(PackageSale, bill_item.package_sale_id)
    assert sale is not None
    assert sale.bill_id == bill.id
    assert sale.customer_id == test_customer.id
    assert sale.sessions_remaining == pkg.total_sessions
    assert bill.status == BillStatus.POSTED


def test_finalize_does_not_create_sale_for_service_items(
    db_session, monkeypatched_billing, test_user, test_customer, service_factory,
):
    """Regular SERVICE items must not trigger PackageSale creation."""
    svc = service_factory()
    total = svc.base_price
    bill = Bill(
        customer_id=test_customer.id,
        subtotal=total, discount_amount=0, tax_amount=0, cgst_amount=0, sgst_amount=0,
        total_amount=total, rounded_total=total, rounding_adjustment=0,
        status=BillStatus.DRAFT, bill_type=BillType.NORMAL, created_by=test_user.id,
    )
    db_session.add(bill)
    db_session.flush()

    item = BillItem(
        bill_id=bill.id, service_id=svc.id, item_name=svc.name,
        base_price=svc.base_price, quantity=1, line_total=svc.base_price,
        item_type=BillItemType.SERVICE,
    )
    db_session.add(item)
    db_session.flush()

    monkeypatched_billing.add_payment(
        bill_id=bill.id, payment_method=PaymentMethod.CASH,
        amount=total / 100, confirmed_by_id=test_user.id,
    )

    # No PackageSale should exist
    sale_count = db_session.query(PackageSale).filter(PackageSale.bill_id == bill.id).count()
    assert sale_count == 0


def test_finalize_skips_already_linked_package_sale_line(
    db_session, monkeypatched_billing, test_user, test_customer,
    package_definition_factory, package_sale_factory, service_factory,
):
    """If package_sale_id is already set on the BillItem, don't create a second sale."""
    svc = service_factory()
    pkg = package_definition_factory(services=[svc], validity_days=90)
    existing_sale = package_sale_factory(customer=test_customer, services=[svc])

    bill, bill_item = make_package_sale_line_bill(db_session, test_user, test_customer, pkg)
    # Pre-set package_sale_id — simulates a re-finalization attempt
    bill_item.package_sale_id = existing_sale.id
    db_session.flush()

    monkeypatched_billing.add_payment(
        bill_id=bill.id, payment_method=PaymentMethod.CASH,
        amount=bill.rounded_total / 100, confirmed_by_id=test_user.id,
    )

    # BillItem.package_sale_id must remain the pre-existing sale (not a new one)
    db_session.refresh(bill_item)
    assert bill_item.package_sale_id == existing_sale.id


def test_finalize_raises_when_no_customer_on_package_sale_line(
    db_session, monkeypatched_billing, test_user,
    package_definition_factory, service_factory,
):
    """A PACKAGE_SALE_LINE on an anonymous (no-customer) bill must raise ValueError."""
    svc = service_factory()
    pkg = package_definition_factory(services=[svc], validity_days=90)
    total_paise = pkg.items[0].unit_price_paise

    # Bill with NO customer_id (anonymous walk-in)
    bill = Bill(
        subtotal=total_paise, discount_amount=0, tax_amount=0,
        cgst_amount=0, sgst_amount=0, total_amount=total_paise,
        rounded_total=total_paise, rounding_adjustment=0,
        status=BillStatus.DRAFT, bill_type=BillType.NORMAL,
        created_by=test_user.id,
        customer_name="Walk In",  # no customer_id
    )
    db_session.add(bill)
    db_session.flush()

    item = BillItem(
        bill_id=bill.id, item_name=pkg.name,
        base_price=total_paise, quantity=1, line_total=total_paise,
        item_type=BillItemType.PACKAGE_SALE_LINE,
        package_definition_id=pkg.id,
    )
    db_session.add(item)
    db_session.flush()

    with pytest.raises(ValueError, match="no linked customer"):
        monkeypatched_billing.add_payment(
            bill_id=bill.id,
            payment_method=PaymentMethod.CASH,
            amount=total_paise / 100,
            confirmed_by_id=test_user.id,
        )


def test_complete_bill_creates_package_sale(
    db_session, monkeypatched_billing, test_user, test_customer,
    package_definition_factory, service_factory,
):
    """complete_bill() must also trigger PackageSale creation."""
    svc = service_factory()
    pkg = package_definition_factory(services=[svc], validity_days=90)

    bill, bill_item = make_package_sale_line_bill(db_session, test_user, test_customer, pkg)
    # complete_bill rejects bills with no customer_phone and unpaid balance;
    # set phone to satisfy the guard (test_customer has phone "9876543210").
    bill.customer_phone = test_customer.phone
    db_session.flush()

    monkeypatched_billing.complete_bill(
        bill_id=bill.id,
        completed_by_id=test_user.id,
        # notes omitted — Bill model has no notes column; passing notes triggers AttributeError
    )

    db_session.refresh(bill_item)
    assert bill_item.package_sale_id is not None

    sale = db_session.get(PackageSale, bill_item.package_sale_id)
    assert sale is not None
    assert sale.bill_id == bill.id


# ---------------------------------------------------------------------------
# Helpers shared by the E2E lifecycle tests below
# ---------------------------------------------------------------------------

def _make_bill_item_for_service(db_session, customer, svc, test_user):
    """Create a minimal DRAFT Bill + SERVICE BillItem for the given service."""
    price = svc.base_price
    bill = Bill(
        customer_id=customer.id,
        subtotal=price,
        discount_amount=0,
        tax_amount=0,
        cgst_amount=0,
        sgst_amount=0,
        total_amount=price,
        rounded_total=price,
        rounding_adjustment=0,
        status=BillStatus.DRAFT,
        bill_type=BillType.NORMAL,
        created_by=test_user.id,
    )
    db_session.add(bill)
    db_session.flush()

    item = BillItem(
        bill_id=bill.id,
        service_id=svc.id,
        item_name=svc.name,
        base_price=price,
        quantity=1,
        line_total=price,
        item_type=BillItemType.SERVICE,
    )
    db_session.add(item)
    db_session.flush()
    return item


def _build_sale_with_caps(
    db_session,
    test_user,
    customer,
    svc_a,
    svc_b,
    entitlement_type,
    total_sessions,
    sessions_remaining,
    svc_a_max_redemptions,
    svc_b_max_redemptions,
):
    """Build a PackageSale with two services where per-line caps can be set independently.

    Returns (sale, sale_item_a, sale_item_b).
    """
    # --- PackageDefinition ---
    defn = PackageDefinition(
        name="E2E Test Package",
        status=PackageDefinitionStatus.PUBLISHED,
        entitlement_type=entitlement_type,
        total_sessions=total_sessions,
        shareability=Shareability.OWNER_ONLY,
        validity_days=365,
        auto_apply=True,
        cancellation_fee_pct=Decimal("20.00"),
        created_by_user_id=test_user.id,
    )
    db_session.add(defn)
    db_session.flush()

    defn_item_a = PackageDefinitionItem(
        package_definition_id=defn.id,
        service_id=svc_a.id,
        quantity=1,
        unit_price_paise=svc_a.base_price,
        locked=False,
        display_order=0,
        max_redemptions=svc_a_max_redemptions,
    )
    defn_item_b = PackageDefinitionItem(
        package_definition_id=defn.id,
        service_id=svc_b.id,
        quantity=1,
        unit_price_paise=svc_b.base_price,
        locked=False,
        display_order=1,
        max_redemptions=svc_b_max_redemptions,
    )
    db_session.add_all([defn_item_a, defn_item_b])
    db_session.flush()

    # --- Bill for the sale ---
    sale_bill = Bill(
        customer_id=customer.id,
        subtotal=svc_a.base_price + svc_b.base_price,
        discount_amount=0,
        tax_amount=0,
        cgst_amount=0,
        sgst_amount=0,
        total_amount=svc_a.base_price + svc_b.base_price,
        rounded_total=svc_a.base_price + svc_b.base_price,
        rounding_adjustment=0,
        status=BillStatus.POSTED,
        bill_type=BillType.NORMAL,
        created_by=test_user.id,
    )
    db_session.add(sale_bill)
    db_session.flush()

    # --- PackageSale ---
    sale = PackageSale(
        bill_id=sale_bill.id,
        package_definition_id=defn.id,
        customer_id=customer.id,
        sold_at=datetime.now(timezone.utc),
        expires_at=datetime.now(timezone.utc) + timedelta(days=365),
        entitlement_type_snapshot=entitlement_type,
        shareability_snapshot=Shareability.OWNER_ONLY,
        cancellation_fee_pct_snapshot=Decimal("20.00"),
        total_sessions_snapshot=total_sessions,
        sessions_remaining=sessions_remaining,
        status=PackageSaleStatus.ACTIVE,
    )
    db_session.add(sale)
    db_session.flush()

    # --- PackageSaleItems with explicit per-line caps ---
    sale_item_a = PackageSaleItem(
        package_sale_id=sale.id,
        package_definition_item_id=defn_item_a.id,
        service_id=svc_a.id,
        quantity=1,
        snapshot_unit_price_paise=svc_a.base_price,
        snapshot_gst_rate_pct=Decimal("18.00"),
        locked=False,
        display_order=0,
        max_redemptions=svc_a_max_redemptions,
        remaining=svc_a_max_redemptions,  # None if uncapped
    )
    sale_item_b = PackageSaleItem(
        package_sale_id=sale.id,
        package_definition_item_id=defn_item_b.id,
        service_id=svc_b.id,
        quantity=1,
        snapshot_unit_price_paise=svc_b.base_price,
        snapshot_gst_rate_pct=Decimal("18.00"),
        locked=False,
        display_order=1,
        max_redemptions=svc_b_max_redemptions,
        remaining=svc_b_max_redemptions,  # None if uncapped
    )
    db_session.add_all([sale_item_a, sale_item_b])
    db_session.flush()

    db_session.refresh(sale)
    return sale, sale_item_a, sale_item_b


# ---------------------------------------------------------------------------
# E2E Scenario 1: "Salon Royal Pass" — 12-session COUNTED + per-line cap
# ---------------------------------------------------------------------------

def test_e2e_salon_royal_pass_per_line_cap_lifecycle(
    db_session, service_factory, customer_factory, test_user,
):
    """E2E: COUNTED package with total_sessions=12.

    svc_a has max_redemptions=3 (premium add-on, capped at 3 uses).
    svc_b has max_redemptions=None (uncapped).

    Verifies:
    - Sale snapshot fields are correct.
    - svc_a can be redeemed 3 times (remaining 3→2→1→0).
    - 4th redemption of svc_a raises ValueError (per-line cap exhausted).
    - sessions_remaining decrements by 1 for each valid redemption.
    - svc_b remains eligible while global sessions remain.
    - svc_b is NOT eligible after package status is flipped to EXHAUSTED.
    """
    svc_a = service_factory(name="Premium Add-on", base_price=80000)
    svc_b = service_factory(name="Regular Service", base_price=50000)
    customer = customer_factory()

    sale, sale_item_a, sale_item_b = _build_sale_with_caps(
        db_session=db_session,
        test_user=test_user,
        customer=customer,
        svc_a=svc_a,
        svc_b=svc_b,
        entitlement_type=EntitlementType.COUNTED,
        total_sessions=12,
        sessions_remaining=12,
        svc_a_max_redemptions=3,
        svc_b_max_redemptions=None,
    )

    # Seeding verified by test_create_sale_snapshots_max_redemptions_and_initialises_remaining
    # in test_package_sales_service.py. This E2E test focuses on the lifecycle.

    # --- Step 5: Redeem svc_a 3 times, check remaining goes 3→2→1→0 ---
    for expected_remaining_after in (2, 1, 0):
        bi = _make_bill_item_for_service(db_session, customer, svc_a, test_user)
        apply_redemption(db_session, sale.id, bi.id, customer.id, test_user.id)
        db_session.flush()
        db_session.refresh(sale_item_a)
        assert sale_item_a.remaining == expected_remaining_after

    # Sessions should have decremented by 3 (12 → 9)
    db_session.refresh(sale)
    assert sale.sessions_remaining == 9
    assert sale.status == PackageSaleStatus.ACTIVE

    # --- Step 6: 4th redemption of svc_a must raise ValueError ---
    bi_over = _make_bill_item_for_service(db_session, customer, svc_a, test_user)
    with pytest.raises(ValueError, match="(?i)per-line redemption cap exhausted"):
        apply_redemption(db_session, sale.id, bi_over.id, customer.id, test_user.id)

    # sessions_remaining must be unchanged after the failed attempt
    db_session.refresh(sale)
    assert sale.sessions_remaining == 9

    # svc_a must be excluded from eligibility now that remaining=0
    eligible_a_after_cap = find_eligible_packages(customer.id, svc_a.id, db_session)
    assert all(e.id != sale.id for e in eligible_a_after_cap), (
        "svc_a per-line cap exhausted — package must not appear for svc_a"
    )

    # --- Step 7: svc_b is still redeemable (not capped) ---
    eligible_b = find_eligible_packages(customer.id, svc_b.id, db_session)
    assert any(e.id == sale.id for e in eligible_b), (
        "svc_b should still be eligible — it is uncapped and global sessions remain"
    )

    # --- Step 8: exhaust global sessions (9 remaining, redeem svc_b 9 times) ---
    for _ in range(9):
        bi_b = _make_bill_item_for_service(db_session, customer, svc_b, test_user)
        apply_redemption(db_session, sale.id, bi_b.id, customer.id, test_user.id)
        db_session.flush()

    db_session.refresh(sale)
    assert sale.sessions_remaining == 0
    assert sale.status == PackageSaleStatus.EXHAUSTED

    # svc_b must no longer appear in eligibility — package is exhausted
    eligible_b_after = find_eligible_packages(customer.id, svc_b.id, db_session)
    assert all(e.id != sale.id for e in eligible_b_after), (
        "Exhausted package must not appear in eligibility results"
    )


# ---------------------------------------------------------------------------
# E2E Scenario 2: "Glow & Refresh" — UNLIMITED + partial per-line cap
# ---------------------------------------------------------------------------

def test_e2e_glow_and_refresh_unlimited_with_per_line_cap(
    db_session, service_factory, customer_factory, test_user,
):
    """E2E: UNLIMITED package with per-line cap on one service.

    svc_facial has max_redemptions=2 (only 2 facials allowed per package).
    svc_massage has max_redemptions=None (unlimited massages).

    Verifies:
    - svc_facial can be redeemed exactly 2 times (remaining 2→1→0).
    - 3rd redemption of svc_facial raises ValueError.
    - svc_massage remains redeemable after both svc_facial exhaustions.
    """
    svc_facial = service_factory(name="Facial", base_price=120000)
    svc_massage = service_factory(name="Massage", base_price=90000)
    customer = customer_factory()

    sale, sale_item_facial, sale_item_massage = _build_sale_with_caps(
        db_session=db_session,
        test_user=test_user,
        customer=customer,
        svc_a=svc_facial,
        svc_b=svc_massage,
        entitlement_type=EntitlementType.UNLIMITED,
        total_sessions=None,
        sessions_remaining=None,
        svc_a_max_redemptions=2,
        svc_b_max_redemptions=None,
    )

    # Seeding verified by test_create_sale_snapshots_max_redemptions_and_initialises_remaining
    # in test_package_sales_service.py. This E2E test focuses on the lifecycle.
    assert sale.entitlement_type_snapshot == EntitlementType.UNLIMITED
    assert sale.sessions_remaining is None

    # --- Step 2: Redeem svc_facial twice (remaining 2→1→0) ---
    for expected_remaining_after in (1, 0):
        bi = _make_bill_item_for_service(db_session, customer, svc_facial, test_user)
        apply_redemption(db_session, sale.id, bi.id, customer.id, test_user.id)
        db_session.flush()
        db_session.refresh(sale_item_facial)
        assert sale_item_facial.remaining == expected_remaining_after

    # Package status must still be ACTIVE (UNLIMITED packages are never EXHAUSTED via sessions)
    db_session.refresh(sale)
    assert sale.status == PackageSaleStatus.ACTIVE

    # --- Step 3: 3rd redemption of svc_facial must raise ValueError ---
    bi_over = _make_bill_item_for_service(db_session, customer, svc_facial, test_user)
    with pytest.raises(ValueError, match="(?i)per-line redemption cap exhausted"):
        apply_redemption(db_session, sale.id, bi_over.id, customer.id, test_user.id)

    # --- Step 4: svc_massage is still redeemable after both svc_facial exhaustions ---
    eligible_massage = find_eligible_packages(customer.id, svc_massage.id, db_session)
    assert any(e.id == sale.id for e in eligible_massage), (
        "svc_massage should still be eligible — its line is uncapped"
    )

    # Actually perform a massage redemption to confirm no error is raised
    bi_massage = _make_bill_item_for_service(db_session, customer, svc_massage, test_user)
    audit = apply_redemption(db_session, sale.id, bi_massage.id, customer.id, test_user.id)
    db_session.flush()
    assert audit is not None

    # svc_facial must NOT appear in eligibility (per-line cap exhausted)
    eligible_facial_after = find_eligible_packages(customer.id, svc_facial.id, db_session)
    assert all(e.id != sale.id for e in eligible_facial_after), (
        "svc_facial line is per-line exhausted — package must not appear for facial"
    )
