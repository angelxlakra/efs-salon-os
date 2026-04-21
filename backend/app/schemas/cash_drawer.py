from datetime import datetime
from typing import Optional, Dict
from pydantic import BaseModel, Field, ConfigDict, field_validator, model_validator


class DenominationBreakdown(BaseModel):
    """Physical currency note/coin counts."""
    note_5: int = Field(0, ge=0, le=10000, description="Count of ₹5 coins")
    note_10: int = Field(0, ge=0, le=10000, description="Count of ₹10 notes")
    note_20: int = Field(0, ge=0, le=10000, description="Count of ₹20 notes")
    note_50: int = Field(0, ge=0, le=10000, description="Count of ₹50 notes")
    note_100: int = Field(0, ge=0, le=10000, description="Count of ₹100 notes")
    note_200: int = Field(0, ge=0, le=10000, description="Count of ₹200 notes")
    note_500: int = Field(0, ge=0, le=10000, description="Count of ₹500 notes")

    @property
    def total_paise(self) -> int:
        """Calculate total amount in paise from note/coin counts."""
        return (
            self.note_5 * 5 +
            self.note_10 * 10 +
            self.note_20 * 20 +
            self.note_50 * 50 +
            self.note_100 * 100 +
            self.note_200 * 200 +
            self.note_500 * 500
        ) * 100

    def to_dict(self) -> Dict[str, int]:
        """Convert to dict for JSONB storage."""
        return {
            "5": self.note_5,
            "10": self.note_10,
            "20": self.note_20,
            "50": self.note_50,
            "100": self.note_100,
            "200": self.note_200,
            "500": self.note_500
        }

    @classmethod
    def from_dict(cls, data: Optional[Dict]) -> Optional['DenominationBreakdown']:
        """Create from JSONB-retrieved dict."""
        if not data:
            return None
        return cls(
            note_5=data.get("5", 0),
            note_10=data.get("10", 0),
            note_20=data.get("20", 0),
            note_50=data.get("50", 0),
            note_100=data.get("100", 0),
            note_200=data.get("200", 0),
            note_500=data.get("500", 0)
        )


class DrawerOpenRequest(BaseModel):
    """Request to open cash drawer - supports both legacy total and new denomination modes."""
    opening_float: Optional[int] = Field(None, description="Opening float in paise (legacy)", ge=0)
    opening_denominations: Optional[DenominationBreakdown] = Field(None, description="Denomination breakdown")

    @model_validator(mode='after')
    def validate_at_least_one(self):
        """Ensure either opening_float or opening_denominations is provided."""
        if self.opening_float is None and self.opening_denominations is None:
            raise ValueError("Either opening_float or opening_denominations must be provided")
        return self

    def get_opening_float_paise(self) -> int:
        """Get opening float in paise from either source."""
        if self.opening_denominations is not None:
            return self.opening_denominations.total_paise
        return self.opening_float  # guaranteed non-None by model_validator


class DrawerCloseRequest(BaseModel):
    """Request to close cash drawer - supports both legacy total and new denomination modes."""
    closing_counted: Optional[int] = Field(None, description="Actual cash counted in paise (legacy)", ge=0)
    closing_denominations: Optional[DenominationBreakdown] = Field(None, description="Denomination breakdown")
    cash_taken_out: int = Field(0, ge=0, description="Cash taken out of drawer in paise")
    cash_taken_out_reason: Optional[str] = Field(None, description="Reason for cash removal", max_length=500)
    notes: Optional[str] = Field(None, max_length=1000)

    @model_validator(mode='after')
    def validate_at_least_one(self):
        """Ensure either closing_counted or closing_denominations is provided."""
        if self.closing_counted is None and self.closing_denominations is None:
            raise ValueError("Either closing_counted or closing_denominations must be provided")
        return self

    def get_closing_counted_paise(self) -> int:
        """Get closing counted in paise from either source."""
        if self.closing_denominations is not None:
            return self.closing_denominations.total_paise
        return self.closing_counted  # guaranteed non-None by model_validator

class DrawerReopenRequest(BaseModel):
    reason: str = Field(..., min_length=5, description="Reason for reopening the drawer")

class CashDrawerResponse(BaseModel):
    id: str
    opened_by: str
    opened_at: datetime
    opening_float: int

    closed_by: Optional[str] = None
    closed_at: Optional[datetime] = None
    closing_counted: Optional[int] = None

    expected_cash: int
    variance: Optional[int] = None

    # Denomination tracking
    opening_denominations: Optional[Dict[str, int]] = None
    closing_denominations: Optional[Dict[str, int]] = None
    cash_taken_out: Optional[int] = None
    cash_taken_out_reason: Optional[str] = None

    reopened_at: Optional[datetime] = None
    reopened_by: Optional[str] = None
    reopen_reason: Optional[str] = None

    notes: Optional[str] = None

    # Computed fields available from the model properties
    opening_float_rupees: float
    closing_counted_rupees: float
    variance_rupees: float

    model_config = ConfigDict(from_attributes=True)

class CashDrawerSummary(BaseModel):
    session_id: Optional[str] = None
    date: datetime
    is_open: bool
    opening_float: int
    cash_payments: int
    cash_refunds: int
    expected_cash: int
    closing_counted: Optional[int] = None
    variance: Optional[int] = None
    
    model_config = ConfigDict(from_attributes=True)
