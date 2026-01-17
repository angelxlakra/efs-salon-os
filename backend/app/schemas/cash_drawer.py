from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict

class DrawerOpenRequest(BaseModel):
    opening_float: int = Field(..., description="Opening float in paise", ge=0)

class DrawerCloseRequest(BaseModel):
    closing_counted: int = Field(..., description="Actual cash counted in paise", ge=0)
    notes: Optional[str] = None

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
