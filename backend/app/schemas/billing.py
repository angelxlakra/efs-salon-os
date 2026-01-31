"""Pydantic schemas for billing API requests and responses.

These schemas validate incoming requests and serialize outgoing responses
for the POS billing endpoints.
"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, model_validator
from app.models.billing import BillStatus, PaymentMethod


class BillItemCreate(BaseModel):
    """Schema for creating a bill item (service OR product)."""

    service_id: Optional[str] = Field(None, min_length=26, max_length=26)
    sku_id: Optional[str] = Field(None, min_length=26, max_length=26)
    quantity: int = Field(default=1, ge=1, description="Quantity (must be >= 1)")
    staff_id: Optional[str] = Field(None, min_length=26, max_length=26)
    appointment_id: Optional[str] = Field(None, min_length=26, max_length=26)
    walkin_id: Optional[str] = Field(None, min_length=26, max_length=26)
    notes: Optional[str] = Field(None, max_length=500)

    @model_validator(mode='after')
    def validate_item_type(self):
        """Ensure exactly one of service_id or sku_id is set."""
        if not self.service_id and not self.sku_id:
            raise ValueError("Either service_id or sku_id must be provided")
        if self.service_id and self.sku_id:
            raise ValueError("Cannot specify both service_id and sku_id")
        return self

    class Config:
        from_attributes = True  # For SQLAlchemy model conversion


class BillItemResponse(BaseModel):
    """Schema for bill item in response."""

    id: str
    service_id: Optional[str] = None
    sku_id: Optional[str] = None
    item_name: str
    base_price: int  # paise
    quantity: int
    line_total: int  # paise
    cogs_amount: Optional[int] = None  # paise
    staff_id: Optional[str] = None
    notes: Optional[str] = None

    class Config:
        from_attributes = True

    @property
    def base_price_rupees(self) -> float:
        """Get base price in rupees."""
        return self.base_price / 100.0

    @property
    def line_total_rupees(self) -> float:
        """Get line total in rupees."""
        return self.line_total / 100.0

    @property
    def cogs_amount_rupees(self) -> Optional[float]:
        """Get COGS amount in rupees."""
        return self.cogs_amount / 100.0 if self.cogs_amount else None


class BillCreate(BaseModel):
    """Schema for creating a new bill."""

    items: List[BillItemCreate] = Field(..., min_length=1, description="At least one item required")
    customer_id: Optional[str] = Field(None, min_length=26, max_length=26)
    customer_name: Optional[str] = Field(None, min_length=1, max_length=200)
    customer_phone: Optional[str] = Field(None, min_length=10, max_length=15)
    discount_amount: int = Field(default=0, ge=0, description="Discount in paise")
    discount_reason: Optional[str] = Field(None, max_length=500)
    session_id: Optional[str] = Field(None, min_length=26, max_length=26, description="Session ID to link walk-ins")
    tip_amount: int = Field(default=0, ge=0, description="Tip amount in paise")
    tip_staff_id: Optional[str] = Field(None, min_length=26, max_length=26, description="Staff receiving tip")

    @model_validator(mode='after')
    def validate_customer_info(self):
        """Validate that customer info is provided if no customer_id."""
        # This validation will be handled in the service layer
        return self

    class Config:
        json_schema_extra = {
            "example": {
                "items": [
                    {
                        "service_id": "01HXXX1234567890ABCDEFGHIJ",
                        "quantity": 1,
                        "staff_id": "01HYYY1234567890ABCDEFGHIJ"
                    }
                ],
                "customer_name": "John Doe",
                "customer_phone": "9876543210",
                "discount_amount": 50,
                "discount_reason": "Regular customer discount"
            }
        }


class BillResponse(BaseModel):
    """Schema for bill in response."""

    id: str
    invoice_number: Optional[str] = None
    status: BillStatus

    # Customer info
    customer_id: Optional[str] = None
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None

    # Amounts (in paise)
    subtotal: int
    discount_amount: int
    tax_amount: int
    cgst_amount: int
    sgst_amount: int
    total_amount: int
    rounded_total: int
    rounding_adjustment: int
    tip_amount: int = 0
    tip_staff_id: Optional[str] = None

    # Items
    items: List[BillItemResponse] = []

    # Timestamps
    created_at: datetime
    posted_at: Optional[datetime] = None

    # Creator
    created_by: str

    class Config:
        from_attributes = True

    @property
    def subtotal_rupees(self) -> float:
        """Get subtotal in rupees."""
        return self.subtotal / 100.0

    @property
    def discount_rupees(self) -> float:
        """Get discount in rupees."""
        return self.discount_amount / 100.0

    @property
    def total_rupees(self) -> float:
        """Get total in rupees."""
        return self.rounded_total / 100.0


class PaymentCreate(BaseModel):
    """Schema for creating a payment."""

    method: PaymentMethod = Field(..., description="Payment method")
    amount: float = Field(..., gt=0, description="Payment amount in rupees")
    reference_number: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = Field(None, max_length=500)

    class Config:
        json_schema_extra = {
            "example": {
                "method": "cash",
                "amount": 1470.00,
                "reference_number": "UPI123456",
                "notes": "Paid via PhonePe"
            }
        }


class PaymentResponse(BaseModel):
    """Schema for payment in response."""

    id: str
    bill_id: str
    payment_method: PaymentMethod
    amount: int  # paise
    reference_number: Optional[str] = None
    notes: Optional[str] = None
    confirmed_at: datetime
    confirmed_by: str

    class Config:
        from_attributes = True

    @property
    def amount_rupees(self) -> float:
        """Get amount in rupees."""
        return self.amount / 100.0


class PaymentResponseWithBill(PaymentResponse):
    """Payment response including updated bill status."""

    bill_status: BillStatus
    invoice_number: Optional[str] = None


class VoidCreate(BaseModel):
    """Schema for voiding a bill."""

    reason: Optional[str] = Field(None, max_length=500, description="Reason for voiding")

    class Config:
        json_schema_extra = {
            "example": {
                "reason": "Customer cancelled appointment"
            }
        }


class RefundCreate(BaseModel):
    """Schema for creating a refund."""

    reason: str = Field(..., min_length=1, max_length=500, description="Reason for refund")
    notes: Optional[str] = Field(None, max_length=500)

    class Config:
        json_schema_extra = {
            "example": {
                "reason": "Customer dissatisfaction with service",
                "notes": "Issue with hair color result"
            }
        }


class RefundResponse(BaseModel):
    """Schema for refund response."""

    refund_bill_id: str
    original_bill_id: str
    original_invoice_number: str
    refund_invoice_number: str
    refund_amount: int  # paise (will be negative)
    status: BillStatus
    refunded_at: datetime

    class Config:
        from_attributes = True

    @property
    def refund_amount_rupees(self) -> float:
        """Get refund amount in rupees."""
        return abs(self.refund_amount) / 100.0


class BillListItem(BaseModel):
    """Simplified bill schema for list views."""

    id: str
    invoice_number: Optional[str] = None
    status: BillStatus
    customer_name: Optional[str] = None
    rounded_total: int  # paise
    created_at: datetime
    posted_at: Optional[datetime] = None

    class Config:
        from_attributes = True

    @property
    def total_rupees(self) -> float:
        """Get total in rupees."""
        return self.rounded_total / 100.0


class BillListResponse(BaseModel):
    """Paginated bill list response."""

    bills: List[BillListItem]
    pagination: dict

    class Config:
        json_schema_extra = {
            "example": {
                "bills": [
                    {
                        "id": "01HXXX...",
                        "invoice_number": "SAL-25-0042",
                        "status": "posted",
                        "customer_name": "John Doe",
                        "rounded_total": 147000,
                        "created_at": "2025-10-15T10:30:00",
                        "posted_at": "2025-10-15T10:32:00"
                    }
                ],
                "pagination": {
                    "page": 1,
                    "limit": 50,
                    "total": 243,
                    "pages": 5
                }
            }
        }
