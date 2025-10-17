"""
SQLAlchemy Models for SalonOS

All models are imported here so Alembic can detect them for migrations.
"""
from app.database import Base
from app.models.base import TimestampMixin, SoftDeleteMixin, ULIDMixin

# User & Access Control
from app.models.user import Role, RoleEnum, User, Staff

# Customer
from app.models.customer import Customer

# Service Catalog
from app.models.service import ServiceCategory, Service, ServiceAddon

# Appointments
from app.models.appointment import Appointment, AppointmentStatus, WalkIn

# Billing
from app.models.billing import Bill, BillItem, BillStatus, Payment, PaymentMethod

# Inventory
from app.models.inventory import (
    InventoryCategory,
    Supplier,
    SKU,
    UOMEnum,
    InventoryChangeRequest,
    ChangeType,
    ChangeStatus,
    StockLedger,
)

# Accounting
from app.models.accounting import CashDrawer, DaySummary, ExportLog

# Audit
from app.models.audit import Event, AuditLog

__all__ = [
    # Base
    "Base",
    "TimestampMixin",
    "SoftDeleteMixin",
    "ULIDMixin",
    # User
    "Role",
    "RoleEnum",
    "User",
    "Staff",
    # Customer
    "Customer",
    # Service
    "ServiceCategory",
    "Service",
    "ServiceAddon",
    # Appointment
    "Appointment",
    "AppointmentStatus",
    "WalkIn",
    # Billing
    "Bill",
    "BillItem",
    "BillStatus",
    "Payment",
    "PaymentMethod",
    # Inventory
    "InventoryCategory",
    "Supplier",
    "SKU",
    "UOMEnum",
    "InventoryChangeRequest",
    "ChangeType",
    "ChangeStatus",
    "StockLedger",
    # Accounting
    "CashDrawer",
    "DaySummary",
    "ExportLog",
    # Audit
    "Event",
    "AuditLog",
]