"""Pydantic schemas for purchase management."""

from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict

from app.models.purchase import PurchaseStatus


# ============ Supplier Schemas ============

class SupplierBase(BaseModel):
    """Base supplier fields."""
    name: str = Field(..., min_length=1, max_length=255)
    contact_person: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=20)
    email: Optional[str] = Field(None, max_length=255)
    address: Optional[str] = None
    gstin: Optional[str] = Field(None, max_length=15)
    payment_terms: Optional[str] = Field(None, max_length=255)
    notes: Optional[str] = None


class SupplierCreate(SupplierBase):
    """Schema for creating a supplier."""
    pass


class SupplierUpdate(BaseModel):
    """Schema for updating a supplier."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    contact_person: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    gstin: Optional[str] = None
    payment_terms: Optional[str] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None


class SupplierResponse(SupplierBase):
    """Schema for supplier response."""
    id: str
    is_active: bool
    total_outstanding: int  # Calculated property
    total_purchases: int  # Calculated property
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SupplierListItem(BaseModel):
    """Schema for supplier in list view."""
    id: str
    name: str
    contact_person: Optional[str]
    phone: Optional[str]
    total_outstanding: int
    total_purchases: int
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class SupplierListResponse(BaseModel):
    """Paginated supplier list."""
    items: List[SupplierListItem]
    total: int
    page: int
    size: int
    pages: int


# ============ Purchase Item Schemas ============

class PurchaseItemBase(BaseModel):
    """Base purchase item fields."""
    sku_id: Optional[str] = None  # Optional link to existing SKU
    product_name: str = Field(..., min_length=1, max_length=255)
    barcode: Optional[str] = Field(None, max_length=100)
    uom: str = Field(..., max_length=20)
    quantity: Decimal = Field(..., gt=0)
    unit_cost: int = Field(..., gt=0)  # In paise
    discount_amount: int = Field(0, ge=0)  # Discount in paise


class PurchaseItemCreate(PurchaseItemBase):
    """Schema for creating a purchase item."""
    pass


class PurchaseItemResponse(PurchaseItemBase):
    """Schema for purchase item response."""
    id: str
    purchase_invoice_id: str
    total_cost: int  # Calculated
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============ Purchase Invoice Schemas ============

class PurchaseInvoiceBase(BaseModel):
    """Base purchase invoice fields."""
    supplier_id: str
    invoice_number: str = Field(..., min_length=1, max_length=100)
    invoice_date: date
    due_date: Optional[date] = None
    notes: Optional[str] = None
    invoice_file_url: Optional[str] = Field(None, max_length=500)


class PurchaseInvoiceCreate(PurchaseInvoiceBase):
    """Schema for creating a purchase invoice."""
    items: List[PurchaseItemCreate] = Field(..., min_items=1)
    invoice_discount_amount: int = Field(0, ge=0)  # Invoice-level discount in paise


class PurchaseInvoiceUpdate(BaseModel):
    """Schema for updating a purchase invoice (draft only)."""
    invoice_number: Optional[str] = None
    invoice_date: Optional[date] = None
    due_date: Optional[date] = None
    notes: Optional[str] = None
    invoice_file_url: Optional[str] = None
    items: Optional[List[PurchaseItemCreate]] = None


class PurchaseInvoiceEditRequest(BaseModel):
    """Schema for editing invoice with discounts (any status)."""
    items: List[PurchaseItemCreate] = Field(..., min_items=1)
    invoice_discount_amount: int = Field(0, ge=0)  # Invoice-level discount in paise
    notes: Optional[str] = None


class PurchaseInvoiceResponse(PurchaseInvoiceBase):
    """Schema for purchase invoice response."""
    id: str
    subtotal: int  # Sum of items before invoice discount
    invoice_discount_amount: int  # Invoice-level discount
    total_amount: int  # In paise (after discounts)
    paid_amount: int
    balance_due: int
    status: PurchaseStatus
    received_at: Optional[datetime]
    received_by: Optional[str]
    created_by: str
    created_at: datetime
    updated_at: datetime
    items: List[PurchaseItemResponse]

    # Supplier details
    supplier_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class PurchaseInvoiceListItem(BaseModel):
    """Schema for purchase invoice in list view."""
    id: str
    supplier_id: str
    supplier_name: str
    invoice_number: str
    invoice_date: date
    due_date: Optional[date]
    total_amount: int
    paid_amount: int
    balance_due: int
    status: PurchaseStatus
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PurchaseInvoiceListResponse(BaseModel):
    """Paginated purchase invoice list."""
    items: List[PurchaseInvoiceListItem]
    total: int
    page: int
    size: int
    pages: int


# ============ Supplier Payment Schemas ============

class SupplierPaymentBase(BaseModel):
    """Base supplier payment fields."""
    supplier_id: str
    purchase_invoice_id: Optional[str] = None  # Optional: can be general payment
    payment_date: date
    amount: int = Field(..., gt=0)  # In paise
    payment_method: str = Field(..., max_length=50)
    reference_number: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = None


class SupplierPaymentCreate(SupplierPaymentBase):
    """Schema for creating a supplier payment."""
    pass


class SupplierPaymentResponse(SupplierPaymentBase):
    """Schema for supplier payment response."""
    id: str
    recorded_by: str
    recorded_at: datetime
    created_at: datetime

    # Additional details
    supplier_name: Optional[str] = None
    invoice_number: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class SupplierPaymentListResponse(BaseModel):
    """Paginated supplier payment list."""
    items: List[SupplierPaymentResponse]
    total: int
    page: int
    size: int
    pages: int


# ============ Action Schemas ============

class GoodsReceiptRequest(BaseModel):
    """Schema for marking goods as received."""
    received_at: Optional[datetime] = None  # Defaults to now if not provided


class BarcodeSearchRequest(BaseModel):
    """Schema for searching product by barcode."""
    barcode: str = Field(..., min_length=1, max_length=100)


class BarcodeSearchResponse(BaseModel):
    """Schema for barcode search result."""
    found: bool
    sku_id: Optional[str] = None
    product_name: Optional[str] = None
    barcode: Optional[str] = None
    avg_cost_per_unit: Optional[int] = None  # Last known cost
    uom: Optional[str] = None
    current_stock: Optional[Decimal] = None
