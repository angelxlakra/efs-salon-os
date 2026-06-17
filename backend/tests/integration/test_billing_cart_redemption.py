"""Live-in-cart redemption: a service line carrying package_sale_id is redeemed
(not charged) at bill creation — the POS cart resolves eligibility and tells the
backend which package each covered line draws from."""

from app.services.billing_service import BillingService
from app.schemas.billing import BillItemCreate
from app.models.billing import BillItemType, Payment, PaymentMethod
from app.models.package import PackageSaleStatus


def test_bill_item_create_schema_preserves_package_sale_id():
    """Regression: the API schema must carry package_sale_id through to the
    service. Pydantic drops undeclared fields silently, which previously made
    redemptions vanish at the route boundary (bill charged in full)."""
    dumped = BillItemCreate(
        service_id="01HXX" + "A" * 21, package_sale_id="01HYY" + "B" * 21
    ).model_dump()
    assert dumped.get("package_sale_id") == "01HYY" + "B" * 21


def test_create_bill_applies_redemption_for_flagged_service_line(
    db_session, service_factory, customer_factory, package_sale_factory, test_user
):
    svc = service_factory(base_price=250000)
    customer = customer_factory()
    sale = package_sale_factory(
        customer=customer, services=[svc], sessions_remaining=5,
    )

    # Build items the way the route does — through the schema's model_dump,
    # so a missing schema field would be caught here.
    items = [
        BillItemCreate(service_id=svc.id, quantity=1, package_sale_id=sale.id).model_dump()
    ]
    bill = BillingService(db_session).create_bill(
        items=items,
        created_by_id=test_user.id,
        customer_id=customer.id,
    )

    # The service line is redeemed, not charged
    line = next(i for i in bill.items if i.service_id == svc.id)
    assert line.item_type == BillItemType.PACKAGE_REDEMPTION
    assert line.package_sale_id == sale.id

    # The package was decremented
    db_session.refresh(sale)
    assert sale.sessions_remaining == 4

    # An internal package-redemption payment covers the line (no cash due for it)
    pay = (
        db_session.query(Payment)
        .filter(Payment.bill_id == bill.id,
                Payment.payment_method == PaymentMethod.PACKAGE_REDEMPTION)
        .first()
    )
    assert pay is not None


def test_create_bill_without_package_sale_id_still_charges(
    db_session, service_factory, customer_factory, test_user
):
    """Control: a normal service line (no package_sale_id) is charged as before."""
    svc = service_factory(base_price=250000)
    customer = customer_factory()

    bill = BillingService(db_session).create_bill(
        items=[{"service_id": svc.id, "quantity": 1}],
        created_by_id=test_user.id,
        customer_id=customer.id,
    )
    line = next(i for i in bill.items if i.service_id == svc.id)
    assert line.item_type == BillItemType.SERVICE
