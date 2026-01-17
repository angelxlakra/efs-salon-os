# Customer Model

**File**: `backend/app/models/customer.py`

Model for tracking salon customers and their visit history.

---

## Customer

Customer records with contact information and analytics.

**Table**: `customers`

**Mixins**: `ULIDMixin`, `TimestampMixin`, `SoftDeleteMixin`

### Columns

| Column | Type | Nullable | Unique | Index | Description |
|--------|------|----------|--------|-------|-------------|
| `id` | String(26) | No | Yes | PK | ULID primary key |
| `first_name` | String | No | - | - | Customer's first name |
| `last_name` | String | Yes | - | - | Customer's last name |
| `phone` | String | No | Yes | Yes | Phone number (encrypted in production) |
| `email` | String | Yes | - | - | Email address (encrypted in production) |
| `date_of_birth` | Date | Yes | - | - | Birthday (for promotions) |
| `gender` | String | Yes | - | - | Gender |
| `notes` | Text | Yes | - | - | Internal notes about customer |
| `total_visits` | Integer | No | - | - | Total visit count (default: 0) |
| `total_spent` | Integer | No | - | - | Total amount spent in paise (default: 0) |
| `last_visit_at` | DateTime(tz) | Yes | - | Yes | Timestamp of last visit |
| `deleted_at` | DateTime(tz) | Yes | - | - | Soft delete timestamp |
| `created_at` | DateTime(tz) | No | - | - | Creation timestamp |
| `updated_at` | DateTime(tz) | No | - | - | Last update timestamp |

### Properties

| Property | Return Type | Description |
|----------|-------------|-------------|
| `full_name` | str | Combined first and last name |
| `total_spent_rupees` | float | Total spent in rupees |

---

## Analytics Fields

Customer records automatically track visit analytics:

### total_visits

Incremented when a bill is posted:

```python
# In billing service, after posting bill
if bill.customer_id:
    customer = db.query(Customer).get(bill.customer_id)
    customer.total_visits += 1
```

### total_spent

Updated with bill total when posted:

```python
# Add bill amount
customer.total_spent += bill.rounded_total

# Subtract on refund
customer.total_spent -= refund_bill.rounded_total
```

### last_visit_at

Set to current timestamp when bill is posted:

```python
customer.last_visit_at = datetime.utcnow()
```

---

## Privacy & Encryption

### PII Fields

These fields contain Personally Identifiable Information:

| Field | Encryption | Notes |
|-------|------------|-------|
| `phone` | Required | Primary identifier, must be unique |
| `email` | Required | Optional field |
| `date_of_birth` | Optional | Used for birthday promotions |

### Encryption Implementation

```python
# Using cryptography library (example)
from cryptography.fernet import Fernet

# Encrypt before storing
encrypted_phone = fernet.encrypt(phone.encode())

# Decrypt when reading
decrypted_phone = fernet.decrypt(encrypted_phone).decode()
```

### Staff Privacy Restrictions

Staff members see limited customer information:

| Field | Owner | Receptionist | Staff |
|-------|-------|--------------|-------|
| First Name | Yes | Yes | Yes |
| Last Name | Yes | Yes | No |
| Phone | Yes | Yes | No |
| Email | Yes | Yes | No |
| Full History | Yes | Yes | No |

Staff only see: **First name + Ticket number**

---

## Soft Delete Behavior

Customers use soft delete to preserve historical data:

```python
# Soft delete a customer
customer.soft_delete()  # Sets deleted_at timestamp
db.commit()

# Query only active customers
active_customers = db.query(Customer).filter(
    Customer.deleted_at.is_(None)
).all()

# Restore a deleted customer
customer.restore()
db.commit()
```

### Why Soft Delete?

1. **Historical Bills**: Bills reference customer_id
2. **Analytics**: Reports need historical customer data
3. **Regulatory**: Some jurisdictions require data retention
4. **Recovery**: Accidentally deleted records can be restored

---

## Entity Relationship

```
┌─────────────────┐
│    Customer     │
├─────────────────┤
│ id (PK)         │
│ first_name      │
│ last_name       │
│ phone (unique)  │
│ email           │
│ total_visits    │
│ total_spent     │
│ last_visit_at   │
└────────┬────────┘
         │
         │ Referenced by:
         │
    ┌────┴────┬──────────────┐
    ▼         ▼              ▼
┌───────┐ ┌───────────┐ ┌─────────┐
│ Bill  │ │Appointment│ │ WalkIn  │
└───────┘ └───────────┘ └─────────┘
```

---

## Anonymous vs Registered Customers

### Registered Customer

- Has a `Customer` record with ID
- `customer_id` populated on bills/appointments
- Analytics tracked automatically
- Can lookup history by phone

### Anonymous Customer

- No `Customer` record
- `customer_id` is NULL
- `customer_name` and `customer_phone` stored directly on bill
- No analytics tracking
- No history lookup

```python
# Bill with registered customer
bill = Bill(
    customer_id="01HXXX...",
    customer_name=None,  # Not needed
    customer_phone=None  # Not needed
)

# Bill with anonymous customer
bill = Bill(
    customer_id=None,
    customer_name="John Doe",
    customer_phone="9876543210"
)
```

---

## Common Queries

### Find Customer by Phone

```python
customer = db.query(Customer).filter(
    Customer.phone == phone_number,
    Customer.deleted_at.is_(None)
).first()
```

### Top Customers by Spending

```python
top_customers = db.query(Customer).filter(
    Customer.deleted_at.is_(None)
).order_by(
    Customer.total_spent.desc()
).limit(10).all()
```

### Customers Not Visited in 30 Days

```python
from datetime import datetime, timedelta

cutoff = datetime.utcnow() - timedelta(days=30)

inactive_customers = db.query(Customer).filter(
    Customer.deleted_at.is_(None),
    Customer.last_visit_at < cutoff
).all()
```

### Search by Name

```python
customers = db.query(Customer).filter(
    Customer.deleted_at.is_(None),
    (Customer.first_name.ilike(f"%{search}%") |
     Customer.last_name.ilike(f"%{search}%"))
).all()
```

---

## Future: CRM & Loyalty (Phase 3+)

The Customer model is designed to support future CRM features:

| Future Feature | Supporting Fields |
|----------------|-------------------|
| Birthday promotions | `date_of_birth` |
| Loyalty points | New `loyalty_points` column |
| Customer segments | New `tags` JSONB column |
| Communication history | New `CommunicationLog` table |
| Preferences | New `preferences` JSONB column |

---

## API Usage Notes

### Creating a Customer

```json
POST /api/customers
{
  "first_name": "John",
  "last_name": "Doe",
  "phone": "9876543210",
  "email": "john@example.com",
  "gender": "male"
}
```

### Updating Customer Notes

```json
PATCH /api/customers/{id}
{
  "notes": "Prefers Sarah for haircuts. Allergic to certain products."
}
```

### Customer Summary Response

```json
{
  "id": "01HXXX...",
  "full_name": "John Doe",
  "phone": "9876543210",
  "total_visits": 15,
  "total_spent": 2500000,
  "total_spent_rupees": 25000.00,
  "last_visit_at": "2025-10-10T14:30:00+05:30",
  "member_since": "2024-03-15T10:00:00+05:30"
}
```
