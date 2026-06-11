"""Tests for GST-mode billing in BillingService (Phase 4 of GST split billing).

When the salon is GST-registered (settings.gst_registered=True and bill date
>= gst_effective_from):
  - service lines: 5% EXCLUSIVE tax added on top of the discounted base
  - product lines: 18% INCLUSIVE tax extracted from the discounted MRP
  - per-line tax columns populated, bill totals are sums of lines
  - payable floors to the whole rupee
  - single-class bills get bill_class SERVICE/PRODUCT and SRV/PRD invoices

When GST mode is off, the legacy inclusive-18% bill-level math is unchanged.
"""

from datetime import date, timedelta

import pytest

from app.models.billing import BillClass, BillStatus, PaymentMethod, TaxMode
from app.services.billing_service import BillingService
from app.services.invoice_generator import InvoiceNumberGenerator
from app.utils import generate_ulid


@pytest.fixture
def gst_on(db_session):
    """Enable GST mode effective yesterday.

    Writes the settings row directly (no SettingsService.update_settings):
    that method commits, which would break per-test rollback isolation.
    """
    from app.models.settings import SalonSettings

    s = db_session.query(SalonSettings).first()
    if not s:
        s = SalonSettings(salon_name="Test Salon", salon_address="Test Addr")
        db_session.add(s)
    s.gst_registered = True
    s.gstin = "29ABCDE1234F1Z5"
    s.gst_effective_from = date.today() - timedelta(days=1)
    db_session.flush()
    return s


# BillingService.create_bill commits mid-test, so shared conftest fixtures
# with fixed unique names (test_role/test_service_category) collide on the
# next test in this file. These local fixtures use ULID-unique names instead.


@pytest.fixture
def gst_user(db_session):
    from app.models.user import Role, RoleEnum, User

    uid = generate_ulid()
    # Role names are a fixed enum and unique — reuse if a commit leaked one
    role = db_session.query(Role).filter(Role.name == RoleEnum.OWNER).first()
    if not role:
        role = Role(name=RoleEnum.OWNER, description="t", permissions={"*": ["*"]})
        db_session.add(role)
        db_session.flush()
    user = User(
        role_id=role.id,
        username=f"gst_user_{uid}",
        password_hash="x",
        full_name="GST Test User",
        is_active=True,
    )
    db_session.add(user)
    db_session.flush()
    return user


@pytest.fixture
def gst_service(db_session):
    """Service: menu price ₹500 (50000 paise)."""
    from app.models.service import Service, ServiceCategory

    uid = generate_ulid()
    cat = ServiceCategory(name=f"GST Cat {uid}", display_order=1)
    db_session.add(cat)
    db_session.flush()
    svc = Service(
        category_id=cat.id,
        name=f"GST Haircut {uid}",
        base_price=50000,
        duration_minutes=30,
        is_active=True,
    )
    db_session.add(svc)
    db_session.flush()
    return svc


@pytest.fixture
def sellable_sku(db_session):
    """Retail product: MRP ₹1,180 (GST-inclusive), in stock."""
    from app.models.inventory import SKU, InventoryCategory

    uid = generate_ulid()
    cat = InventoryCategory(id=generate_ulid(), name=f"Retail GST {uid}")
    db_session.add(cat)
    db_session.flush()
    sku = SKU(
        id=generate_ulid(),
        sku_code=f"GST{uid[:10]}",
        name=f"Shampoo {uid}",
        uom="bottle",
        category_id=cat.id,
        is_active=True,
        is_sellable=True,
        retail_price=118000,
        current_stock=10,
    )
    db_session.add(sku)
    db_session.flush()
    return sku


class TestGstModeServiceBill:
    def test_service_bill_adds_5_percent_on_top(
        self, db_session, gst_on, gst_service, gst_user
    ):
        svc = BillingService(db_session)
        bill = svc.create_bill(
            items=[{"service_id": gst_service.id, "quantity": 1}],
            created_by_id=gst_user.id,
            customer_name="GST Customer",
        )

        # test_service.base_price = 50000 (₹500)
        assert bill.subtotal == 50000
        assert bill.cgst_amount == 1250  # 2.5%
        assert bill.sgst_amount == 1250
        assert bill.tax_amount == 2500
        assert bill.total_amount == 52500  # customer pays base + 5%
        assert bill.rounded_total == 52500
        assert bill.bill_class == BillClass.SERVICE

        item = bill.items[0]
        assert item.tax_rate == 5
        assert item.tax_mode == TaxMode.EXCLUSIVE
        assert item.taxable_value == 50000
        assert item.cgst_amount == item.sgst_amount == 1250

    def test_discount_reduces_base_before_tax(
        self, db_session, gst_on, gst_service, gst_user
    ):
        svc = BillingService(db_session)
        bill = svc.create_bill(
            items=[{"service_id": gst_service.id, "quantity": 1}],
            created_by_id=gst_user.id,
            customer_name="GST Customer",
            discount_amount=10000,
        )

        # base 50000 - 10000 = 40000 → 2.5% halves = 1000 each
        assert bill.cgst_amount == 1000
        assert bill.sgst_amount == 1000
        assert bill.total_amount == 42000
        assert bill.items[0].taxable_value == 40000

    def test_payable_floors_to_rupee(
        self, db_session, gst_on, gst_service, gst_user
    ):
        svc = BillingService(db_session)
        bill = svc.create_bill(
            items=[{"service_id": gst_service.id, "quantity": 1}],
            created_by_id=gst_user.id,
            customer_name="GST Customer",
            discount_amount=3,
        )

        # base 49997 → cgst = sgst = floor(49997*0.025) = 1249
        # total 49997 + 2498 = 52495 (₹524.95) → floors to ₹524
        assert bill.cgst_amount == 1249
        assert bill.total_amount == 52495
        assert bill.rounded_total == 52400
        assert bill.rounding_adjustment == -95

    def test_apply_discount_recomputes_gst(
        self, db_session, gst_on, gst_service, gst_user
    ):
        svc = BillingService(db_session)
        bill = svc.create_bill(
            items=[{"service_id": gst_service.id, "quantity": 1}],
            created_by_id=gst_user.id,
            customer_name="GST Customer",
        )
        bill = svc.apply_discount(
            bill_id=bill.id,
            discount_amount=10000,
            discount_reason="loyalty",
            applied_by_id=gst_user.id,
        )
        assert bill.cgst_amount == 1000
        assert bill.total_amount == 42000


class TestGstModeProductBill:
    def test_product_bill_extracts_18_percent_from_mrp(
        self, db_session, gst_on, sellable_sku, gst_user
    ):
        svc = BillingService(db_session)
        bill = svc.create_bill(
            items=[{"sku_id": sellable_sku.id, "quantity": 1}],
            created_by_id=gst_user.id,
            customer_name="GST Customer",
        )

        # MRP 118000 → taxable 100000 + 9000 + 9000; customer pays MRP
        assert bill.subtotal == 118000
        assert bill.cgst_amount == 9000
        assert bill.sgst_amount == 9000
        assert bill.total_amount == 118000
        assert bill.bill_class == BillClass.PRODUCT

        item = bill.items[0]
        assert item.tax_rate == 18
        assert item.tax_mode == TaxMode.INCLUSIVE
        assert item.taxable_value == 100000


class TestBillGroupSplit:
    """Phase 5: mixed cart → service bill + product bill, one payment."""

    def _mixed_group(self, db_session, gst_service, sellable_sku, gst_user, **kw):
        svc = BillingService(db_session)
        return svc, svc.create_bill_group(
            items=[
                {"service_id": gst_service.id, "quantity": 1},
                {"sku_id": sellable_sku.id, "quantity": 1},
            ],
            created_by_id=gst_user.id,
            customer_name="GST Customer",
            **kw,
        )

    def test_mixed_cart_splits_into_two_bills(
        self, db_session, gst_on, gst_service, sellable_sku, gst_user
    ):
        _, bills = self._mixed_group(db_session, gst_service, sellable_sku, gst_user)
        assert len(bills) == 2
        service_bill = next(b for b in bills if b.bill_class == BillClass.SERVICE)
        product_bill = next(b for b in bills if b.bill_class == BillClass.PRODUCT)

        assert service_bill.bill_group_id == product_bill.bill_group_id
        assert service_bill.bill_group_id is not None

        # service side: 50000 + 5% = 52500
        assert service_bill.subtotal == 50000
        assert service_bill.cgst_amount == service_bill.sgst_amount == 1250
        assert service_bill.total_amount == 52500
        # product side: MRP 118000, tax extracted
        assert product_bill.subtotal == 118000
        assert product_bill.cgst_amount == product_bill.sgst_amount == 9000
        assert product_bill.total_amount == 118000

        # lines landed on the right bills
        assert all(not i.sku_id for i in service_bill.items)
        assert all(i.sku_id for i in product_bill.items)

    def test_discount_applies_to_service_bill_only(
        self, db_session, gst_on, gst_service, sellable_sku, gst_user
    ):
        # Discount applies to services only — all of it lands on the service
        # bill; the product bill is never discounted (sold at MRP).
        _, bills = self._mixed_group(
            db_session, gst_service, sellable_sku, gst_user,
            discount_amount=10000,
        )
        service_bill = next(b for b in bills if b.bill_class == BillClass.SERVICE)
        product_bill = next(b for b in bills if b.bill_class == BillClass.PRODUCT)
        assert service_bill.discount_amount == 10000
        assert product_bill.discount_amount == 0
        # service: (50000 - 10000) + 5% = 42000; product: MRP 118000 untouched
        assert service_bill.total_amount == 42000
        assert product_bill.total_amount == 118000

    def test_discount_exceeding_services_subtotal_rejected(
        self, db_session, gst_on, gst_service, sellable_sku, gst_user
    ):
        # Service subtotal is 50000; a 60000 discount must be rejected even
        # though the combined subtotal (168000) is larger.
        svc = BillingService(db_session)
        with pytest.raises(ValueError, match="services subtotal"):
            svc.create_bill_group(
                items=[
                    {"service_id": gst_service.id, "quantity": 1},
                    {"sku_id": sellable_sku.id, "quantity": 1},
                ],
                created_by_id=gst_user.id,
                customer_name="GST Customer",
                discount_amount=60000,
            )

    def test_product_only_cart_rejects_discount(
        self, db_session, gst_on, sellable_sku, gst_user
    ):
        svc = BillingService(db_session)
        with pytest.raises(ValueError, match="services subtotal"):
            svc.create_bill(
                items=[{"sku_id": sellable_sku.id, "quantity": 1}],
                created_by_id=gst_user.id,
                customer_name="GST Customer",
                discount_amount=5000,
            )

    def test_single_side_cart_stays_one_bill(
        self, db_session, gst_on, gst_service, gst_user
    ):
        svc = BillingService(db_session)
        bills = svc.create_bill_group(
            items=[{"service_id": gst_service.id, "quantity": 1}],
            created_by_id=gst_user.id,
            customer_name="GST Customer",
        )
        assert len(bills) == 1
        assert bills[0].bill_class == BillClass.SERVICE

    def test_pay_bill_group_posts_both_with_split_payment(
        self, db_session, gst_on, gst_service, sellable_sku, gst_user
    ):
        svc, bills = self._mixed_group(db_session, gst_service, sellable_sku, gst_user)
        group_id = bills[0].bill_group_id
        group_total = sum(b.rounded_total for b in bills)  # 52500 + 118000

        payments = svc.pay_bill_group(
            bill_group_id=group_id,
            payments=[{"payment_method": PaymentMethod.UPI,
                       "amount": group_total // 100}],
            confirmed_by_id=gst_user.id,
        )

        for b in bills:
            db_session.refresh(b)
        service_bill = next(b for b in bills if b.bill_class == BillClass.SERVICE)
        product_bill = next(b for b in bills if b.bill_class == BillClass.PRODUCT)

        assert service_bill.status == BillStatus.POSTED
        assert product_bill.status == BillStatus.POSTED
        assert service_bill.invoice_number.startswith("SRV-")
        assert product_bill.invoice_number.startswith("PRD-")

        # one tender split into one payment per bill, linked by group id
        assert len(payments) == 2
        assert len({p.payment_group_id for p in payments}) == 1
        assert payments[0].payment_group_id is not None
        assert sum(p.amount for p in payments) == group_total
        by_bill = {p.bill_id: p.amount for p in payments}
        assert by_bill[service_bill.id] == service_bill.rounded_total
        assert by_bill[product_bill.id] == product_bill.rounded_total

    def test_pay_bill_group_rejects_underpayment(
        self, db_session, gst_on, gst_service, sellable_sku, gst_user
    ):
        svc, bills = self._mixed_group(db_session, gst_service, sellable_sku, gst_user)
        with pytest.raises(ValueError, match="full payment"):
            svc.pay_bill_group(
                bill_group_id=bills[0].bill_group_id,
                payments=[{"payment_method": PaymentMethod.CASH, "amount": 100}],
                confirmed_by_id=gst_user.id,
            )

    def test_pay_bill_group_reduces_product_stock(
        self, db_session, gst_on, gst_service, sellable_sku, gst_user
    ):
        svc, bills = self._mixed_group(db_session, gst_service, sellable_sku, gst_user)
        stock_before = sellable_sku.current_stock
        group_total = sum(b.rounded_total for b in bills)
        svc.pay_bill_group(
            bill_group_id=bills[0].bill_group_id,
            payments=[{"payment_method": PaymentMethod.CASH,
                       "amount": group_total // 100}],
            confirmed_by_id=gst_user.id,
        )
        db_session.refresh(sellable_sku)
        assert sellable_sku.current_stock == stock_before - 1


class TestLegacyBillsNotRetroTaxed:
    """Regression (review C1): editing a pre-registration legacy bill after
    GST is enabled must NOT re-tax it or reclassify its invoice series."""

    def test_apply_discount_on_legacy_bill_keeps_zero_tax(
        self, db_session, gst_service, gst_user
    ):
        from datetime import datetime, timedelta
        from app.models.billing import Bill, BillClass, BillStatus, BillItem, BillItemType
        from app.models.settings import SalonSettings
        from app.utils import IST

        # A legacy bill created before registration (tax already zeroed by the
        # backfill), classed mixed_legacy.
        created = datetime.now(IST) - timedelta(days=30)
        bill = Bill(
            id=generate_ulid(), customer_name="Old Cust",
            subtotal=50000, discount_amount=0, tax_amount=0,
            cgst_amount=0, sgst_amount=0, total_amount=50000,
            rounded_total=50000, rounding_adjustment=0,
            status=BillStatus.DRAFT, bill_class=BillClass.MIXED_LEGACY,
            created_by=gst_user.id, created_at=created,
        )
        db_session.add(bill)
        db_session.flush()
        db_session.add(BillItem(
            id=generate_ulid(), bill_id=bill.id, service_id=gst_service.id,
            item_name="Haircut", base_price=50000, quantity=1, line_total=50000,
            item_type=BillItemType.SERVICE,
        ))
        db_session.flush()

        # Now GST is registered, effective today.
        s = db_session.query(SalonSettings).first() or SalonSettings(
            salon_name="T", salon_address="A")
        if not s.id:
            db_session.add(s)
        s.gst_registered = True
        s.gstin = "29ABCDE1234F1Z5"
        s.gst_effective_from = datetime.now(IST).date()
        db_session.flush()

        svc = BillingService(db_session)
        bill = svc.apply_discount(
            bill_id=bill.id, discount_amount=5000,
            discount_reason="x", applied_by_id=gst_user.id,
        )

        # Legacy math: 18% extracted from the inclusive 45000 — NOT 0, NOT 5%
        # exclusive. Crucially the bill stays mixed_legacy (no SRV reclass).
        assert bill.bill_class == BillClass.MIXED_LEGACY
        assert bill.total_amount == 45000  # inclusive, tax not added on top
        expected_tax = round((45000 * 18) / 118)
        assert abs(bill.tax_amount - expected_tax) <= 1


class TestSplitBillRefunds:
    """Phase 6: each half of a split checkout is refundable independently,
    with the credit note drawn from that bill's own invoice series."""

    def _paid_group(self, db_session, gst_service, sellable_sku, gst_user):
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
        for b in bills:
            db_session.refresh(b)
        return svc, bills

    def test_refund_product_half_only(
        self, db_session, gst_on, gst_service, sellable_sku, gst_user
    ):
        svc, bills = self._paid_group(db_session, gst_service, sellable_sku, gst_user)
        service_bill = next(b for b in bills if b.bill_class == BillClass.SERVICE)
        product_bill = next(b for b in bills if b.bill_class == BillClass.PRODUCT)

        credit = svc.refund_bill(
            bill_id=product_bill.id, reason="returned item",
            refunded_by_id=gst_user.id,
        )

        assert credit.invoice_number.startswith("PRD-")
        assert credit.bill_class == BillClass.PRODUCT
        assert credit.bill_group_id == product_bill.bill_group_id
        assert credit.total_amount == -product_bill.total_amount
        assert credit.cgst_amount == -product_bill.cgst_amount

        db_session.refresh(service_bill)
        db_session.refresh(product_bill)
        assert product_bill.status == BillStatus.REFUNDED
        assert service_bill.status == BillStatus.POSTED  # untouched

    def test_refund_service_half_uses_srv_series(
        self, db_session, gst_on, gst_service, sellable_sku, gst_user
    ):
        svc, bills = self._paid_group(db_session, gst_service, sellable_sku, gst_user)
        service_bill = next(b for b in bills if b.bill_class == BillClass.SERVICE)
        credit = svc.refund_bill(
            bill_id=service_bill.id, reason="complaint",
            refunded_by_id=gst_user.id,
        )
        assert credit.invoice_number.startswith("SRV-")
        assert credit.sgst_amount == -service_bill.sgst_amount


@pytest.fixture
def gst_off(db_session):
    """Force GST mode off (a prior test's commit may have left it on)."""
    from app.models.settings import SalonSettings

    s = db_session.query(SalonSettings).first()
    if s:
        s.gst_registered = False
        s.gst_effective_from = None
        db_session.flush()
    return s


class TestLegacyModeUnchanged:
    def test_legacy_extraction_when_gst_off(
        self, db_session, gst_off, gst_service, gst_user
    ):
        svc = BillingService(db_session)
        bill = svc.create_bill(
            items=[{"service_id": gst_service.id, "quantity": 1}],
            created_by_id=gst_user.id,
            customer_name="Legacy Customer",
        )

        # Old behavior: 18% extracted from inclusive 50000, total unchanged
        expected_tax = round((50000 * 18) / 118)
        assert abs(bill.tax_amount - expected_tax) <= 1
        assert bill.total_amount == 50000
        assert bill.bill_class == BillClass.MIXED_LEGACY
        assert bill.items[0].tax_mode == TaxMode.NONE


class TestInvoiceSeries:
    def test_generator_accepts_prefix(self, db_session):
        # dedicated prefix: other tests in this file commit SRV invoices
        n = InvoiceNumberGenerator.generate(db_session, prefix="TSX", lock_id=987226)
        assert n.startswith("TSX-")
        assert n.endswith("-0001")

    def test_series_are_independent(self, db_session):
        a1 = InvoiceNumberGenerator.generate(db_session, prefix="TSA", lock_id=987224)
        assert a1.endswith("-0001")
        b1 = InvoiceNumberGenerator.generate(db_session, prefix="TSB", lock_id=987225)
        assert b1.endswith("-0001")

    def test_default_stays_sal(self, db_session):
        n = InvoiceNumberGenerator.generate(db_session)
        assert n.startswith("SAL-")

    def test_gst_service_bill_gets_srv_invoice(
        self, db_session, gst_on, gst_service, gst_user
    ):
        svc = BillingService(db_session)
        bill = svc.create_bill(
            items=[{"service_id": gst_service.id, "quantity": 1}],
            created_by_id=gst_user.id,
            customer_name="GST Customer",
        )
        svc.add_payment(
            bill_id=bill.id,
            payment_method=PaymentMethod.CASH,
            amount=bill.rounded_total // 100,  # add_payment takes rupees
            confirmed_by_id=gst_user.id,
        )
        db_session.refresh(bill)
        assert bill.status == BillStatus.POSTED
        assert bill.invoice_number.startswith("SRV-")

    def test_gst_product_bill_gets_prd_invoice(
        self, db_session, gst_on, sellable_sku, gst_user
    ):
        svc = BillingService(db_session)
        bill = svc.create_bill(
            items=[{"sku_id": sellable_sku.id, "quantity": 1}],
            created_by_id=gst_user.id,
            customer_name="GST Customer",
        )
        svc.add_payment(
            bill_id=bill.id,
            payment_method=PaymentMethod.CASH,
            amount=bill.rounded_total // 100,  # add_payment takes rupees
            confirmed_by_id=gst_user.id,
        )
        db_session.refresh(bill)
        assert bill.invoice_number.startswith("PRD-")
