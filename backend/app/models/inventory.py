"""Inventory models for SKU management, suppliers, and stock tracking."""

import enum
from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import relationship
from app.database import Base
from app.models.base import TimestampMixin, ULIDMixin


class UOMEnum(str, enum.Enum):
    """Unit of Measurement types."""
    PIECE = "piece"
    ML = "ml"
    GM = "gm"
    KG = "kg"
    LITER = "liter"
    BOX = "box"
    BOTTLE = "bottle"


class ChangeType(str, enum.Enum):
    """Types of inventory changes."""
    RECEIVE = "receive"
    ADJUST = "adjust"
    CONSUME = "consume"


class ChangeStatus(str, enum.Enum):
    """Status of inventory change requests."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class InventoryCategory(Base, ULIDMixin, TimestampMixin):
    """Categories for organizing inventory items."""
    __tablename__ = "inventory_categories"

    name = Column(String, nullable=False, unique=True)
    description = Column(Text)

    # Relationships
    skus = relationship("SKU", back_populates="category")

    def __repr__(self):
        return f"<InventoryCategory {self.name}>"


class Supplier(Base, ULIDMixin, TimestampMixin):
    """Supplier information for inventory procurement."""
    __tablename__ = "suppliers"

    name = Column(String, nullable=False)
    contact_person = Column(String)
    phone = Column(String)
    email = Column(String)
    address = Column(Text)
    notes = Column(Text)
    is_active = Column(Boolean, nullable=False, default=True)

    # Business details
    gstin = Column(String(15))  # GST Identification Number
    payment_terms = Column(String(255))  # e.g., "Net 30", "50% advance, 50% on delivery"

    # Relationships
    skus = relationship("SKU", back_populates="supplier")
    purchase_invoices = relationship("PurchaseInvoice", back_populates="supplier")
    payments = relationship("SupplierPayment", back_populates="supplier")

    @property
    def total_outstanding(self) -> int:
        """Calculate total outstanding balance across all invoices."""
        return sum(invoice.balance_due for invoice in self.purchase_invoices if invoice.balance_due > 0)

    @property
    def total_purchases(self) -> int:
        """Calculate total purchase amount from this supplier."""
        return sum(invoice.total_amount for invoice in self.purchase_invoices)

    def __repr__(self):
        return f"<Supplier {self.name}>"


class SKU(Base, ULIDMixin, TimestampMixin):
    """
    Stock Keeping Unit - individual inventory items.

    Tracks quantity, costs, and reorder points.
    """
    __tablename__ = "skus"

    category_id = Column(String(26), ForeignKey("inventory_categories.id"), nullable=False, index=True)
    supplier_id = Column(String(26), ForeignKey("suppliers.id"), index=True)

    sku_code = Column(String, nullable=False, unique=True)
    name = Column(String, nullable=False)
    description = Column(Text)
    brand_name = Column(String(255))  # Brand/manufacturer name
    volume = Column(String(50))  # Product volume/size (e.g., "500ml", "100gm")
    barcode = Column(String(100), index=True)  # Product barcode for purchase lookup

    uom = Column(Enum(UOMEnum), nullable=False)
    reorder_point = Column(Numeric(10, 2), nullable=False, default=0)
    current_stock = Column(Numeric(10, 2), nullable=False, default=0, index=True)

    # Weighted average cost in paise per UOM
    avg_cost_per_unit = Column(Integer, nullable=False, default=0)

    is_active = Column(Boolean, nullable=False, default=True, index=True)

    # Retail capability
    is_sellable = Column(Boolean, nullable=False, default=False, index=True)
    retail_price = Column(Integer, nullable=True)  # paise (tax-inclusive)
    retail_markup_percent = Column(Numeric(5, 2), nullable=True)

    # Relationships
    category = relationship("InventoryCategory", back_populates="skus")
    supplier = relationship("Supplier", back_populates="skus")
    change_requests = relationship("InventoryChangeRequest", back_populates="sku")
    ledger_entries = relationship("StockLedger", back_populates="sku")
    bill_items = relationship("BillItem", back_populates="sku")

    def __repr__(self):
        return f"<SKU {self.sku_code} - {self.name}>"

    @property
    def is_low_stock(self) -> bool:
        """Check if current stock is at or below reorder point."""
        return self.current_stock <= self.reorder_point


class InventoryChangeRequest(Base, ULIDMixin, TimestampMixin):
    """
    Requests for inventory changes requiring approval.

    Owner approval needed before stock changes are applied.
    """
    __tablename__ = "inventory_change_requests"

    sku_id = Column(String(26), ForeignKey("skus.id"), nullable=False, index=True)

    change_type = Column(Enum(ChangeType), nullable=False)
    quantity = Column(Numeric(10, 2), nullable=False)

    # For receives: unit cost in paise
    unit_cost = Column(Integer)

    reason_code = Column(String, nullable=False)  # 'new_stock', 'correction', 'damage', etc.
    notes = Column(Text)

    status = Column(Enum(ChangeStatus), nullable=False, default=ChangeStatus.PENDING, index=True)

    requested_by = Column(String(26), ForeignKey("users.id"), nullable=False)
    requested_at = Column(DateTime(timezone=True), nullable=False)

    reviewed_by = Column(String(26), ForeignKey("users.id"))
    reviewed_at = Column(DateTime(timezone=True))
    review_notes = Column(Text)

    # Relationships
    sku = relationship("SKU", back_populates="change_requests")
    requester = relationship("User", foreign_keys=[requested_by])
    reviewer = relationship("User", foreign_keys=[reviewed_by])

    def __repr__(self):
        return f"<InventoryChangeRequest {self.change_type} - {self.status}>"


class StockLedger(Base, ULIDMixin, TimestampMixin):
    """
    Immutable audit trail of all stock movements.

    Every inventory change creates a ledger entry.
    """
    __tablename__ = "stock_ledger"

    sku_id = Column(String(26), ForeignKey("skus.id"), nullable=False, index=True)
    change_request_id = Column(String(26), ForeignKey("inventory_change_requests.id"))

    transaction_type = Column(String, nullable=False)  # 'receive', 'adjust', 'consume'
    quantity_change = Column(Numeric(10, 2), nullable=False)  # Can be negative
    quantity_after = Column(Numeric(10, 2), nullable=False)

    # Cost tracking
    unit_cost = Column(Integer)  # paise
    total_value = Column(Integer)  # paise
    avg_cost_after = Column(Integer)  # paise

    reference_type = Column(String)  # 'bill', 'service', etc.
    reference_id = Column(String(26))

    notes = Column(Text)
    created_by = Column(String(26), ForeignKey("users.id"), nullable=False)

    # Relationships
    sku = relationship("SKU", back_populates="ledger_entries")
    change_request = relationship("InventoryChangeRequest")
    creator = relationship("User", foreign_keys=[created_by])

    def __repr__(self):
        return f"<StockLedger {self.transaction_type} {self.quantity_change:+}>"
