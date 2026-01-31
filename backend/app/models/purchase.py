"""Purchase order and payment tracking models."""

from datetime import datetime, date
from decimal import Decimal
from enum import Enum as PyEnum

from sqlalchemy import Column, String, Integer, Text, Date, DateTime, ForeignKey, Enum, Numeric
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.base import ULIDMixin, TimestampMixin


class PurchaseStatus(str, PyEnum):
    """Purchase invoice status."""
    DRAFT = "draft"  # Invoice created but goods not received
    RECEIVED = "received"  # Goods received, unpaid
    PARTIALLY_PAID = "partially_paid"  # Some payment made
    PAID = "paid"  # Fully paid


class PurchaseInvoice(Base, ULIDMixin, TimestampMixin):
    """Purchase invoice from supplier."""

    __tablename__ = "purchase_invoices"

    # Supplier
    supplier_id = Column(String(26), ForeignKey("suppliers.id"), nullable=False, index=True)

    # Invoice details
    invoice_number = Column(String(100), nullable=False)
    invoice_date = Column(Date, nullable=False, index=True)
    due_date = Column(Date)

    # Amounts (in paise)
    total_amount = Column(Integer, nullable=False, default=0)
    paid_amount = Column(Integer, nullable=False, default=0)
    balance_due = Column(Integer, nullable=False, default=0)  # Auto-calculated

    # Status
    status = Column(Enum(PurchaseStatus), nullable=False, default=PurchaseStatus.DRAFT, index=True)

    # Goods receipt
    received_at = Column(DateTime)
    received_by = Column(String(26), ForeignKey("users.id"))

    # Notes and attachments
    notes = Column(Text)
    invoice_file_url = Column(String(500))  # Optional PDF/image upload

    # Audit
    created_by = Column(String(26), ForeignKey("users.id"), nullable=False)

    # Relationships
    supplier = relationship("Supplier", back_populates="purchase_invoices")
    items = relationship("PurchaseItem", back_populates="invoice", cascade="all, delete-orphan")
    payments = relationship("SupplierPayment", back_populates="invoice")
    receiver = relationship("User", foreign_keys=[received_by])
    creator = relationship("User", foreign_keys=[created_by])

    def calculate_totals(self):
        """Calculate total_amount from items."""
        self.total_amount = sum(item.total_cost for item in self.items)
        self.balance_due = self.total_amount - (self.paid_amount or 0)

    def update_status(self):
        """Update status based on payment."""
        paid = self.paid_amount or 0
        if paid == 0:
            if self.received_at:
                self.status = PurchaseStatus.RECEIVED
            else:
                self.status = PurchaseStatus.DRAFT
        elif paid >= self.total_amount:
            self.status = PurchaseStatus.PAID
        else:
            self.status = PurchaseStatus.PARTIALLY_PAID

    def __repr__(self):
        return f"<PurchaseInvoice {self.invoice_number}>"


class PurchaseItem(Base, ULIDMixin, TimestampMixin):
    """Line item in a purchase invoice."""

    __tablename__ = "purchase_items"

    # Invoice
    purchase_invoice_id = Column(String(26), ForeignKey("purchase_invoices.id"), nullable=False, index=True)

    # Product (optional link to existing SKU)
    sku_id = Column(String(26), ForeignKey("skus.id"), index=True)

    # Product details (always stored for record-keeping)
    product_name = Column(String(255), nullable=False)
    barcode = Column(String(100))  # For lookup and matching
    uom = Column(String(20))  # Unit of measure (pcs, kg, ml, etc.)

    # Quantity and pricing (in paise)
    quantity = Column(Numeric(10, 2), nullable=False)
    unit_cost = Column(Integer, nullable=False)  # Buying price per unit
    total_cost = Column(Integer, nullable=False)  # quantity × unit_cost

    # Relationships
    invoice = relationship("PurchaseInvoice", back_populates="items")
    sku = relationship("SKU")

    def calculate_total(self):
        """Calculate total_cost."""
        self.total_cost = int(Decimal(str(self.quantity)) * self.unit_cost)

    def __repr__(self):
        return f"<PurchaseItem {self.product_name} x{self.quantity}>"


class SupplierPayment(Base, ULIDMixin, TimestampMixin):
    """Payment made to supplier."""

    __tablename__ = "supplier_payments"

    # Supplier
    supplier_id = Column(String(26), ForeignKey("suppliers.id"), nullable=False, index=True)

    # Optional: Link to specific invoice (can also be general payment)
    purchase_invoice_id = Column(String(26), ForeignKey("purchase_invoices.id"), index=True)

    # Payment details
    payment_date = Column(Date, nullable=False, index=True)
    amount = Column(Integer, nullable=False)  # In paise

    # Payment method
    payment_method = Column(String(50), nullable=False)  # cash, upi, card, bank_transfer, cheque
    reference_number = Column(String(100))  # UPI transaction ID, cheque number, etc.

    # Notes
    notes = Column(Text)

    # Audit
    recorded_by = Column(String(26), ForeignKey("users.id"), nullable=False)
    recorded_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    supplier = relationship("Supplier", back_populates="payments")
    invoice = relationship("PurchaseInvoice", back_populates="payments")
    recorder = relationship("User")

    def __repr__(self):
        return f"<SupplierPayment {self.amount} to {self.supplier_id}>"
