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
from app.models.pending_payment import PendingPaymentCollection

# Service Catalog
from app.models.service import ServiceCategory, Service, ServiceAddon, ServiceMaterialUsage, ServiceStaffTemplate

# Appointments
from app.models.appointment import Appointment, AppointmentStatus, WalkIn

# Billing
from app.models.billing import Bill, BillItem, BillItemStaffContribution, BillStatus, Payment, PaymentMethod

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

# Expenses
from app.models.expense import Expense, ExpenseCategory, RecurrenceType, ExpenseStatus

# Purchases
from app.models.purchase import PurchaseInvoice, PurchaseItem, SupplierPayment, PurchaseStatus

# Reconciliation
from app.models.reconciliation import DailyReconciliation

# Audit
from app.models.audit import Event, AuditLog

# Settings
from app.models.settings import SalonSettings

# Attendance
from app.models.attendance import Attendance, AttendanceStatus

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
    "PendingPaymentCollection",
    # Service
    "ServiceCategory",
    "Service",
    "ServiceAddon",
    "ServiceMaterialUsage",
    "ServiceStaffTemplate",
    # Appointment
    "Appointment",
    "AppointmentStatus",
    "WalkIn",
    # Billing
    "Bill",
    "BillItem",
    "BillItemStaffContribution",
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
    # Expenses
    "Expense",
    "ExpenseCategory",
    "RecurrenceType",
    "ExpenseStatus",
    # Purchases
    "PurchaseInvoice",
    "PurchaseItem",
    "SupplierPayment",
    "PurchaseStatus",
    # Reconciliation
    "DailyReconciliation",
    # Audit
    "Event",
    "AuditLog",
    # Settings
    "SalonSettings",
    # Attendance
    "Attendance",
    "AttendanceStatus",
]