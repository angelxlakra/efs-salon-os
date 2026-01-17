# Service Catalog Models

**File**: `backend/app/models/service.py`

Models for managing salon services and their categories.

---

## ServiceCategory

Categories for organizing services.

**Table**: `service_categories`

**Mixins**: `ULIDMixin`, `TimestampMixin`

### Columns

| Column | Type | Nullable | Unique | Description |
|--------|------|----------|--------|-------------|
| `id` | String(26) | No | Yes (PK) | ULID primary key |
| `name` | String | No | Yes | Category name |
| `description` | Text | Yes | - | Category description |
| `display_order` | Integer | No | - | Sort order (default: 0) |
| `is_active` | Boolean | No | - | Active status (default: true) |
| `created_at` | DateTime(tz) | No | - | Creation timestamp |
| `updated_at` | DateTime(tz) | No | - | Last update timestamp |

### Relationships

| Relationship | Target | Type | Description |
|--------------|--------|------|-------------|
| `services` | Service | One-to-Many | Services in this category |

### Example Categories

```
1. Haircut (display_order: 1)
2. Hair Color (display_order: 2)
3. Hair Spa (display_order: 3)
4. Facial (display_order: 4)
5. Makeup (display_order: 5)
6. Nails (display_order: 6)
7. Waxing (display_order: 7)
```

---

## Service

Individual salon services.

**Table**: `services`

**Mixins**: `ULIDMixin`, `TimestampMixin`, `SoftDeleteMixin`

### Columns

| Column | Type | Nullable | Index | Description |
|--------|------|----------|-------|-------------|
| `id` | String(26) | No | PK | ULID primary key |
| `category_id` | String(26) | No | Yes | FK to service_categories.id |
| `name` | String | No | - | Service name |
| `description` | Text | Yes | - | Service description |
| `base_price` | Integer | No | - | Price in paise (tax-inclusive) |
| `duration_minutes` | Integer | No | - | Expected duration |
| `is_active` | Boolean | No | Yes | Active status (default: true) |
| `display_order` | Integer | No | - | Sort order within category (default: 0) |
| `deleted_at` | DateTime(tz) | Yes | - | Soft delete timestamp |
| `created_at` | DateTime(tz) | No | - | Creation timestamp |
| `updated_at` | DateTime(tz) | No | - | Last update timestamp |

### Relationships

| Relationship | Target | Type | Description |
|--------------|--------|------|-------------|
| `category` | ServiceCategory | Many-to-One | Parent category |
| `addons` | ServiceAddon | One-to-Many | Available add-ons |

### Properties

| Property | Return Type | Description |
|----------|-------------|-------------|
| `base_price_rupees` | float | Price in rupees |

### Pricing Convention

All prices are **tax-inclusive**:

```
Display Price: Rs 750.00 (what customer sees)
Stored Value:  75000 paise

Tax Extraction (at billing):
  Taxable Value = 75000 / 1.18 = 63559 paise
  CGST (9%)     = 63559 * 0.09 = 5720 paise
  SGST (9%)     = 63559 * 0.09 = 5720 paise
```

### Example Services

| Service | Category | Price (paise) | Duration |
|---------|----------|---------------|----------|
| Men's Haircut | Haircut | 40000 | 30 min |
| Women's Haircut | Haircut | 60000 | 45 min |
| Hair Color (Root Touch-up) | Hair Color | 150000 | 90 min |
| Hair Color (Full) | Hair Color | 250000 | 120 min |
| Deep Conditioning Spa | Hair Spa | 80000 | 60 min |
| Basic Facial | Facial | 100000 | 60 min |

---

## ServiceAddon

Optional add-ons for services.

**Table**: `service_addons`

**Mixins**: `ULIDMixin`, `TimestampMixin`

### Columns

| Column | Type | Nullable | Index | Description |
|--------|------|----------|-------|-------------|
| `id` | String(26) | No | PK | ULID primary key |
| `service_id` | String(26) | No | Yes | FK to services.id |
| `name` | String | No | - | Add-on name |
| `price` | Integer | No | - | Price in paise (tax-inclusive) |
| `created_at` | DateTime(tz) | No | - | Creation timestamp |
| `updated_at` | DateTime(tz) | No | - | Last update timestamp |

### Relationships

| Relationship | Target | Type | Description |
|--------------|--------|------|-------------|
| `service` | Service | Many-to-One | Parent service |

### Properties

| Property | Return Type | Description |
|----------|-------------|-------------|
| `price_rupees` | float | Price in rupees |

### Example Add-ons

| Service | Add-on | Price (paise) |
|---------|--------|---------------|
| Men's Haircut | Head Massage | 15000 |
| Men's Haircut | Beard Trim | 10000 |
| Women's Haircut | Blow Dry | 20000 |
| Women's Haircut | Hair Treatment | 30000 |
| Hair Color | Olaplex Treatment | 50000 |
| Hair Color | Toner Application | 30000 |

---

## Entity Relationship

```
┌──────────────────┐
│ ServiceCategory  │
├──────────────────┤
│ id (PK)          │
│ name             │
│ display_order    │
│ is_active        │
└────────┬─────────┘
         │ 1:N
         ▼
┌──────────────────┐
│     Service      │
├──────────────────┤
│ id (PK)          │
│ category_id (FK) │
│ name             │
│ base_price       │
│ duration_minutes │
│ is_active        │
└────────┬─────────┘
         │ 1:N
         ▼
┌──────────────────┐
│  ServiceAddon    │
├──────────────────┤
│ id (PK)          │
│ service_id (FK)  │
│ name             │
│ price            │
└──────────────────┘
```

---

## Soft Delete Behavior

Services use soft delete to preserve historical data:

```python
# Deactivate a service (soft delete)
service.soft_delete()  # Sets deleted_at timestamp
db.commit()

# Query only active services
active_services = db.query(Service).filter(
    Service.is_active == True,
    Service.deleted_at.is_(None)
).all()

# Restore a deleted service
service.restore()  # Sets deleted_at to NULL
db.commit()
```

### Why Soft Delete?

1. **Historical Bills**: Old bills reference services by ID
2. **Reports**: Analytics need historical service data
3. **Audit Trail**: Track when services were discontinued
4. **Recovery**: Accidentally deleted services can be restored

---

## Display Ordering

Services are ordered by:
1. Category `display_order` (ascending)
2. Service `display_order` within category (ascending)

```python
# Get ordered service catalog
services = db.query(Service).join(ServiceCategory).filter(
    Service.is_active == True,
    Service.deleted_at.is_(None),
    ServiceCategory.is_active == True
).order_by(
    ServiceCategory.display_order,
    Service.display_order
).all()
```

---

## API Usage Notes

### Creating a Service

```json
POST /api/catalog/service
{
  "category_id": "01HXXX...",
  "name": "Premium Haircut",
  "description": "Includes consultation and styling",
  "base_price": 80000,
  "duration_minutes": 45
}
```

### Listing Services with Add-ons

```json
GET /api/catalog/services

{
  "services": [
    {
      "id": "01HYYY...",
      "name": "Men's Haircut",
      "base_price": 40000,
      "duration_minutes": 30,
      "category": {
        "id": "01HXXX...",
        "name": "Haircut"
      },
      "addons": [
        {"id": "01HZZZ...", "name": "Head Massage", "price": 15000},
        {"id": "01HAAA...", "name": "Beard Trim", "price": 10000}
      ]
    }
  ]
}
```
