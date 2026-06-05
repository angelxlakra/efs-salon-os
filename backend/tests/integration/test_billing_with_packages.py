"""Integration tests for PackageSale creation at billing finalization."""

import pytest

from app.services.billing_service import BillingService
from app.models.billing import Bill, BillItem, BillItemType, BillStatus, BillType, Payment, PaymentMethod
from app.models.package import PackageSale


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
    import pytest

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
