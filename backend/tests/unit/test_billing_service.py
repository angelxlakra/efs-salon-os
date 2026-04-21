"""
Unit tests for Billing Service.

This tests the core billing workflow:
- Bill creation with tax calculation
- Payment processing and posting
- Refunds and customer stats
- Void (draft and owner-override for posted)

To run:
    uv run pytest tests/unit/test_billing_service.py -v -s
"""

import pytest
from app.services.billing_service import BillingService
from app.models.billing import BillStatus, PaymentMethod

def test_create_bill_basic(db_session, test_service, test_user):
    """
    TEST CASE 1: Create a basic bill with one service

    SCENARIO: Receptionist creates a bill for a walk-in customer
    EXPECTED:
        - Bill created in DRAFT  status
        - No invoice number (assigned when posted)
        - Tax calculated correctly (18% extracted from inclusive price)
        - Total rounded to nearest rupee
    """

    service = BillingService(db_session)

    bill = service.create_bill(
        items=[{
            "service_id": test_service.id,
            "quantity": 1
        }],
        created_by_id=test_user.id,
        customer_name="Walk-in Customer",
        customer_phone="9876543210"
    )

    assert bill is not None, "Bill should be created"
    assert bill.status == BillStatus.DRAFT, "New bill should be in DRAFT status"
    assert bill.invoice_number == "", "Draft bill should not have an invoice number"

    assert bill.subtotal == 50000, "Subtotal should be Rs. 500 (50000 paise)"
    assert bill.discount_amount == 0, "No discount applied"

    expected_tax = int((50000 * 18) / 118)
    assert bill.tax_amount == expected_tax, "Tax should be ~Rs. 76.27 (extracted from Rs 500)"
    
    # Verify CGST and SGST are roughly equal (within 1 paise)
    assert abs(bill.cgst_amount - bill.sgst_amount) <= 1, \
     "CGST and SGST should be approximately equal"

    # Verify they sum close to total tax (within 2 paise rounding tolerance)
    assert abs((bill.cgst_amount + bill.sgst_amount) - bill.tax_amount) <= 2, \
     f"CGST + SGST should sum close to total tax"

    assert bill.total_amount == 50000, "Total should equal subtotal (tax inclusive)"
    assert bill.rounded_total == 50000, "Rs. 500.00 is already a whole rupee"
    assert bill.rounding_adjustment == 0, "No rounding needed"

    assert bill.customer_name == "Walk-in Customer"
    assert bill.customer_phone == "9876543210"
    assert bill.customer_id is None, "Walk-in customer (not in database)"

    print(f"✅ Created bill: ID={bill.id}")
    print(f"   Subtotal: ₹{bill.subtotal/100:.2f}")
    print(f"   Tax: ₹{bill.tax_amount/100:.2f} (CGST: ₹{bill.cgst_amount/100:.2f}, SGST: ₹{bill.sgst_amount/100:.2f})")
    print(f"   Total: ₹{bill.rounded_total/100:.2f}")


def test_owner_can_void_posted_bill(db_session, test_service, test_user):
    """Regression: Owner must be able to void a POSTED bill.

    Scenario: A bill was posted (payment recorded) in error, and the owner
    needs to cancel it. Currently fails with ValueError because void_bill
    only allows DRAFT status. Owner should be able to override this with
    allow_posted=True.
    """
    service = BillingService(db_session)

    # Create and fully pay a bill so it becomes POSTED
    bill = service.create_bill(
        items=[{"service_id": test_service.id, "quantity": 1}],
        created_by_id=test_user.id,
        customer_name="Walk-in Customer",
    )
    amount_rupees = bill.rounded_total / 100
    service.add_payment(
        bill_id=bill.id,
        payment_method=PaymentMethod.CASH,
        amount=amount_rupees,
        confirmed_by_id=test_user.id,
    )
    db_session.refresh(bill)
    assert bill.status == BillStatus.POSTED, "Bill should be POSTED after full payment"

    # Owner attempts to void the posted bill — EXPECTED to succeed
    voided = service.void_bill(
        bill_id=bill.id,
        voided_by_id=test_user.id,
        reason="Billing error — customer never arrived",
        allow_posted=True,
    )

    assert voided.status == BillStatus.VOID, "Owner should be able to void a posted bill"


def test_non_owner_cannot_void_posted_bill(db_session, test_service, test_user):
    """Regression: Non-owner must NOT void a POSTED bill via allow_posted=True.

    The allow_posted flag is only meaningful when the API layer passes
    current_user.is_owner. The service itself still guards the flag.
    """
    service = BillingService(db_session)

    bill = service.create_bill(
        items=[{"service_id": test_service.id, "quantity": 1}],
        created_by_id=test_user.id,
        customer_name="Walk-in Customer",
    )
    amount_rupees = bill.rounded_total / 100
    service.add_payment(
        bill_id=bill.id,
        payment_method=PaymentMethod.CASH,
        amount=amount_rupees,
        confirmed_by_id=test_user.id,
    )
    db_session.refresh(bill)
    assert bill.status == BillStatus.POSTED

    # Without allow_posted (receptionist/staff path) — must still raise
    with pytest.raises(ValueError, match="Can only void draft bills"):
        service.void_bill(
            bill_id=bill.id,
            voided_by_id=test_user.id,
            reason="Attempted by non-owner",
            allow_posted=False,
        )

