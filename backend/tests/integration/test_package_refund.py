"""Integration tests for package_refund_service.py."""

import pytest
from app.services.package_refund_service import issue_refund
from app.models.package import PackageSaleStatus
from app.models.billing import Bill, BillType, BillStatus, BillItem, BillItemType, Payment, PaymentMethod


def test_refund_counted_creates_credit_note(
    db_session, service_factory, customer_factory,
    package_sale_factory, user_factory,
):
    """issue_refund creates a CREDIT_NOTE bill with refund + fee line items."""
    svc = service_factory(base_price=200000)
    customer = customer_factory()
    user = user_factory()
    sale = package_sale_factory(
        customer=customer,
        services=[svc],
        sessions_remaining=5,
        total_sessions_snapshot=10,
    )

    credit_note = issue_refund(db_session, sale.id, "cash", "Customer relocating", user.id)

    assert credit_note.bill_type == BillType.CREDIT_NOTE
    assert credit_note.status == BillStatus.POSTED
    assert credit_note.original_bill_id == sale.bill_id

    items = db_session.query(BillItem).filter(BillItem.bill_id == credit_note.id).all()
    assert len(items) == 2  # refund line + fee line

    db_session.refresh(sale)
    assert sale.status == PackageSaleStatus.REFUNDED
    assert sale.refund_bill_id == credit_note.id
    assert sale.refunded_at is not None


def test_refund_already_refunded_raises(
    db_session, service_factory, customer_factory,
    package_sale_factory, user_factory,
):
    """issue_refund raises ValueError if sale is already refunded."""
    svc = service_factory(base_price=200000)
    customer = customer_factory()
    user = user_factory()
    sale = package_sale_factory(
        customer=customer, services=[svc],
        sessions_remaining=5, total_sessions_snapshot=10,
    )

    issue_refund(db_session, sale.id, "cash", "First refund", user.id)
    with pytest.raises(ValueError, match="already refunded"):
        issue_refund(db_session, sale.id, "cash", "Duplicate", user.id)


def test_refund_payment_row_created(
    db_session, service_factory, customer_factory,
    package_sale_factory, user_factory,
):
    """A Payment row with the correct amount is created on the credit note."""
    from sqlalchemy import select
    svc = service_factory(base_price=200000)
    customer = customer_factory()
    user = user_factory()
    sale = package_sale_factory(
        customer=customer, services=[svc],
        sessions_remaining=5, total_sessions_snapshot=10,
    )

    credit_note = issue_refund(db_session, sale.id, "cash", "Reason", user.id)

    pay = db_session.scalar(
        select(Payment).where(Payment.bill_id == credit_note.id)
    )
    assert pay is not None
    assert pay.payment_method == PaymentMethod.CASH
    # Refund amount should be positive (cash paid out)
    assert pay.amount > 0
