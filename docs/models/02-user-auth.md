# User & Authentication Models

**File**: `backend/app/models/user.py`

Models for user accounts, roles, and staff profiles.

---

## RoleEnum

Enumeration of system roles.

```python
class RoleEnum(str, enum.Enum):
    OWNER = "owner"
    RECEPTIONIST = "receptionist"
    STAFF = "staff"
```

### Role Permissions Summary

| Feature | Owner | Receptionist | Staff |
|---------|-------|--------------|-------|
| Create bills | Yes | Yes | No |
| Apply discounts | Unlimited | Up to Rs 500 | No |
| Refund bills | Yes | No | No |
| View profit/COGS | Yes | No | No |
| Approve inventory | Yes | No | No |
| View all schedules | Yes | Yes | Yes (limited PII) |
| Mark service complete | Yes | Yes | Yes |
| Export reports | Yes | Yes | No |

---

## Role

Defines access levels in the system.

**Table**: `roles`

**Mixins**: `ULIDMixin`, `TimestampMixin`

### Columns

| Column | Type | Nullable | Unique | Index | Description |
|--------|------|----------|--------|-------|-------------|
| `id` | String(26) | No | Yes | PK | ULID primary key |
| `name` | Enum(RoleEnum) | No | Yes | - | Role name (owner/receptionist/staff) |
| `description` | Text | Yes | - | - | Human-readable description |
| `permissions` | JSONB | No | - | - | Permission set (default: empty dict) |
| `created_at` | DateTime(tz) | No | - | - | Creation timestamp |
| `updated_at` | DateTime(tz) | No | - | - | Last update timestamp |

### Relationships

| Relationship | Target | Type | Description |
|--------------|--------|------|-------------|
| `users` | User | One-to-Many | Users with this role |

### Permissions JSONB Structure

```json
{
  "bills": ["create", "read", "update"],
  "appointments": ["create", "read", "update", "delete"],
  "inventory": ["read"],
  "reports": ["read", "export"]
}
```

---

## User

User accounts for system access.

**Table**: `users`

**Mixins**: `ULIDMixin`, `TimestampMixin`, `SoftDeleteMixin`

### Columns

| Column | Type | Nullable | Unique | Index | Description |
|--------|------|----------|--------|-------|-------------|
| `id` | String(26) | No | Yes | PK | ULID primary key |
| `role_id` | String(26) | No | - | Yes | FK to roles.id |
| `username` | String | No | Yes | Yes | Login username |
| `email` | String | Yes | Yes | - | Email (encrypted in production) |
| `password_hash` | String | No | - | - | Bcrypt password hash |
| `password_history` | ARRAY(String) | Yes | - | - | Previous password hashes |
| `full_name` | String | No | - | - | Display name |
| `phone` | String | Yes | - | - | Phone (encrypted in production) |
| `is_active` | Boolean | No | - | - | Account active status (default: true) |
| `last_login_at` | DateTime(tz) | Yes | - | - | Last successful login |
| `deleted_at` | DateTime(tz) | Yes | - | - | Soft delete timestamp |
| `created_at` | DateTime(tz) | No | - | - | Creation timestamp |
| `updated_at` | DateTime(tz) | No | - | - | Last update timestamp |

### Relationships

| Relationship | Target | Type | Description |
|--------------|--------|------|-------------|
| `role` | Role | Many-to-One | User's role |
| `staff` | Staff | One-to-One | Staff profile (if applicable) |

### Properties

| Property | Return Type | Description |
|----------|-------------|-------------|
| `is_owner` | bool | True if user has owner role |
| `is_receptionist` | bool | True if user has receptionist role |
| `is_staff` | bool | True if user has staff role |

### Password Security

- **Hashing**: Bcrypt with cost factor 12
- **History**: Stores last N password hashes to prevent reuse
- **Policy**: Minimum length and complexity enforced at service layer

### Example Usage

```python
# Check user role
if user.is_owner:
    # Allow refund operation
    pass

# Get user's role name
role_name = user.role.name  # RoleEnum.OWNER

# Check if account is active and not deleted
if user.is_active and not user.is_deleted:
    # Allow login
    pass
```

---

## Staff

Staff profile for service providers (stylists, beauticians).

**Table**: `staff`

**Mixins**: `ULIDMixin`, `TimestampMixin`

### Columns

| Column | Type | Nullable | Unique | Index | Description |
|--------|------|----------|--------|-------|-------------|
| `id` | String(26) | No | Yes | PK | ULID primary key |
| `user_id` | String(26) | No | Yes | Yes | FK to users.id |
| `display_name` | String | No | - | - | Customer-facing name |
| `specialization` | ARRAY(String) | Yes | - | - | Service specializations |
| `is_active` | Boolean | No | - | - | Active status (default: true) |
| `created_at` | DateTime(tz) | No | - | - | Creation timestamp |
| `updated_at` | DateTime(tz) | No | - | - | Last update timestamp |

### Relationships

| Relationship | Target | Type | Description |
|--------------|--------|------|-------------|
| `user` | User | One-to-One | Linked user account |

### Specializations

Array of service types the staff member can perform:

```python
["haircut", "coloring", "spa", "makeup", "nails"]
```

### Usage Notes

- Staff members have both a `User` account (for login) and a `Staff` profile (for service assignments)
- `display_name` is shown to customers (e.g., on receipts)
- Only `is_active` staff can be assigned to appointments

---

## Entity Relationship

```
┌─────────────┐       ┌─────────────┐       ┌─────────────┐
│    Role     │       │    User     │       │    Staff    │
├─────────────┤       ├─────────────┤       ├─────────────┤
│ id (PK)     │◄──────│ role_id(FK) │       │ id (PK)     │
│ name        │  1:N  │ id (PK)     │◄──────│ user_id(FK) │
│ permissions │       │ username    │  1:1  │ display_name│
└─────────────┘       │ password    │       │ specializ.  │
                      └─────────────┘       └─────────────┘
```

---

## Seeding Default Roles

```python
# Default roles created on initial setup
roles = [
    Role(
        name=RoleEnum.OWNER,
        description="Full system access",
        permissions={"*": ["*"]}
    ),
    Role(
        name=RoleEnum.RECEPTIONIST,
        description="POS, appointments, limited reports",
        permissions={
            "bills": ["create", "read", "update"],
            "appointments": ["create", "read", "update", "delete"],
            "customers": ["create", "read", "update"],
            "reports": ["read"]
        }
    ),
    Role(
        name=RoleEnum.STAFF,
        description="View schedules, mark services complete",
        permissions={
            "appointments": ["read", "update"],
            "bills": ["read"]
        }
    )
]
```
