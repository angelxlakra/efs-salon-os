"""
Unit tests for Billing Service.

This tests the core billing workflow:
- Bill creation with tax calculation
- Payment processing and posting
- Refunds and customer stats

To run:
    uv run pytest tests/unit/test_billing_service.py -v -s
"""

import pytest
from app.services.billing_service import BillingService
from app.models.billing import BillStatus

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

