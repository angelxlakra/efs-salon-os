# Billing Models

**File**: `backend/app/models/billing.py`

Models for bills, line items, and payments.

---

## PaymentMethod

Enumeration of accepted payment methods.

```python
class PaymentMethod(str, enum.Enum):
    CASH = "cash"
    UPI = "upi"
    CARD = "card"
    OTHER = "other"
```

---

## BillStatus

Bill lifecycle states.

```python
class BillStatus(str, enum.Enum):
    DRAFT = "draft"      # Being created, not yet paid
    POSTED = "posted"    # Fully paid, invoice generated
    REFUNDED = "refunded" # Refund processed
    VOID = "void"        # Cancelled before payment
```

### Status Flow

```
┌─────────┐     Payment      ┌─────────┐
│  DRAFT  │ ───────────────► │ POSTED  │
└─────────┘   (auto-post     └─────────┘
     │        when paid)          │
     │                            │ Refund
     │ Cancel                     ▼
     ▼                      ┌──────────┐
┌─────────┐                 │ REFUNDED │
│  VOID   │                 └──────────┘
└─────────┘
```

---

## Bill

Customer invoices/bills.

**Table**: `bills`

**Mixins**: `ULIDMixin`, `TimestampMixin`

### Invoice Number Format

```
SAL-YY-NNNN
│   │  │
│   │  └─ Sequential number (0001-9999)
│   └──── Two-digit year
└──────── Salon prefix

Example: SAL-25-0042
```

- Resets annually on April 1st (fiscal year)
- Generated atomically using PostgreSQL advisory locks
- No gaps allowed

### Columns

| Column | Type | Nullable | Index | Description |
|--------|------|----------|-------|-------------|
| `id` | String(26) | No | PK | ULID primary key |
| `invoice_number` | String | No | Yes (unique) | SAL-YY-NNNN format |
| `customer_id` | String(26) | Yes | Yes | FK to customers.id |
| `subtotal` | Integer | No | - | Sum of line items (paise) |
| `discount_amount` | Integer | No | - | Discount applied (paise) |
| `tax_amount` | Integer | No | - | Total tax CGST+SGST (paise) |
| `cgst_amount` | Integer | No | - | Central GST (paise) |
| `sgst_amount` | Integer | No | - | State GST (paise) |
| `total_amount` | Integer | No | - | Pre-rounding total (paise) |
| `rounded_total` | Integer | No | - | Final amount after rounding (paise) |
| `rounding_adjustment` | Integer | No | - | Rounding difference (paise) |
| `status` | Enum(BillStatus) | No | Yes | Current status |
| `posted_at` | DateTime(tz) | Yes | Yes | When bill was posted |
| `customer_name` | String | Yes | - | Name for anonymous bills |
| `customer_phone` | String | Yes | - | Phone for anonymous bills |
| `discount_reason` | Text | Yes | - | Reason for discount |
| `discount_approved_by` | String(26) | Yes | - | FK to users.id |
| `refunded_at` | DateTime(tz) | Yes | - | When refund processed |
| `refund_reason` | Text | Yes | - | Reason for refund |
| `refund_approved_by` | String(26) | Yes | - | FK to users.id |
| `original_bill_id` | String(26) | Yes | - | FK to bills.id (for refund bills) |
| `created_by` | String(26) | No | - | FK to users.id |
| `created_at` | DateTime(tz) | No | - | Creation timestamp |
| `updated_at` | DateTime(tz) | No | - | Last update timestamp |

### Relationships

| Relationship | Target | Type | Description |
|--------------|--------|------|-------------|
| `customer` | Customer | Many-to-One | Linked customer record |
| `items` | BillItem | One-to-Many | Line items |
| `payments` | Payment | One-to-Many | Payment records |
| `created_by_user` | User | Many-to-One | Creator |
| `discount_approver` | User | Many-to-One | Who approved discount |
| `refund_approver` | User | Many-to-One | Who approved refund |
| `original_bill` | Bill | Self-referential | Original bill (for refunds) |

### Properties

| Property | Return Type | Description |
|----------|-------------|-------------|
| `total_rupees` | float | Total in rupees |

### Money Calculation Flow

```
Subtotal (sum of line items)         150000 paise (Rs 1500.00)
 - Discount                          -  5000 paise (Rs   50.00)
 = Amount after discount             145000 paise (Rs 1450.00)

Tax extracted from inclusive price:
  taxable_value = 145000 / 1.18     122881 paise
  CGST (9%)     = 122881 * 0.09      11059 paise
  SGST (9%)     = 122881 * 0.09      11059 paise

Total tax                             22118 paise (Rs 221.18)
Pre-rounding total                   145000 paise (Rs 1450.00)
Rounded total                        145000 paise (Rs 1450.00)
Rounding adjustment                       0 paise
```

---

## BillItem

Individual line items on a bill.

**Table**: `bill_items`

**Mixins**: `ULIDMixin`, `TimestampMixin`

### Columns

| Column | Type | Nullable | Index | Description |
|--------|------|----------|-------|-------------|
| `id` | String(26) | No | PK | ULID primary key |
| `bill_id` | String(26) | No | Yes | FK to bills.id (CASCADE delete) |
| `service_id` | String(26) | No | Yes | FK to services.id |
| `appointment_id` | String(26) | Yes | - | FK to appointments.id |
| `walkin_id` | String(26) | Yes | - | FK to walkins.id |
| `staff_id` | String(26) | Yes | - | FK to staff.id |
| `item_name` | String | No | - | Service name at time of billing |
| `base_price` | Integer | No | - | Unit price (paise) |
| `quantity` | Integer | No | - | Quantity (default: 1) |
| `line_total` | Integer | No | - | base_price * quantity (paise) |
| `notes` | Text | Yes | - | Line item notes |
| `created_at` | DateTime(tz) | No | - | Creation timestamp |
| `updated_at` | DateTime(tz) | No | - | Last update timestamp |

### Relationships

| Relationship | Target | Type | Description |
|--------------|--------|------|-------------|
| `bill` | Bill | Many-to-One | Parent bill |
| `service` | Service | Many-to-One | Service reference |
| `appointment` | Appointment | Many-to-One | Linked appointment |
| `walkin` | WalkIn | Many-to-One | Linked walk-in |
| `staff` | Staff | Many-to-One | Staff who performed service |

### Properties

| Property | Return Type | Description |
|----------|-------------|-------------|
| `line_total_rupees` | float | Line total in rupees |

---

## Payment

Payment records for bills.

**Table**: `payments`

**Mixins**: `ULIDMixin`, `TimestampMixin`

### Columns

| Column | Type | Nullable | Index | Description |
|--------|------|----------|-------|-------------|
| `id` | String(26) | No | PK | ULID primary key |
| `bill_id` | String(26) | No | Yes | FK to bills.id |
| `payment_method` | Enum(PaymentMethod) | No | - | Cash/UPI/Card/Other |
| `amount` | Integer | No | - | Payment amount (paise) |
| `confirmed_at` | DateTime(tz) | No | - | When payment was confirmed |
| `confirmed_by` | String(26) | No | - | FK to users.id |
| `reference_number` | String | Yes | - | External reference (UPI ID, etc.) |
| `notes` | Text | Yes | - | Payment notes |
| `created_at` | DateTime(tz) | No | - | Creation timestamp |
| `updated_at` | DateTime(tz) | No | - | Last update timestamp |

### Relationships

| Relationship | Target | Type | Description |
|--------------|--------|------|-------------|
| `bill` | Bill | Many-to-One | Associated bill |
| `confirmed_by_user` | User | Many-to-One | Who confirmed payment |

### Properties

| Property | Return Type | Description |
|----------|-------------|-------------|
| `amount_rupees` | float | Amount in rupees |

### Split Payments

A bill can have multiple payments:

```
Bill Total: Rs 1000.00
├── Payment 1: Cash Rs 500.00
├── Payment 2: UPI Rs 300.00
└── Payment 3: Card Rs 200.00
```

When sum of payments >= `rounded_total`, bill auto-posts.

---

## Entity Relationship

```
┌─────────────┐
│    Bill     │
├─────────────┤
│ id (PK)     │
│ invoice_num │───────────────────────────────┐
│ customer_id │◄──┐                           │
│ subtotal    │   │                           │
│ total       │   │                           │
│ status      │   │   ┌─────────────┐         │
└─────────────┘   │   │  Customer   │         │
       │          └───│ id (PK)     │         │
       │ 1:N          └─────────────┘         │
       ▼                                      │
┌─────────────┐       ┌─────────────┐         │
│  BillItem   │       │   Payment   │◄────────┘
├─────────────┤       ├─────────────┤    1:N
│ id (PK)     │       │ id (PK)     │
│ bill_id(FK) │       │ bill_id(FK) │
│ service_id  │       │ method      │
│ base_price  │       │ amount      │
│ quantity    │       │ confirmed_by│
└─────────────┘       └─────────────┘
```

---

## Refund Flow

When a bill is refunded:

1. A new "refund bill" is created with negative amounts
2. `original_bill_id` links to the original bill
3. Original bill status changes to `REFUNDED`
4. Customer's `total_spent` is decremented
5. Refund appears in "Adjustments" section of reports

```python
# Refund bill structure
refund_bill = Bill(
    invoice_number="SAL-25-0043",  # New sequential number
    original_bill_id=original.id,
    subtotal=-original.subtotal,
    total_amount=-original.total_amount,
    rounded_total=-original.rounded_total,
    status=BillStatus.POSTED,
    refund_reason="Customer dissatisfaction"
)
```
