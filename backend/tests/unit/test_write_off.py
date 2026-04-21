"""
Unit tests for write-off Option B implementation.

Tests the new write_off_pending_discount method which records write-offs
as separate fields (write_off_amount, write_off_at, write_off_reason,
write_off_approved_by) WITHOUT mutating discount_amount or rounded_total.

To run:
    uv run pytest tests/unit/test_write_off.py -v -s
"""

import pytest
from datetime import datetime

from app.services.billing_service import BillingService
from app.models.billing import BillStatus, PaymentMethod
from app.utils import IST


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _create_posted_bill(db_session, test_service, test_user, customer=None):
    """Create a fully-paid (POSTED) bill and return it."""
    svc = BillingService(db_session)

    kwargs = dict(
        items=[{"service_id": test_service.id, "quantity": 1}],
        created_by_id=test_user.id,
    )
    if customer:
        kwargs["customer_id"] = customer.id
    else:
        kwargs["customer_name"] = "Walk-in"
        kwargs["customer_phone"] = "9876543210"

    bill = svc.create_bill(**kwargs)
    # Pay in full so it becomes POSTED
    svc.add_payment(
        bill_id=bill.id,
        payment_method=PaymentMethod.CASH,
        amount=bill.rounded_total / 100,
        confirmed_by_id=test_user.id,
    )
    db_session.refresh(bill)
    assert bill.status == BillStatus.POSTED
    return bill, svc


def _create_partial_pay_bill(db_session, test_service, test_user, customer=None, pay_fraction=0.5):
    """Create a bill paid partially, leaving a pending balance. Returns (bill, svc)."""
    svc = BillingService(db_session)

    kwargs = dict(
        items=[{"service_id": test_service.id, "quantity": 1}],
        created_by_id=test_user.id,
    )
    if customer:
        kwargs["customer_id"] = customer.id
    else:
        kwargs["customer_name"] = "Walk-in"
        kwargs["customer_phone"] = "9876543210"

    bill = svc.create_bill(**kwargs)

    partial_rupees = (bill.rounded_total * pay_fraction) / 100
    svc.add_payment(
        bill_id=bill.id,
        payment_method=PaymentMethod.CASH,
        amount=partial_rupees,
        confirmed_by_id=test_user.id,
    )
    # Post the bill with pending balance
    svc.complete_bill_with_pending(bill_id=bill.id, notes="partial payment")
    db_session.refresh(bill)
    assert bill.status == BillStatus.POSTED
    return bill, svc


# ---------------------------------------------------------------------------
# Core write-off behaviour
# ---------------------------------------------------------------------------

class TestWriteOffCoreFields:
    """The new write-off must populate the four new fields and NOT touch the
    financial columns that were incorrectly mutated in the old implementation."""

    def test_write_off_does_not_mutate_financial_columns(
        self, db_session, test_service, test_user
    ):
        """
        CRITICAL: write_off_pending_discount must NOT change discount_amount,
        rounded_total, total_amount, tax_amount, cgst_amount, sgst_amount,
        or rounding_adjustment.
        """
        bill, svc = _create_partial_pay_bill(db_session, test_service, test_user)

        # Capture original financial values
        original_discount = bill.discount_amount
        original_rounded_total = bill.rounded_total
        original_total_amount = bill.total_amount
        original_tax = bill.tax_amount
        original_cgst = bill.cgst_amount
        original_sgst = bill.sgst_amount
        original_rounding = bill.rounding_adjustment

        total_paid = sum(p.amount for p in bill.payments)
        pending = bill.rounded_total - total_paid
        assert pending > 0, "Test requires pending balance"

        write_off_paise = pending // 2  # partial write-off

        updated = svc.write_off_pending_discount(
            bill_id=bill.id,
            write_off_amount=write_off_paise,
            reason="Goodwill gesture",
            approved_by_id=test_user.id,
        )

        # Financial columns must be UNCHANGED
        assert updated.discount_amount == original_discount, \
            "discount_amount must NOT be mutated"
        assert updated.rounded_total == original_rounded_total, \
            "rounded_total must NOT be mutated"
        assert updated.total_amount == original_total_amount, \
            "total_amount must NOT be mutated"
        assert updated.tax_amount == original_tax, \
            "tax_amount must NOT be mutated"
        assert updated.cgst_amount == original_cgst, \
            "cgst_amount must NOT be mutated"
        assert updated.sgst_amount == original_sgst, \
            "sgst_amount must NOT be mutated"
        assert updated.rounding_adjustment == original_rounding, \
            "rounding_adjustment must NOT be mutated"

    def test_write_off_sets_write_off_amount(
        self, db_session, test_service, test_user
    ):
        """write_off_amount column is set to the forgiven paise."""
        bill, svc = _create_partial_pay_bill(db_session, test_service, test_user)

        total_paid = sum(p.amount for p in bill.payments)
        pending = bill.rounded_total - total_paid

        write_off_paise = pending  # full write-off

        updated = svc.write_off_pending_discount(
            bill_id=bill.id,
            write_off_amount=write_off_paise,
            reason="Full forgiveness",
            approved_by_id=test_user.id,
        )

        assert updated.write_off_amount == write_off_paise

    def test_write_off_sets_write_off_at(
        self, db_session, test_service, test_user
    ):
        """write_off_at must be a timezone-aware datetime close to now."""
        bill, svc = _create_partial_pay_bill(db_session, test_service, test_user)

        total_paid = sum(p.amount for p in bill.payments)
        pending = bill.rounded_total - total_paid

        before = datetime.now(IST)
        updated = svc.write_off_pending_discount(
            bill_id=bill.id,
            write_off_amount=pending,
            reason="Timed write-off",
            approved_by_id=test_user.id,
        )
        after = datetime.now(IST)

        assert updated.write_off_at is not None
        # write_off_at must be between before and after
        woa = updated.write_off_at
        # Normalise to IST for comparison
        if woa.tzinfo is None:
            woa = IST.localize(woa)
        assert before <= woa <= after, \
            f"write_off_at {woa} not in [{before}, {after}]"

    def test_write_off_sets_write_off_reason(
        self, db_session, test_service, test_user
    ):
        """write_off_reason must store the provided reason string."""
        bill, svc = _create_partial_pay_bill(db_session, test_service, test_user)

        total_paid = sum(p.amount for p in bill.payments)
        pending = bill.rounded_total - total_paid

        reason = "Customer complained — goodwill gesture"
        updated = svc.write_off_pending_discount(
            bill_id=bill.id,
            write_off_amount=pending,
            reason=reason,
            approved_by_id=test_user.id,
        )

        assert updated.write_off_reason == reason

    def test_write_off_sets_write_off_approved_by(
        self, db_session, test_service, test_user
    ):
        """write_off_approved_by must store the approver's user ID."""
        bill, svc = _create_partial_pay_bill(db_session, test_service, test_user)

        total_paid = sum(p.amount for p in bill.payments)
        pending = bill.rounded_total - total_paid

        updated = svc.write_off_pending_discount(
            bill_id=bill.id,
            write_off_amount=pending,
            reason="Approved",
            approved_by_id=test_user.id,
        )

        assert updated.write_off_approved_by == test_user.id


# ---------------------------------------------------------------------------
# Validation / guard rails
# ---------------------------------------------------------------------------

class TestWriteOffValidation:
    """Guard-rail tests — invalid inputs must raise ValueError."""

    def test_raises_for_unknown_bill(self, db_session, test_service, test_user):
        svc = BillingService(db_session)
        with pytest.raises(ValueError, match="Bill not found"):
            svc.write_off_pending_discount(
                bill_id="01XXXXXXXXXXXXXXXXXXXXXXXXX",
                write_off_amount=100,
                reason="N/A",
                approved_by_id=test_user.id,
            )

    def test_raises_for_draft_bill(self, db_session, test_service, test_user):
        """Cannot write off a DRAFT bill."""
        svc = BillingService(db_session)
        bill = svc.create_bill(
            items=[{"service_id": test_service.id, "quantity": 1}],
            created_by_id=test_user.id,
            customer_name="Draft Customer",
        )

        with pytest.raises(ValueError, match="posted bills"):
            svc.write_off_pending_discount(
                bill_id=bill.id,
                write_off_amount=100,
                reason="N/A",
                approved_by_id=test_user.id,
            )

    def test_raises_when_no_pending_balance(self, db_session, test_service, test_user):
        """Cannot write off a fully-paid bill."""
        bill, svc = _create_posted_bill(db_session, test_service, test_user)
        # Bill is fully paid; no pending

        with pytest.raises(ValueError, match="no pending balance"):
            svc.write_off_pending_discount(
                bill_id=bill.id,
                write_off_amount=100,
                reason="N/A",
                approved_by_id=test_user.id,
            )

    def test_raises_when_write_off_exceeds_pending(
        self, db_session, test_service, test_user
    ):
        """write_off_amount > pending must raise."""
        bill, svc = _create_partial_pay_bill(db_session, test_service, test_user)

        total_paid = sum(p.amount for p in bill.payments)
        pending = bill.rounded_total - total_paid
        too_much = pending + 1

        with pytest.raises(ValueError, match="between 1 and"):
            svc.write_off_pending_discount(
                bill_id=bill.id,
                write_off_amount=too_much,
                reason="Over the limit",
                approved_by_id=test_user.id,
            )

    def test_raises_when_write_off_is_zero(
        self, db_session, test_service, test_user
    ):
        """write_off_amount == 0 is not a valid forgiveness."""
        bill, svc = _create_partial_pay_bill(db_session, test_service, test_user)

        with pytest.raises(ValueError, match="between 1 and"):
            svc.write_off_pending_discount(
                bill_id=bill.id,
                write_off_amount=0,
                reason="Zero amount",
                approved_by_id=test_user.id,
            )

    def test_raises_when_write_off_is_negative(
        self, db_session, test_service, test_user
    ):
        """Negative write_off_amount must also raise."""
        bill, svc = _create_partial_pay_bill(db_session, test_service, test_user)

        with pytest.raises(ValueError, match="between 1 and"):
            svc.write_off_pending_discount(
                bill_id=bill.id,
                write_off_amount=-500,
                reason="Negative",
                approved_by_id=test_user.id,
            )


# ---------------------------------------------------------------------------
# Customer pending_balance reduction
# ---------------------------------------------------------------------------

class TestWriteOffCustomerBalance:
    """Write-off must reduce customer.pending_balance by write_off_amount."""

    def test_customer_pending_balance_reduced(
        self, db_session, test_service, test_user, test_customer
    ):
        """customer.pending_balance decreases by write_off_amount after write-off."""
        from app.models.customer import Customer

        bill, svc = _create_partial_pay_bill(
            db_session, test_service, test_user, customer=test_customer
        )
        db_session.refresh(test_customer)

        total_paid = sum(p.amount for p in bill.payments)
        pending = bill.rounded_total - total_paid
        assert pending > 0

        # Simulate customer.pending_balance already reflecting the pending debt
        test_customer.pending_balance = pending
        db_session.flush()

        write_off_paise = pending // 2

        svc.write_off_pending_discount(
            bill_id=bill.id,
            write_off_amount=write_off_paise,
            reason="Partial forgiveness",
            approved_by_id=test_user.id,
        )
        db_session.refresh(test_customer)

        expected_balance = pending - write_off_paise
        assert test_customer.pending_balance == expected_balance, (
            f"Expected customer balance {expected_balance} "
            f"but got {test_customer.pending_balance}"
        )

    def test_customer_balance_never_goes_negative(
        self, db_session, test_service, test_user, test_customer
    ):
        """customer.pending_balance must be floored at 0 (never negative)."""
        from app.models.customer import Customer

        bill, svc = _create_partial_pay_bill(
            db_session, test_service, test_user, customer=test_customer
        )
        db_session.refresh(test_customer)

        total_paid = sum(p.amount for p in bill.payments)
        pending = bill.rounded_total - total_paid

        # Set customer balance lower than pending (edge: balance already partially resolved)
        test_customer.pending_balance = pending // 4
        db_session.flush()

        svc.write_off_pending_discount(
            bill_id=bill.id,
            write_off_amount=pending,  # write off more than customer.pending_balance
            reason="Full forgiveness",
            approved_by_id=test_user.id,
        )
        db_session.refresh(test_customer)

        assert test_customer.pending_balance == 0, \
            "pending_balance must be floored at 0, not go negative"

    def test_no_customer_no_error(self, db_session, test_service, test_user):
        """Write-off on a walk-in bill (no customer_id) must not raise."""
        bill, svc = _create_partial_pay_bill(db_session, test_service, test_user)
        assert bill.customer_id is None

        total_paid = sum(p.amount for p in bill.payments)
        pending = bill.rounded_total - total_paid

        # Must not raise even though there is no customer
        updated = svc.write_off_pending_discount(
            bill_id=bill.id,
            write_off_amount=pending,
            reason="Walk-in write-off",
            approved_by_id=test_user.id,
        )
        assert updated.write_off_amount == pending


# ---------------------------------------------------------------------------
# Cumulative / additive write-offs
# ---------------------------------------------------------------------------

class TestWriteOffAdditive:
    """Multiple write-offs on the same bill accumulate correctly."""

    def test_second_write_off_accumulates(
        self, db_session, test_service, test_user
    ):
        """
        If a bill has a partial write-off and still has remaining pending,
        a second write-off must add to write_off_amount (not replace it).
        """
        bill, svc = _create_partial_pay_bill(
            db_session, test_service, test_user, pay_fraction=0.25
        )

        total_paid = sum(p.amount for p in bill.payments)
        pending = bill.rounded_total - total_paid

        first_wo = pending // 3
        svc.write_off_pending_discount(
            bill_id=bill.id,
            write_off_amount=first_wo,
            reason="First write-off",
            approved_by_id=test_user.id,
        )
        db_session.refresh(bill)

        # Remaining pending after first write-off
        remaining_pending = pending - first_wo
        second_wo = remaining_pending // 2

        updated = svc.write_off_pending_discount(
            bill_id=bill.id,
            write_off_amount=second_wo,
            reason="Second write-off",
            approved_by_id=test_user.id,
        )

        assert updated.write_off_amount == first_wo + second_wo, (
            "Second write-off should accumulate on top of first"
        )

    def test_second_write_off_respects_remaining_pending(
        self, db_session, test_service, test_user
    ):
        """
        After a partial write-off, the remaining pending is:
        rounded_total - total_paid - existing_write_off_amount.
        A second write-off exceeding this remaining pending must raise.
        """
        bill, svc = _create_partial_pay_bill(
            db_session, test_service, test_user, pay_fraction=0.25
        )

        total_paid = sum(p.amount for p in bill.payments)
        pending = bill.rounded_total - total_paid

        first_wo = pending // 2
        svc.write_off_pending_discount(
            bill_id=bill.id,
            write_off_amount=first_wo,
            reason="First write-off",
            approved_by_id=test_user.id,
        )
        db_session.refresh(bill)

        remaining = pending - first_wo
        too_much = remaining + 1

        with pytest.raises(ValueError, match="between 1 and"):
            svc.write_off_pending_discount(
                bill_id=bill.id,
                write_off_amount=too_much,
                reason="Over the remaining",
                approved_by_id=test_user.id,
            )
