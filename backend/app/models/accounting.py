"""Accounting models for cash management and financial reporting."""

from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from app.database import Base
from app.models.base import TimestampMixin, ULIDMixin


class CashDrawer(Base, ULIDMixin):
    """
    Cash drawer sessions tracking opening/closing cash.

    Each drawer session tracks the physical cash on hand.
    """
    __tablename__ = "cash_drawer"

    opened_by = Column(String(26), ForeignKey("users.id"), nullable=False)
    opened_at = Column(DateTime(timezone=True), nullable=False)
    opening_float = Column(Integer, nullable=False)  # paise

    closed_by = Column(String(26), ForeignKey("users.id"))
    closed_at = Column(DateTime(timezone=True))
    closing_counted = Column(Integer)  # paise

    expected_cash = Column(Integer, nullable=False, default=0)  # paise (calculated)
    variance = Column(Integer)  # paise (counted - expected)

    # Denomination tracking
    opening_denominations = Column(JSONB, nullable=True)  # {"50": 10, "100": 20, "200": 5, "500": 8}
    closing_denominations = Column(JSONB, nullable=True)
    cash_taken_out = Column(Integer, nullable=True, default=0)  # paise
    cash_taken_out_reason = Column(Text, nullable=True)

    # Reopen tracking
    reopened_at = Column(DateTime(timezone=True))
    reopened_by = Column(String(26), ForeignKey("users.id"))
    reopen_reason = Column(Text)

    notes = Column(Text)

    # Relationships
    opener = relationship("User", foreign_keys=[opened_by])
    closer = relationship("User", foreign_keys=[closed_by])
    reopener = relationship("User", foreign_keys=[reopened_by])

    def __repr__(self):
        return f"<CashDrawer opened {self.opened_at}>"

    @property
    def opening_float_rupees(self) -> float:
        """Get opening float in rupees."""
        return self.opening_float / 100.0

    @property
    def closing_counted_rupees(self) -> float:
        """Get closing counted in rupees."""
        return self.closing_counted / 100.0 if self.closing_counted else 0.0

    @property
    def variance_rupees(self) -> float:
        """Get variance in rupees."""
        return self.variance / 100.0 if self.variance else 0.0


class DaySummary(Base, ULIDMixin, TimestampMixin):
    """
    Daily business summary auto-generated each night.

    Aggregates revenue, taxes, payment methods, and profit estimates.
    """
    __tablename__ = "day_summary"

    summary_date = Column(Date, nullable=False, unique=True, index=True)

    # Bill counts
    total_bills = Column(Integer, nullable=False, default=0)
    refund_count = Column(Integer, nullable=False, default=0)

    # Revenue in paise
    gross_revenue = Column(Integer, nullable=False, default=0)
    discount_amount = Column(Integer, nullable=False, default=0)
    refund_amount = Column(Integer, nullable=False, default=0)
    net_revenue = Column(Integer, nullable=False, default=0)

    # Tax breakdown in paise
    cgst_collected = Column(Integer, nullable=False, default=0)
    sgst_collected = Column(Integer, nullable=False, default=0)
    total_tax = Column(Integer, nullable=False, default=0)

    # Payment split in paise
    cash_collected = Column(Integer, nullable=False, default=0)
    digital_collected = Column(Integer, nullable=False, default=0)

    # COGS estimate (deprecated - kept for backward compatibility)
    estimated_cogs = Column(Integer, nullable=False, default=0)
    estimated_profit = Column(Integer, nullable=False, default=0)

    # Actual COGS and profit (owner only)
    actual_service_cogs = Column(Integer, nullable=False, default=0)  # From service materials
    actual_product_cogs = Column(Integer, nullable=False, default=0)  # From retail products
    total_cogs = Column(Integer, nullable=False, default=0)  # Sum of service + product COGS

    # Operating expenses
    total_expenses = Column(Integer, nullable=False, default=0)  # Rent, salaries, utilities, etc.

    # Accurate profit
    gross_profit = Column(Integer, nullable=False, default=0)  # Revenue - COGS
    net_profit = Column(Integer, nullable=False, default=0)  # Gross profit - Expenses

    # Tips
    total_tips = Column(Integer, nullable=False, default=0)

    # Generation tracking
    generated_at = Column(DateTime(timezone=True), nullable=False)
    generated_by = Column(String(26), ForeignKey("users.id"))
    is_final = Column(Boolean, nullable=False, default=False)

    # Relationships
    generator = relationship("User", foreign_keys=[generated_by])

    def __repr__(self):
        return f"<DaySummary {self.summary_date}>"

    @property
    def net_revenue_rupees(self) -> float:
        """Get net revenue in rupees."""
        return self.net_revenue / 100.0


class ExportLog(Base, ULIDMixin, TimestampMixin):
    """
    Audit log for report exports.

    Tracks all exported reports for compliance.
    """
    __tablename__ = "export_log"

    export_type = Column(String, nullable=False)  # 'daily_summary', 'monthly_tax', etc.
    export_format = Column(String, nullable=False)  # 'pdf', 'xlsx', 'csv'

    file_path = Column(String, nullable=False)
    file_size = Column(Integer)

    # Filters/parameters used
    parameters = Column(JSONB)

    exported_by = Column(String(26), ForeignKey("users.id"), nullable=False)
    exported_at = Column(DateTime(timezone=True), nullable=False, index=True)

    # Relationships
    exporter = relationship("User", foreign_keys=[exported_by])

    def __repr__(self):
        return f"<ExportLog {self.export_type} - {self.export_format}>"
