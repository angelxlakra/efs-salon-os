"""Customer model for tracking salon customers."""

from sqlalchemy import Column, Date, DateTime, Integer, String, Text
from app.database import Base
from app.models.base import TimestampMixin, SoftDeleteMixin, ULIDMixin


class Customer(Base, ULIDMixin, TimestampMixin, SoftDeleteMixin):
    """
    Customer records for tracking visits, spending, and contact information.

    PII fields (phone, email) should be encrypted in production.
    """
    __tablename__ = "customers"

    first_name = Column(String, nullable=False)
    last_name = Column(String)
    phone = Column(String, nullable=True, index=True)  # Encrypted, nullable for walk-ins
    email = Column(String)  # Encrypted
    date_of_birth = Column(Date)
    gender = Column(String)
    notes = Column(Text)

    # Analytics fields
    total_visits = Column(Integer, nullable=False, default=0)
    total_spent = Column(Integer, nullable=False, default=0)  # in paise
    last_visit_at = Column(DateTime(timezone=True), index=True)

    def __repr__(self):
        return f"<Customer {self.first_name} {self.last_name or ''}>"

    @property
    def full_name(self) -> str:
        """Get customer's full name."""
        if self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.first_name

    @property
    def total_spent_rupees(self) -> float:
        """Get total spent in rupees."""
        return self.total_spent / 100.0
