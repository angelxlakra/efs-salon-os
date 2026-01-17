# Audit & Event Models

**File**: `backend/app/models/audit.py`

Models for event sourcing and comprehensive audit logging.

---

## Event

Event sourcing table for business events.

**Table**: `events`

**Mixins**: `ULIDMixin`, `TimestampMixin`

### Purpose

Records all significant business events for:
- **Audit trail**: Who did what and when
- **Event replay**: Reconstruct state from events
- **Analytics**: Track patterns and trends
- **Integration**: Trigger downstream actions

### Columns

| Column | Type | Nullable | Index | Description |
|--------|------|----------|-------|-------------|
| `id` | String(26) | No | PK | ULID primary key |
| `event_type` | String | No | Yes | Event type identifier |
| `aggregate_type` | String | No | Yes | Entity type (bill, appointment, etc.) |
| `aggregate_id` | String(26) | No | Yes | Entity ID |
| `payload` | JSONB | No | - | Event data |
| `event_metadata` | JSONB | Yes | - | Additional context |
| `created_at` | DateTime(tz) | No | - | Event timestamp |
| `updated_at` | DateTime(tz) | No | - | Last update (rarely changes) |

### Event Types

#### Billing Events

| Event Type | Trigger | Payload |
|------------|---------|---------|
| `bill.created` | Bill created as draft | bill_id, items, subtotal |
| `bill.posted` | Bill fully paid | bill_id, invoice_number, total, customer_id |
| `bill.refunded` | Refund processed | bill_id, refund_bill_id, amount, reason |
| `bill.voided` | Bill cancelled | bill_id, reason |

#### Payment Events

| Event Type | Trigger | Payload |
|------------|---------|---------|
| `payment.captured` | Payment recorded | payment_id, bill_id, method, amount |

#### Appointment Events

| Event Type | Trigger | Payload |
|------------|---------|---------|
| `appointment.created` | New booking | appointment_id, customer, service, time |
| `appointment.checked_in` | Customer arrived | appointment_id, checked_in_at |
| `appointment.started` | Service began | appointment_id, staff_id |
| `appointment.completed` | Service finished | appointment_id, completed_at |
| `appointment.cancelled` | Booking cancelled | appointment_id, reason |
| `appointment.no_show` | Customer didn't arrive | appointment_id |

#### Inventory Events

| Event Type | Trigger | Payload |
|------------|---------|---------|
| `inventory.requested` | Change request created | request_id, sku_id, type, quantity |
| `inventory.approved` | Owner approved change | request_id, sku_id, quantity_after |
| `inventory.rejected` | Owner rejected change | request_id, reason |

#### Day Close Events

| Event Type | Trigger | Payload |
|------------|---------|---------|
| `day.opened` | Cash drawer opened | drawer_id, opening_float |
| `day.closed` | Cash drawer closed | drawer_id, expected, counted, variance |
| `day.summary_generated` | Daily summary created | summary_id, date, revenue |

### Payload Examples

#### bill.posted

```json
{
  "bill_id": "01HXXX...",
  "invoice_number": "SAL-25-0042",
  "customer_id": "01HYYY...",
  "total_amount": 147000,
  "cgst": 11059,
  "sgst": 11059,
  "payment_methods": ["cash", "upi"],
  "items_count": 3
}
```

#### payment.captured

```json
{
  "payment_id": "01HAAA...",
  "bill_id": "01HXXX...",
  "method": "cash",
  "amount": 100000,
  "reference_number": null,
  "confirmed_by": "01HBBB..."
}
```

### Event Metadata

Additional context stored separately:

```json
{
  "user_id": "01HCCC...",
  "user_role": "receptionist",
  "ip_address": "192.168.1.10",
  "device_id": "reception-terminal-1",
  "request_id": "req_abc123",
  "timestamp_utc": "2025-10-15T05:02:00Z"
}
```

### Usage: Emitting Events

```python
from app.models import Event
from app.utils import generate_ulid
from datetime import datetime

def emit_event(db, event_type: str, payload: dict, metadata: dict = None):
    """Emit a business event."""
    aggregate_type, _ = event_type.split(".", 1)
    aggregate_id = payload.get(f"{aggregate_type}_id") or payload.get("id")

    event = Event(
        id=generate_ulid(),
        event_type=event_type,
        aggregate_type=aggregate_type,
        aggregate_id=aggregate_id,
        payload=payload,
        event_metadata=metadata
    )
    db.add(event)
    db.commit()
    return event
```

### Usage: Querying Events

```python
# Get all events for a bill
bill_events = db.query(Event).filter(
    Event.aggregate_type == "bill",
    Event.aggregate_id == bill_id
).order_by(Event.created_at).all()

# Get recent payment events
recent_payments = db.query(Event).filter(
    Event.event_type == "payment.captured",
    Event.created_at >= today_start
).all()
```

---

## AuditLog

Detailed audit trail of all user actions with before/after state.

**Table**: `audit_log`

**Mixins**: `ULIDMixin`, `TimestampMixin`

### Purpose

Provides detailed forensic-level logging for:
- **Compliance**: Prove who changed what
- **Investigation**: Debug issues
- **Security**: Detect anomalies
- **Recovery**: Understand state at any point

### Columns

| Column | Type | Nullable | Index | Description |
|--------|------|----------|-------|-------------|
| `id` | String(26) | No | PK | ULID primary key |
| `user_id` | String(26) | Yes | Yes | FK to users.id |
| `action` | String | No | - | Action type |
| `entity_type` | String | No | Yes | Type of entity |
| `entity_id` | String(26) | No | Yes | Entity ID |
| `old_values` | JSONB | Yes | - | State before change |
| `new_values` | JSONB | Yes | - | State after change |
| `ip_address` | String | Yes | - | Client IP |
| `user_agent` | String | Yes | - | Browser/client info |
| `device_id` | String | Yes | - | Device identifier |
| `created_at` | DateTime(tz) | No | - | Action timestamp |
| `updated_at` | DateTime(tz) | No | - | Last update |

### Relationships

| Relationship | Target | Type | Description |
|--------------|--------|------|-------------|
| `user` | User | Many-to-One | Who performed action |

### Actions

| Action | Description | Entities |
|--------|-------------|----------|
| `create` | New record created | All entities |
| `update` | Record modified | All entities |
| `delete` | Record removed | All entities |
| `approve` | Approval granted | Inventory, discounts |
| `reject` | Approval denied | Inventory, discounts |
| `login` | User authenticated | User sessions |
| `logout` | User signed out | User sessions |
| `export` | Data exported | Reports |

### Sensitive Operations

These operations **always** create audit logs:

| Operation | Entity Type | Details Logged |
|-----------|-------------|----------------|
| Discount applied | `discount` | Amount, reason, who approved |
| Refund processed | `refund` | Bill ID, amount, reason |
| Price override | `price_override` | Original price, new price |
| Inventory adjustment | `inventory` | SKU, quantity, reason |
| User role change | `user_role` | Old role, new role |
| Password reset | `password` | Who reset (not the password) |

### Before/After Snapshots

```json
// old_values
{
  "discount_amount": 0,
  "status": "draft"
}

// new_values
{
  "discount_amount": 5000,
  "discount_reason": "Regular customer",
  "status": "draft"
}
```

### Example Audit Log Entry

```json
{
  "id": "01HXXX...",
  "user_id": "01HYYY...",
  "action": "update",
  "entity_type": "bill",
  "entity_id": "01HZZZ...",
  "old_values": {
    "discount_amount": 0
  },
  "new_values": {
    "discount_amount": 5000,
    "discount_reason": "VIP customer discount"
  },
  "ip_address": "192.168.1.15",
  "user_agent": "Mozilla/5.0...",
  "device_id": "reception-01",
  "created_at": "2025-10-15T10:30:00+05:30"
}
```

### Usage: Creating Audit Logs

```python
from app.models import AuditLog
from app.utils import generate_ulid

def audit_log(
    db,
    user_id: str,
    action: str,
    entity_type: str,
    entity_id: str,
    old_values: dict = None,
    new_values: dict = None,
    context: dict = None
):
    """Create an audit log entry."""
    log = AuditLog(
        id=generate_ulid(),
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        old_values=old_values,
        new_values=new_values,
        ip_address=context.get("ip") if context else None,
        user_agent=context.get("user_agent") if context else None,
        device_id=context.get("device_id") if context else None
    )
    db.add(log)
    db.commit()
    return log
```

---

## Event vs AuditLog

| Aspect | Event | AuditLog |
|--------|-------|----------|
| **Purpose** | Business events | Forensic trail |
| **Granularity** | High-level actions | Field-level changes |
| **Content** | What happened | What changed |
| **Usage** | Workflows, analytics | Compliance, debugging |
| **old_values** | Not stored | Stored |
| **new_values** | In payload | Stored |

### When to Use Each

**Use Event for:**
- Triggering workflows (e.g., send receipt after bill.posted)
- Real-time dashboards
- Analytics and reporting
- Event sourcing/replay

**Use AuditLog for:**
- Compliance requirements
- Security investigations
- Debugging issues
- Historical queries ("What was the price at time X?")

---

## Entity Relationship

```
┌─────────────────┐
│      Event      │
├─────────────────┤
│ id (PK)         │
│ event_type      │───► 'bill.posted', 'payment.captured', etc.
│ aggregate_type  │───► 'bill', 'appointment', etc.
│ aggregate_id    │───► ULID of the entity
│ payload         │───► JSONB event data
│ event_metadata  │───► JSONB context
│ created_at      │
└─────────────────┘

┌─────────────────┐      ┌──────────────┐
│    AuditLog     │      │     User     │
├─────────────────┤      ├──────────────┤
│ id (PK)         │      │ id (PK)      │
│ user_id (FK)    │─────►│ username     │
│ action          │      └──────────────┘
│ entity_type     │
│ entity_id       │
│ old_values      │───► JSONB before state
│ new_values      │───► JSONB after state
│ ip_address      │
│ device_id       │
│ created_at      │
└─────────────────┘
```

---

## Retention Policy

| Data Type | Retention | Notes |
|-----------|-----------|-------|
| Events | Indefinite | Required for replay |
| Audit Logs | 7 years | GST compliance (India) |
| Export Logs | 3 years | Reference only |

---

## Querying Audit History

### Who changed a bill?

```python
changes = db.query(AuditLog).filter(
    AuditLog.entity_type == "bill",
    AuditLog.entity_id == bill_id
).order_by(AuditLog.created_at.desc()).all()
```

### All discounts applied today

```python
discounts = db.query(AuditLog).filter(
    AuditLog.entity_type == "discount",
    AuditLog.action == "create",
    AuditLog.created_at >= today_start
).all()
```

### User activity log

```python
activity = db.query(AuditLog).filter(
    AuditLog.user_id == user_id
).order_by(AuditLog.created_at.desc()).limit(100).all()
```
