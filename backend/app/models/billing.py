"""Billing models for bills, bill items, and payments."""

import enum
from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from app.database import Base
from app.models.base import TimestampMixin, ULIDMixin


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

    invoice_number = Column(String, nullable=False, unique=True, index=True)
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

    def __repr__(self):
        return f"<Bill {self.invoice_number} - Rs {self.rounded_total / 100:.2f}>"

    @property
    def total_rupees(self) -> float:
        """Get total in rupees."""
        return self.rounded_total / 100.0


class BillItem(Base, ULIDMixin, TimestampMixin):
    """
    Individual line items on a bill.

    Links to services and optionally to appointments/walk-ins.
    """
    __tablename__ = "bill_items"

    bill_id = Column(String(26), ForeignKey("bills.id", ondelete="CASCADE"), nullable=False, index=True)

    # Reference to service/appointment/walkin
    service_id = Column(String(26), ForeignKey("services.id"), nullable=False, index=True)
    appointment_id = Column(String(26), ForeignKey("appointments.id"))
    walkin_id = Column(String(26), ForeignKey("walkins.id"))
    staff_id = Column(String(26), ForeignKey("staff.id"))

    # Pricing at time of billing (paise)
    item_name = Column(String, nullable=False)
    base_price = Column(Integer, nullable=False)
    quantity = Column(Integer, nullable=False, default=1)
    line_total = Column(Integer, nullable=False)

    # Notes
    notes = Column(Text)

    # Relationships
    bill = relationship("Bill", back_populates="items")
    service = relationship("Service")
    appointment = relationship("Appointment")
    walkin = relationship("WalkIn")
    staff = relationship("Staff")

    def __repr__(self):
        return f"<BillItem {self.item_name} x{self.quantity}>"

    @property
    def line_total_rupees(self) -> float:
        """Get line total in rupees."""
        return self.line_total / 100.0


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
