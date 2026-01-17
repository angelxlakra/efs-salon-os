# SalonOS Database Models

Comprehensive documentation for all SQLAlchemy models in the SalonOS backend.

---

## Overview

SalonOS uses **SQLAlchemy 2.0** with **PostgreSQL 15** for data persistence. All models follow consistent conventions for IDs, timestamps, and soft deletion.

### Model Count Summary

| Domain | Models | Tables |
|--------|--------|--------|
| User & Auth | 3 | `roles`, `users`, `staff` |
| Customer | 1 | `customers` |
| Services | 3 | `service_categories`, `services`, `service_addons` |
| Appointments | 2 | `appointments`, `walkins` |
| Billing | 3 | `bills`, `bill_items`, `payments` |
| Inventory | 4 | `inventory_categories`, `suppliers`, `skus`, `stock_ledger`, `inventory_change_requests` |
| Accounting | 3 | `cash_drawer`, `day_summary`, `export_log` |
| Audit | 2 | `events`, `audit_log` |
| **Total** | **21+** | **21+ tables** |

---

## Documentation Index

| # | Document | Description |
|---|----------|-------------|
| 01 | [Base Mixins](./01-base-mixins.md) | TimestampMixin, SoftDeleteMixin, ULIDMixin |
| 02 | [User & Auth](./02-user-auth.md) | Role, User, Staff models |
| 03 | [Billing](./03-billing.md) | Bill, BillItem, Payment models |
| 04 | [Appointments](./04-appointments.md) | Appointment, WalkIn models |
| 05 | [Services](./05-services.md) | ServiceCategory, Service, ServiceAddon |
| 06 | [Customers](./06-customers.md) | Customer model |
| 07 | [Inventory](./07-inventory.md) | SKU, Supplier, ChangeRequest, StockLedger |
| 08 | [Accounting](./08-accounting.md) | CashDrawer, DaySummary, ExportLog |
| 09 | [Audit](./09-audit.md) | Event, AuditLog models |

---

## Core Conventions

### Primary Keys: ULID

All tables use **ULID** (Universally Unique Lexicographically Sortable Identifier) as primary keys.

```
Format: 01HXXX1234ABCD567890EFGH (26 characters)
        └──┬──┘└───────┬───────┘
       Timestamp    Randomness
```

**Benefits:**
- Time-sortable (better index performance)
- No sequential guessing
- URL-safe (no special characters)
- Shorter than UUID (26 vs 36 chars)

### Money: Integer Paise

All monetary values stored as **integers in paise** (100 paise = Rs 1).

```python
# Storing Rs 1,500.50
amount_paise = 150050  # Integer

# Displaying
amount_rupees = amount_paise / 100.0  # 1500.50
```

**Why?**
- Avoids floating-point precision errors
- Consistent across all calculations
- Industry standard for financial systems

### Timestamps: UTC Storage, IST Display

```python
# Stored in database (UTC)
created_at = "2025-10-15T05:00:00+00:00"

# Displayed to user (IST = UTC+5:30)
created_at = "2025-10-15T10:30:00+05:30"
```

### Soft Delete

Entities that need historical preservation use soft delete:

```python
# Soft delete
record.deleted_at = datetime.utcnow()

# Query active records
Model.deleted_at.is_(None)
```

**Soft-deleted models:** User, Customer, Service

---

## Entity Relationship Diagram (Summary)

```
                    ┌──────────┐
                    │   Role   │
                    └────┬─────┘
                         │ 1:N
                         ▼
┌──────────┐        ┌──────────┐        ┌──────────┐
│ Customer │◄───────│   User   │───────►│  Staff   │
└────┬─────┘   N:1  └────┬─────┘   1:1  └────┬─────┘
     │                   │                   │
     │              ┌────┴────┐              │
     │              ▼         ▼              │
     │         ┌────────┐ ┌────────┐         │
     │         │  Bill  │ │Appoint.│◄────────┘
     │         └───┬────┘ └────────┘
     │             │
     └─────────────┘
                   │
                   ▼
            ┌────────────┐
            │  BillItem  │────────►┌─────────┐
            └────────────┘         │ Service │
                   │               └─────────┘
                   ▼                    │
            ┌────────────┐              ▼
            │  Payment   │        ┌────────────┐
            └────────────┘        │ServiceAddon│
                                  └────────────┘

┌──────────────┐     ┌──────────┐     ┌─────────────┐
│InventoryCat. │────►│   SKU    │◄────│  Supplier   │
└──────────────┘     └────┬─────┘     └─────────────┘
                          │
              ┌───────────┼───────────┐
              ▼           ▼           ▼
        ┌──────────┐ ┌──────────┐ ┌──────────┐
        │ChangeReq │ │StockLedger│ │   ...    │
        └──────────┘ └──────────┘ └──────────┘

┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  CashDrawer  │     │  DaySummary  │     │  ExportLog   │
└──────────────┘     └──────────────┘     └──────────────┘

┌──────────────┐     ┌──────────────┐
│    Event     │     │   AuditLog   │
└──────────────┘     └──────────────┘
```

---

## Numbering Conventions

### Invoice Numbers

```
SAL-YY-NNNN
│   │   │
│   │   └─ Sequential (0001-9999)
│   └───── Two-digit year
└───────── Prefix

Example: SAL-25-0042
Reset: April 1st (fiscal year)
```

### Ticket Numbers

```
TKT-YYMMDD-###
│   │      │
│   │      └─ Daily sequential (001-999)
│   └──────── Date (YYMMDD)
└──────────── Prefix

Example: TKT-251015-001
Reset: Daily at midnight
```

---

## Enumerations Reference

| Enum | Values | Used In |
|------|--------|---------|
| `RoleEnum` | owner, receptionist, staff | Role.name |
| `BillStatus` | draft, posted, refunded, void | Bill.status |
| `PaymentMethod` | cash, upi, card, other | Payment.payment_method |
| `AppointmentStatus` | scheduled, checked_in, in_progress, completed, cancelled, no_show | Appointment.status, WalkIn.status |
| `UOMEnum` | piece, ml, gm, kg, liter, box, bottle | SKU.uom |
| `ChangeType` | receive, adjust, consume | InventoryChangeRequest.change_type |
| `ChangeStatus` | pending, approved, rejected | InventoryChangeRequest.status |

---

## Common Query Patterns

### Active Records (Not Deleted)

```python
active_customers = db.query(Customer).filter(
    Customer.deleted_at.is_(None)
).all()
```

### Today's Bills

```python
from datetime import datetime, time

today_start = datetime.combine(datetime.today(), time.min)
today_end = datetime.combine(datetime.today(), time.max)

today_bills = db.query(Bill).filter(
    Bill.posted_at >= today_start,
    Bill.posted_at <= today_end,
    Bill.status == BillStatus.POSTED
).all()
```

### Low Stock Items

```python
low_stock = db.query(SKU).filter(
    SKU.is_active == True,
    SKU.current_stock <= SKU.reorder_point
).all()
```

### Customer Lookup by Phone

```python
customer = db.query(Customer).filter(
    Customer.phone == phone_number,
    Customer.deleted_at.is_(None)
).first()
```

---

## Migration Commands

```bash
# Create new migration
uv run alembic revision --autogenerate -m "Add new field"

# Apply migrations
uv run alembic upgrade head

# Rollback one version
uv run alembic downgrade -1

# Show current version
uv run alembic current

# Show history
uv run alembic history
```

---

## Model Imports

All models are exported from `app.models`:

```python
from app.models import (
    # Base
    Base, TimestampMixin, SoftDeleteMixin, ULIDMixin,

    # User & Auth
    Role, RoleEnum, User, Staff,

    # Customer
    Customer,

    # Services
    ServiceCategory, Service, ServiceAddon,

    # Appointments
    Appointment, AppointmentStatus, WalkIn,

    # Billing
    Bill, BillItem, BillStatus, Payment, PaymentMethod,

    # Inventory
    InventoryCategory, Supplier, SKU, UOMEnum,
    InventoryChangeRequest, ChangeType, ChangeStatus, StockLedger,

    # Accounting
    CashDrawer, DaySummary, ExportLog,

    # Audit
    Event, AuditLog,
)
```

---

## File Structure

```
backend/app/models/
├── __init__.py        # Exports all models
├── base.py            # Mixins (Timestamp, SoftDelete, ULID)
├── user.py            # Role, User, Staff
├── customer.py        # Customer
├── service.py         # ServiceCategory, Service, ServiceAddon
├── appointment.py     # Appointment, WalkIn
├── billing.py         # Bill, BillItem, Payment
├── inventory.py       # InventoryCategory, Supplier, SKU, etc.
├── accounting.py      # CashDrawer, DaySummary, ExportLog
└── audit.py           # Event, AuditLog
```

---

## Related Documentation

- [API Contracts](../api/) - REST API specifications
- [Authentication](../auth/) - JWT and RBAC details
- [Business Logic](../services/) - Service layer documentation
- [Deployment](../deployment/) - Docker and infrastructure

---

**Last Updated**: October 2025
**Models Version**: 1.0
**Database**: PostgreSQL 15
