import pytest
from datetime import date
from app.models.purchase import PurchaseInvoice, SupplierPayment
from app.models.inventory import Supplier
from app.utils import generate_ulid


# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def supplier(db_session):
    s = Supplier(
        id=generate_ulid(),
        name="Test Supplier",
        is_active=True,
    )
    db_session.add(s)
    db_session.flush()
    return s


def make_invoice(db_session, supplier_id: str, total: int, created_by: str, invoice_date=None):
    """Create a RECEIVED invoice with the given total_amount (paise)."""
    inv = PurchaseInvoice(
        id=generate_ulid(),
        supplier_id=supplier_id,
        invoice_number=f"INV-{generate_ulid()[:6]}",
        invoice_date=invoice_date or date(2026, 1, 1),
        subtotal=total,
        invoice_discount_amount=0,
        round_off_amount=0,
        total_amount=total,
        paid_amount=0,
        balance_due=total,
        status="received",
        created_by=created_by,
    )
    db_session.add(inv)
    db_session.flush()
    return inv


def _call_record_payment(payment_data, test_user, db_session, monkeypatch):
    """
    Call record_supplier_payment with commit replaced by flush so the test
    transaction stays within the rollback boundary of db_session.
    """
    from app.api.purchases import record_supplier_payment

    # Replace db.commit with db.flush to keep everything in the test transaction
    monkeypatch.setattr(db_session, "commit", db_session.flush)
    # Replace db.refresh with a no-op (object is already flushed and up-to-date)
    monkeypatch.setattr(db_session, "refresh", lambda obj: None)

    return record_supplier_payment(
        payment_data=payment_data,
        current_user=test_user,
        db=db_session,
    )


# ── FIFO allocation tests ─────────────────────────────────────────────────────

def test_fifo_payment_fully_settles_oldest_invoice(db_session, supplier, test_user, monkeypatch):
    """A general payment that exactly covers the oldest invoice marks it PAID."""
    inv1 = make_invoice(db_session, supplier.id, total=100_00, created_by=test_user.id, invoice_date=date(2026, 1, 1))
    inv2 = make_invoice(db_session, supplier.id, total=200_00, created_by=test_user.id, invoice_date=date(2026, 2, 1))

    from app.schemas.purchase import SupplierPaymentCreate

    _call_record_payment(
        payment_data=SupplierPaymentCreate(
            supplier_id=supplier.id,
            payment_date=date.today(),
            amount=100_00,
            payment_method="cash",
        ),
        test_user=test_user,
        db_session=db_session,
        monkeypatch=monkeypatch,
    )

    db_session.flush()

    assert inv1.status == "paid"
    assert inv1.balance_due == 0
    assert inv2.status == "received"  # untouched
    assert inv2.balance_due == 200_00


def test_fifo_payment_spans_multiple_invoices(db_session, supplier, test_user, monkeypatch):
    """A payment larger than the first invoice spills over into the second."""
    inv1 = make_invoice(db_session, supplier.id, total=100_00, created_by=test_user.id, invoice_date=date(2026, 1, 1))
    inv2 = make_invoice(db_session, supplier.id, total=200_00, created_by=test_user.id, invoice_date=date(2026, 2, 1))

    from app.schemas.purchase import SupplierPaymentCreate

    _call_record_payment(
        payment_data=SupplierPaymentCreate(
            supplier_id=supplier.id,
            payment_date=date.today(),
            amount=150_00,  # covers inv1 fully, ₹50 into inv2
            payment_method="cash",
        ),
        test_user=test_user,
        db_session=db_session,
        monkeypatch=monkeypatch,
    )

    db_session.flush()

    assert inv1.status == "paid"
    assert inv1.balance_due == 0
    assert inv2.status == "partially_paid"
    assert inv2.balance_due == 150_00  # 200 - 50 = 150


def test_invoice_linked_payment_unchanged(db_session, supplier, test_user, monkeypatch):
    """Existing behaviour: invoice-linked payment only touches that invoice."""
    inv1 = make_invoice(db_session, supplier.id, total=100_00, created_by=test_user.id, invoice_date=date(2026, 1, 1))
    inv2 = make_invoice(db_session, supplier.id, total=200_00, created_by=test_user.id, invoice_date=date(2026, 2, 1))

    from app.schemas.purchase import SupplierPaymentCreate

    _call_record_payment(
        payment_data=SupplierPaymentCreate(
            supplier_id=supplier.id,
            purchase_invoice_id=inv1.id,
            payment_date=date.today(),
            amount=50_00,
            payment_method="cash",
        ),
        test_user=test_user,
        db_session=db_session,
        monkeypatch=monkeypatch,
    )

    db_session.flush()

    assert inv1.status == "partially_paid"
    assert inv1.balance_due == 50_00
    assert inv2.balance_due == 200_00  # untouched


# ── Ledger endpoint tests ─────────────────────────────────────────────────────

def test_supplier_ledger_running_balance(db_session, supplier, test_user):
    """Ledger entries sorted by date; running balance reflects debits then credits."""
    inv = make_invoice(db_session, supplier.id, total=300_00, invoice_date=date(2026, 3, 1), created_by=test_user.id)

    # Manually create a payment and apply it to simulate post-allocation state
    payment = SupplierPayment(
        id=generate_ulid(),
        supplier_id=supplier.id,
        payment_date=date(2026, 3, 15),
        amount=100_00,
        payment_method="cash",
        recorded_by=test_user.id,
    )
    db_session.add(payment)
    inv.paid_amount = 100_00
    inv.balance_due = 200_00
    inv.status = "partially_paid"
    db_session.flush()

    from app.api.purchases import get_supplier_ledger

    result = get_supplier_ledger(
        supplier_id=supplier.id,
        current_user=test_user,
        db=db_session,
    )

    assert result.total_outstanding == 200_00
    assert len(result.entries) == 2

    invoice_entry = next(e for e in result.entries if e.entry_type == "invoice")
    assert invoice_entry.debit == 300_00
    assert invoice_entry.credit == 0
    assert invoice_entry.running_balance == 300_00

    payment_entry = next(e for e in result.entries if e.entry_type == "payment")
    assert payment_entry.credit == 100_00
    assert payment_entry.debit == 0
    assert payment_entry.running_balance == 200_00


def test_supplier_ledger_empty(db_session, supplier, test_user):
    """Ledger for a supplier with no transactions returns empty entries."""
    from app.api.purchases import get_supplier_ledger

    result = get_supplier_ledger(
        supplier_id=supplier.id,
        current_user=test_user,
        db=db_session,
    )

    assert result.total_outstanding == 0
    assert result.entries == []
