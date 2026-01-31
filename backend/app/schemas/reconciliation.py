"""Pydantic schemas for end-of-day reconciliation."""

from datetime import datetime
from typing import Optional, Dict
from pydantic import BaseModel, Field


class PaymentMethodBreakdown(BaseModel):
    """Breakdown by payment method."""
    cash: int = 0  # paise
    card: int = 0  # paise
    upi: int = 0  # paise
    bank_transfer: int = 0  # paise


class EODSummary(BaseModel):
    """End of day summary data."""
    date: str  # YYYY-MM-DD
    total_bills: int
    total_revenue: int  # paise
    total_tax: int  # paise
    total_discount: int  # paise
    payment_breakdown: PaymentMethodBreakdown
    bills_by_status: Dict[str, int]  # status -> count


class CashReconciliation(BaseModel):
    """Cash reconciliation submission."""
    date: str = Field(..., description="Date being reconciled (YYYY-MM-DD)")
    expected_cash: int = Field(..., description="Expected cash from system (paise)")
    actual_cash: int = Field(..., description="Actual cash counted (paise)")
    notes: Optional[str] = Field(None, max_length=1000, description="Reconciliation notes")


class EODReport(BaseModel):
    """Complete end-of-day report."""
    date: str
    summary: EODSummary
    expected_cash: int  # paise
    actual_cash: Optional[int] = None  # paise
    cash_difference: Optional[int] = None  # paise (actual - expected)
    reconciled: bool = False
    reconciled_at: Optional[datetime] = None
    reconciled_by: Optional[str] = None
    notes: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "date": "2026-01-25",
                "summary": {
                    "date": "2026-01-25",
                    "total_bills": 42,
                    "total_revenue": 5230000,
                    "total_tax": 79610,
                    "total_discount": 50000,
                    "payment_breakdown": {
                        "cash": 2100000,
                        "card": 1800000,
                        "upi": 1230000,
                        "bank_transfer": 100000
                    },
                    "bills_by_status": {
                        "posted": 40,
                        "draft": 1,
                        "void": 1
                    }
                },
                "expected_cash": 2100000,
                "actual_cash": 2098500,
                "cash_difference": -1500,
                "reconciled": True,
                "reconciled_at": "2026-01-25T22:30:00",
                "reconciled_by": "01OWNER1234567890",
                "notes": "₹15 short due to customer change shortage"
            }
        }
