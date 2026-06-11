"""Receipt generation for GST tax invoices (Phase 10).

Verifies the Rule 46 layout renders for service bills (5% exclusive),
product bills (18% MRP-inclusive), and credit notes — and that legacy
mixed_legacy bills are untouched. We assert the PDF builds without error and
contains the expected declarations by extracting its text.
"""

from io import BytesIO

import pytest
from pypdf import PdfReader

from app.models.billing import (
    Bill, BillClass, BillItem, BillItemType, BillStatus, BillType, TaxMode,
)
from app.models.settings import SalonSettings
from app.services.receipt_service import ReceiptService
from app.utils import generate_ulid


@pytest.fixture
def sellable_sku(db_session):
    from app.models.inventory import SKU, InventoryCategory

    uid = generate_ulid()
    cat = InventoryCategory(id=generate_ulid(), name=f"Retail {uid}")
    db_session.add(cat)
    db_session.flush()
    sku = SKU(
        id=generate_ulid(), sku_code=f"RCPT{uid[:8]}", name="Shampoo",
        uom="bottle", category_id=cat.id, is_active=True, is_sellable=True,
        retail_price=118000, current_stock=10,
    )
    db_session.add(sku)
    db_session.flush()
    return sku


@pytest.fixture
def gst_settings(db_session):
    s = db_session.query(SalonSettings).first()
    if not s:
        s = SalonSettings(salon_name="Test Salon", salon_address="1 Test Rd")
        db_session.add(s)
    s.gstin = "29ABCDE1234F1Z5"
    s.gst_registered = True
    s.receipt_show_gstin = True
    db_session.flush()
    return s


def _pdf_text(bill, db_session) -> str:
    result = ReceiptService.generate_receipt_pdf(bill, db=db_session)
    assert isinstance(result, BytesIO)
    data = result.getvalue()
    assert len(data) > 0
    reader = PdfReader(BytesIO(data))
    return "".join(page.extract_text() for page in reader.pages)


def test_service_bill_is_tax_invoice(db_session, gst_settings, test_user, service_factory):
    svc = service_factory()
    bill = Bill(
        customer_name="GST Cust", subtotal=50000, discount_amount=0,
        tax_amount=2500, cgst_amount=1250, sgst_amount=1250,
        total_amount=52500, rounded_total=52500, rounding_adjustment=0,
        status=BillStatus.POSTED, bill_type=BillType.NORMAL,
        bill_class=BillClass.SERVICE, created_by=test_user.id,
        invoice_number="SRV-26-0001",
    )
    db_session.add(bill)
    db_session.flush()
    db_session.add(BillItem(
        bill_id=bill.id, service_id=svc.id, item_name="Haircut",
        base_price=50000, quantity=1,
        line_total=50000, item_type=BillItemType.SERVICE,
        tax_rate=5, tax_mode=TaxMode.EXCLUSIVE, taxable_value=50000,
        cgst_amount=1250, sgst_amount=1250,
    ))
    db_session.flush()
    db_session.refresh(bill)

    text = _pdf_text(bill, db_session)
    assert "TAX INVOICE" in text
    assert "GSTIN" in text and "29ABCDE1234F1Z5" in text
    assert "CGST @ 2.5%" in text
    assert "SGST @ 2.5%" in text
    assert "Taxable Value" in text
    assert "reverse charge" in text
    assert "Authorised Signatory" in text


def test_product_bill_marks_inclusive(db_session, gst_settings, test_user, sellable_sku):
    bill = Bill(
        customer_name="GST Cust", subtotal=118000, discount_amount=0,
        tax_amount=18000, cgst_amount=9000, sgst_amount=9000,
        total_amount=118000, rounded_total=118000, rounding_adjustment=0,
        status=BillStatus.POSTED, bill_type=BillType.NORMAL,
        bill_class=BillClass.PRODUCT, created_by=test_user.id,
        invoice_number="PRD-26-0001",
    )
    db_session.add(bill)
    db_session.flush()
    db_session.add(BillItem(
        bill_id=bill.id, sku_id=sellable_sku.id, item_name="Shampoo",
        base_price=118000, quantity=1,
        line_total=118000, item_type=BillItemType.PRODUCT,
        tax_rate=18, tax_mode=TaxMode.INCLUSIVE, taxable_value=100000,
        cgst_amount=9000, sgst_amount=9000,
    ))
    db_session.flush()
    db_session.refresh(bill)

    text = _pdf_text(bill, db_session)
    assert "TAX INVOICE" in text
    assert "CGST @ 9%" in text
    assert "incl" in text  # marked included-in-MRP


def test_credit_note_label(db_session, gst_settings, test_user):
    original = Bill(
        customer_name="GST Cust", subtotal=50000, discount_amount=0,
        tax_amount=2500, cgst_amount=1250, sgst_amount=1250,
        total_amount=52500, rounded_total=52500, rounding_adjustment=0,
        status=BillStatus.REFUNDED, bill_type=BillType.NORMAL,
        bill_class=BillClass.SERVICE, created_by=test_user.id,
        invoice_number="SRV-26-0002",
    )
    db_session.add(original)
    db_session.flush()
    credit = Bill(
        customer_name="GST Cust", subtotal=-50000, discount_amount=0,
        tax_amount=-2500, cgst_amount=-1250, sgst_amount=-1250,
        total_amount=-52500, rounded_total=-52500, rounding_adjustment=0,
        status=BillStatus.POSTED, bill_type=BillType.CREDIT_NOTE,
        bill_class=BillClass.SERVICE, created_by=test_user.id,
        original_bill_id=original.id, invoice_number="SRV-26-0003",
    )
    db_session.add(credit)
    db_session.flush()
    db_session.refresh(credit)

    text = _pdf_text(credit, db_session)
    assert "CREDIT NOTE" in text
    assert "SRV-26-0002" in text  # references the original invoice


def test_draft_bill_prints_without_payment(db_session, gst_settings, test_user, service_factory):
    """Print-before-payment: a DRAFT bill renders with items + tax but NO
    payment details, and is not yet a numbered TAX INVOICE."""
    svc = service_factory()
    bill = Bill(
        customer_name="GST Cust", subtotal=50000, discount_amount=0,
        tax_amount=2500, cgst_amount=1250, sgst_amount=1250,
        total_amount=52500, rounded_total=52500, rounding_adjustment=0,
        status=BillStatus.DRAFT, bill_type=BillType.NORMAL,
        bill_class=BillClass.SERVICE, created_by=test_user.id,
        invoice_number=None,
    )
    db_session.add(bill)
    db_session.flush()
    db_session.add(BillItem(
        bill_id=bill.id, service_id=svc.id, item_name="Haircut",
        base_price=50000, quantity=1, line_total=50000,
        item_type=BillItemType.SERVICE, tax_rate=5, tax_mode=TaxMode.EXCLUSIVE,
        taxable_value=50000, cgst_amount=1250, sgst_amount=1250,
    ))
    db_session.flush()
    db_session.refresh(bill)

    text = _pdf_text(bill, db_session)
    # Bill content is present (items + tax)
    assert "Haircut" in text
    assert "CGST @ 2.5%" in text
    assert "TOTAL" in text
    # Professional, customer-facing: titled TAX INVOICE with no internal
    # "draft" wording and no placeholder invoice number...
    assert "TAX INVOICE" in text
    assert "DRAFT" not in text
    assert "Invoice No" not in text  # no number until the sale is posted
    # ...and no payment details until paid
    assert "Payment Method" not in text
    assert "PENDING" not in text


def test_group_receipt_is_two_pages(db_session, gst_settings, test_user, service_factory, sellable_sku):
    """A split checkout renders one PDF with two pages: service then product."""
    from app.services.receipt_service import ReceiptService

    group = "01HGRPRCPT0000000000000001"
    svc = service_factory()
    service_bill = Bill(
        customer_name="GST Cust", subtotal=50000, discount_amount=0,
        tax_amount=2500, cgst_amount=1250, sgst_amount=1250,
        total_amount=52500, rounded_total=52500, rounding_adjustment=0,
        status=BillStatus.POSTED, bill_type=BillType.NORMAL,
        bill_class=BillClass.SERVICE, created_by=test_user.id,
        invoice_number="SRV-26-0010", bill_group_id=group,
    )
    product_bill = Bill(
        customer_name="GST Cust", subtotal=88000, discount_amount=0,
        tax_amount=13422, cgst_amount=6711, sgst_amount=6711,
        total_amount=88000, rounded_total=88000, rounding_adjustment=0,
        status=BillStatus.POSTED, bill_type=BillType.NORMAL,
        bill_class=BillClass.PRODUCT, created_by=test_user.id,
        invoice_number="PRD-26-0010", bill_group_id=group,
    )
    db_session.add_all([service_bill, product_bill])
    db_session.flush()
    db_session.add(BillItem(
        bill_id=service_bill.id, service_id=svc.id, item_name="Haircut",
        base_price=50000, quantity=1, line_total=50000,
        item_type=BillItemType.SERVICE, tax_rate=5, tax_mode=TaxMode.EXCLUSIVE,
        taxable_value=50000, cgst_amount=1250, sgst_amount=1250,
    ))
    db_session.add(BillItem(
        bill_id=product_bill.id, sku_id=sellable_sku.id, item_name="Shampoo",
        base_price=88000, quantity=1, line_total=88000,
        item_type=BillItemType.PRODUCT, tax_rate=18, tax_mode=TaxMode.INCLUSIVE,
        taxable_value=74578, cgst_amount=6711, sgst_amount=6711,
    ))
    db_session.flush()
    db_session.refresh(service_bill)
    db_session.refresh(product_bill)

    from io import BytesIO
    from pypdf import PdfReader

    out = ReceiptService.generate_group_receipt_pdf([service_bill, product_bill], db_session)
    reader = PdfReader(BytesIO(out.getvalue()))
    assert len(reader.pages) == 2
    page1 = reader.pages[0].extract_text()
    page2 = reader.pages[1].extract_text()
    assert "SRV-26-0010" in page1 and "Haircut" in page1
    assert "PRD-26-0010" in page2 and "Shampoo" in page2


def test_legacy_bill_unchanged(db_session, gst_settings, test_user):
    bill = Bill(
        customer_name="Old Cust", subtotal=50000, discount_amount=0,
        tax_amount=7627, cgst_amount=3814, sgst_amount=3813,
        total_amount=50000, rounded_total=50000, rounding_adjustment=0,
        status=BillStatus.POSTED, bill_type=BillType.NORMAL,
        bill_class=BillClass.MIXED_LEGACY, created_by=test_user.id,
        invoice_number="SAL-25-0001",
    )
    db_session.add(bill)
    db_session.flush()
    db_session.refresh(bill)

    text = _pdf_text(bill, db_session)
    assert "TAX INVOICE" not in text
    assert "Authorised Signatory" not in text
    assert "reverse charge" not in text
