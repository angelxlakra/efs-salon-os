"""Schema tests for GST split-billing columns (Phase 2a).

New columns:
  Bill.bill_class       service | product | mixed_legacy (GST rate-class of the bill)
  Bill.bill_group_id    shared ULID linking the service+product halves of one checkout
  BillItem.tax_rate / tax_mode / taxable_value / cgst_amount / sgst_amount
  Payment.payment_group_id  links the per-bill splits of one customer tender
"""

import pytest

from app.models.billing import (
    Bill,
    BillClass,
    BillItem,
    BillItemType,
    Payment,
    PaymentMethod,
    TaxMode,
)


@pytest.fixture
def owner_user(test_user):
    return test_user


def _bill(owner_user, **kw):
    defaults = dict(
        subtotal=50000,
        tax_amount=0,
        cgst_amount=0,
        sgst_amount=0,
        total_amount=50000,
        rounded_total=50000,
        created_by=owner_user.id,
    )
    defaults.update(kw)
    return Bill(**defaults)


class TestBillGstColumns:
    def test_defaults_legacy(self, db_session, owner_user):
        b = _bill(owner_user)
        db_session.add(b)
        db_session.flush()
        db_session.refresh(b)

        assert b.bill_class == BillClass.MIXED_LEGACY
        assert b.bill_group_id is None

    def test_service_and_product_classes(self, db_session, owner_user):
        group = "01HGROUPULID0000000000TEST"
        svc = _bill(owner_user, bill_class=BillClass.SERVICE, bill_group_id=group)
        prd = _bill(owner_user, bill_class=BillClass.PRODUCT, bill_group_id=group)
        db_session.add_all([svc, prd])
        db_session.flush()

        siblings = (
            db_session.query(Bill).filter(Bill.bill_group_id == group).all()
        )
        assert {b.bill_class for b in siblings} == {
            BillClass.SERVICE,
            BillClass.PRODUCT,
        }


class TestBillItemTaxColumns:
    def test_defaults_zero_tax(self, db_session, owner_user):
        b = _bill(owner_user)
        db_session.add(b)
        db_session.flush()
        item = BillItem(
            bill_id=b.id,
            item_name="Haircut",
            base_price=50000,
            quantity=1,
            line_total=50000,
            item_type=BillItemType.PACKAGE_REDEMPTION,
        )
        db_session.add(item)
        db_session.flush()
        db_session.refresh(item)

        assert item.tax_rate == 0
        assert item.tax_mode == TaxMode.NONE
        assert item.taxable_value == 0
        assert item.cgst_amount == 0
        assert item.sgst_amount == 0

    def test_exclusive_service_line(self, db_session, owner_user):
        b = _bill(owner_user, bill_class=BillClass.SERVICE)
        db_session.add(b)
        db_session.flush()
        item = BillItem(
            bill_id=b.id,
            item_name="Haircut",
            base_price=50000,
            quantity=1,
            line_total=50000,
            item_type=BillItemType.PACKAGE_REDEMPTION,
            tax_rate=5,
            tax_mode=TaxMode.EXCLUSIVE,
            taxable_value=50000,
            cgst_amount=1250,
            sgst_amount=1250,
        )
        db_session.add(item)
        db_session.flush()
        db_session.refresh(item)

        assert item.tax_mode == TaxMode.EXCLUSIVE
        assert item.cgst_amount == item.sgst_amount == 1250


class TestPaymentGroupColumn:
    def test_payment_group_links_split_tender(self, db_session, owner_user):
        from datetime import datetime, timezone

        group = "01HPAYGROUP00000000000TEST"
        b1 = _bill(owner_user, bill_class=BillClass.SERVICE)
        b2 = _bill(owner_user, bill_class=BillClass.PRODUCT)
        db_session.add_all([b1, b2])
        db_session.flush()

        now = datetime.now(timezone.utc)
        p1 = Payment(
            bill_id=b1.id, payment_method=PaymentMethod.UPI, amount=52500,
            confirmed_at=now, confirmed_by=owner_user.id, payment_group_id=group,
        )
        p2 = Payment(
            bill_id=b2.id, payment_method=PaymentMethod.UPI, amount=118000,
            confirmed_at=now, confirmed_by=owner_user.id, payment_group_id=group,
        )
        db_session.add_all([p1, p2])
        db_session.flush()

        linked = (
            db_session.query(Payment)
            .filter(Payment.payment_group_id == group)
            .all()
        )
        assert len(linked) == 2
        assert sum(p.amount for p in linked) == 170500

    def test_payment_group_default_null(self, db_session, owner_user):
        from datetime import datetime, timezone

        b = _bill(owner_user)
        db_session.add(b)
        db_session.flush()
        p = Payment(
            bill_id=b.id, payment_method=PaymentMethod.CASH, amount=50000,
            confirmed_at=datetime.now(timezone.utc), confirmed_by=owner_user.id,
        )
        db_session.add(p)
        db_session.flush()
        db_session.refresh(p)
        assert p.payment_group_id is None
