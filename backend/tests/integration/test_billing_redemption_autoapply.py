"""Integration tests for add_bill_item with auto-apply package redemption."""
import pytest
from app.services.billing_service import BillingService
from app.models.billing import Bill, BillStatus, BillType, BillItemType, PaymentMethod
from app.models.package import PackageSaleStatus


@pytest.fixture
def monkeypatched_billing(db_session, monkeypatch):
    monkeypatch.setattr(db_session, "commit", db_session.flush)
    return BillingService(db_session)


def make_draft_bill(db_session, test_user, customer):
    """Helper: create a minimal DRAFT bill."""
    bill = Bill(
        customer_id=customer.id,
        subtotal=0, discount_amount=0, tax_amount=0,
        cgst_amount=0, sgst_amount=0,
        total_amount=0, rounded_total=0, rounding_adjustment=0,
        status=BillStatus.DRAFT, bill_type=BillType.NORMAL,
        created_by=test_user.id,
    )
    db_session.add(bill)
    db_session.flush()
    return bill


def test_add_item_no_eligible_package(
    db_session, monkeypatched_billing, test_user, test_customer, service_factory
):
    """Adding a service with no eligible packages returns empty eligible_packages."""
    svc = service_factory()
    bill = make_draft_bill(db_session, test_user, test_customer)

    result = monkeypatched_billing.add_bill_item(
        bill_id=bill.id,
        service_id=svc.id,
        quantity=1,
        user_id=test_user.id,
    )

    assert result["bill_item"].item_type == BillItemType.SERVICE
    assert result["auto_applied_package_sale_id"] is None
    assert result["eligible_packages"] == []

    # Bill totals updated
    db_session.refresh(bill)
    assert bill.subtotal == svc.base_price


def test_add_item_single_eligible_auto_applies(
    db_session, monkeypatched_billing, test_user, test_customer,
    package_sale_factory, service_factory,
):
    """Single eligible package with auto_apply=True is applied automatically."""
    svc = service_factory()
    sale = package_sale_factory(customer=test_customer, services=[svc])
    bill = make_draft_bill(db_session, test_user, test_customer)

    result = monkeypatched_billing.add_bill_item(
        bill_id=bill.id,
        service_id=svc.id,
        quantity=1,
        user_id=test_user.id,
    )

    assert result["auto_applied_package_sale_id"] == sale.id
    assert result["eligible_packages"] == []
    # BillItem should now have PACKAGE_REDEMPTION item type
    bill_item = result["bill_item"]
    db_session.refresh(bill_item)
    assert bill_item.item_type == BillItemType.PACKAGE_REDEMPTION
    assert bill_item.package_sale_id == sale.id


def test_add_item_multiple_eligible_returns_list(
    db_session, monkeypatched_billing, test_user, test_customer,
    package_sale_factory, service_factory,
):
    """Two eligible packages -> no auto-apply, returns list of sale IDs."""
    svc = service_factory()
    sale1 = package_sale_factory(customer=test_customer, services=[svc])
    sale2 = package_sale_factory(customer=test_customer, services=[svc])
    bill = make_draft_bill(db_session, test_user, test_customer)

    result = monkeypatched_billing.add_bill_item(
        bill_id=bill.id,
        service_id=svc.id,
        quantity=1,
        user_id=test_user.id,
    )

    assert result["auto_applied_package_sale_id"] is None
    assert len(result["eligible_packages"]) == 2
    assert sale1.id in result["eligible_packages"]
    assert sale2.id in result["eligible_packages"]
    # BillItem stays as SERVICE (no auto-apply)
    db_session.refresh(result["bill_item"])
    assert result["bill_item"].item_type == BillItemType.SERVICE


def test_add_item_to_non_draft_bill_raises(
    db_session, monkeypatched_billing, test_user, test_customer, service_factory
):
    """Adding item to a non-DRAFT bill raises ValueError mentioning DRAFT."""
    svc = service_factory()
    bill = make_draft_bill(db_session, test_user, test_customer)
    bill.status = BillStatus.POSTED
    db_session.flush()

    with pytest.raises(ValueError, match="DRAFT"):
        monkeypatched_billing.add_bill_item(
            bill_id=bill.id, service_id=svc.id, user_id=test_user.id
        )
