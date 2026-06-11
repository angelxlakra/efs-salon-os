"""Tests for per-rate GST breakdown in the tax report (Phase 7).

GSTR filing needs taxable value + CGST + SGST per rate slab (5% services,
18% products). The breakdown is computed from per-line tax columns of POSTED
GST-classed bills; legacy (mixed_legacy, zero-tax) and refunded bills are
excluded.
"""

from datetime import date, timedelta

import pytest

from app.models.billing import PaymentMethod
from app.services.accounting_service import AccountingService
from app.services.billing_service import BillingService
from app.utils import generate_ulid

from tests.unit.test_billing_service_gst import (  # reuse fixtures
    gst_on, gst_service, gst_user, sellable_sku,  # noqa: F401
)


@pytest.fixture
def posted_group(db_session, gst_on, gst_service, sellable_sku, gst_user):  # noqa: F811
    svc = BillingService(db_session)
    bills = svc.create_bill_group(
        items=[
            {"service_id": gst_service.id, "quantity": 1},
            {"sku_id": sellable_sku.id, "quantity": 1},
        ],
        created_by_id=gst_user.id,
        customer_name="GST Customer",
    )
    svc.pay_bill_group(
        bill_group_id=bills[0].bill_group_id,
        payments=[{"payment_method": PaymentMethod.CASH,
                   "amount": sum(b.rounded_total for b in bills) // 100}],
        confirmed_by_id=gst_user.id,
    )
    return bills


def test_tax_report_has_rate_breakdown(db_session, posted_group, gst_user):
    service = AccountingService(db_session)
    report = service.generate_tax_report(
        start_date=date.today() - timedelta(days=1),
        end_date=date.today() + timedelta(days=1),
        generated_by=gst_user.id,
    )

    breakdown = {row["tax_rate"]: row for row in report["rate_breakdown"]}
    assert 5 in breakdown
    assert 18 in breakdown

    # service: ₹500 base at 5% (this test's bill at minimum; other committed
    # test bills may add to the sums, so check internal consistency + floor)
    five = breakdown[5]
    assert five["taxable_value"] >= 50000
    assert five["cgst_amount"] == five["sgst_amount"]
    assert five["cgst_amount"] >= 1250

    eighteen = breakdown[18]
    assert eighteen["taxable_value"] >= 100000
    assert eighteen["cgst_amount"] == eighteen["sgst_amount"]
    assert eighteen["cgst_amount"] >= 9000


def test_rate_breakdown_excludes_refunded(db_session, posted_group, gst_user):
    svc = BillingService(db_session)
    service = AccountingService(db_session)

    before = service.generate_tax_report(
        start_date=date.today() - timedelta(days=1),
        end_date=date.today() + timedelta(days=1),
        generated_by=gst_user.id,
    )
    five_before = next(
        r for r in before["rate_breakdown"] if r["tax_rate"] == 5
    )

    service_bill = next(b for b in posted_group if not any(i.sku_id for i in b.items))
    svc.refund_bill(
        bill_id=service_bill.id, reason="test", refunded_by_id=gst_user.id
    )

    after = service.generate_tax_report(
        start_date=date.today() - timedelta(days=1),
        end_date=date.today() + timedelta(days=1),
        generated_by=gst_user.id,
    )
    five_after = next(
        (r for r in after["rate_breakdown"] if r["tax_rate"] == 5), None
    )
    removed = five_before["taxable_value"] - (
        five_after["taxable_value"] if five_after else 0
    )
    assert removed == service_bill.subtotal - service_bill.discount_amount
