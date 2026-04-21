"""Expense schemas for request/response validation."""

from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, Field, model_validator

from app.models.expense import ExpenseCategory, RecurrenceType, ExpenseStatus


class ExpenseBase(BaseModel):
    """Base expense schema with common fields."""
    category: ExpenseCategory
    amount: int = Field(..., gt=0, description="Amount in paise")
    expense_date: date
    description: str = Field(..., min_length=1, max_length=500)
    vendor_name: Optional[str] = Field(None, max_length=200)
    invoice_number: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = None
    is_recurring: bool = False
    recurrence_type: Optional[RecurrenceType] = None
    staff_id: Optional[str] = None
    requires_approval: bool = False

    @model_validator(mode="after")
    def validate_expense_rules(self) -> "ExpenseBase":
        """Validate cross-field business rules.

        Uses model_validator (not field_validator) because Pydantic v2
        field_validator does NOT run for fields that use their default
        value — model_validator always runs after all fields are resolved.
        """
        if self.category == ExpenseCategory.SALARIES and not self.staff_id:
            raise ValueError("staff_id required for salary expenses")
        if self.is_recurring and not self.recurrence_type:
            raise ValueError("recurrence_type required when is_recurring=True")
        if not self.is_recurring and self.recurrence_type:
            raise ValueError("recurrence_type should not be set when is_recurring=False")
        return self


class ExpenseCreate(ExpenseBase):
    """Schema for creating a new expense."""
    pass


class ExpenseUpdate(BaseModel):
    """Schema for updating an expense."""
    amount: Optional[int] = Field(None, gt=0)
    expense_date: Optional[date] = None
    description: Optional[str] = Field(None, min_length=1, max_length=500)
    vendor_name: Optional[str] = Field(None, max_length=200)
    invoice_number: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = None
    staff_id: Optional[str] = None


class ExpenseApproval(BaseModel):
    """Schema for approving or rejecting an expense."""
    approved: bool
    notes: Optional[str] = None


class ExpenseResponse(ExpenseBase):
    """Schema for expense response."""
    id: str
    status: ExpenseStatus
    parent_expense_id: Optional[str] = None
    recorded_by: str
    recorded_at: datetime
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    rejected_by: Optional[str] = None
    rejected_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ExpenseListItem(BaseModel):
    """Simplified expense schema for list views."""
    id: str
    category: ExpenseCategory
    amount: int
    expense_date: date
    description: str
    vendor_name: Optional[str] = None
    status: ExpenseStatus
    is_recurring: bool
    staff_id: Optional[str] = None

    class Config:
        from_attributes = True


class ExpenseListResponse(BaseModel):
    """Paginated list of expenses."""
    items: list[ExpenseListItem]
    total: int
    page: int
    size: int
    pages: int


class ExpenseSummary(BaseModel):
    """Summary of expenses for a period."""
    total_amount: int
    by_category: dict[str, int]
    approved_count: int
    pending_count: int
    rejected_count: int


class RetailProductResponse(BaseModel):
    """Schema for retail products catalog."""
    id: str
    sku_code: str
    name: str
    description: Optional[str] = None
    retail_price: int
    current_stock: float
    uom: str
    category_name: str
    category_id: str

    class Config:
        from_attributes = True
