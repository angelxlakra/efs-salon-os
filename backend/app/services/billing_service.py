"""Billing service for creating and managing bills.

  This module handles the complete billing workflow:
  - Bill creation with tax calculation
  - Payment processing
  - Invoice number generation
  - Customer stats updates
  - Refund processing

  The service integrates with:
  - TaxCalculator: GST breakdown
  - InvoiceNumberGenerator: Sequential invoice numbers
  - IdempotencyService: Duplicate prevention
  - Database models: Bill, BillItem, Payment, Customer, Service

  Workflow:
      1. Create bill (draft status, no invoice number)
      2. Add payment(s)
      3. When fully paid → Generate invoice, mark as posted
      4. Update customer statistics
"""

from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import Session
from ulid import ULID

from app.models.billing import Bill, BillItem, BillStatus, Payment, PaymentMethod
from app.models.customer import Customer
from app.models.service import Service
from app.services.invoice_generator import InvoiceNumberGenerator
from app.services.tax_calculator import TaxCalculator


class BillingService:
    """Handle bill creation, payments, and refunds.

      This service manages the complete lifecycle of a bill from
      creation through payment to posting.

      Attributes:
          db: SQLAlchemy database session.
    """

    def __init__(self, db: Session):
        """Initialize billing service.

          Args:
              db: Database session for all operations.
        """

        self.db = db
    
    def create_bill(
        self,
        items: List[dict],  # [{"service_id": str, "quantity": int, "staff_id": str, ...}]
        created_by_id: str,
        customer_id: Optional[str] = None,
        customer_name: Optional[str] = None,
        customer_phone: Optional[str] = None,
        discount_amount: int = 0, # in rupees
        discount_reason: Optional[str] = None,
    ) -> Bill:
        """Create a new bill in draft status.

            Creates a bill with line items, calculates tax, applies discount,
            and rounds to nearest rupee. Bill starts in 'draft' status with
            no invoice number (assigned when posted).

            Args:
                items: List of bill items with service_id, quantity, staff_id, etc.
                created_by_id: User ID creating the bill.
                customer_id: Optional customer ID (for existing customers).
                customer_name: Customer name (required if no customer_id).
                customer_phone: Customer phone (required if no customer_id).
                discount_amount: Discount in rupees (converted to paise).
                discount_reason: Optional reason for discount.

            Returns:
                Bill: Created bill in draft status.

            Raises:
                ValueError: If validation fails (invalid service, discount too high, etc.).

            Example:
                >>> service = BillingService(db)
                >>> bill = service.create_bill(
                ...     items=[{"service_id": "01SVC...", "quantity": 1}],
                ...     created_by_id="01USER...",
                ...     customer_name="John Doe",
                ...     customer_phone="9876543210",
                ...     discount_amount=50
                ... )
                >>> bill.status
                'draft'
        """

        if not customer_id and (not customer_name or not customer_phone):
            raise ValueError("Customer name and phone required if no customer_id")

        subtotal = 0
        bill_items_data = []

        for item in items:
            # Type hint to help IDE understand SQLAlchemy column attributes
            service = self.db.query(Service).filter(
                Service.id == item["service_id"],
                Service.is_active,  # noqa: E712
                Service.deleted_at == None  # noqa: E711
            ).first()

            if not service:
                raise ValueError(f"Service not found: {item['service_id']}")

            quantity = item.get("quantity", 1)
            line_total = service.base_price * quantity
            subtotal += line_total

            bill_items_data.append({
                "service_id": service.id,
                "item_name": service.name,
                "base_price": service.base_price,
                "quantity": quantity,
                "line_total": line_total,
                "staff_id": item.get("staff_id"),
                "appointment_id": item.get("appointment_id"),
                "walkin_id": item.get("walkin_id"),
                "notes": item.get("notes")
            })
        discount_paise = discount_amount * 100
        if discount_paise > subtotal:
            raise ValueError("Discount cannot exceed subtotal")

        amount_after_discount = subtotal - discount_paise
        tax_breakdown = TaxCalculator.calculate_tax_breakdown(amount_after_discount)
        total_amount = amount_after_discount # Tax already inclusive
        rounded_total, rounding_adjustment = TaxCalculator.round_to_rupee(total_amount)

        bill = Bill(
            id=str(ULID()),
            invoice_number="",
            customer_id=customer_id,
            customer_name=customer_name,
            customer_phone=customer_phone,
            subtotal=subtotal,
            discount_amount=discount_paise,
            discount_reason=discount_reason,
            tax_amount=tax_breakdown["total_tax"],
            cgst_amount=tax_breakdown["cgst"],
            sgst_amount=tax_breakdown["sgst"],
            total_amount=total_amount,
            rounded_total=rounded_total,
            rounding_adjustment=rounding_adjustment,
            status=BillStatus.DRAFT,
            created_by=created_by_id
        )

        self.db.add(bill)
        self.db.flush() # Get bill.id without committing

        for item_data in bill_items_data:
            bill_item = BillItem(
                id=str(ULID()),
                bill_id=bill.id,
                **item_data
            )
            self.db.add(bill_item)

        self.db.commit()
        self.db.refresh(bill)
        return bill

    def add_payment(
        self,
        bill_id: str,
        payment_method: PaymentMethod,
        amount: int, # in rupees
        confirmed_by_id: str,
        reference_number: Optional[str] = None,
        notes: Optional[str] = None
    ) -> Payment:
        """Add payment to bill and post if fully paid.

            Records a payment against a draft bill. If total payments meet or
            exceed the bill total, generates invoice number and marks as posted.

            Args:
                bill_id: ID of the bill to pay.
                payment_method: Payment method (cash, upi, card, other).
                amount: Payment amount in rupees.
                confirmed_by_id: User confirming the payment.
                reference_number: Optional transaction reference.
                notes: Optional payment notes.

            Returns:
                Payment: Created payment record.

            Raises:
                ValueError: If bill not found, not draft, or overpayment.

            Example:
                >>> payment = service.add_payment(
                ...     bill_id="01BILL...",
                ...     payment_method=PaymentMethod.CASH,
                ...     amount=1470,
                ...     confirmed_by_id="01USER..."
                ... )
                >>> payment.bill.status  # May be 'posted' if fully paid
                'posted'
        """

        bill = self.db.query(Bill).filter(Bill.id == bill_id).first()

        if not bill:
            raise ValueError("Bill not found")
        
        if bill.status != BillStatus.DRAFT:
            raise ValueError("Can only add payments to draft bills")
        


        existing_payments = self.db.query(Payment).filter(
            Payment.bill_id == bill_id
        ).all()

        current_total = sum(p.amount for p in existing_payments)
        amount_paise = amount * 100
        new_total = current_total + amount_paise

        TOLERANCE = 1000 # Rs 10 tolerance

        if new_total > bill.rounded_total + TOLERANCE:
            raise ValueError(
                f"Payment would exceed bill total. "
                f"Bill: Rs {bill.rounded_total/100:.2f}, "
                f"Paid: Rs {new_total/100:.2f}"
            )
        
        payment = Payment(
            id=str(ULID()),
            bill_id=bill_id,
            payment_method=payment_method,
            amount=amount_paise,
            reference_number=reference_number,
            notes=notes,
            confirmed_at=datetime.utcnow(),
            confirmed_by=confirmed_by_id
        )

        self.db.add(payment)

        if new_total >= bill.rounded_total:
            # Generate invoice number
            invoice_number = InvoiceNumberGenerator.generate(self.db)

            bill.invoice_number = invoice_number
            bill.status = BillStatus.POSTED
            bill.posted_at = datetime.utcnow()

            # Update customer stats
            if bill.customer_id:
                self._update_customer_stats(bill.customer_id, bill.rounded_total, increment=True)
            
        self.db.commit()
        self.db.refresh(payment)
        return payment


    def refund_bill(
        self,
        bill_id: str,
        reason: str,
        refunded_by_id: str,
        notes: Optional[str] = None
    ) -> Bill:
        """Create refund for a posted bill.

            Creates a negative bill linked to the original. Updates original
            bill status to 'refunded' and decrements customer stats.

            Args:
                bill_id: ID of bill to refund.
                reason: Reason for refund (required).
                refunded_by_id: User processing refund (must be owner).
                notes: Optional additional notes.

            Returns:
                Bill: New refund bill with negative amounts.

            Raises:
                ValueError: If bill not found, not posted, or already refunded.

            Example:
                >>> refund = service.refund_bill(
                ...     bill_id="01BILL...",
                ...     reason="Customer dissatisfaction",
                ...     refunded_by_id="01OWNER..."
                ... )
                >>> refund.total_amount  # Negative
                -147000
        """

        original_bill = self.db.query(Bill).filter(Bill.id == bill_id).first()

        if not original_bill:
            raise ValueError("Bill not found")
        
        if original_bill.status != BillStatus.POSTED:
            raise ValueError("Can only refund posted bills")
        
        if original_bill.status == BillStatus.REFUNDED:
            raise ValueError("Bill already refunded")
        
        refund_bill = Bill(
            id=str(ULID()),
            invoice_number=InvoiceNumberGenerator.generate(self.db),
            customer_id=original_bill.customer_id,
            customer_name=original_bill.customer_name,
            customer_phone=original_bill.customer_phone,
            subtotal=-original_bill.subtotal,
            discount_amount=-original_bill.discount_amount,
            tax_amount=-original_bill.tax_amount,
            cgst_amount=-original_bill.cgst_amount,
            sgst_amount=-original_bill.sgst_amount,
            total_amount=-original_bill.total_amount,
            rounded_total=-original_bill.rounded_total,
            rounding_adjustment=-original_bill.rounding_adjustment,
            status=BillStatus.POSTED,
            posted_at=datetime.utcnow(),
            original_bill_id=original_bill.id,
            refund_reason=reason,
            refund_approved_by=refunded_by_id,
            refunded_at=datetime.utcnow(),
            created_by=refunded_by_id
        )

        self.db.add(refund_bill)

        original_bill.status = BillStatus.REFUNDED
        original_bill.refunded_at = datetime.utcnow()
        original_bill.refund_reason = reason
        original_bill.refund_approved_by = refunded_by_id

        if original_bill.customer_id:
            self._update_customer_stats(
                original_bill.customer_id,
                original_bill.rounded_total,
                increment=False
            )
        
        self.db.commit()
        self.db.refresh(refund_bill)
        
        return refund_bill

    def get_bill(self, bill_id: str) -> Optional[Bill]:
        """Get bill by ID with relationships loaded.

            Args:
                bill_id: Bill ID to retrieve.

            Returns:
                Optional[Bill]: Bill if found, None otherwise.
        """

        return self.db.query(Bill).filter(Bill.id == bill_id).first()

    def _update_customer_stats(
        self,
        customer_id: str,
        amount: int,
        increment: bool = True
    ) -> None:
        """Update customer statistics after bill posting or refund.

            Args:
                customer_id: Customer to update.
                amount: Amount to add/subtract (in paise).
                increment: True to add, False to subtract.
        """

        customer = self.db.query(Customer).filter(Customer.id == customer_id).first()

        if not customer:
            return
        
        if increment:
            customer.total_visits += 1
            customer.total_spent += amount
            customer.last_visit_at = datetime.utcnow()

        else:
            customer.total_spent = max(0, customer.total_spent - amount) # To not go negative
        







