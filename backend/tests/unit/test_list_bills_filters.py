"""
Unit tests for list_bills query filters:
  - search (multi-field ilike)
  - pending_only (posted bills with unpaid balance)

These tests operate directly on the SQLAlchemy query layer — no HTTP client
needed — so they run fast and without requiring a running FastAPI server.

To run:
    uv run pytest tests/unit/test_list_bills_filters.py -v -s
"""

import pytest
from sqlalchemy import or_, func, select as sa_select

from app.models.billing import Bill, BillStatus, Payment, PaymentMethod
from app.services.billing_service import BillingService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_posted_bill(db, service, user, customer_name, customer_phone):
    """Create a fully-paid (POSTED) bill and return it."""
    svc = BillingService(db)
    bill = svc.create_bill(
        items=[{"service_id": service.id, "quantity": 1}],
        created_by_id=user.id,
        customer_name=customer_name,
        customer_phone=customer_phone,
    )
    svc.add_payment(
        bill_id=bill.id,
        payment_method=PaymentMethod.CASH,
        amount=bill.rounded_total / 100,
        confirmed_by_id=user.id,
    )
    db.refresh(bill)
    assert bill.status == BillStatus.POSTED
    return bill


def _make_partially_paid_bill(db, service, user, customer_name, customer_phone):
    """Create a POSTED bill with partial payment (balance still outstanding)."""
    svc = BillingService(db)
    bill = svc.create_bill(
        items=[{"service_id": service.id, "quantity": 1}],
        created_by_id=user.id,
        customer_name=customer_name,
        customer_phone=customer_phone,
    )
    # Pay only half (in rupees)
    partial_rupees = (bill.rounded_total / 100) / 2
    svc.add_payment(
        bill_id=bill.id,
        payment_method=PaymentMethod.UPI,
        amount=partial_rupees,
        confirmed_by_id=user.id,
    )
    db.refresh(bill)
    # Bill is still POSTED after partial payment in BillingService
    # (full payment triggers status change; partial does not)
    return bill


def _make_draft_bill(db, service, user, customer_name, customer_phone):
    """Create a DRAFT bill (no payment)."""
    svc = BillingService(db)
    bill = svc.create_bill(
        items=[{"service_id": service.id, "quantity": 1}],
        created_by_id=user.id,
        customer_name=customer_name,
        customer_phone=customer_phone,
    )
    db.refresh(bill)
    assert bill.status == BillStatus.DRAFT
    return bill


# ---------------------------------------------------------------------------
# search filter tests
# ---------------------------------------------------------------------------

class TestSearchFilter:
    """Test the multi-field ilike search on invoice_number, customer_name, phone."""

    def test_search_by_customer_name(self, db_session, test_service, test_user):
        """search=priya matches bill with customer_name containing 'Priya'."""
        _make_posted_bill(db_session, test_service, test_user, "Priya Sharma", "9876500001")
        _make_posted_bill(db_session, test_service, test_user, "Raju Kumar", "9876500002")

        search = "priya"
        query = db_session.query(Bill).filter(
            or_(
                Bill.invoice_number.ilike(f"%{search}%"),
                Bill.customer_name.ilike(f"%{search}%"),
                Bill.customer_phone.ilike(f"%{search}%"),
            )
        )
        results = query.all()

        names = [b.customer_name for b in results]
        assert "Priya Sharma" in names, "Should match bill with 'Priya' in customer_name"
        assert "Raju Kumar" not in names, "Should not match unrelated customer"

    def test_search_by_customer_phone(self, db_session, test_service, test_user):
        """search=00003 matches bill with customer_phone containing '00003'."""
        _make_posted_bill(db_session, test_service, test_user, "Customer A", "9876500003")
        _make_posted_bill(db_session, test_service, test_user, "Customer B", "9876500004")

        search = "00003"
        query = db_session.query(Bill).filter(
            or_(
                Bill.invoice_number.ilike(f"%{search}%"),
                Bill.customer_name.ilike(f"%{search}%"),
                Bill.customer_phone.ilike(f"%{search}%"),
            )
        )
        results = query.all()

        phones = [b.customer_phone for b in results]
        assert "9876500003" in phones
        assert "9876500004" not in phones

    def test_search_by_invoice_number(self, db_session, test_service, test_user):
        """search matches invoice_number substring (posted bills have invoice numbers)."""
        bill = _make_posted_bill(db_session, test_service, test_user, "Search Test", "9000000001")
        assert bill.invoice_number, "Posted bill must have an invoice_number"

        # Use a substring of the actual invoice number
        substr = bill.invoice_number[4:]  # e.g. "25-0001" from "SAL-25-0001"
        search = substr

        query = db_session.query(Bill).filter(
            or_(
                Bill.invoice_number.ilike(f"%{search}%"),
                Bill.customer_name.ilike(f"%{search}%"),
                Bill.customer_phone.ilike(f"%{search}%"),
            )
        )
        results = query.all()
        ids = [b.id for b in results]
        assert bill.id in ids, "Should find bill by invoice_number substring"

    def test_search_empty_string_matches_all(self, db_session, test_service, test_user):
        """An empty search string ilike '%' matches every bill."""
        b1 = _make_posted_bill(db_session, test_service, test_user, "Alpha", "9100000001")
        b2 = _make_posted_bill(db_session, test_service, test_user, "Beta", "9100000002")

        search = ""
        query = db_session.query(Bill).filter(
            or_(
                Bill.invoice_number.ilike(f"%{search}%"),
                Bill.customer_name.ilike(f"%{search}%"),
                Bill.customer_phone.ilike(f"%{search}%"),
            )
        )
        results = query.all()
        ids = [b.id for b in results]
        assert b1.id in ids
        assert b2.id in ids

    def test_search_no_match_returns_empty(self, db_session, test_service, test_user):
        """A search string that matches nothing returns an empty list."""
        _make_posted_bill(db_session, test_service, test_user, "Ordinary Name", "9200000001")

        search = "ZZZNOMATCH"
        query = db_session.query(Bill).filter(
            or_(
                Bill.invoice_number.ilike(f"%{search}%"),
                Bill.customer_name.ilike(f"%{search}%"),
                Bill.customer_phone.ilike(f"%{search}%"),
            )
        )
        results = query.all()
        assert results == [], "Should return empty list when no bills match"


# ---------------------------------------------------------------------------
# pending_only filter tests
# ---------------------------------------------------------------------------

class TestPendingOnlyFilter:
    """Test the pending_only filter: POSTED bills where rounded_total > sum(payments)."""

    def _pending_query(self, db):
        """Return a query using the same subquery logic as the endpoint."""
        payment_subquery = (
            sa_select(func.coalesce(func.sum(Payment.amount), 0))
            .where(Payment.bill_id == Bill.id)
            .correlate(Bill)
            .scalar_subquery()
        )
        return db.query(Bill).filter(
            Bill.status == BillStatus.POSTED,
            Bill.rounded_total > payment_subquery,
        )

    def test_partially_paid_posted_bill_is_returned(self, db_session, test_service, test_user):
        """A POSTED bill with partial payment appears in pending_only results."""
        bill = _make_partially_paid_bill(
            db_session, test_service, test_user, "Pending Payer", "9300000001"
        )
        # Confirm partial payment was recorded
        total_paid = sum(p.amount for p in bill.payments)
        assert total_paid < bill.rounded_total, "Bill must still have an outstanding balance"

        results = self._pending_query(db_session).all()
        ids = [b.id for b in results]
        assert bill.id in ids, "Partially paid POSTED bill should appear in pending_only results"

    def test_fully_paid_posted_bill_is_excluded(self, db_session, test_service, test_user):
        """A fully-paid POSTED bill does NOT appear in pending_only results."""
        bill = _make_posted_bill(
            db_session, test_service, test_user, "Full Payer", "9300000002"
        )
        total_paid = sum(p.amount for p in bill.payments)
        assert total_paid >= bill.rounded_total, "Bill must be fully paid"

        results = self._pending_query(db_session).all()
        ids = [b.id for b in results]
        assert bill.id not in ids, "Fully paid POSTED bill must not appear in pending_only results"

    def test_draft_bill_is_excluded(self, db_session, test_service, test_user):
        """A DRAFT bill (no payment) does NOT appear in pending_only results (wrong status)."""
        bill = _make_draft_bill(
            db_session, test_service, test_user, "Draft Customer", "9300000003"
        )

        results = self._pending_query(db_session).all()
        ids = [b.id for b in results]
        assert bill.id not in ids, "DRAFT bill must not appear in pending_only results"

    def test_bill_with_no_payments_but_posted_status_is_returned(
        self, db_session, test_service, test_user
    ):
        """
        Edge case: a POSTED bill with zero payments (e.g. manually forced to POSTED
        or a data anomaly) has rounded_total > 0 and should appear as pending.
        We simulate this by directly setting the status to POSTED on a draft bill.
        """
        svc = BillingService(db_session)
        bill = svc.create_bill(
            items=[{"service_id": test_service.id, "quantity": 1}],
            created_by_id=test_user.id,
            customer_name="Zero Pay Posted",
            customer_phone="9300000004",
        )
        # Force status to POSTED without any payment
        bill.status = BillStatus.POSTED
        db_session.flush()
        db_session.refresh(bill)

        assert len(bill.payments) == 0, "No payments on this bill"

        results = self._pending_query(db_session).all()
        ids = [b.id for b in results]
        assert bill.id in ids, "POSTED bill with no payments must appear in pending_only"

    def test_pending_only_false_does_not_apply_filter(
        self, db_session, test_service, test_user
    ):
        """When pending_only=False, the filter block is skipped; all bills visible."""
        fully_paid = _make_posted_bill(
            db_session, test_service, test_user, "Paid Up", "9400000001"
        )
        partial = _make_partially_paid_bill(
            db_session, test_service, test_user, "Still Owes", "9400000002"
        )

        # No pending_only filter applied
        all_bills = db_session.query(Bill).all()
        ids = [b.id for b in all_bills]
        assert fully_paid.id in ids
        assert partial.id in ids
