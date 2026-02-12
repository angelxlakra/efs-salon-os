from datetime import date, datetime
from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field

class CustomerBase(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, pattern=r"^\+?[1-9]\d{1,14}$")  # Optional for walk-ins
    email: Optional[EmailStr] = None
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    notes: Optional[str] = None

class CustomerCreate(CustomerBase):
    pass

class CustomerUpdate(BaseModel):
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, pattern=r"^\+?[1-9]\d{1,14}$")
    email: Optional[EmailStr] = None
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    notes: Optional[str] = None

class CustomerResponse(CustomerBase):
    id: str
    phone: Optional[str]  # Override to remove pattern validation for responses, nullable for walk-ins
    total_visits: int
    total_spent: int
    total_spent_rupees: float
    pending_balance: int  # Outstanding amount owed in paise
    pending_balance_rupees: float
    last_visit_at: Optional[datetime]
    full_name: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class CustomerListResponse(BaseModel):
    items: List[CustomerResponse]
    total: int
    page: int
    size: int
    pages: int
