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

from app.models.billing import Bill, BillItem, BillStatus, Payment, PaymentMethod, BillItemStaffContribution
from app.models.customer import Customer
from app.models.pending_payment import PendingPaymentCollection
from app.utils import IST
from app.models.service import Service, ServiceMaterialUsage
from app.models.inventory import SKU
from app.models.appointment import WalkIn
from app.services.invoice_generator import InvoiceNumberGenerator
from app.services.tax_calculator import TaxCalculator
from app.services.inventory_service import InventoryService
from app.services.contribution_calculator import ContributionCalculator, ContributionCalculationError


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
        items: List[dict],  # [{"service_id": str, ...} OR {"sku_id": str, ...}]
        created_by_id: str,
        customer_id: Optional[str] = None,
        customer_name: Optional[str] = None,
        customer_phone: Optional[str] = None,
        discount_amount: int = 0, # in rupees
        discount_reason: Optional[str] = None,
        session_id: Optional[str] = None,  # Link walk-ins to bill
        tip_amount: int = 0,  # in paise
        tip_staff_id: Optional[str] = None,
    ) -> Bill:
        """Create a new bill in draft status.

            Creates a bill with line items (services and/or products), calculates
            tax, COGS, applies discount, and rounds to nearest rupee. Bill starts
            in 'draft' status with no invoice number (assigned when posted).

            Items can be services (service_id) OR retail products (sku_id).
            COGS is calculated for both services (material usage) and products.

            If session_id is provided, links all walk-ins with that session_id
            to this bill (useful for walk-in service flow where services are
            completed before payment).

            Args:
                items: List of bill items with service_id OR sku_id, quantity, etc.
                created_by_id: User ID creating the bill.
                customer_id: Optional customer ID (for existing customers).
                customer_name: Customer name (required if no customer_id).
                customer_phone: Customer phone (required if no customer_id).
                discount_amount: Discount in rupees (converted to paise).
                discount_reason: Optional reason for discount.
                session_id: Optional session ID to link walk-ins to this bill.
                tip_amount: Tip amount in paise.
                tip_staff_id: Staff receiving the tip.

            Returns:
                Bill: Created bill in draft status.

            Raises:
                ValueError: If validation fails (invalid service/product, discount too high, etc.).

            Example:
                >>> service = BillingService(db)
                >>> bill = service.create_bill(
                ...     items=[
                ...         {"service_id": "01SVC...", "quantity": 1},
                ...         {"sku_id": "01SKU...", "quantity": 2}
                ...     ],
                ...     created_by_id="01USER...",
                ...     customer_name="John Doe",
                ...     customer_phone="9876543210",
                ...     discount_amount=50,
                ...     tip_amount=5000
                ... )
                >>> bill.status
                'draft'
        """

        if not customer_id and not customer_name:
            raise ValueError("Customer name required if no customer_id")

        if session_id:
            # Check for existing draft bill for this session to prevent duplicates
            existing_draft = self.db.query(Bill).join(WalkIn, WalkIn.bill_id == Bill.id).filter(
                WalkIn.session_id == session_id,
                Bill.status == BillStatus.DRAFT
            ).first()
            if existing_draft:
                return existing_draft

        subtotal = 0
        bill_items_data = []
        inventory_service = InventoryService(self.db)

        for item in items:
            # Check if item is a service or product
            if "service_id" in item and item["service_id"]:
                # Service item
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

                # Calculate COGS for service (material usage)
                cogs_amount = self._calculate_service_cogs(service.id, quantity)

                bill_item_data = {
                    "service_id": service.id,
                    "sku_id": None,
                    "item_name": service.name,
                    "base_price": service.base_price,
                    "quantity": quantity,
                    "line_total": line_total,
                    "cogs_amount": cogs_amount,
                    "staff_id": item.get("staff_id"),
                    "appointment_id": item.get("appointment_id"),
                    "walkin_id": item.get("walkin_id"),
                    "notes": item.get("notes"),
                    "staff_contributions": item.get("staff_contributions")  # Multi-staff data
                }
                bill_items_data.append(bill_item_data)

            elif "sku_id" in item and item["sku_id"]:
                # Retail product item
                sku_id = item["sku_id"]
                quantity = item.get("quantity", 1)

                # Validate product is sellable and in stock
                sku = inventory_service.validate_sellable_product(
                    sku_id=sku_id,
                    quantity=quantity,
                    raise_on_error=True
                )

                line_total = sku.retail_price * quantity
                subtotal += line_total

                # Calculate COGS for product
                cogs_amount = inventory_service.calculate_product_cogs(sku_id, quantity)

                bill_items_data.append({
                    "service_id": None,
                    "sku_id": sku.id,
                    "item_name": sku.name,
                    "base_price": sku.retail_price,
                    "quantity": quantity,
                    "line_total": line_total,
                    "cogs_amount": cogs_amount,
                    "staff_id": None,
                    "appointment_id": None,
                    "walkin_id": None,
                    "notes": item.get("notes")
                })
            else:
                raise ValueError("Each item must have either service_id or sku_id")
        discount_paise = discount_amount
        if discount_paise > subtotal:
            raise ValueError("Discount cannot exceed subtotal")

        amount_after_discount = subtotal - discount_paise
        tax_breakdown = TaxCalculator.calculate_tax_breakdown(amount_after_discount)
        total_amount = amount_after_discount # Tax already inclusive
        rounded_total, rounding_adjustment = TaxCalculator.round_to_rupee(total_amount)

        bill = Bill(
            id=str(ULID()),
            invoice_number=None,
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
            tip_amount=tip_amount,
            tip_staff_id=tip_staff_id,
            status=BillStatus.DRAFT,
            created_by=created_by_id
        )

        self.db.add(bill)
        self.db.flush() # Get bill.id without committing

        for item_data in bill_items_data:
            # Extract staff_contributions before creating bill_item
            staff_contributions_data = item_data.pop("staff_contributions", None)

            # Create bill item
            bill_item = BillItem(
                id=str(ULID()),
                bill_id=bill.id,
                **item_data
            )
            self.db.add(bill_item)
            self.db.flush()  # Get bill_item.id

            # Handle multi-staff contributions if present
            if staff_contributions_data:
                self._create_staff_contributions(
                    bill_item_id=bill_item.id,
                    line_total_paise=bill_item.line_total,
                    contributions_data=staff_contributions_data
                )

        # Link walk-ins to bill if session_id provided
        if session_id:
            walkins = self.db.query(WalkIn).filter(
                WalkIn.session_id == session_id,
                WalkIn.bill_id.is_(None)  # Only link walk-ins not already billed
            ).all()

            for walkin in walkins:
                walkin.bill_id = bill.id

        self.db.commit()
        self.db.refresh(bill)
        return bill

    def _create_staff_contributions(
        self,
        bill_item_id: str,
        line_total_paise: int,
        contributions_data: List[dict]
    ) -> None:
        """
        Create staff contribution records for a multi-staff service.

        Calculates contributions using ContributionCalculator and creates
        BillItemStaffContribution records.

        Args:
            bill_item_id: Bill item ID to link contributions to
            line_total_paise: Total amount to split among staff
            contributions_data: List of contribution dicts with staff info

        Raises:
            ValueError: If contribution calculation or validation fails
        """
        try:
            # Calculate contributions
            calculated_contributions = ContributionCalculator.calculate_contributions(
                line_total_paise=line_total_paise,
                contributions=contributions_data
            )

            # Validate results
            ContributionCalculator.validate_contributions(
                calculated_contributions,
                line_total_paise
            )

            # Create contribution records
            for contrib in calculated_contributions:
                contribution = BillItemStaffContribution(
                    id=str(ULID()),
                    bill_item_id=bill_item_id,
                    staff_id=contrib["staff_id"],
                    role_in_service=contrib["role_in_service"],
                    sequence_order=contrib["sequence_order"],
                    contribution_split_type=contrib.get("contribution_split_type"),
                    contribution_percent=contrib.get("contribution_percent"),
                    contribution_fixed=contrib.get("contribution_fixed"),
                    contribution_amount=contrib["contribution_amount"],
                    time_spent_minutes=contrib.get("time_spent_minutes"),
                    base_percent_component=contrib.get("base_percent_component"),
                    time_component=contrib.get("time_component"),
                    skill_component=contrib.get("skill_component"),
                    notes=contrib.get("notes")
                )
                self.db.add(contribution)

        except ContributionCalculationError as e:
            raise ValueError(f"Contribution calculation failed: {str(e)}")

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

        # Check for overpayment
        overpayment_amount = 0
        if new_total > bill.rounded_total + TOLERANCE:
            # If customer has pending balance, allow overpayment to reduce it
            if bill.customer_id:
                customer = self.db.query(Customer).filter(Customer.id == bill.customer_id).first()
                if customer and customer.pending_balance > 0:
                    overpayment_amount = new_total - bill.rounded_total
                    if overpayment_amount > customer.pending_balance:
                        raise ValueError(
                            f"Overpayment exceeds pending balance. "
                            f"Bill: Rs {bill.rounded_total/100:.2f}, "
                            f"Payment: Rs {new_total/100:.2f}, "
                            f"Pending Balance: Rs {customer.pending_balance/100:.2f}"
                        )
                else:
                    raise ValueError(
                        f"Payment would exceed bill total. "
                        f"Bill: Rs {bill.rounded_total/100:.2f}, "
                        f"Paid: Rs {new_total/100:.2f}"
                    )
            else:
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
            confirmed_at=datetime.now(IST),
            confirmed_by=confirmed_by_id
        )

        self.db.add(payment)

        # Apply overpayment to pending balance if any
        if overpayment_amount > 0 and bill.customer_id:
            customer = self.db.query(Customer).filter(Customer.id == bill.customer_id).first()
            if customer:
                previous_balance = customer.pending_balance
                customer.pending_balance -= overpayment_amount

                # Create pending payment collection record
                collection = PendingPaymentCollection(
                    id=str(ULID()),
                    customer_id=bill.customer_id,
                    amount=overpayment_amount,
                    payment_method=payment_method,
                    reference_number=reference_number,
                    notes=f"Overpayment on bill {bill.invoice_number or bill.id}",
                    bill_id=bill.id,
                    collected_by=confirmed_by_id,
                    collected_at=datetime.now(IST),
                    previous_balance=previous_balance,
                    new_balance=customer.pending_balance
                )
                self.db.add(collection)

                # Add note to payment
                if payment.notes:
                    payment.notes += f" | Applied Rs {overpayment_amount/100:.2f} to pending balance"
                else:
                    payment.notes = f"Applied Rs {overpayment_amount/100:.2f} to pending balance"

        if new_total >= bill.rounded_total:
            # Generate invoice number
            invoice_number = InvoiceNumberGenerator.generate(self.db)

            bill.invoice_number = invoice_number
            bill.status = BillStatus.POSTED
            bill.posted_at = datetime.now(IST)

            # Reduce stock for retail products
            inventory_service = InventoryService(self.db)
            for item in bill.items:
                if item.sku_id:  # Retail product
                    inventory_service.reduce_stock_for_sale(
                        sku_id=item.sku_id,
                        quantity=item.quantity,
                        bill_id=bill.id,
                        user_id=confirmed_by_id
                    )

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
            posted_at=datetime.now(IST),
            original_bill_id=original_bill.id,
            refund_reason=reason,
            refund_approved_by=refunded_by_id,
            refunded_at=datetime.now(IST),
            created_by=refunded_by_id
        )

        self.db.add(refund_bill)

        original_bill.status = BillStatus.REFUNDED
        original_bill.refunded_at = datetime.now(IST)
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

    def complete_bill(
        self,
        bill_id: str,
        completed_by_id: str,
        notes: Optional[str] = None
    ) -> Bill:
        """Complete a bill even with pending balance.

        Allows posting a bill that hasn't been fully paid yet. Useful for:
        - Free services (family members, complimentary services)
        - Credit customers (pay later)
        - Partial payments with pending balance

        Args:
            bill_id: Bill ID to complete.
            completed_by_id: User ID completing the bill.
            notes: Optional notes about the pending payment.

        Returns:
            Bill: Completed bill with invoice number.

        Raises:
            ValueError: If bill not found or not in draft status.
        """
        bill = self.get_bill(bill_id)

        if not bill:
            raise ValueError(f"Bill not found: {bill_id}")

        if bill.status != BillStatus.DRAFT:
            raise ValueError(
                f"Can only complete draft bills. Current status: {bill.status}"
            )

        # Generate invoice number
        invoice_number = InvoiceNumberGenerator.generate(self.db)
        bill.invoice_number = invoice_number
        bill.status = BillStatus.POSTED
        bill.posted_at = datetime.now(IST)

        # Add notes about pending balance if provided
        if notes:
            complete_note = f"[Bill completed with pending balance] {notes}"
            if bill.notes:
                bill.notes = f"{bill.notes}\n{complete_note}"
            else:
                bill.notes = complete_note

        # Reduce stock for retail products
        inventory_service = InventoryService(self.db)
        for item in bill.items:
            if item.sku_id:  # Retail product
                inventory_service.reduce_stock_for_sale(
                    sku_id=item.sku_id,
                    quantity=item.quantity,
                    bill_id=bill.id,
                    user_id=completed_by_id
                )

        # Update customer stats (use actual paid amount, not bill total)
        if bill.customer_id:
            # Get total paid
            total_paid = sum(payment.amount for payment in bill.payments)
            pending_amount = bill.rounded_total - total_paid

            # Only update customer stats with what they actually paid
            if total_paid > 0:
                self._update_customer_stats(bill.customer_id, total_paid, increment=True)

            # Update pending balance if there's an outstanding amount
            if pending_amount > 0:
                customer = self.db.query(Customer).filter(Customer.id == bill.customer_id).first()
                if customer:
                    customer.pending_balance += pending_amount

        self.db.commit()
        self.db.refresh(bill)

        return bill

    def void_bill(
        self,
        bill_id: str,
        voided_by_id: str,
        reason: Optional[str] = None
    ) -> Bill:
        """Void a draft bill.

            Voids a bill that hasn't been posted yet. Only draft bills
            can be voided. This is used for cancellations or mistakes.

            Args:
                bill_id: Bill ID to void.
                voided_by_id: User ID performing the void operation.
                reason: Optional reason for voiding.

            Returns:
                Bill: Voided bill.

            Raises:
                ValueError: If bill not found or not in draft status.
        """
        bill = self.get_bill(bill_id)

        if not bill:
            raise ValueError(f"Bill not found: {bill_id}")

        if bill.status != BillStatus.DRAFT:
            raise ValueError(
                f"Can only void draft bills. Current status: {bill.status}"
            )

        # Update bill status
        bill.status = BillStatus.VOID
        bill.updated_at = datetime.now(IST)

        # Store void reason in notes if provided
        if reason:
            void_note = f"[VOIDED by user {voided_by_id}] {reason}"
            if bill.notes:
                bill.notes = f"{bill.notes}\n{void_note}"
            else:
                bill.notes = void_note

        # Unlink any walk-ins associated with this bill
        # (so they can be rebilled if needed)
        walk_ins = self.db.query(WalkIn).filter(WalkIn.bill_id == bill_id).all()
        for walk_in in walk_ins:
            walk_in.bill_id = None

        self.db.commit()
        self.db.refresh(bill)

        return bill

    def get_bill(self, bill_id: str) -> Optional[Bill]:
        """Get bill by ID with relationships loaded.

            Args:
                bill_id: Bill ID to retrieve.

            Returns:
                Optional[Bill]: Bill if found, None otherwise.
        """

        return self.db.query(Bill).filter(Bill.id == bill_id).first()

    def update_payment(
        self,
        payment_id: str,
        payment_method: Optional[PaymentMethod] = None,
        amount: Optional[int] = None,  # in paise
        reference_number: Optional[str] = None,
        notes: Optional[str] = None,
        updated_by_id: str = None
    ) -> Payment:
        """Update an existing payment.

        Updates payment details and recalculates bill status if amount changes.
        Cannot update payments on refunded bills.

        Args:
            payment_id: ID of the payment to update.
            payment_method: Optional new payment method.
            amount: Optional new amount in paise.
            reference_number: Optional new transaction reference.
            notes: Optional new notes.
            updated_by_id: User making the update.

        Returns:
            Payment: Updated payment record.

        Raises:
            ValueError: If payment not found or bill is refunded.
        """
        payment = self.db.query(Payment).filter(Payment.id == payment_id).first()

        if not payment:
            raise ValueError("Payment not found")

        bill = self.db.query(Bill).filter(Bill.id == payment.bill_id).first()

        if not bill:
            raise ValueError("Associated bill not found")

        if bill.status == BillStatus.REFUNDED:
            raise ValueError("Cannot edit payments on refunded bills")

        # Store old amount for recalculation
        old_amount = payment.amount

        # Update fields if provided
        if payment_method is not None:
            payment.payment_method = payment_method
        if amount is not None:
            payment.amount = amount
        if reference_number is not None:
            payment.reference_number = reference_number
        if notes is not None:
            payment.notes = notes

        # If amount changed, recalculate bill status
        if amount is not None and amount != old_amount:
            # Calculate total payments
            all_payments = self.db.query(Payment).filter(
                Payment.bill_id == bill.id
            ).all()
            total_payments = sum(p.amount for p in all_payments)

            TOLERANCE = 1000  # Rs 10 tolerance

            # Check if new total would exceed bill amount
            if total_payments > bill.rounded_total + TOLERANCE:
                raise ValueError(
                    f"Updated payment would exceed bill total. "
                    f"Bill: Rs {bill.rounded_total/100:.2f}, "
                    f"Total Payments: Rs {total_payments/100:.2f}"
                )

            # Update bill status based on payment total
            if total_payments >= bill.rounded_total:
                # If was draft and now fully paid, post it
                if bill.status == BillStatus.DRAFT:
                    # Generate invoice number
                    invoice_number = InvoiceNumberGenerator.generate(self.db)
                    bill.invoice_number = invoice_number
                    bill.status = BillStatus.POSTED
                    bill.posted_at = datetime.now(IST)

                    # Reduce stock for retail products
                    inventory_service = InventoryService(self.db)
                    for item in bill.items:
                        if item.sku_id:  # Retail product
                            inventory_service.reduce_stock_for_sale(
                                sku_id=item.sku_id,
                                quantity=item.quantity,
                                bill_id=bill.id,
                                user_id=updated_by_id
                            )

                    # Update customer stats
                    if bill.customer_id:
                        self._update_customer_stats(bill.customer_id, bill.rounded_total, increment=True)

            elif total_payments < bill.rounded_total:
                # If was posted and now underpaid, revert to draft
                if bill.status == BillStatus.POSTED:
                    # Note: We're not reversing stock or customer stats here
                    # This is a business decision - once posted, stock reduction is permanent
                    # Only the bill status changes back to draft
                    bill.status = BillStatus.DRAFT
                    bill.posted_at = None
                    # Keep invoice_number as audit trail

        self.db.commit()
        self.db.refresh(payment)
        return payment

    def delete_payment(
        self,
        payment_id: str,
        deleted_by_id: str = None
    ) -> Bill:
        """Delete a payment and recalculate bill status.

        Removes payment and updates bill status if necessary.
        Cannot delete payments from refunded bills.

        Args:
            payment_id: ID of the payment to delete.
            deleted_by_id: User deleting the payment.

        Returns:
            Bill: Updated bill after payment deletion.

        Raises:
            ValueError: If payment not found or bill is refunded.
        """
        payment = self.db.query(Payment).filter(Payment.id == payment_id).first()

        if not payment:
            raise ValueError("Payment not found")

        bill = self.db.query(Bill).filter(Bill.id == payment.bill_id).first()

        if not bill:
            raise ValueError("Associated bill not found")

        if bill.status == BillStatus.REFUNDED:
            raise ValueError("Cannot delete payments from refunded bills")

        # Store payment amount before deletion
        payment_amount = payment.amount

        # Delete the payment
        self.db.delete(payment)

        # Recalculate total payments
        remaining_payments = self.db.query(Payment).filter(
            Payment.bill_id == bill.id
        ).all()
        total_payments = sum(p.amount for p in remaining_payments)

        # Update bill status if now underpaid
        if total_payments < bill.rounded_total:
            if bill.status == BillStatus.POSTED:
                # Revert to draft (stock and customer stats remain as-is)
                bill.status = BillStatus.DRAFT
                bill.posted_at = None
                # Keep invoice_number as audit trail

        self.db.commit()
        self.db.refresh(bill)
        return bill

    def _calculate_service_cogs(self, service_id: str, quantity: int) -> int:
        """Calculate COGS for a service based on material usage.

            Args:
                service_id: Service ID
                quantity: Number of services performed

            Returns:
                COGS amount in paise
        """
        # Get material usage for this service
        material_usage = self.db.query(ServiceMaterialUsage).filter(
            ServiceMaterialUsage.service_id == service_id
        ).all()

        if not material_usage:
            return 0

        total_cogs = 0
        for usage in material_usage:
            # Get SKU to get cost per unit
            sku = self.db.query(SKU).filter(SKU.id == usage.sku_id).first()
            if sku:
                material_quantity = float(usage.quantity_per_service) * quantity
                material_cost = int(sku.avg_cost_per_unit * material_quantity)
                total_cogs += material_cost

        return total_cogs

    def collect_pending_payment(
        self,
        customer_id: str,
        amount: int,  # in paise
        payment_method: PaymentMethod,
        collected_by_id: str,
        reference_number: Optional[str] = None,
        notes: Optional[str] = None
    ) -> PendingPaymentCollection:
        """Collect pending payment from customer without creating a bill.

        Args:
            customer_id: Customer ID who is paying.
            amount: Payment amount in paise.
            payment_method: Payment method used.
            collected_by_id: User ID collecting the payment.
            reference_number: Optional transaction reference.
            notes: Optional payment notes.

        Returns:
            PendingPaymentCollection: Created payment collection record.

        Raises:
            ValueError: If customer not found or amount exceeds pending balance.
        """
        customer = self.db.query(Customer).filter(Customer.id == customer_id).first()

        if not customer:
            raise ValueError("Customer not found")

        if customer.pending_balance <= 0:
            raise ValueError("Customer has no pending balance")

        if amount > customer.pending_balance:
            raise ValueError(
                f"Payment amount exceeds pending balance. "
                f"Pending: Rs {customer.pending_balance/100:.2f}, "
                f"Payment: Rs {amount/100:.2f}"
            )

        # Reduce pending balance
        previous_balance = customer.pending_balance
        customer.pending_balance -= amount

        # Create pending payment collection record
        collection = PendingPaymentCollection(
            id=str(ULID()),
            customer_id=customer_id,
            amount=amount,
            payment_method=payment_method,
            reference_number=reference_number,
            notes=notes,
            bill_id=None,  # Direct collection, not linked to specific bill
            collected_by=collected_by_id,
            collected_at=datetime.now(IST),
            previous_balance=previous_balance,
            new_balance=customer.pending_balance
        )

        self.db.add(collection)
        self.db.commit()
        self.db.refresh(collection)

        return collection

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
            customer.last_visit_at = datetime.now(IST)

        else:
            customer.total_spent = max(0, customer.total_spent - amount) # To not go negative
        







