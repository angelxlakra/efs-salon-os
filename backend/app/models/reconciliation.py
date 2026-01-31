"""End of Day Reconciliation model."""

from sqlalchemy import Column, String, Integer, Text, Date, DateTime, Boolean
from app.database import Base
from app.models.base import TimestampMixin, ULIDMixin


class DailyReconciliation(Base, ULIDMixin, TimestampMixin):
    """
    Daily reconciliation records.

    Stores end-of-day cash reconciliation data.
    One record per day.
    """
    __tablename__ = "daily_reconciliations"

    reconciliation_date = Column(Date, nullable=False, unique=True, index=True)

    # Expected values from system
    expected_cash = Column(Integer, nullable=False, default=0)  # paise
    total_revenue = Column(Integer, nullable=False, default=0)  # paise
    total_bills = Column(Integer, nullable=False, default=0)

    # Actual values entered by user
    actual_cash = Column(Integer, nullable=True)  # paise
    cash_difference = Column(Integer, nullable=True)  # paise (actual - expected)

    # Reconciliation status
    reconciled = Column(Boolean, nullable=False, default=False)
    reconciled_at = Column(DateTime(timezone=True), nullable=True)
    reconciled_by = Column(String(26), nullable=True)  # User ID

    # Notes
    notes = Column(Text, nullable=True)

    def __repr__(self):
        return f"<DailyReconciliation {self.reconciliation_date} - {'Reconciled' if self.reconciled else 'Pending'}>"
