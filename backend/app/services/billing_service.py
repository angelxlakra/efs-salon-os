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
from app.models.service import Service, ServiceMaterialUsage
from app.models.inventory import SKU
from app.models.appointment import WalkIn
from app.services.invoice_generator import InvoiceNumberGenerator
from app.services.tax_calculator import TaxCalculator
from app.services.inventory_service import InventoryService


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

        if not customer_id and (not customer_name or not customer_phone):
            raise ValueError("Customer name and phone required if no customer_id")

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

                bill_items_data.append({
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
                    "notes": item.get("notes")
                })

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
            bill_item = BillItem(
                id=str(ULID()),
                bill_id=bill.id,
                **item_data
            )
            self.db.add(bill_item)

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
        bill.updated_at = datetime.utcnow()

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
        







