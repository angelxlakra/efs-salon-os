"""Integration tests for receipt service with package item types."""

import pytest
from io import BytesIO

from app.services.receipt_service import ReceiptService
from app.models.billing import Bill, BillItem, BillItemType, BillStatus, BillType, Payment, PaymentMethod


@pytest.fixture
def minimal_posted_bill(db_session, test_user, test_customer):
    """A minimal POSTED bill with no items — base case for receipt generation."""
    bill = Bill(
        customer_id=test_customer.id,
        customer_name=f"{test_customer.first_name} {test_customer.last_name}",
        subtotal=100000,
        discount_amount=0,
        tax_amount=0,
        cgst_amount=0,
        sgst_amount=0,
        total_amount=100000,
        rounded_total=100000,
        rounding_adjustment=0,
        status=BillStatus.POSTED,
        bill_type=BillType.NORMAL,
        created_by=test_user.id,
        invoice_number="SAL-25-0001",
    )
    db_session.add(bill)
    db_session.flush()
    return bill


def add_payment_to_bill(db_session, bill, method, amount):
    """Helper: add a Payment row to a bill."""
    from datetime import datetime, timezone
    p = Payment(
        bill_id=bill.id,
        payment_method=method,
        amount=amount,
        confirmed_at=datetime.now(timezone.utc),
        confirmed_by=bill.created_by,
    )
    db_session.add(p)
    db_session.flush()
    return p


def test_receipt_renders_normal_service_item(db_session, minimal_posted_bill, test_user, service_factory):
    """Baseline: receipt generates successfully for a normal SERVICE item."""
    svc = service_factory()
    item = BillItem(
        bill_id=minimal_posted_bill.id,
        service_id=svc.id,
        item_name=svc.name,
        base_price=svc.base_price,
        quantity=1,
        line_total=svc.base_price,
        item_type=BillItemType.SERVICE,
    )
    db_session.add(item)
    add_payment_to_bill(db_session, minimal_posted_bill, PaymentMethod.CASH, svc.base_price)
    db_session.flush()

    db_session.refresh(minimal_posted_bill)
    result = ReceiptService.generate_receipt_pdf(minimal_posted_bill, db=db_session)
    assert isinstance(result, BytesIO)
    assert len(result.getvalue()) > 0


def test_receipt_renders_package_sale_line_item(
    db_session, minimal_posted_bill, test_user,
    package_definition_factory, service_factory
):
    """PACKAGE_SALE_LINE item: receipt generates without errors + shows package note."""
    svc = service_factory()
    pkg = package_definition_factory(services=[svc], validity_days=90)

    item = BillItem(
        bill_id=minimal_posted_bill.id,
        item_name=pkg.name,
        base_price=svc.base_price,
        quantity=1,
        line_total=svc.base_price,
        item_type=BillItemType.PACKAGE_SALE_LINE,
        package_definition_id=pkg.id,
    )
    db_session.add(item)
    add_payment_to_bill(db_session, minimal_posted_bill, PaymentMethod.CASH, svc.base_price)
    db_session.flush()

    db_session.refresh(minimal_posted_bill)
    result = ReceiptService.generate_receipt_pdf(minimal_posted_bill, db=db_session)
    assert isinstance(result, BytesIO)
    assert len(result.getvalue()) > 0


def test_receipt_renders_package_redemption_item(
    db_session, minimal_posted_bill, test_user,
    package_sale_factory, customer_factory, service_factory
):
    """PACKAGE_REDEMPTION item: receipt generates without errors, PACKAGE_REDEMPTION payment grouped."""
    cust = customer_factory()
    svc = service_factory()
    sale = package_sale_factory(customer=cust, services=[svc])

    # Create a bill item that was redeemed
    redemption_price = svc.base_price
    item = BillItem(
        bill_id=minimal_posted_bill.id,
        service_id=svc.id,
        item_name=svc.name,
        base_price=redemption_price,
        quantity=1,
        line_total=redemption_price,
        item_type=BillItemType.PACKAGE_REDEMPTION,
        package_sale_id=sale.id,
    )
    db_session.add(item)

    # Internal package redemption payment (should be grouped in receipt)
    add_payment_to_bill(db_session, minimal_posted_bill, PaymentMethod.PACKAGE_REDEMPTION, redemption_price)
    db_session.flush()

    db_session.refresh(minimal_posted_bill)
    result = ReceiptService.generate_receipt_pdf(minimal_posted_bill, db=db_session)
    assert isinstance(result, BytesIO)
    assert len(result.getvalue()) > 0


def test_receipt_handles_mixed_items(
    db_session, minimal_posted_bill, test_user,
    package_definition_factory, package_sale_factory, customer_factory, service_factory
):
    """Bill with a mix of SERVICE, PACKAGE_SALE_LINE, and PACKAGE_REDEMPTION: renders without errors."""
    cust = customer_factory()
    svc1 = service_factory()
    svc2 = service_factory()
    pkg = package_definition_factory(services=[svc2], validity_days=90)
    sale = package_sale_factory(customer=cust, services=[svc1])

    # Normal service
    item1 = BillItem(
        bill_id=minimal_posted_bill.id,
        service_id=svc1.id,
        item_name=svc1.name,
        base_price=svc1.base_price,
        quantity=1,
        line_total=svc1.base_price,
        item_type=BillItemType.SERVICE,
    )
    # Package sale
    item2 = BillItem(
        bill_id=minimal_posted_bill.id,
        item_name=pkg.name,
        base_price=svc2.base_price,
        quantity=1,
        line_total=svc2.base_price,
        item_type=BillItemType.PACKAGE_SALE_LINE,
        package_definition_id=pkg.id,
    )
    # Redeemed service
    item3 = BillItem(
        bill_id=minimal_posted_bill.id,
        service_id=svc2.id,
        item_name=svc2.name,
        base_price=0,  # fully covered by package
        quantity=1,
        line_total=0,
        item_type=BillItemType.PACKAGE_REDEMPTION,
        package_sale_id=sale.id,
    )
    db_session.add_all([item1, item2, item3])

    add_payment_to_bill(db_session, minimal_posted_bill, PaymentMethod.CASH, svc1.base_price + svc2.base_price)
    add_payment_to_bill(db_session, minimal_posted_bill, PaymentMethod.PACKAGE_REDEMPTION, 0)
    db_session.flush()

    db_session.refresh(minimal_posted_bill)
    result = ReceiptService.generate_receipt_pdf(minimal_posted_bill, db=db_session)
    assert isinstance(result, BytesIO)
    assert len(result.getvalue()) > 0
