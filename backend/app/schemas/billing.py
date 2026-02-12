"""Pydantic schemas for billing API requests and responses.

These schemas validate incoming requests and serialize outgoing responses
for the POS billing endpoints.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, model_validator
from app.models.billing import BillStatus, PaymentMethod
from enum import Enum


class ContributionSplitTypeEnum(str, Enum):
    """How contribution is calculated for multi-staff services."""
    PERCENTAGE = "percentage"
    FIXED = "fixed"
    EQUAL = "equal"
    TIME_BASED = "time_based"
    HYBRID = "hybrid"


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


class BillItemStaffContributionCreate(BaseModel):
    """Schema for creating staff contribution on a bill item (for multi-staff services)."""

    staff_id: str = Field(..., min_length=26, max_length=26, description="Staff member ID")
    role_in_service: str = Field(..., min_length=1, max_length=100, description="Role/task performed")
    sequence_order: int = Field(..., ge=1, description="Order in workflow")
    contribution_split_type: ContributionSplitTypeEnum = Field(default=ContributionSplitTypeEnum.PERCENTAGE)
    contribution_percent: Optional[int] = Field(None, ge=0, le=100, description="Percentage for PERCENTAGE/HYBRID")
    contribution_fixed: Optional[int] = Field(None, gt=0, description="Fixed amount in paise for FIXED")
    time_spent_minutes: Optional[int] = Field(None, gt=0, description="Time spent (for TIME_BASED/HYBRID)")
    notes: Optional[str] = Field(None, max_length=500)

    class Config:
        json_schema_extra = {
            "example": {
                "staff_id": "01HXXX1234567890ABCDEFGHIJ",
                "role_in_service": "Botox Application",
                "sequence_order": 1,
                "contribution_split_type": "percentage",
                "contribution_percent": 50,
                "time_spent_minutes": 30
            }
        }


class BillItemStaffContributionResponse(BaseModel):
    """Schema for staff contribution in response."""

    id: str
    bill_item_id: str
    staff_id: str
    role_in_service: str
    sequence_order: int
    contribution_split_type: str
    contribution_percent: Optional[int] = None
    contribution_fixed: Optional[int] = None
    contribution_amount: int  # Calculated actual paise earned
    time_spent_minutes: Optional[int] = None
    base_percent_component: Optional[int] = None
    time_component: Optional[int] = None
    skill_component: Optional[int] = None
    notes: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

    @property
    def contribution_rupees(self) -> float:
        """Get contribution amount in rupees."""
        return self.contribution_amount / 100.0


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
    staff_contributions: List[BillItemStaffContributionResponse] = []  # Multi-staff tracking

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


class BillItemCreateWithContributions(BillItemCreate):
    """Extended bill item creation schema with multi-staff contributions."""

    staff_contributions: Optional[List[BillItemStaffContributionCreate]] = Field(
        default=None,
        description="Multiple staff contributions (use this for multi-person services instead of staff_id)"
    )

    @model_validator(mode='after')
    def validate_staff_assignment(self):
        """Ensure either staff_id OR staff_contributions is set, not both."""
        if self.staff_id and self.staff_contributions:
            raise ValueError("Cannot specify both staff_id and staff_contributions. Use staff_contributions for multi-person services.")
        return self


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


class PaymentCreate(BaseModel):
    """Schema for creating a payment."""

    method: PaymentMethod = Field(..., description="Payment method")
    amount: float = Field(..., ge=0, description="Payment amount in rupees (can be 0 for free services)")
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


class PaymentUpdate(BaseModel):
    """Schema for updating a payment."""

    method: Optional[PaymentMethod] = Field(None, description="Payment method")
    amount: Optional[float] = Field(None, ge=0, description="Payment amount in rupees (can be 0 for free services)")
    reference_number: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = Field(None, max_length=500)

    class Config:
        json_schema_extra = {
            "example": {
                "method": "upi",
                "amount": 1500.00,
                "reference_number": "UPI987654",
                "notes": "Updated payment method"
            }
        }


class PaymentResponseWithBill(PaymentResponse):
    """Payment response including updated bill status."""

    bill_status: BillStatus
    invoice_number: Optional[str] = None


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

    # Payments
    payments: List[PaymentResponse] = []

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

    @property
    def total_paid(self) -> int:
        """Get total amount paid in paise."""
        return sum(payment.amount for payment in self.payments)

    @property
    def total_paid_rupees(self) -> float:
        """Get total amount paid in rupees."""
        return self.total_paid / 100.0

    @property
    def pending_balance(self) -> int:
        """Get pending balance in paise."""
        return max(0, self.rounded_total - self.total_paid)

    @property
    def pending_balance_rupees(self) -> float:
        """Get pending balance in rupees."""
        return self.pending_balance / 100.0


class CompleteBillCreate(BaseModel):
    """Schema for completing a bill with pending balance."""

    notes: Optional[str] = Field(None, max_length=500, description="Notes about pending payment")

    class Config:
        json_schema_extra = {
            "example": {
                "notes": "Family member - balance to be collected later"
            }
        }


class PendingPaymentCollect(BaseModel):
    """Schema for collecting pending payment from customer."""

    customer_id: str = Field(..., min_length=26, max_length=26, description="Customer ID")
    amount: float = Field(..., gt=0, description="Amount to collect in rupees")
    payment_method: PaymentMethod = Field(..., description="Payment method")
    reference_number: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = Field(None, max_length=500)

    class Config:
        json_schema_extra = {
            "example": {
                "customer_id": "01HXXX1234567890ABCDEFGHIJ",
                "amount": 500.00,
                "payment_method": "cash",
                "notes": "Collected pending balance"
            }
        }


class PendingPaymentCollectionResponse(BaseModel):
    """Schema for pending payment collection response."""

    id: str
    customer_id: str
    amount: int  # in paise
    payment_method: PaymentMethod
    reference_number: Optional[str] = None
    notes: Optional[str] = None
    bill_id: Optional[str] = None  # If collected via overpayment
    collected_by: str
    collected_at: datetime
    previous_balance: int  # in paise
    new_balance: int  # in paise

    class Config:
        from_attributes = True

    @property
    def amount_rupees(self) -> float:
        """Get amount in rupees."""
        return self.amount / 100.0

    @property
    def previous_balance_rupees(self) -> float:
        """Get previous balance in rupees."""
        return self.previous_balance / 100.0

    @property
    def new_balance_rupees(self) -> float:
        """Get new balance in rupees."""
        return self.new_balance / 100.0


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
