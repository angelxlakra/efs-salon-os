"""Pending Payment model for tracking collections of customer pending balances."""

from sqlalchemy import Column, DateTime, Integer, String, Text, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from app.database import Base
from app.models.base import TimestampMixin, ULIDMixin
from app.models.billing import PaymentMethod


class PendingPaymentCollection(Base, ULIDMixin, TimestampMixin):
    """
    Records of pending payment collections.

    Tracks when customers pay off their pending balances, either through
    direct collection or overpayment on new bills.
    """
    __tablename__ = "pending_payment_collections"

    customer_id = Column(String, ForeignKey("customers.id"), nullable=False, index=True)
    amount = Column(Integer, nullable=False)  # Amount collected in paise
    payment_method = Column(SQLEnum(PaymentMethod), nullable=False)
    reference_number = Column(String, nullable=True)
    notes = Column(Text, nullable=True)

    # If collected via overpayment on a bill
    bill_id = Column(String, ForeignKey("bills.id"), nullable=True, index=True)

    # Who collected it
    collected_by = Column(String, ForeignKey("users.id"), nullable=False)
    collected_at = Column(DateTime(timezone=True), nullable=False, index=True)

    # Previous and new balance for audit trail
    previous_balance = Column(Integer, nullable=False)  # Balance before collection
    new_balance = Column(Integer, nullable=False)  # Balance after collection

    # Relationships
    customer = relationship("Customer", back_populates="pending_payment_collections")
    bill = relationship("Bill", foreign_keys=[bill_id])
    collected_by_user = relationship("User", foreign_keys=[collected_by])

    def __repr__(self):
        return f"<PendingPaymentCollection {self.id} customer={self.customer_id} amount={self.amount}>"

    @property
    def amount_rupees(self) -> float:
        """Get amount in rupees."""
        return self.amount / 100.0
