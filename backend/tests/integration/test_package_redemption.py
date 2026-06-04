"""Integration tests for package_redemption_service.py."""

import pytest
from sqlalchemy import select
from app.services.package_redemption_service import apply_redemption, undo_redemption
from app.models.package import PackageRedemptionAudit, PackageSaleStatus
from app.models.billing import BillItem, BillItemType, Payment, PaymentMethod


def test_apply_decrements_sessions(
    db_session, service_factory, customer_factory, package_sale_factory,
    bill_item_factory, user_factory,
):
    """apply_redemption decrements sessions_remaining and creates audit + payment rows."""
    svc = service_factory(base_price=100000)
    customer = customer_factory()
    # total_sessions_snapshot=5 so session_number = 5 - 5 + 1 = 1 for the first redemption
    sale = package_sale_factory(
        customer=customer, services=[svc],
        sessions_remaining=5, total_sessions_snapshot=5,
    )
    bi = bill_item_factory(service_id=svc.id, base_price=100000)
    user = user_factory()

    audit = apply_redemption(
        db_session, sale.id, bi.id,
        redeemed_for_customer_id=customer.id,
        user_id=user.id,
    )

    db_session.refresh(sale)
    assert sale.sessions_remaining == 4
    assert audit.package_sale_id == sale.id
    assert audit.bill_item_id == bi.id
    assert audit.session_number == 1  # first session redeemed from a 5-session package

    db_session.refresh(bi)
    assert bi.item_type == BillItemType.PACKAGE_REDEMPTION
    assert bi.package_sale_id == sale.id

    # Internal Payment row
    pay = db_session.scalar(
        select(Payment).where(
            Payment.bill_id == bi.bill_id,
            Payment.payment_method == PaymentMethod.PACKAGE_REDEMPTION,
        )
    )
    assert pay is not None
    assert pay.amount == bi.base_price * bi.quantity


def test_apply_last_session_marks_exhausted(
    db_session, service_factory, customer_factory, package_sale_factory,
    bill_item_factory, user_factory,
):
    """Redeeming the last session sets status to EXHAUSTED."""
    svc = service_factory(base_price=100000)
    customer = customer_factory()
    sale = package_sale_factory(customer=customer, services=[svc], sessions_remaining=1)
    bi = bill_item_factory(service_id=svc.id, base_price=100000)
    user = user_factory()

    apply_redemption(db_session, sale.id, bi.id, customer.id, user.id)

    db_session.refresh(sale)
    assert sale.sessions_remaining == 0
    assert sale.status == PackageSaleStatus.EXHAUSTED


def test_apply_zero_sessions_raises(
    db_session, service_factory, customer_factory, package_sale_factory,
    bill_item_factory, user_factory,
):
    """apply_redemption raises ValueError when no sessions remain on an ACTIVE sale."""
    svc = service_factory(base_price=100000)
    customer = customer_factory()
    # ACTIVE with sessions_remaining=0 reaches guard 3 (sessions check) not guard 1 (status check)
    sale = package_sale_factory(
        customer=customer, services=[svc],
        sessions_remaining=0, status=PackageSaleStatus.ACTIVE,
    )
    bi = bill_item_factory(service_id=svc.id, base_price=100000)
    user = user_factory()

    with pytest.raises(ValueError, match="no sessions"):
        apply_redemption(db_session, sale.id, bi.id, customer.id, user.id)


def test_undo_restores_sessions(
    db_session, service_factory, customer_factory, package_sale_factory,
    bill_item_factory, user_factory,
):
    """undo_redemption restores sessions_remaining and removes audit + payment rows."""
    svc = service_factory(base_price=100000)
    customer = customer_factory()
    sale = package_sale_factory(customer=customer, services=[svc], sessions_remaining=5)
    bi = bill_item_factory(service_id=svc.id, base_price=100000)
    user = user_factory()

    audit = apply_redemption(db_session, sale.id, bi.id, customer.id, user.id)
    undo_redemption(db_session, audit.id, user.id)

    db_session.refresh(sale)
    assert sale.sessions_remaining == 5
    assert sale.status == PackageSaleStatus.ACTIVE
    assert db_session.get(PackageRedemptionAudit, audit.id) is None

    db_session.refresh(bi)
    assert bi.item_type == BillItemType.SERVICE
    assert bi.package_sale_id is None
    assert bi.base_price == svc.base_price  # Gap 2: base_price restored to original service price

    # Gap 3: PACKAGE_REDEMPTION Payment row must be deleted after undo
    pay_after = db_session.scalar(
        select(Payment).where(
            Payment.bill_id == bi.bill_id,
            Payment.payment_method == PaymentMethod.PACKAGE_REDEMPTION,
        )
    )
    assert pay_after is None
