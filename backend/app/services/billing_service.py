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

from datetime import datetime, date
from typing import List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session
from ulid import ULID

from app.models.billing import (
    Bill, BillClass, BillItem, BillItemType, BillStatus, BillType,
    Payment, PaymentMethod, BillItemStaffContribution, TaxMode,
)
from app.models.customer import Customer
from app.models.pending_payment import PendingPaymentCollection
from app.utils import IST
from app.models.service import Service, ServiceMaterialUsage
from app.models.inventory import SKU
from app.models.appointment import WalkIn
from app.services.invoice_generator import InvoiceNumberGenerator
from app.services.tax_calculator import TaxCalculator
from app.services.discount_allocator import allocate_discount
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

    # ------------------------------------------------------------------
    # GST mode (split billing scheme, see docs/superpowers/plans/
    # 2026-06-11-gst-split-billing.md)
    # ------------------------------------------------------------------

    # Whole-percent GST rates per line kind (owner-confirmed)
    SERVICE_GST_RATE = 5    # exclusive: added on top of discounted base
    PRODUCT_GST_RATE = 18   # inclusive: extracted from discounted MRP

    @staticmethod
    def _effective_date(settings) -> Optional[date]:
        """GST effective date as a date.

        Settings can come from the Redis cache, where to_dict() serialized the
        date to an ISO string and SalonSettings(**cached) rebuilt it as a str.
        Normalize so date comparisons never raise.
        """
        eff = settings.gst_effective_from
        if isinstance(eff, str):
            return date.fromisoformat(eff) if eff else None
        return eff

    def _split_billing_active(self) -> bool:
        """True when the split-billing scheme is on (retail products on their own
        18%-inclusive bill, services on theirs).

        Gated on gst_effective_from being set — the "scheme start" — NOT on the
        GST-registered toggle: products are always billed separately at 18%
        inclusive once the salon opts in. The toggle only controls whether
        SERVICES carry 5% GST (see _services_taxed)."""
        from app.services.settings_service import SettingsService

        settings = SettingsService.get_or_create_settings(self.db)
        eff = self._effective_date(settings)
        if not eff:
            return False
        return datetime.now(IST).date() >= eff

    def _services_taxed(self) -> bool:
        """True when services carry 5% GST (salon is GST-registered)."""
        from app.services.settings_service import SettingsService

        settings = SettingsService.get_or_create_settings(self.db)
        return bool(settings.gst_registered)

    def _split_billing_for_bill(self, bill: Bill) -> bool:
        """Whether a specific bill uses the split-billing scheme.

        Bound to the BILL, not wall-clock: a bill created before the scheme's
        effective date stays on legacy inclusive-18% math forever, so editing an
        old bill never retro-converts it. New bills (created on/after the
        effective date) get the scheme. An already-classified service/product
        bill always stays in the scheme.
        """
        if bill.bill_class in (BillClass.SERVICE, BillClass.PRODUCT):
            return True
        from app.services.settings_service import SettingsService

        settings = SettingsService.get_or_create_settings(self.db)
        eff = self._effective_date(settings)
        if not eff:
            return False
        bill_date = (
            bill.created_at.astimezone(IST).date()
            if bill.created_at else datetime.now(IST).date()
        )
        return bill_date >= eff

    def _line_tax_params(self, item: BillItem) -> tuple[int, str]:
        """(rate_percent, tax_mode) for a bill line in the split-billing scheme.

        - Retail products: 18% inclusive, always (sold at MRP).
        - Services: 5% exclusive when the salon is GST-registered, otherwise no
          GST (menu price only).
        - Package sale/redemption lines: no GST (redemptions have zero realized
          value; package sales keep current treatment until revisited).

        Classified by FK first (historic rows predate item_type=PRODUCT being
        set on retail lines), then by item_type.
        """
        if item.item_type in (
            BillItemType.PACKAGE_SALE_LINE, BillItemType.PACKAGE_REDEMPTION
        ):
            return 0, TaxMode.NONE.value
        if item.sku_id:
            return BillingService.PRODUCT_GST_RATE, TaxMode.INCLUSIVE.value
        if item.service_id:
            if self._services_taxed():
                return BillingService.SERVICE_GST_RATE, TaxMode.EXCLUSIVE.value
            return 0, TaxMode.NONE.value
        return 0, TaxMode.NONE.value

    def _recalculate_bill_tax(self, bill: Bill) -> None:
        """Recompute per-line tax and bill totals from bill.items.

        GST mode: discount is allocated proportionally across lines first,
        then each line is taxed by its own rate/mode (floor rounding) and the
        bill totals are sums of lines; payable floors to the whole rupee.

        Legacy mode: original bill-level 18%-inclusive extraction with
        ROUND_HALF_UP, so pre-registration bills stay reproducible.

        Caller must have flushed items and set bill.subtotal/discount_amount.
        """
        items = list(bill.items)
        discount = bill.discount_amount or 0

        if not self._split_billing_for_bill(bill):
            amount_after_discount = bill.subtotal - discount
            breakdown = TaxCalculator.calculate_tax_breakdown(amount_after_discount)
            bill.tax_amount = breakdown["total_tax"]
            bill.cgst_amount = breakdown["cgst"]
            bill.sgst_amount = breakdown["sgst"]
            bill.total_amount = amount_after_discount  # prices tax-inclusive
            bill.rounded_total, bill.rounding_adjustment = (
                TaxCalculator.round_to_rupee(amount_after_discount)
            )
            return

        # Discounts apply to SERVICES only — retail products are never
        # discounted (sold at MRP). Products contribute 0 to the allocation,
        # so the whole discount lands on the service lines.
        discountable = [0 if i.sku_id else i.line_total for i in items]
        line_discounts = allocate_discount(discountable, discount)

        cgst = sgst = total = 0
        for item, line_discount in zip(items, line_discounts):
            rate, mode = self._line_tax_params(item)
            tax = TaxCalculator.calculate_line_tax(
                item.line_total - line_discount, rate, mode
            )
            item.tax_rate = rate
            item.tax_mode = mode
            item.taxable_value = tax["taxable_value"]
            item.cgst_amount = tax["cgst"]
            item.sgst_amount = tax["sgst"]
            cgst += tax["cgst"]
            sgst += tax["sgst"]
            total += tax["gross"]

        bill.cgst_amount = cgst
        bill.sgst_amount = sgst
        bill.tax_amount = cgst + sgst
        bill.total_amount = total
        bill.rounded_total, bill.rounding_adjustment = (
            TaxCalculator.round_down_to_rupee(total)
        )

        # Single-class carts get their GST rate-class (drives SRV/PRD invoice
        # series). Mixed carts split into two bills at checkout (Phase 5);
        # until then they remain MIXED_LEGACY. Product lines are identified
        # by sku_id; everything else (services, package lines) is the
        # service-side of a checkout.
        has_product = any(i.sku_id for i in items)
        has_service_side = any(not i.sku_id for i in items)
        if items and has_product and not has_service_side:
            bill.bill_class = BillClass.PRODUCT
        elif items and has_service_side and not has_product:
            bill.bill_class = BillClass.SERVICE

    def _generate_invoice_number(self, bill: Bill) -> str:
        """Pick the invoice series for a bill (SRV/PRD in GST mode, else SAL)."""
        from app.services.settings_service import SettingsService

        if bill.bill_class in (BillClass.SERVICE, BillClass.PRODUCT):
            settings = SettingsService.get_or_create_settings(self.db)
            if bill.bill_class == BillClass.SERVICE:
                return InvoiceNumberGenerator.generate(
                    self.db,
                    prefix=settings.invoice_prefix_service,
                    lock_id=InvoiceNumberGenerator.SERVICE_LOCK_ID,
                )
            return InvoiceNumberGenerator.generate(
                self.db,
                prefix=settings.invoice_prefix_product,
                lock_id=InvoiceNumberGenerator.PRODUCT_LOCK_ID,
            )
        return InvoiceNumberGenerator.generate(self.db)

    def create_bill_group(self, items: List[dict], created_by_id: str, **kwargs) -> List[Bill]:
        """Create a checkout, splitting mixed carts into service + product bills.

        GST mode with both service-side and product lines → two DRAFT bills
        sharing a bill_group_id (services tax at 5% exclusive, products at 18%
        MRP-inclusive, each with its own invoice series at posting). Single-
        class carts and legacy mode → one bill, exactly like create_bill.

        Returns:
            List of 1 or 2 DRAFT bills.
        """
        # Single transaction: create_bill defers its commit so a split failure
        # rolls the whole checkout back (no orphaned, mis-taxed single bill).
        try:
            bill = self.create_bill(
                items=items, created_by_id=created_by_id, commit=False, **kwargs
            )
            sibling = self._split_bill_if_mixed(bill)
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
        self.db.refresh(bill)
        if sibling is None:
            return [bill]
        self.db.refresh(sibling)
        return [bill, sibling]

    def _split_bill_if_mixed(self, bill: Bill) -> Optional[Bill]:
        """Move product lines off a mixed DRAFT bill onto a sibling product bill.

        The original bill keeps the service-side lines (services + package
        lines) and becomes the SERVICE bill; both share bill_group_id. The
        bill-level discount is allocated proportionally across ALL lines first,
        then each side keeps its share, so the customer's total discount is
        preserved exactly. Returns the new product bill, or None if no split
        is needed (single-class cart or GST mode off).
        """
        if not self._split_billing_for_bill(bill) or bill.status != BillStatus.DRAFT:
            return None

        items = list(bill.items)
        product_items = [i for i in items if i.sku_id]
        if not product_items or len(product_items) == len(items):
            return None

        # Discounts apply to services only, so the entire discount stays on the
        # service bill; the product bill is never discounted.
        prd_discount = 0
        svc_discount = bill.discount_amount or 0

        group_id = bill.id
        bill.bill_group_id = group_id

        product_bill = Bill(
            id=str(ULID()),
            invoice_number=None,
            customer_id=bill.customer_id,
            customer_name=bill.customer_name,
            customer_phone=bill.customer_phone,
            subtotal=sum(i.line_total for i in product_items),
            discount_amount=prd_discount,
            discount_reason=bill.discount_reason if prd_discount else None,
            discount_approved_by=bill.discount_approved_by if prd_discount else None,
            tax_amount=0,
            cgst_amount=0,
            sgst_amount=0,
            total_amount=0,
            rounded_total=0,
            rounding_adjustment=0,
            tip_amount=0,  # tips belong to staff → stay on the service bill
            status=BillStatus.DRAFT,
            created_by=bill.created_by,
            bill_class=BillClass.PRODUCT,
            bill_group_id=group_id,
        )
        self.db.add(product_bill)
        self.db.flush()

        for item in product_items:
            item.bill_id = product_bill.id
        self.db.flush()
        # bill.items was loaded before the move; reload so the recompute
        # below only sees the service-side lines
        self.db.expire(bill, ["items"])

        bill.subtotal = sum(i.line_total for i in items if not i.sku_id)
        bill.discount_amount = svc_discount
        self._recalculate_bill_tax(bill)
        self._recalculate_bill_tax(product_bill)
        self.db.flush()
        return product_bill

    def pay_bill_group(
        self,
        bill_group_id: str,
        payments: List[dict],  # [{"payment_method", "amount" (rupees), ...}]
        confirmed_by_id: str,
    ) -> List[Payment]:
        """Settle every DRAFT bill in a checkout group with one customer tender.

        The tendered total must equal the group total exactly (totals are
        already floored to whole rupees, so the customer pays a round figure).
        Each tender is split across the bills service-bill-first; every bill
        gets its own Payment rows tied together by payment_group_id. All bills
        post atomically — invoice numbers, stock reduction, package sales and
        customer stats happen in ONE transaction.

        Raises:
            ValueError: group not found / not draft / tender != group total.
        """
        # Lock the group's draft bills FOR UPDATE so two terminals can't both
        # pass the draft check and double-post / double-reduce stock.
        bills = (
            self.db.query(Bill)
            .filter(
                Bill.bill_group_id == bill_group_id,
                Bill.status == BillStatus.DRAFT,
            )
            .with_for_update()
            .all()
        )
        if not bills:
            raise ValueError(f"No draft bills found for group {bill_group_id}")

        group_total = sum(b.rounded_total for b in bills)
        tendered = sum(p["amount"] for p in payments) * 100
        if tendered < group_total:
            raise ValueError(
                f"Group checkout requires full payment. "
                f"Due: Rs {group_total/100:.2f}, tendered: Rs {tendered/100:.2f}"
            )
        if tendered > group_total:
            raise ValueError(
                f"Tendered amount exceeds group total. "
                f"Due: Rs {group_total/100:.2f}, tendered: Rs {tendered/100:.2f}"
            )

        # Service bill first: tips/pending conventions live there, and the
        # allocation must be deterministic for reconciliation.
        bills_sorted = sorted(
            bills, key=lambda b: 0 if b.bill_class == BillClass.SERVICE else 1
        )
        remaining = {b.id: b.rounded_total for b in bills_sorted}
        payment_group_id = str(ULID())
        now = datetime.now(IST)
        created: List[Payment] = []

        bill_index = 0
        for tender in payments:
            amount_paise = tender["amount"] * 100
            while amount_paise > 0 and bill_index < len(bills_sorted):
                target = bills_sorted[bill_index]
                take = min(amount_paise, remaining[target.id])
                if take > 0:
                    payment = Payment(
                        id=str(ULID()),
                        bill_id=target.id,
                        payment_group_id=payment_group_id,
                        payment_method=tender["payment_method"],
                        amount=take,
                        confirmed_at=now,
                        confirmed_by=confirmed_by_id,
                        reference_number=tender.get("reference_number"),
                        notes=tender.get("notes"),
                    )
                    self.db.add(payment)
                    created.append(payment)
                    remaining[target.id] -= take
                    amount_paise -= take
                if remaining[target.id] == 0:
                    bill_index += 1

        # Defensive: never post a bill that the allocation left short. The
        # equality guards above should make this impossible, but a POSTED bill
        # with an unpaid balance is silent money loss, so assert it.
        if any(r != 0 for r in remaining.values()):
            raise ValueError("Payment allocation did not fully cover every bill in the group")

        # Post every bill in the group (one transaction — all or nothing)
        inventory_service = InventoryService(self.db)
        for bill in bills_sorted:
            if not bill.invoice_number:
                bill.invoice_number = self._generate_invoice_number(bill)
            bill.status = BillStatus.POSTED
            bill.posted_at = now

            for item in bill.items:
                if item.sku_id:
                    inventory_service.reduce_stock_for_sale(
                        sku_id=item.sku_id,
                        quantity=item.quantity,
                        bill_id=bill.id,
                        user_id=confirmed_by_id,
                    )

            self._create_package_sales_for_bill(bill, confirmed_by_id)

            if bill.customer_id:
                self._update_customer_stats(
                    bill.customer_id, bill.rounded_total, increment=True
                )

        self.db.commit()
        for payment in created:
            self.db.refresh(payment)
        return created

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
        commit: bool = True,  # set False to keep the txn open (group checkout)
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
            # Package-sale line: one line sold at the package's price; the
            # PackageSale is created at settlement (see _create_package_sales).
            if item.get("package_definition_id"):
                from app.models.package import PackageDefinition
                pkg = self.db.get(PackageDefinition, item["package_definition_id"])
                if not pkg or pkg.deleted_at:
                    raise ValueError(f"Package not found: {item['package_definition_id']}")
                price = item.get("unit_price")
                if price is None:
                    price = pkg.final_price_paise
                subtotal += price
                bill_items_data.append({
                    "service_id": None,
                    "sku_id": None,
                    "item_name": pkg.name,
                    "base_price": price,
                    "quantity": 1,
                    "line_total": price,
                    "cogs_amount": 0,
                    "item_type": BillItemType.PACKAGE_SALE_LINE,
                    "package_definition_id": pkg.id,
                    "package_locked_choices": item.get("locked_choices"),
                    "staff_id": item.get("staff_id"),
                    "appointment_id": None,
                    "walkin_id": None,
                    "notes": item.get("notes"),
                })
                continue

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
                    "item_type": BillItemType.SERVICE,
                    "staff_id": item.get("staff_id"),
                    "appointment_id": item.get("appointment_id"),
                    "walkin_id": item.get("walkin_id"),
                    "notes": item.get("notes"),
                    "staff_contributions": item.get("staff_contributions"),  # Multi-staff data
                    # Live-in-cart redemption: the cart resolved an eligible package
                    # for this line; apply it after the bill item exists.
                    "_redeem_package_sale_id": item.get("package_sale_id"),
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
                    "item_type": BillItemType.PRODUCT,
                    "staff_id": None,
                    "appointment_id": None,
                    "walkin_id": None,
                    "notes": item.get("notes")
                })
            else:
                raise ValueError("Each item must have either service_id or sku_id")
        discount_paise = discount_amount
        # In GST mode the discount applies to services only, so it cannot
        # exceed the services subtotal (retail products are sold at MRP).
        if self._split_billing_active():
            services_subtotal = sum(
                d["line_total"] for d in bill_items_data if not d.get("sku_id")
            )
            if discount_paise > services_subtotal:
                raise ValueError(
                    "Discount cannot exceed the services subtotal "
                    "(retail products are not discountable)"
                )
        elif discount_paise > subtotal:
            raise ValueError("Discount cannot exceed subtotal")

        # Totals are placeholders here; _recalculate_bill_tax() computes the
        # real figures once items are flushed (per-line tax needs the items).
        bill = Bill(
            id=str(ULID()),
            invoice_number=None,
            customer_id=customer_id,
            customer_name=customer_name,
            customer_phone=customer_phone,
            subtotal=subtotal,
            discount_amount=discount_paise,
            discount_reason=discount_reason,
            tax_amount=0,
            cgst_amount=0,
            sgst_amount=0,
            total_amount=subtotal - discount_paise,
            rounded_total=subtotal - discount_paise,
            rounding_adjustment=0,
            tip_amount=tip_amount,
            tip_staff_id=tip_staff_id,
            status=BillStatus.DRAFT,
            created_by=created_by_id
        )

        self.db.add(bill)
        self.db.flush() # Get bill.id without committing

        redemption_intents: list[tuple[str, str]] = []  # (bill_item_id, package_sale_id)
        for item_data in bill_items_data:
            # Extract non-column extras before creating bill_item
            staff_contributions_data = item_data.pop("staff_contributions", None)
            redeem_sale_id = item_data.pop("_redeem_package_sale_id", None)

            # Create bill item
            bill_item = BillItem(
                id=str(ULID()),
                bill_id=bill.id,
                **item_data
            )
            self.db.add(bill_item)
            self.db.flush()  # Get bill_item.id

            if redeem_sale_id:
                redemption_intents.append((bill_item.id, redeem_sale_id))

            # Handle multi-staff contributions if present
            if staff_contributions_data:
                self._create_staff_contributions(
                    bill_item_id=bill_item.id,
                    line_total_paise=bill_item.line_total,
                    contributions_data=staff_contributions_data
                )

        # Apply cart-resolved package redemptions: converts each flagged service
        # line to PACKAGE_REDEMPTION, decrements the package, and books an
        # internal payment that covers the line (no cash due for it).
        if redemption_intents and customer_id:
            from app.services import package_redemption_service
            for bill_item_id, sale_id in redemption_intents:
                package_redemption_service.apply_redemption(
                    db=self.db,
                    package_sale_id=sale_id,
                    bill_item_id=bill_item_id,
                    redeemed_for_customer_id=customer_id,
                    user_id=created_by_id,
                )
            self.db.flush()

        # Compute taxes now that all items exist (per-line in GST mode)
        self._recalculate_bill_tax(bill)

        # Link walk-ins to bill if session_id provided
        if session_id:
            walkins = self.db.query(WalkIn).filter(
                WalkIn.session_id == session_id,
                WalkIn.bill_id.is_(None)  # Only link walk-ins not already billed
            ).all()

            for walkin in walkins:
                walkin.bill_id = bill.id

        if not commit:
            self.db.flush()
            return bill

        self.db.commit()
        self.db.refresh(bill)
        return bill

    def add_bill_item(
        self,
        bill_id: str,
        service_id: str,
        quantity: int = 1,
        staff_id: Optional[str] = None,
        appointment_id: Optional[str] = None,
        walkin_id: Optional[str] = None,
        notes: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> dict:
        """Add a single service item to an existing DRAFT bill.

        After creating the BillItem, recalculates bill totals and runs a
        package eligibility check. If exactly one eligible package with
        auto_apply=True, applies the redemption automatically.

        Returns:
            dict with keys:
              - bill_item: the new BillItem ORM object
              - auto_applied_package_sale_id: str or None
              - eligible_packages: list of sale IDs (when 2+ eligible, no auto-apply)

        Raises:
            ValueError: Bill not found, bill not DRAFT, service not found.
        """
        bill = self.db.get(Bill, bill_id)
        if not bill:
            raise ValueError(f"Bill {bill_id} not found")
        if bill.status != BillStatus.DRAFT:
            raise ValueError("Can only add items to DRAFT bills")

        service = self.db.query(Service).filter(
            Service.id == service_id,
            Service.is_active,  # noqa: E712
            Service.deleted_at.is_(None),
        ).first()
        if not service:
            raise ValueError(f"Service {service_id} not found or inactive")

        line_total = service.base_price * quantity
        cogs_amount = self._calculate_service_cogs(service.id, quantity)

        bill_item = BillItem(
            id=str(ULID()),  # explicit ULID, consistent with create_bill
            bill_id=bill_id,
            service_id=service.id,
            item_name=service.name,
            base_price=service.base_price,
            quantity=quantity,
            line_total=line_total,
            cogs_amount=cogs_amount,
            staff_id=staff_id,
            appointment_id=appointment_id,
            walkin_id=walkin_id,
            notes=notes,
            item_type=BillItemType.SERVICE,
        )
        self.db.add(bill_item)
        self.db.flush()  # Get bill_item.id

        # Recalculate bill totals (per-line GST when active)
        bill.subtotal = bill.subtotal + line_total
        self._recalculate_bill_tax(bill)
        self.db.flush()

        # Package eligibility check
        auto_applied_package_sale_id = None
        eligible_package_ids: list[str] = []

        if bill.customer_id and service.id:
            from app.services.package_eligibility import find_eligible_packages
            from app.services import package_redemption_service

            eligible = find_eligible_packages(bill.customer_id, service.id, self.db)

            if len(eligible) == 1 and eligible[0].definition and eligible[0].definition.auto_apply:
                package_redemption_service.apply_redemption(
                    db=self.db,
                    package_sale_id=eligible[0].id,
                    bill_item_id=bill_item.id,
                    redeemed_for_customer_id=bill.customer_id,
                    user_id=user_id or bill.created_by,
                )
                auto_applied_package_sale_id = eligible[0].id
            elif len(eligible) >= 2:
                eligible_package_ids = [s.id for s in eligible]

        self.db.flush()
        self.db.refresh(bill_item)   # ensure item_type reflects apply_redemption mutations
        self.db.commit()

        return {
            "bill_item": bill_item,
            "auto_applied_package_sale_id": auto_applied_package_sale_id,
            "eligible_packages": eligible_package_ids,
        }

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
            # Preserve existing invoice number if bill was previously posted and
            # reverted to draft via payment deletion — don't generate a duplicate.
            if not bill.invoice_number:
                bill.invoice_number = self._generate_invoice_number(bill)
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

            # Create PackageSale rows for any package_sale_line items on this bill
            self._create_package_sales_for_bill(bill, confirmed_by_id)

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
            invoice_number=None,  # assigned below: credit note uses the
                                  # original bill's series (SRV/PRD/SAL)
            bill_type=BillType.CREDIT_NOTE,  # required by
                                  # ck_bill_credit_note_has_original
            bill_class=original_bill.bill_class,
            bill_group_id=original_bill.bill_group_id,
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

        refund_bill.invoice_number = self._generate_invoice_number(refund_bill)
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

        # Walk-in customers (no phone) cannot have pending balance
        total_paid = sum(payment.amount for payment in bill.payments)
        if not bill.customer_phone and bill.rounded_total > 0 and total_paid < bill.rounded_total:
            raise ValueError(
                "Walk-in customers cannot have pending balance. "
                "Please assign a customer profile or collect full payment."
            )

        # Generate invoice number
        bill.invoice_number = self._generate_invoice_number(bill)
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

        # Create PackageSale rows for any package_sale_line items on this bill
        self._create_package_sales_for_bill(bill, completed_by_id)

        # Update customer stats (use actual paid amount, not bill total)
        if bill.customer_id:
            # Get total paid
            total_paid = sum(payment.amount for payment in bill.payments)
            pending_amount = bill.rounded_total - total_paid

            # Always count the visit and update last_visit_at; total_spent reflects
            # only the amount actually received (may be 0 for full-pending bills).
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
        reason: Optional[str] = None,
        allow_posted: bool = False,
    ) -> Bill:
        """Void a bill.

            Voids a draft bill, or — when allow_posted=True (owner only) — a
            posted bill. Used for cancellations or billing mistakes.

            When a posted bill is voided the customer's stats are reversed so
            that total_spent and total_visits remain accurate.

            Args:
                bill_id: Bill ID to void.
                voided_by_id: User ID performing the void operation.
                reason: Optional reason for voiding.
                allow_posted: If True, also allows voiding POSTED bills.
                    Should only be set to True when the caller is an Owner.

            Returns:
                Bill: Voided bill.

            Raises:
                ValueError: If bill not found or status not voidable.
        """
        bill = self.get_bill(bill_id)

        if not bill:
            raise ValueError(f"Bill not found: {bill_id}")

        if bill.status == BillStatus.DRAFT:
            # Delete any partial payment records — the bill was never finalized,
            # so these payments are orphaned and should be treated as if they
            # never occurred (cash must be returned to the customer manually).
            self.db.query(Payment).filter(Payment.bill_id == bill_id).delete()
        elif bill.status == BillStatus.POSTED and allow_posted:
            # Reverse customer stats that were recorded on posting
            if bill.customer_id:
                self._update_customer_stats(
                    bill.customer_id, bill.rounded_total, increment=False
                )
        else:
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

    def apply_discount(
        self,
        bill_id: str,
        discount_amount: int,  # paise
        discount_reason: Optional[str] = None,
        applied_by_id: Optional[str] = None,
    ) -> Bill:
        """Update the discount on a draft bill and recalculate totals.

            Only works on DRAFT bills. If the revised total is now fully covered
            by existing partial payments, the bill is automatically posted.

            Args:
                bill_id: Bill ID to update.
                discount_amount: New discount in paise.
                discount_reason: Optional reason for the discount.
                applied_by_id: User ID applying the discount.

            Returns:
                Bill: Updated bill (may transition to POSTED if fully paid).

            Raises:
                ValueError: If bill not found, not draft, or discount exceeds subtotal.
        """
        bill = self.get_bill(bill_id)
        if not bill:
            raise ValueError(f"Bill not found: {bill_id}")
        if bill.status != BillStatus.DRAFT:
            raise ValueError("Can only edit discount on draft bills")
        # Services-only discount cap in GST mode (products sold at MRP). After a
        # mixed cart is split, a product bill has no service lines, so any
        # discount on it is rejected.
        if self._split_billing_for_bill(bill):
            services_subtotal = sum(i.line_total for i in bill.items if not i.sku_id)
            if discount_amount > services_subtotal:
                raise ValueError(
                    "Discount cannot exceed the services subtotal "
                    "(retail products are not discountable)"
                )
        elif discount_amount > bill.subtotal:
            raise ValueError("Discount cannot exceed subtotal")

        # Recalculate all totals from scratch using the new discount
        # (per-line GST when active; legacy inclusive extraction otherwise)
        bill.discount_amount = discount_amount
        bill.discount_reason = discount_reason
        bill.discount_approved_by = applied_by_id
        self._recalculate_bill_tax(bill)
        bill.updated_at = datetime.now(IST)

        # Auto-post if partial payments now fully cover the revised total
        existing_payments = self.db.query(Payment).filter(
            Payment.bill_id == bill_id
        ).all()
        total_paid = sum(p.amount for p in existing_payments)
        if existing_payments and total_paid >= bill.rounded_total:
            bill.status = BillStatus.POSTED
            bill.posted_at = datetime.now(IST)
            # Preserve existing invoice number (bill may have been posted before
            # and reverted to draft via payment deletion — don't generate a duplicate)
            if not bill.invoice_number:
                bill.invoice_number = self._generate_invoice_number(bill)
            if bill.customer_id:
                self._update_customer_stats(
                    bill.customer_id, bill.rounded_total, increment=True
                )

        self.db.commit()
        self.db.refresh(bill)
        return bill

    def write_off_pending_discount(
        self,
        bill_id: str,
        write_off_amount: int,    # paise — amount to forgive (1 to pending balance)
        reason: str,              # required
        approved_by_id: str,
    ) -> Bill:
        """Write off (forgive) some or all pending balance on a posted bill.

            Records the forgiven amount in write_off_amount, write_off_at,
            write_off_reason, and write_off_approved_by WITHOUT altering
            discount_amount, rounded_total, total_amount, tax_amount,
            cgst_amount, sgst_amount, or rounding_adjustment.

            Multiple calls accumulate: each call adds write_off_amount to the
            existing bill.write_off_amount, and the remaining pending is
            computed as:

                pending = rounded_total - sum(payments) - existing_write_off_amount

            Args:
                bill_id: Bill ID to update.
                write_off_amount: Paise to forgive this call (1 to remaining pending).
                reason: Required reason for the write-off.
                approved_by_id: User ID of the approving owner.

            Returns:
                Bill: Updated bill with write_off fields set.

            Raises:
                ValueError: If bill not found, not posted, no remaining pending
                            balance, or write_off_amount out of [1, remaining].
        """
        bill = self.get_bill(bill_id)
        if not bill:
            raise ValueError(f"Bill not found: {bill_id}")
        if bill.status != BillStatus.POSTED:
            raise ValueError("Can only write off pending balance on posted bills")

        total_paid = sum(p.amount for p in bill.payments)
        existing_write_off = bill.write_off_amount or 0
        # Remaining pending accounts for prior write-offs on the same bill
        pending = bill.rounded_total - total_paid - existing_write_off
        if pending <= 0:
            raise ValueError("Bill has no pending balance")
        if write_off_amount <= 0 or write_off_amount > pending:
            raise ValueError(f"Write-off amount must be between 1 and {pending} paise")

        # Accumulate the write-off amount; do NOT touch any financial column
        bill.write_off_amount = existing_write_off + write_off_amount
        bill.write_off_at = datetime.now(IST)
        bill.write_off_reason = reason
        bill.write_off_approved_by = approved_by_id
        bill.updated_at = datetime.now(IST)

        if bill.customer_id:
            customer = self.db.query(Customer).filter(Customer.id == bill.customer_id).first()
            if customer:
                customer.pending_balance = max(0, customer.pending_balance - write_off_amount)

        self.db.commit()
        self.db.refresh(bill)
        return bill

    def collect_pending_bill_payment(
        self,
        bill_id: str,
        payment_method: PaymentMethod,
        amount_paise: int,
        confirmed_by_id: str,
        reference_number: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> Bill:
        """Collect a payment against a posted bill that has a pending balance.

            Creates a Payment record directly on the bill and reduces the linked
            customer's pending_balance. Only works on POSTED bills with remaining
            pending (rounded_total - total_paid - write_off_amount > 0).

            Args:
                bill_id: Posted bill ID to collect against.
                payment_method: Payment method (cash, upi, card, other).
                amount_paise: Amount to collect in paise.
                confirmed_by_id: User confirming the payment.
                reference_number: Optional transaction reference.
                notes: Optional payment notes.

            Returns:
                Bill: Updated bill with new payment attached.

            Raises:
                ValueError: If bill not found, not posted, no pending balance,
                            or amount exceeds remaining pending.
        """
        bill = self.get_bill(bill_id)
        if not bill:
            raise ValueError("Bill not found")
        if bill.status != BillStatus.POSTED:
            raise ValueError("Can only collect payment on posted bills")

        total_paid = sum(p.amount for p in bill.payments)
        existing_write_off = bill.write_off_amount or 0
        pending = bill.rounded_total - total_paid - existing_write_off
        if pending <= 0:
            raise ValueError("Bill has no pending balance")
        if amount_paise <= 0 or amount_paise > pending:
            raise ValueError(f"Amount must be between 1 and {pending} paise")

        payment = Payment(
            id=str(ULID()),
            bill_id=bill_id,
            payment_method=payment_method,
            amount=amount_paise,
            reference_number=reference_number,
            notes=notes,
            confirmed_at=datetime.now(IST),
            confirmed_by=confirmed_by_id,
        )
        self.db.add(payment)

        if bill.customer_id:
            customer = self.db.query(Customer).filter(Customer.id == bill.customer_id).first()
            if customer:
                customer.pending_balance = max(0, customer.pending_balance - amount_paise)

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
                    bill.invoice_number = self._generate_invoice_number(bill)
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

                    # Create PackageSale rows for any package_sale_line items on this bill
                    self._create_package_sales_for_bill(bill, updated_by_id)

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

        # Allocate collection amount to outstanding bills in FIFO order
        # (oldest posted bill first) so the bills list can show them as settled.
        pending_bills = (
            self.db.query(Bill)
            .filter(
                Bill.customer_id == customer_id,
                Bill.status == BillStatus.POSTED,
                Bill.original_bill_id.is_(None),
            )
            .order_by(Bill.posted_at.asc())
            .all()
        )

        remaining = amount
        current_balance = previous_balance
        first_collection: Optional[PendingPaymentCollection] = None
        collected_at = datetime.now(IST)

        for bill in pending_bills:
            if remaining <= 0:
                break

            # How much of this bill is still uncovered by payments + prior collections?
            bill_paid_direct = sum(p.amount for p in bill.payments)
            bill_already_collected = (
                self.db.query(func.coalesce(func.sum(PendingPaymentCollection.amount), 0))
                .filter(PendingPaymentCollection.bill_id == bill.id)
                .scalar()
            )
            bill_uncovered = max(0, bill.rounded_total - bill_paid_direct - bill_already_collected)
            if bill_uncovered <= 0:
                continue

            apply_amount = min(remaining, bill_uncovered)
            new_balance = current_balance - apply_amount

            coll = PendingPaymentCollection(
                id=str(ULID()),
                customer_id=customer_id,
                amount=apply_amount,
                payment_method=payment_method,
                reference_number=reference_number,
                notes=notes,
                bill_id=bill.id,
                collected_by=collected_by_id,
                collected_at=collected_at,
                previous_balance=current_balance,
                new_balance=new_balance,
            )
            self.db.add(coll)
            if first_collection is None:
                first_collection = coll

            remaining -= apply_amount
            current_balance = new_balance

        # Any unallocated remainder (e.g. no pending bills yet, or float rounding)
        if remaining > 0:
            new_balance = current_balance - remaining
            coll = PendingPaymentCollection(
                id=str(ULID()),
                customer_id=customer_id,
                amount=remaining,
                payment_method=payment_method,
                reference_number=reference_number,
                notes=notes,
                bill_id=None,
                collected_by=collected_by_id,
                collected_at=collected_at,
                previous_balance=current_balance,
                new_balance=new_balance,
            )
            self.db.add(coll)
            if first_collection is None:
                first_collection = coll

        self.db.commit()
        if first_collection:
            self.db.refresh(first_collection)
        return first_collection

    def _create_package_sales_for_bill(self, bill: "Bill", user_id: str) -> None:
        """Create PackageSale rows for all PACKAGE_SALE_LINE items not yet linked.

        Called from every code path that transitions a bill to POSTED.
        Uses db.flush() only — caller owns the transaction commit.

        Raises ValueError if a PACKAGE_SALE_LINE item exists but the bill has no customer_id,
        since PackageSale.customer_id is non-nullable.
        """
        from app.services import package_sales_service

        for item in bill.items:
            if (
                item.item_type == BillItemType.PACKAGE_SALE_LINE
                and not item.package_sale_id
                and item.package_definition_id
            ):
                if not bill.customer_id:
                    raise ValueError(
                        f"BillItem {item.id} is a PACKAGE_SALE_LINE but bill {bill.id} "
                        "has no linked customer. Package sales require a customer account."
                    )
                sale = package_sales_service.create_sale(
                    self.db,
                    package_definition_id=item.package_definition_id,
                    bill_id=bill.id,
                    customer_id=bill.customer_id,
                    selling_staff_id=item.staff_id,
                    locked_choices=item.package_locked_choices,
                )
                item.package_sale_id = sale.id
                # flush so FK assignment is visible before the outer commit
                self.db.flush()

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
        







