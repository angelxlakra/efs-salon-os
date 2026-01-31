"""Expense tracking models for rent, salaries, utilities, and operating costs."""

import enum
from sqlalchemy import Boolean, Column, Date, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from app.database import Base
from app.models.base import TimestampMixin, ULIDMixin


class ExpenseCategory(str, enum.Enum):
    """Categories for expense classification."""
    RENT = "rent"
    SALARIES = "salaries"
    UTILITIES = "utilities"
    SUPPLIES = "supplies"
    MARKETING = "marketing"
    MAINTENANCE = "maintenance"
    INSURANCE = "insurance"
    TAXES_FEES = "taxes_fees"
    PROFESSIONAL_SERVICES = "professional_services"
    OTHER = "other"


class RecurrenceType(str, enum.Enum):
    """Frequency of recurring expenses."""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"


class ExpenseStatus(str, enum.Enum):
    """Status of expense records."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class Expense(Base, ULIDMixin, TimestampMixin):
    """
    Operating expense records for accurate profit calculation.

    Tracks rent, salaries, utilities, and other business expenses.
    All amounts in paise (Rs 1 = 100 paise).
    """
    __tablename__ = "expenses"

    # Core expense details
    category = Column(Enum(ExpenseCategory), nullable=False, index=True)
    amount = Column(Integer, nullable=False)  # paise
    expense_date = Column(Date, nullable=False, index=True)

    # Description and documentation
    description = Column(Text, nullable=False)
    vendor_name = Column(String)
    invoice_number = Column(String)
    notes = Column(Text)

    # Recurring expense support
    is_recurring = Column(Boolean, nullable=False, default=False, index=True)
    recurrence_type = Column(Enum(RecurrenceType), nullable=True)
    parent_expense_id = Column(String(26), ForeignKey("expenses.id"))  # For recurring instances

    # Staff linkage (for salary expenses)
    staff_id = Column(String(26), ForeignKey("staff.id"), nullable=True, index=True)

    # Approval workflow
    status = Column(Enum(ExpenseStatus), nullable=False, default=ExpenseStatus.APPROVED, index=True)
    requires_approval = Column(Boolean, nullable=False, default=False)

    # Audit trail
    recorded_by = Column(String(26), ForeignKey("users.id"), nullable=False)
    recorded_at = Column(DateTime(timezone=True), nullable=False)

    approved_by = Column(String(26), ForeignKey("users.id"))
    approved_at = Column(DateTime(timezone=True))

    rejected_by = Column(String(26), ForeignKey("users.id"))
    rejected_at = Column(DateTime(timezone=True))
    rejection_reason = Column(Text)

    # Relationships
    staff = relationship("Staff", foreign_keys=[staff_id])
    recorder = relationship("User", foreign_keys=[recorded_by])
    approver = relationship("User", foreign_keys=[approved_by])
    rejector = relationship("User", foreign_keys=[rejected_by])
    parent_expense = relationship("Expense", remote_side="Expense.id", foreign_keys=[parent_expense_id])
    recurring_instances = relationship("Expense", foreign_keys=[parent_expense_id], remote_side=[parent_expense_id])

    def __repr__(self):
        return f"<Expense {self.category.value} - Rs {self.amount / 100:.2f}>"

    @property
    def amount_rupees(self) -> float:
        """Get amount in rupees."""
        return self.amount / 100.0

    @property
    def is_approved(self) -> bool:
        """Check if expense is approved."""
        return self.status == ExpenseStatus.APPROVED

    @property
    def is_salary_expense(self) -> bool:
        """Check if this is a salary expense."""
        return self.category == ExpenseCategory.SALARIES and self.staff_id is not None
