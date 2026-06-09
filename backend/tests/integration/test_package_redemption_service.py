"""Integration tests for per-line redemption cap logic in package_redemption_service.py.

These tests cover T7: enforce and decrement per-line remaining on apply/undo.
"""

import pytest
from app.services.package_redemption_service import apply_redemption, undo_redemption
from app.models.package import PackageRedemptionAudit


def test_apply_redemption_decrements_per_line_remaining(
    db_session, service_factory, customer_factory, package_sale_factory,
    bill_item_factory, user_factory,
):
    """apply_redemption decrements remaining when the line has a per-line cap."""
    svc = service_factory(base_price=100000)
    customer = customer_factory()
    sale = package_sale_factory(customer=customer, services=[svc], sessions_remaining=5)
    user = user_factory()

    # Set per-line cap on the sale item
    sale_item = next(it for it in sale.items if it.service_id == svc.id)
    sale_item.max_redemptions = 3
    sale_item.remaining = 3
    db_session.flush()

    bi = bill_item_factory(service_id=svc.id, base_price=100000)

    apply_redemption(db_session, sale.id, bi.id, customer.id, user.id)
    db_session.flush()
    db_session.refresh(sale_item)

    assert sale_item.remaining == 2


def test_apply_redemption_rejects_when_per_line_remaining_zero(
    db_session, service_factory, customer_factory, package_sale_factory,
    bill_item_factory, user_factory,
):
    """apply_redemption raises an error when remaining=0 (per-line cap exhausted)."""
    svc = service_factory(base_price=100000)
    customer = customer_factory()
    sale = package_sale_factory(customer=customer, services=[svc], sessions_remaining=5)
    user = user_factory()

    # Exhaust the per-line cap
    sale_item = next(it for it in sale.items if it.service_id == svc.id)
    sale_item.max_redemptions = 3
    sale_item.remaining = 0
    db_session.flush()

    bi = bill_item_factory(service_id=svc.id, base_price=100000)

    with pytest.raises(Exception):  # ValueError or HTTPException
        apply_redemption(db_session, sale.id, bi.id, customer.id, user.id)


def test_undo_redemption_restores_per_line_remaining(
    db_session, service_factory, customer_factory, package_sale_factory,
    bill_item_factory, user_factory,
):
    """undo_redemption increments remaining back by 1 after a prior apply."""
    svc = service_factory(base_price=100000)
    customer = customer_factory()
    sale = package_sale_factory(customer=customer, services=[svc], sessions_remaining=5)
    user = user_factory()

    # Simulate 1 already used: remaining=2 out of cap=3
    sale_item = next(it for it in sale.items if it.service_id == svc.id)
    sale_item.max_redemptions = 3
    sale_item.remaining = 2
    db_session.flush()

    bi = bill_item_factory(service_id=svc.id, base_price=100000)

    audit = apply_redemption(db_session, sale.id, bi.id, customer.id, user.id)
    db_session.flush()
    db_session.refresh(sale_item)
    assert sale_item.remaining == 1  # decremented by apply

    # Now undo — remaining should go back to 2
    undo_redemption(db_session, audit.id, user.id)
    db_session.flush()
    db_session.refresh(sale_item)
    assert sale_item.remaining == 2  # restored by undo
