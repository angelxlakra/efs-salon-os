from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field, condecimal

from app.models.inventory import UOMEnum, ChangeType, ChangeStatus

# --- Supplier Schemas ---

class SupplierBase(BaseModel):
    name: str
    contact_person: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    notes: Optional[str] = None
    is_active: bool = True

class SupplierCreate(SupplierBase):
    pass

class SupplierUpdate(BaseModel):
    name: Optional[str] = None
    contact_person: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None

class SupplierResponse(SupplierBase):
    id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# --- Category Schemas ---

class CategoryBase(BaseModel):
    name: str
    description: Optional[str] = None

class CategoryCreate(CategoryBase):
    pass

class CategoryResponse(CategoryBase):
    id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# --- SKU Schemas ---

class SKUBase(BaseModel):
    sku_code: str
    name: str
    description: Optional[str] = None
    brand_name: Optional[str] = None
    volume: Optional[str] = None
    uom: UOMEnum
    reorder_point: float = Field(default=0, ge=0)
    category_id: str
    supplier_id: Optional[str] = None
    is_active: bool = True
    # Retail fields
    is_sellable: bool = False
    retail_price: Optional[int] = None  # in paise
    retail_markup_percent: Optional[float] = None

class SKUCreate(SKUBase):
    pass

class SKUUpdate(BaseModel):
    sku_code: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    brand_name: Optional[str] = None
    volume: Optional[str] = None
    barcode: Optional[str] = None
    uom: Optional[UOMEnum] = None
    reorder_point: Optional[float] = Field(None, ge=0)
    category_id: Optional[str] = None
    supplier_id: Optional[str] = None
    is_active: Optional[bool] = None
    # Retail fields
    is_sellable: Optional[bool] = None
    retail_price: Optional[int] = None  # in paise
    retail_markup_percent: Optional[float] = None

class SKUResponse(SKUBase):
    id: str
    barcode: Optional[str] = None
    current_stock: float
    avg_cost_per_unit: int  # in paise
    is_low_stock: bool
    created_at: datetime
    updated_at: datetime

    # Nested responses for convenience (optional, depending on pattern)
    category_name: Optional[str] = None
    supplier_name: Optional[str] = None

    class Config:
        from_attributes = True

class SKUListResponse(BaseModel):
    items: List[SKUResponse]
    total: int
    page: int
    size: int

# --- Change Request Schemas ---

class ChangeRequestCreate(BaseModel):
    sku_id: str
    change_type: ChangeType
    quantity: float = Field(..., gt=0)
    unit_cost: Optional[int] = None  # in paise, required for RECEIVE
    supplier_invoice_number: Optional[str] = Field(None, max_length=100, description="Supplier invoice number")
    supplier_discount_percent: Optional[float] = Field(None, ge=0, le=100, description="Supplier discount percentage")
    supplier_discount_fixed: Optional[int] = Field(None, ge=0, description="Supplier fixed discount in paise")
    reason_code: str
    notes: Optional[str] = None

class ChangeRequestResponse(BaseModel):
    id: str
    sku_id: str
    change_type: ChangeType
    quantity: float
    unit_cost: Optional[int]
    supplier_invoice_number: Optional[str] = None
    supplier_discount_percent: Optional[float] = None
    supplier_discount_fixed: Optional[int] = None
    reason_code: str
    notes: Optional[str]
    status: ChangeStatus
    requested_by: str
    requested_at: datetime
    reviewed_by: Optional[str]
    reviewed_at: Optional[datetime]
    review_notes: Optional[str]

    # Include SKU details for display
    sku_code: Optional[str] = None
    sku_name: Optional[str] = None
    requester_name: Optional[str] = None

    class Config:
        from_attributes = True

# --- Stock Ledger Schemas ---

class LedgerEntryResponse(BaseModel):
    id: str
    sku_id: str
    change_request_id: Optional[str]
    transaction_type: str
    quantity_change: float
    quantity_after: float
    unit_cost: Optional[int]
    total_value: Optional[int]
    created_by: str
    created_at: datetime
    notes: Optional[str]
    
    sku_name: Optional[str] = None
    creator_name: Optional[str] = None

    class Config:
        from_attributes = True
