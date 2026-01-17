# Base Mixins

**File**: `backend/app/models/base.py`

Base classes and mixins that provide common functionality across all models.

---

## TimestampMixin

Adds automatic timestamp tracking to models.

### Columns

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `created_at` | `DateTime(timezone=True)` | No | `func.now()` | Timestamp when record was created |
| `updated_at` | `DateTime(timezone=True)` | No | `func.now()` | Timestamp of last update (auto-updated) |

### Behavior

- `created_at` is set automatically on INSERT
- `updated_at` is set automatically on INSERT and UPDATE

### Usage

```python
from app.models.base import TimestampMixin

class MyModel(Base, TimestampMixin):
    __tablename__ = "my_table"
    # Automatically has created_at and updated_at columns
```

---

## SoftDeleteMixin

Enables soft deletion (logical deletion) instead of permanent removal.

### Columns

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `deleted_at` | `DateTime(timezone=True)` | Yes | `NULL` | Timestamp when record was soft-deleted |

### Properties

| Property | Return Type | Description |
|----------|-------------|-------------|
| `is_deleted` | `bool` | Returns `True` if record is soft-deleted |

### Methods

| Method | Description |
|--------|-------------|
| `soft_delete()` | Sets `deleted_at` to current timestamp |
| `restore()` | Sets `deleted_at` to `NULL` |

### Usage in Queries

```python
# Only active records (not deleted)
query.filter(Model.deleted_at.is_(None))

# Only deleted records
query.filter(Model.deleted_at.isnot(None))

# Soft delete a record
record.soft_delete()
db.commit()

# Restore a deleted record
record.restore()
db.commit()
```

---

## ULIDMixin

Provides ULID-based primary keys.

### Columns

| Column | Type | Primary Key | Default | Description |
|--------|------|-------------|---------|-------------|
| `id` | `String(26)` | Yes | `generate_ulid()` | ULID primary key |

### ULID Characteristics

- **Length**: 26 characters
- **Format**: Crockford's Base32 encoding
- **Sortable**: Lexicographically sortable by creation time
- **Structure**: First 48 bits = timestamp, remaining 80 bits = randomness
- **URL-safe**: No special characters

### Example ULID

```
01HXXX1234ABCD567890EFGH
│└──────────────────────┘
│         └─ Random component (80 bits)
└─ Timestamp component (48 bits)
```

### Benefits Over UUID

1. **Time-ordered**: Naturally sorts by creation time
2. **Shorter**: 26 chars vs 36 chars (with dashes)
3. **Database-friendly**: Better index performance due to sequential nature
4. **No dashes**: Easier to copy/paste

### Usage

```python
from app.models.base import ULIDMixin

class MyModel(Base, ULIDMixin):
    __tablename__ = "my_table"
    # Automatically has `id` column with ULID
```

---

## Combining Mixins

Models typically combine multiple mixins:

```python
class MyModel(Base, ULIDMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "my_table"

    # Gets:
    # - id (ULID primary key)
    # - created_at (auto timestamp)
    # - updated_at (auto timestamp, updates on change)
    # - deleted_at (soft delete support)

    name = Column(String, nullable=False)
```

---

## Conventions

All SalonOS models follow these conventions:

| Convention | Implementation |
|------------|----------------|
| Primary Key | ULID (26-char string) |
| Timestamps | UTC stored, IST displayed |
| Soft Delete | `deleted_at` column where applicable |
| Money | Integer in paise (Rs 1 = 100 paise) |
| Foreign Keys | String(26) matching ULID format |
