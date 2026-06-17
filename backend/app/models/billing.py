"""Billing models for bills, bill items, and payments."""

import enum
from sqlalchemy import CheckConstraint, Column, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from app.database import Base
from app.models.base import TimestampMixin, ULIDMixin


class BillType(str, enum.Enum):
    """Bill kind: normal sale or credit note (refund)."""
    NORMAL = "normal"
    CREDIT_NOTE = "credit_note"


class BillClass(str, enum.Enum):
    """GST rate-class of a bill (split billing scheme, post GST registration).

    SERVICE: only service lines, 5% exclusive GST, SRV invoice series.
    PRODUCT: only retail product lines, 18% MRP-inclusive GST, PRD series.
    MIXED_LEGACY: pre-registration bills (any mix, zero tax recorded).
    """
    SERVICE = "service"
    PRODUCT = "product"
    MIXED_LEGACY = "mixed_legacy"


class TaxMode(str, enum.Enum):
    """How GST applies to a bill line.

    EXCLUSIVE: tax added on top of the discounted base (services, 5%).
    INCLUSIVE: tax extracted from the discounted MRP (products, 18%).
    NONE: no tax (legacy lines, package redemptions, exempt).
    """
    EXCLUSIVE = "exclusive"
    INCLUSIVE = "inclusive"
    NONE = "none"


class BillItemType(str, enum.Enum):
    """BillItem kind: existing service/product or new package item types."""
    SERVICE = "service"
    PRODUCT = "product"
    PACKAGE_SALE_LINE = "package_sale_line"
    PACKAGE_REDEMPTION = "package_redemption"


class ContributionSplitType(str, enum.Enum):
    """How contribution is calculated for multi-staff services."""
    PERCENTAGE = "percentage"  # Percentage of line total
    FIXED = "fixed"           # Fixed amount in paise
    EQUAL = "equal"           # Equal split among all staff
    TIME_BASED = "time_based" # Based on time spent
    HYBRID = "hybrid"         # Combination of factors


class PaymentMethod(str, enum.Enum):
    """Payment methods accepted."""
    CASH = "cash"
    UPI = "upi"
    CARD = "card"
    OTHER = "other"
    PACKAGE_REDEMPTION = "package_redemption"  # NEW: session package redemption


class BillStatus(str, enum.Enum):
    """Bill status lifecycle."""
    DRAFT = "draft"
    POSTED = "posted"
    REFUNDED = "refunded"
    VOID = "void"


class Bill(Base, ULIDMixin, TimestampMixin):
    """
    Bills for customer purchases.

    Invoice Number Format: SAL-YY-NNNN (e.g., SAL-25-0042)
    All amounts in paise (Rs 1 = 100 paise).
    """
    __tablename__ = "bills"

    invoice_number = Column(String, nullable=True, unique=True, index=True)
    customer_id = Column(String(26), ForeignKey("customers.id"), index=True)

    # Amounts in paise
    subtotal = Column(Integer, nullable=False)
    discount_amount = Column(Integer, nullable=False, default=0)
    tax_amount = Column(Integer, nullable=False)  # Total tax (CGST + SGST)
    cgst_amount = Column(Integer, nullable=False)
    sgst_amount = Column(Integer, nullable=False)
    total_amount = Column(Integer, nullable=False)

    # After rounding to nearest Rs 1
    rounded_total = Column(Integer, nullable=False)
    rounding_adjustment = Column(Integer, nullable=False, default=0)

    # Tips
    tip_amount = Column(Integer, nullable=False, default=0)
    tip_staff_id = Column(String(26), ForeignKey("staff.id"))

    # Status
    status = Column(Enum(BillStatus), nullable=False, default=BillStatus.DRAFT, index=True)
    posted_at = Column(DateTime(timezone=True), index=True)

    # Optional customer info (for anonymous bills)
    customer_name = Column(String)
    customer_phone = Column(String)

    # Discount tracking
    discount_reason = Column(Text)
    discount_approved_by = Column(String(26), ForeignKey("users.id"))

    # Write-off tracking (Option B — does NOT mutate discount_amount or rounded_total)
    write_off_amount = Column(Integer, nullable=False, default=0)
    write_off_at = Column(DateTime(timezone=True), nullable=True)
    write_off_reason = Column(Text, nullable=True)
    write_off_approved_by = Column(String(26), ForeignKey("users.id"), nullable=True)

    # Refund tracking
    refunded_at = Column(DateTime(timezone=True))
    refund_reason = Column(Text)
    refund_approved_by = Column(String(26), ForeignKey("users.id"))
    original_bill_id = Column(
        String(26), ForeignKey("bills.id", ondelete="RESTRICT"), nullable=True
    )

    # Free-text annotations (void reason, pending-balance completion notes)
    notes = Column(Text)

    # Audit
    created_by = Column(String(26), ForeignKey("users.id"), nullable=False)

    # Package discriminators
    bill_type = Column(
        Enum(BillType, name="billtype",
             values_callable=lambda obj: [e.value for e in obj]),
        nullable=False, default=BillType.NORMAL, server_default="normal",
        index=True,
    )

    # GST split billing: rate-class of this bill and link to its checkout sibling.
    # A mixed cart posts as TWO bills (service + product) sharing one bill_group_id.
    bill_class = Column(
        Enum(BillClass, name="billclass",
             values_callable=lambda obj: [e.value for e in obj]),
        nullable=False, default=BillClass.MIXED_LEGACY, server_default="mixed_legacy",
        index=True,
    )
    bill_group_id = Column(String(26), nullable=True, index=True)

    __table_args__ = (
        CheckConstraint(
            "(bill_type = 'credit_note' AND original_bill_id IS NOT NULL) "
            "OR (bill_type = 'normal' AND original_bill_id IS NULL)",
            name="ck_bill_credit_note_has_original",
        ),
        {},  # sentinel required by SQLAlchemy when tuple has a single constraint
    )

    # Relationships
    customer = relationship("Customer", foreign_keys=[customer_id])
    items = relationship("BillItem", back_populates="bill", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="bill")
    created_by_user = relationship("User", foreign_keys=[created_by])
    discount_approver = relationship("User", foreign_keys=[discount_approved_by])
    write_off_approver = relationship("User", foreign_keys=[write_off_approved_by])
    refund_approver = relationship("User", foreign_keys=[refund_approved_by])
    original_bill = relationship("Bill", remote_side="Bill.id", foreign_keys=[original_bill_id])
    tip_recipient = relationship("Staff", foreign_keys=[tip_staff_id])

    def __repr__(self):
        return f"<Bill {self.invoice_number} - Rs {self.rounded_total / 100:.2f}>"

    @property
    def total_rupees(self) -> float:
        """Get total in rupees."""
        return self.rounded_total / 100.0

    @property
    def total_paise(self) -> int:
        """Alias for total_amount, used by compute_refund for unlimited packages."""
        return self.total_amount


class BillItem(Base, ULIDMixin, TimestampMixin):
    """
    Individual line items on a bill.

    For SERVICE/PRODUCT items: exactly one of service_id or sku_id must be set.
    For PACKAGE_SALE_LINE and PACKAGE_REDEMPTION items: both service_id and sku_id
    may be null; the item links via package_sale_id / package_sale_item_id instead.
    """
    __tablename__ = "bill_items"
    __table_args__ = (
        CheckConstraint(
            "(service_id IS NOT NULL AND sku_id IS NULL)"
            " OR (service_id IS NULL AND sku_id IS NOT NULL)"
            " OR item_type IN ('package_sale_line', 'package_redemption')",
            name="bill_item_service_or_sku_check",
        ),
    )

    bill_id = Column(String(26), ForeignKey("bills.id", ondelete="CASCADE"), nullable=False, index=True)

    # Reference to service OR product (mutually exclusive)
    service_id = Column(String(26), ForeignKey("services.id"), nullable=True, index=True)
    sku_id = Column(String(26), ForeignKey("skus.id"), nullable=True, index=True)

    # For services: optional link to appointment/walkin
    appointment_id = Column(String(26), ForeignKey("appointments.id"))
    walkin_id = Column(String(26), ForeignKey("walkins.id"))
    staff_id = Column(String(26), ForeignKey("staff.id"))

    # Pricing at time of billing (paise)
    item_name = Column(String, nullable=False)
    base_price = Column(Integer, nullable=False)
    quantity = Column(Integer, nullable=False, default=1)
    line_total = Column(Integer, nullable=False)

    # COGS tracking (actual cost, not estimate)
    cogs_amount = Column(Integer, nullable=True)  # paise

    # Per-line GST (split billing scheme). Amounts floored to the paise.
    # tax_mode EXCLUSIVE: line gross = taxable_value + cgst + sgst
    # tax_mode INCLUSIVE: taxable_value + cgst + sgst == discounted line total
    tax_rate = Column(Integer, nullable=False, default=0, server_default="0")  # whole percent
    tax_mode = Column(
        Enum(TaxMode, name="taxmode",
             values_callable=lambda obj: [e.value for e in obj]),
        nullable=False, default=TaxMode.NONE, server_default="none",
    )
    taxable_value = Column(Integer, nullable=False, default=0, server_default="0")
    cgst_amount = Column(Integer, nullable=False, default=0, server_default="0")
    sgst_amount = Column(Integer, nullable=False, default=0, server_default="0")

    # Notes
    notes = Column(Text)

    # Package discriminators
    item_type = Column(
        Enum(BillItemType, name="billitemtype",
             values_callable=lambda obj: [e.value for e in obj]),
        nullable=False, default=BillItemType.SERVICE, server_default="service",
        index=True,
    )
    package_sale_id = Column(
        String(26), ForeignKey("package_sales.id", ondelete="RESTRICT"),
        nullable=True, index=True,
    )
    package_sale_item_id = Column(
        String(26), ForeignKey("package_sale_items.id", ondelete="RESTRICT"),
        nullable=True, index=True,
    )
    # FK to PackageDefinition — set when item_type=PACKAGE_SALE_LINE; used at bill
    # finalization to create the PackageSale row. NULL for all other item types.
    package_definition_id = Column(
        String(26), ForeignKey("package_definitions.id", ondelete="RESTRICT"),
        nullable=True, index=True,
    )
    # v2 packages: service_ids chosen at purchase for choice blocks, locked into
    # the PackageSale snapshot at settlement. NULL for v1 / non-package lines.
    package_locked_choices = Column(JSONB, nullable=True)

    # Relationships
    bill = relationship("Bill", back_populates="items")
    service = relationship("Service")
    sku = relationship("SKU", back_populates="bill_items")
    appointment = relationship("Appointment")
    walkin = relationship("WalkIn")
    staff = relationship("Staff")
    staff_contributions = relationship("BillItemStaffContribution", back_populates="bill_item", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<BillItem {self.item_name} x{self.quantity}>"

    @property
    def line_total_rupees(self) -> float:
        """Get line total in rupees."""
        return self.line_total / 100.0


class BillItemStaffContribution(Base, ULIDMixin, TimestampMixin):
    """
    Track multiple staff members working on a single service.

    Enables accurate contribution tracking and commission calculation
    for services performed by multiple staff (e.g., Botox treatment
    with application specialist, wash technician, and stylist).

    Key Features:
    - Links to bill item (service line item)
    - Records staff member and their role
    - Tracks contribution amount (calculated from line_total)
    - Supports percentage, fixed, or equal split
    - Maintains workflow sequence for audit trail
    """
    __tablename__ = "bill_item_staff_contributions"

    bill_item_id = Column(String(26), ForeignKey("bill_items.id", ondelete="CASCADE"), nullable=False, index=True)
    staff_id = Column(String(26), ForeignKey("staff.id"), nullable=False, index=True)

    # Role information
    role_in_service = Column(String(100), nullable=False)  # e.g., "Botox Application", "Hair Wash"
    sequence_order = Column(Integer, nullable=False)  # Order in workflow (1, 2, 3...)

    # Contribution calculation
    contribution_split_type = Column(Enum(ContributionSplitType), nullable=False, default=ContributionSplitType.PERCENTAGE)
    contribution_percent = Column(Integer, nullable=True)  # 0-100 (for PERCENTAGE/HYBRID types)
    contribution_fixed = Column(Integer, nullable=True)  # paise (for FIXED type)
    contribution_amount = Column(Integer, nullable=False)  # Calculated actual paise earned

    # Time tracking (optional, for TIME_BASED/HYBRID)
    time_spent_minutes = Column(Integer, nullable=True)

    # Hybrid calculation components (optional)
    base_percent_component = Column(Integer, nullable=True)  # paise from base percentage
    time_component = Column(Integer, nullable=True)  # paise from time-based calculation
    skill_component = Column(Integer, nullable=True)  # paise from skill/complexity weight

    # Notes
    notes = Column(Text)

    # Relationships
    bill_item = relationship("BillItem", back_populates="staff_contributions")
    staff = relationship("Staff")

    def __repr__(self):
        return f"<BillItemStaffContribution {self.role_in_service} - ₹{self.contribution_amount / 100:.2f}>"

    @property
    def contribution_rupees(self) -> float:
        """Get contribution amount in rupees."""
        return self.contribution_amount / 100.0


class Payment(Base, ULIDMixin, TimestampMixin):
    """
    Payment records for bills.

    A bill can have multiple payments (split payments).
    """
    __tablename__ = "payments"

    bill_id = Column(String(26), ForeignKey("bills.id"), nullable=False, index=True)

    # GST split billing: one customer tender split across the two bills of a
    # checkout group shares a payment_group_id (NULL for single-bill payments).
    payment_group_id = Column(String(26), nullable=True, index=True)

    payment_method = Column(Enum(PaymentMethod), nullable=False)
    amount = Column(Integer, nullable=False)  # paise

    # Manual confirmation
    confirmed_at = Column(DateTime(timezone=True), nullable=False)
    confirmed_by = Column(String(26), ForeignKey("users.id"), nullable=False)

    # Optional reference numbers
    reference_number = Column(String)
    notes = Column(Text)

    # Relationships
    bill = relationship("Bill", back_populates="payments")
    confirmed_by_user = relationship("User", foreign_keys=[confirmed_by])

    def __repr__(self):
        return f"<Payment {self.payment_method} - Rs {self.amount / 100:.2f}>"

    @property
    def amount_rupees(self) -> float:
        """Get amount in rupees."""
        return self.amount / 100.0
