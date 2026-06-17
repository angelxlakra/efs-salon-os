"""Buy a v2 package and redeem its services in the same bill at posting."""

from app.services.billing_service import BillingService
from app.schemas.billing import BillItemCreate
from app.models.billing import BillItemType, Payment, PaymentMethod
from app.schemas.package import PackageDefinitionCreate
from app.models.package import Shareability
from app.services.package_catalog_service import create_definition, publish


def _make_service(db_session, suffix, price):
    from app.models.service import Service, ServiceCategory
    cat = ServiceCategory(name=f"Cat{suffix}", display_order=1, is_active=True)
    db_session.add(cat); db_session.flush()
    svc = Service(category_id=cat.id, name=f"Svc{suffix}", base_price=price,
                  duration_minutes=30, is_active=True, display_order=1)
    db_session.add(svc); db_session.flush()
    return svc


def test_buy_package_and_redeem_its_service_same_bill(
    db_session, customer_factory, test_user
):
    eyebrow = _make_service(db_session, "EB", 3000)
    pkg = create_definition(db_session, PackageDefinitionCreate(
        name="Basic Care", validity_days=1, shareability=Shareability.OWNER_ONLY,
        blocks=[{"id": "b1", "kind": "items", "bonus": False,
                 "rows": [{"service_id": eyebrow.id, "quantity": "1",
                           "unit_price_paise": 3000}]}],
        final_price_paise=2500,
    ), test_user.id)
    publish(db_session, pkg.id)
    customer = customer_factory()

    svc = BillingService(db_session)
    items = [
        BillItemCreate(package_definition_id=pkg.id).model_dump(),
        BillItemCreate(service_id=eyebrow.id, quantity=1,
                       redeem_from_definition_id=pkg.id).model_dump(),
    ]
    bill = svc.create_bill(items=items, created_by_id=test_user.id,
                           customer_id=customer.id)

    eb_line = next(i for i in bill.items if i.service_id == eyebrow.id)
    assert eb_line.item_type == BillItemType.SERVICE  # draft: still charged

    svc._create_package_sales_for_bill(bill, test_user.id)
    db_session.flush()

    db_session.refresh(eb_line)
    assert eb_line.item_type == BillItemType.PACKAGE_REDEMPTION
    assert eb_line.package_sale_id is not None
    pay = (db_session.query(Payment)
           .filter(Payment.bill_id == bill.id,
                   Payment.payment_method == PaymentMethod.PACKAGE_REDEMPTION)
           .first())
    assert pay is not None


def test_redeem_from_definition_not_in_bill_is_ignored_safely(
    db_session, customer_factory, test_user
):
    eyebrow = _make_service(db_session, "EB2", 3000)
    pkg = create_definition(db_session, PackageDefinitionCreate(
        name="Care2", validity_days=1, shareability=Shareability.OWNER_ONLY,
        blocks=[{"id": "b1", "kind": "items", "bonus": False,
                 "rows": [{"service_id": eyebrow.id, "quantity": "1",
                           "unit_price_paise": 3000}]}],
        final_price_paise=2500,
    ), test_user.id)
    publish(db_session, pkg.id)
    customer = customer_factory()
    svc = BillingService(db_session)
    bill = svc.create_bill(
        items=[BillItemCreate(service_id=eyebrow.id, quantity=1,
                              redeem_from_definition_id=pkg.id).model_dump()],
        created_by_id=test_user.id, customer_id=customer.id,
    )
    svc._create_package_sales_for_bill(bill, test_user.id)
    db_session.flush()
    line = next(i for i in bill.items if i.service_id == eyebrow.id)
    assert line.item_type == BillItemType.SERVICE  # no matching sale -> still charged
