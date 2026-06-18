"""Buy a v2 package and redeem its services in the SAME cart.

The redemption happens at DRAFT (create_bill), before the tax recompute, exactly
like the owned-package path — so the bill total and the internal redemption
payments reconcile (customer pays the package price; the services are covered).
"""

from app.services.billing_service import BillingService
from app.schemas.billing import BillItemCreate
from app.models.billing import BillItemType, Payment, PaymentMethod
from app.schemas.package import PackageDefinitionCreate
from app.models.package import Shareability, PackageSale
from app.services.package_catalog_service import create_definition, publish


def _make_service(db_session, suffix, price):
    from app.models.service import Service, ServiceCategory
    cat = ServiceCategory(name=f"Cat{suffix}", display_order=1, is_active=True)
    db_session.add(cat); db_session.flush()
    svc = Service(category_id=cat.id, name=f"Svc{suffix}", base_price=price,
                  duration_minutes=30, is_active=True, display_order=1)
    db_session.add(svc); db_session.flush()
    return svc


def _basic_pkg(db_session, user, suffix, svc):
    pkg = create_definition(db_session, PackageDefinitionCreate(
        name=f"Care{suffix}", validity_days=1, shareability=Shareability.OWNER_ONLY,
        blocks=[{"id": "b1", "kind": "items", "bonus": False,
                 "rows": [{"service_id": svc.id, "quantity": "1",
                           "unit_price_paise": 3000}]}],
        final_price_paise=2500,
    ), user.id)
    publish(db_session, pkg.id)
    return pkg


def test_buy_and_use_redeems_at_draft_and_money_reconciles(
    db_session, customer_factory, test_user
):
    eyebrow = _make_service(db_session, "EB", 3000)
    pkg = _basic_pkg(db_session, test_user, "EB", eyebrow)
    customer = customer_factory()

    bill = BillingService(db_session).create_bill(
        items=[
            BillItemCreate(package_definition_id=pkg.id).model_dump(),
            BillItemCreate(service_id=eyebrow.id, quantity=1,
                           redeem_from_definition_id=pkg.id).model_dump(),
        ],
        created_by_id=test_user.id,
        customer_id=customer.id,
    )

    # Redeemed at DRAFT — the service is covered, not charged.
    eb_line = next(i for i in bill.items if i.service_id == eyebrow.id)
    assert eb_line.item_type == BillItemType.PACKAGE_REDEMPTION
    assert eb_line.package_sale_id is not None

    # The package's sale exists and is linked (created at draft).
    sale = db_session.query(PackageSale).filter(
        PackageSale.package_definition_id == pkg.id).one()
    assert eb_line.package_sale_id == sale.id

    # An internal redemption payment covers the service (= its snapshot price).
    internal = (db_session.query(Payment)
                .filter(Payment.bill_id == bill.id,
                        Payment.payment_method == PaymentMethod.PACKAGE_REDEMPTION)
                .all())
    internal_total = sum(p.amount for p in internal)
    assert internal_total == 3000

    # MONEY CONSERVATION: cash the customer owes = total minus what the package
    # covered = the package price only (2500). No double-charge.
    cash_due = bill.rounded_total - internal_total
    assert cash_due == 2500


def test_redeem_from_definition_not_in_cart_stays_charged(
    db_session, customer_factory, test_user
):
    """A flagged line with no matching package sold in this cart is charged."""
    eyebrow = _make_service(db_session, "EB2", 3000)
    pkg = _basic_pkg(db_session, test_user, "EB2", eyebrow)
    customer = customer_factory()

    bill = BillingService(db_session).create_bill(
        items=[BillItemCreate(service_id=eyebrow.id, quantity=1,
                              redeem_from_definition_id=pkg.id).model_dump()],
        created_by_id=test_user.id,
        customer_id=customer.id,
    )
    line = next(i for i in bill.items if i.service_id == eyebrow.id)
    assert line.item_type == BillItemType.SERVICE
    # No sale was created for an un-sold package.
    assert db_session.query(PackageSale).filter(
        PackageSale.package_definition_id == pkg.id).first() is None


def test_voiding_buy_and_use_draft_drops_the_sale_and_redemption(
    db_session, customer_factory, test_user
):
    """Voiding a draft buy-and-use bill must not mint an unpaid package."""
    eyebrow = _make_service(db_session, "EB3", 3000)
    pkg = _basic_pkg(db_session, test_user, "EB3", eyebrow)
    customer = customer_factory()

    svc = BillingService(db_session)
    bill = svc.create_bill(
        items=[
            BillItemCreate(package_definition_id=pkg.id).model_dump(),
            BillItemCreate(service_id=eyebrow.id, quantity=1,
                           redeem_from_definition_id=pkg.id).model_dump(),
        ],
        created_by_id=test_user.id,
        customer_id=customer.id,
    )
    assert db_session.query(PackageSale).filter(
        PackageSale.package_definition_id == pkg.id).count() == 1

    svc.void_bill(bill.id, voided_by_id=test_user.id, reason="customer left")
    db_session.flush()

    # The in-cart sale is gone — no unpaid package owned.
    assert db_session.query(PackageSale).filter(
        PackageSale.package_definition_id == pkg.id).count() == 0
    # No internal redemption payments remain.
    assert db_session.query(Payment).filter(
        Payment.bill_id == bill.id,
        Payment.payment_method == PaymentMethod.PACKAGE_REDEMPTION).count() == 0
