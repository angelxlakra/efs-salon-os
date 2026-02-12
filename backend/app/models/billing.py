"""Billing models for bills, bill items, and payments."""

import enum
from sqlalchemy import CheckConstraint, Column, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from app.database import Base
from app.models.base import TimestampMixin, ULIDMixin


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

    # Refund tracking
    refunded_at = Column(DateTime(timezone=True))
    refund_reason = Column(Text)
    refund_approved_by = Column(String(26), ForeignKey("users.id"))
    original_bill_id = Column(String(26), ForeignKey("bills.id"))  # For refund bills

    # Audit
    created_by = Column(String(26), ForeignKey("users.id"), nullable=False)

    # Relationships
    customer = relationship("Customer", foreign_keys=[customer_id])
    items = relationship("BillItem", back_populates="bill", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="bill")
    created_by_user = relationship("User", foreign_keys=[created_by])
    discount_approver = relationship("User", foreign_keys=[discount_approved_by])
    refund_approver = relationship("User", foreign_keys=[refund_approved_by])
    original_bill = relationship("Bill", remote_side="Bill.id", foreign_keys=[original_bill_id])
    tip_recipient = relationship("Staff", foreign_keys=[tip_staff_id])

    def __repr__(self):
        return f"<Bill {self.invoice_number} - Rs {self.rounded_total / 100:.2f}>"

    @property
    def total_rupees(self) -> float:
        """Get total in rupees."""
        return self.rounded_total / 100.0


class BillItem(Base, ULIDMixin, TimestampMixin):
    """
    Individual line items on a bill.

    Links to services OR retail products (SKUs).
    Exactly one of service_id or sku_id must be set.
    """
    __tablename__ = "bill_items"
    __table_args__ = (
        CheckConstraint(
            "(service_id IS NOT NULL AND sku_id IS NULL) OR (service_id IS NULL AND sku_id IS NOT NULL)",
            name="bill_item_service_or_sku_check"
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

    # Notes
    notes = Column(Text)

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
