# Inventory Models

**File**: `backend/app/models/inventory.py`

Models for SKU management, suppliers, and stock tracking with approval workflow.

---

## Enumerations

### UOMEnum

Unit of Measurement types.

```python
class UOMEnum(str, enum.Enum):
    PIECE = "piece"    # Individual items (bottles, tubes)
    ML = "ml"          # Milliliters
    GM = "gm"          # Grams
    KG = "kg"          # Kilograms
    LITER = "liter"    # Liters
    BOX = "box"        # Boxes/packs
    BOTTLE = "bottle"  # Bottles
```

### ChangeType

Types of inventory changes.

```python
class ChangeType(str, enum.Enum):
    RECEIVE = "receive"   # New stock received from supplier
    ADJUST = "adjust"     # Manual adjustment (correction, damage, etc.)
    CONSUME = "consume"   # Used for service (future feature)
```

### ChangeStatus

Status of inventory change requests.

```python
class ChangeStatus(str, enum.Enum):
    PENDING = "pending"    # Awaiting owner approval
    APPROVED = "approved"  # Approved and applied to stock
    REJECTED = "rejected"  # Rejected by owner
```

---

## InventoryCategory

Categories for organizing inventory items.

**Table**: `inventory_categories`

**Mixins**: `ULIDMixin`, `TimestampMixin`

### Columns

| Column | Type | Nullable | Unique | Description |
|--------|------|----------|--------|-------------|
| `id` | String(26) | No | Yes (PK) | ULID primary key |
| `name` | String | No | Yes | Category name |
| `description` | Text | Yes | - | Category description |
| `created_at` | DateTime(tz) | No | - | Creation timestamp |
| `updated_at` | DateTime(tz) | No | - | Last update timestamp |

### Relationships

| Relationship | Target | Type | Description |
|--------------|--------|------|-------------|
| `skus` | SKU | One-to-Many | SKUs in this category |

### Example Categories

- Hair Products
- Skin Care
- Consumables
- Equipment
- Cleaning Supplies

---

## Supplier

Supplier information for inventory procurement.

**Table**: `suppliers`

**Mixins**: `ULIDMixin`, `TimestampMixin`

### Columns

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | String(26) | No (PK) | ULID primary key |
| `name` | String | No | Supplier name |
| `contact_person` | String | Yes | Primary contact |
| `phone` | String | Yes | Contact phone |
| `email` | String | Yes | Contact email |
| `address` | Text | Yes | Business address |
| `notes` | Text | Yes | Internal notes |
| `is_active` | Boolean | No | Active status (default: true) |
| `created_at` | DateTime(tz) | No | Creation timestamp |
| `updated_at` | DateTime(tz) | No | Last update timestamp |

### Relationships

| Relationship | Target | Type | Description |
|--------------|--------|------|-------------|
| `skus` | SKU | One-to-Many | SKUs from this supplier |

---

## SKU

Stock Keeping Unit - individual inventory items.

**Table**: `skus`

**Mixins**: `ULIDMixin`, `TimestampMixin`

### Columns

| Column | Type | Nullable | Index | Description |
|--------|------|----------|-------|-------------|
| `id` | String(26) | No | PK | ULID primary key |
| `category_id` | String(26) | No | Yes | FK to inventory_categories.id |
| `supplier_id` | String(26) | Yes | Yes | FK to suppliers.id |
| `sku_code` | String | No | Yes (unique) | SKU identifier code |
| `name` | String | No | - | Product name |
| `description` | Text | Yes | - | Product description |
| `uom` | Enum(UOMEnum) | No | - | Unit of measurement |
| `reorder_point` | Numeric(10,2) | No | - | Stock level to trigger reorder (default: 0) |
| `current_stock` | Numeric(10,2) | No | Yes | Current stock quantity (default: 0) |
| `avg_cost_per_unit` | Integer | No | - | Weighted avg cost in paise per UOM (default: 0) |
| `is_active` | Boolean | No | Yes | Active status (default: true) |
| `created_at` | DateTime(tz) | No | - | Creation timestamp |
| `updated_at` | DateTime(tz) | No | - | Last update timestamp |

### Relationships

| Relationship | Target | Type | Description |
|--------------|--------|------|-------------|
| `category` | InventoryCategory | Many-to-One | Product category |
| `supplier` | Supplier | Many-to-One | Primary supplier |
| `change_requests` | InventoryChangeRequest | One-to-Many | Change request history |
| `ledger_entries` | StockLedger | One-to-Many | Stock movement history |

### Properties

| Property | Return Type | Description |
|----------|-------------|-------------|
| `is_low_stock` | bool | True if current_stock <= reorder_point |

### SKU Code Convention

```
{CATEGORY_PREFIX}-{BRAND}-{PRODUCT}-{SIZE}

Examples:
- HP-LOREAL-SHAMPOO-500ML
- SC-OLAY-MOISTURIZER-100GM
- CONS-COTTON-BALLS-100PC
```

### Weighted Average Cost

Cost is maintained as a weighted average:

```python
# When receiving new stock
new_total_value = (current_stock * avg_cost) + (new_qty * new_unit_cost)
new_total_qty = current_stock + new_qty
new_avg_cost = new_total_value / new_total_qty

# Example:
# Current: 10 units @ Rs 100 avg = Rs 1000 total
# Receive: 5 units @ Rs 120 = Rs 600
# New avg: (1000 + 600) / 15 = Rs 106.67
```

---

## InventoryChangeRequest

Requests for inventory changes requiring owner approval.

**Table**: `inventory_change_requests`

**Mixins**: `ULIDMixin`, `TimestampMixin`

### Columns

| Column | Type | Nullable | Index | Description |
|--------|------|----------|-------|-------------|
| `id` | String(26) | No | PK | ULID primary key |
| `sku_id` | String(26) | No | Yes | FK to skus.id |
| `change_type` | Enum(ChangeType) | No | - | receive/adjust/consume |
| `quantity` | Numeric(10,2) | No | - | Quantity to change |
| `unit_cost` | Integer | Yes | - | Cost per unit in paise (for receives) |
| `reason_code` | String | No | - | Reason for change |
| `notes` | Text | Yes | - | Additional notes |
| `status` | Enum(ChangeStatus) | No | Yes | pending/approved/rejected (default: pending) |
| `requested_by` | String(26) | No | - | FK to users.id |
| `requested_at` | DateTime(tz) | No | - | When request was made |
| `reviewed_by` | String(26) | Yes | - | FK to users.id |
| `reviewed_at` | DateTime(tz) | Yes | - | When review was done |
| `review_notes` | Text | Yes | - | Reviewer's notes |
| `created_at` | DateTime(tz) | No | - | Creation timestamp |
| `updated_at` | DateTime(tz) | No | - | Last update timestamp |

### Relationships

| Relationship | Target | Type | Description |
|--------------|--------|------|-------------|
| `sku` | SKU | Many-to-One | Target SKU |
| `requester` | User | Many-to-One | Who requested the change |
| `reviewer` | User | Many-to-One | Who approved/rejected |

### Reason Codes

| Change Type | Reason Codes |
|-------------|--------------|
| RECEIVE | `new_stock`, `restock`, `return_from_customer` |
| ADJUST | `correction`, `damage`, `expired`, `theft`, `audit` |
| CONSUME | `service_use`, `sample`, `internal_use` |

### Approval Workflow

```
┌─────────────────┐
│ Staff/Reception │
│ creates request │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│    PENDING      │
│  (awaits owner) │
└────────┬────────┘
         │
    ┌────┴────┐
    │ Owner   │
    │ reviews │
    └────┬────┘
         │
    ┌────┴────┐
    ▼         ▼
┌────────┐ ┌──────────┐
│APPROVED│ │ REJECTED │
└────┬───┘ └──────────┘
     │
     ▼
┌─────────────────┐
│ Stock updated   │
│ Ledger entry    │
│ created         │
└─────────────────┘
```

---

## StockLedger

Immutable audit trail of all stock movements.

**Table**: `stock_ledger`

**Mixins**: `ULIDMixin`, `TimestampMixin`

### Columns

| Column | Type | Nullable | Index | Description |
|--------|------|----------|-------|-------------|
| `id` | String(26) | No | PK | ULID primary key |
| `sku_id` | String(26) | No | Yes | FK to skus.id |
| `change_request_id` | String(26) | Yes | - | FK to inventory_change_requests.id |
| `transaction_type` | String | No | - | 'receive', 'adjust', 'consume' |
| `quantity_change` | Numeric(10,2) | No | - | Change amount (can be negative) |
| `quantity_after` | Numeric(10,2) | No | - | Stock level after change |
| `unit_cost` | Integer | Yes | - | Cost per unit in paise |
| `total_value` | Integer | Yes | - | Total value of transaction in paise |
| `avg_cost_after` | Integer | Yes | - | Avg cost after this transaction in paise |
| `reference_type` | String | Yes | - | 'bill', 'service', etc. |
| `reference_id` | String(26) | Yes | - | ID of referenced entity |
| `notes` | Text | Yes | - | Transaction notes |
| `created_by` | String(26) | No | - | FK to users.id |
| `created_at` | DateTime(tz) | No | - | Creation timestamp |
| `updated_at` | DateTime(tz) | No | - | Last update timestamp |

### Relationships

| Relationship | Target | Type | Description |
|--------------|--------|------|-------------|
| `sku` | SKU | Many-to-One | Target SKU |
| `change_request` | InventoryChangeRequest | Many-to-One | Source request |
| `creator` | User | Many-to-One | Who created entry |

### Immutability

The StockLedger is **append-only**:
- Records are never updated or deleted
- Corrections create new entries with opposite signs
- Provides complete audit trail

### Example Ledger Entries

| Date | Type | Qty Change | After | Unit Cost | Avg After | Notes |
|------|------|------------|-------|-----------|-----------|-------|
| Oct 1 | receive | +20 | 20 | 10000 | 10000 | Initial stock |
| Oct 5 | receive | +10 | 30 | 12000 | 10667 | Restock |
| Oct 10 | adjust | -2 | 28 | - | 10667 | Damaged items |
| Oct 15 | consume | -1 | 27 | - | 10667 | Used for service |

---

## Entity Relationship

```
┌────────────────────┐     ┌─────────────────┐
│ InventoryCategory  │     │    Supplier     │
├────────────────────┤     ├─────────────────┤
│ id (PK)            │     │ id (PK)         │
│ name               │     │ name            │
└─────────┬──────────┘     │ contact_person  │
          │ 1:N            └────────┬────────┘
          ▼                        │ 1:N
┌────────────────────┐             │
│        SKU         │◄────────────┘
├────────────────────┤
│ id (PK)            │
│ category_id (FK)   │
│ supplier_id (FK)   │
│ sku_code           │
│ current_stock      │
│ avg_cost_per_unit  │
│ reorder_point      │
└─────────┬──────────┘
          │
     ┌────┴────┐
     │ 1:N     │ 1:N
     ▼         ▼
┌──────────────────────┐  ┌─────────────────┐
│InventoryChangeRequest│  │  StockLedger    │
├──────────────────────┤  ├─────────────────┤
│ id (PK)              │  │ id (PK)         │
│ sku_id (FK)          │  │ sku_id (FK)     │
│ change_type          │  │ quantity_change │
│ quantity             │  │ quantity_after  │
│ status               │  │ avg_cost_after  │
│ requested_by         │  │ created_by      │
│ reviewed_by          │──│ change_req_id   │
└──────────────────────┘  └─────────────────┘
```

---

## Low Stock Alert

Query for low stock items:

```python
low_stock_items = db.query(SKU).filter(
    SKU.is_active == True,
    SKU.current_stock <= SKU.reorder_point
).all()
```

### POS Warning

At POS, warn (don't block) if inventory item is at zero:

```
⚠️ Warning: "Shampoo 500ml" is out of stock
   Current stock: 0 | Reorder point: 5
   [Continue Anyway] [Cancel]
```

---

## API Usage Notes

### Creating a SKU

```json
POST /api/inventory/sku
{
  "category_id": "01HXXX...",
  "supplier_id": "01HYYY...",
  "sku_code": "HP-LOREAL-SHAMPOO-500ML",
  "name": "L'Oreal Professional Shampoo 500ml",
  "uom": "bottle",
  "reorder_point": 5
}
```

### Submitting Stock Receive Request

```json
POST /api/inventory/change-request
{
  "sku_id": "01HZZZ...",
  "change_type": "receive",
  "quantity": 10,
  "unit_cost": 45000,
  "reason_code": "new_stock",
  "notes": "Invoice #INV-2025-1234"
}
```

### Approving a Request (Owner Only)

```json
POST /api/inventory/approve/01HAAA...
{
  "review_notes": "Verified against invoice"
}
```
