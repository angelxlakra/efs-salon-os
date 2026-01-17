# Appointment Models

**File**: `backend/app/models/appointment.py`

Models for scheduled appointments and walk-in customers.

---

## AppointmentStatus

Status lifecycle for appointments and walk-ins.

```python
class AppointmentStatus(str, enum.Enum):
    SCHEDULED = "scheduled"     # Booked, not yet arrived
    CHECKED_IN = "checked_in"   # Customer has arrived
    IN_PROGRESS = "in_progress" # Service started
    COMPLETED = "completed"     # Service finished
    CANCELLED = "cancelled"     # Appointment cancelled
    NO_SHOW = "no_show"         # Customer didn't show up
```

### Status Flow

```
                    ┌────────────┐
                    │  SCHEDULED │ (Appointments only)
                    └─────┬──────┘
                          │ Check-in
                          ▼
┌─────────────┐     ┌────────────┐
│   NO_SHOW   │◄────│ CHECKED_IN │ (Walk-ins start here)
└─────────────┘     └─────┬──────┘
                          │ Start service
                          ▼
                    ┌─────────────┐
                    │ IN_PROGRESS │
                    └─────┬───────┘
                          │ Complete
                          ▼
                    ┌─────────────┐
                    │  COMPLETED  │
                    └─────────────┘

┌─────────────┐
│  CANCELLED  │ (Can cancel from SCHEDULED or CHECKED_IN)
└─────────────┘
```

---

## Appointment

Pre-scheduled appointments for customers.

**Table**: `appointments`

**Mixins**: `ULIDMixin`, `TimestampMixin`

### Ticket Number Format

```
TKT-YYMMDD-###
│   │      │
│   │      └─ Daily sequential number (001-999)
│   └──────── Date (Year-Month-Day)
└──────────── Ticket prefix

Example: TKT-251015-001 (Oct 15, 2025, first ticket)
```

- Resets daily at midnight
- Separate sequence per day

### Columns

| Column | Type | Nullable | Index | Description |
|--------|------|----------|-------|-------------|
| `id` | String(26) | No | PK | ULID primary key |
| `ticket_number` | String | No | Yes (unique) | TKT-YYMMDD-### format |
| `visit_id` | String(26) | Yes | - | Groups multiple services for same customer visit |
| `customer_id` | String(26) | Yes | Yes | FK to customers.id |
| `service_id` | String(26) | No | - | FK to services.id |
| `assigned_staff_id` | String(26) | Yes | Yes | FK to staff.id |
| `scheduled_at` | DateTime(tz) | No | Yes | Appointment time |
| `duration_minutes` | Integer | No | - | Expected duration |
| `status` | Enum(AppointmentStatus) | No | Yes | Current status (default: SCHEDULED) |
| `checked_in_at` | DateTime(tz) | Yes | - | When customer checked in |
| `started_at` | DateTime(tz) | Yes | - | When service started |
| `completed_at` | DateTime(tz) | Yes | - | When service completed |
| `customer_name` | String | No | - | Customer name (required) |
| `customer_phone` | String | No | - | Customer phone (required) |
| `booking_notes` | Text | Yes | - | Notes from booking |
| `service_notes` | Text | Yes | - | Staff notes during/after service |
| `service_notes_updated_at` | DateTime(tz) | Yes | - | When service notes were last updated |
| `created_by` | String(26) | No | - | FK to users.id |
| `cancelled_at` | DateTime(tz) | Yes | - | When appointment was cancelled |
| `created_at` | DateTime(tz) | No | - | Creation timestamp |
| `updated_at` | DateTime(tz) | No | - | Last update timestamp |

### Relationships

| Relationship | Target | Type | Description |
|--------------|--------|------|-------------|
| `customer` | Customer | Many-to-One | Linked customer |
| `service` | Service | Many-to-One | Service being performed |
| `assigned_staff` | Staff | Many-to-One | Assigned stylist |
| `created_by_user` | User | Many-to-One | Who created the booking |

### Properties

| Property | Return Type | Description |
|----------|-------------|-------------|
| `is_active` | bool | True if not cancelled |

### Visit ID

When a customer books multiple services in one visit, each service is a separate appointment linked by `visit_id`:

```
Visit ID: 01HXYZ...

├── Appointment 1: Haircut (TKT-251015-001)
├── Appointment 2: Hair Color (TKT-251015-002)
└── Appointment 3: Hair Spa (TKT-251015-003)
```

This allows:
- Individual service tracking and completion
- Different staff for each service
- Separate timing for each service

### Service Notes

Staff can add notes during or after service completion:
- Editable for **15 minutes** after creation
- `service_notes_updated_at` tracks last update
- Visible to receptionist and owner

---

## WalkIn

Walk-in customers without prior appointment.

**Table**: `walkins`

**Mixins**: `ULIDMixin`, `TimestampMixin`

### Columns

| Column | Type | Nullable | Index | Description |
|--------|------|----------|-------|-------------|
| `id` | String(26) | No | PK | ULID primary key |
| `ticket_number` | String | No | Yes (unique) | TKT-YYMMDD-### format |
| `visit_id` | String(26) | Yes | - | Groups multiple services |
| `customer_id` | String(26) | Yes | Yes | FK to customers.id |
| `service_id` | String(26) | No | - | FK to services.id |
| `assigned_staff_id` | String(26) | Yes | Yes | FK to staff.id |
| `duration_minutes` | Integer | No | - | Expected duration |
| `status` | Enum(AppointmentStatus) | No | - | Current status (default: CHECKED_IN) |
| `started_at` | DateTime(tz) | Yes | - | When service started |
| `completed_at` | DateTime(tz) | Yes | - | When service completed |
| `customer_name` | String | No | - | Customer name (required) |
| `customer_phone` | String | No | - | Customer phone (required) |
| `service_notes` | Text | Yes | - | Staff notes |
| `service_notes_updated_at` | DateTime(tz) | Yes | - | When notes were updated |
| `created_by` | String(26) | No | - | FK to users.id |
| `created_at` | DateTime(tz) | No | - | Creation timestamp |
| `updated_at` | DateTime(tz) | No | - | Last update timestamp |

### Relationships

| Relationship | Target | Type | Description |
|--------------|--------|------|-------------|
| `customer` | Customer | Many-to-One | Linked customer |
| `service` | Service | Many-to-One | Service being performed |
| `assigned_staff` | Staff | Many-to-One | Assigned stylist |
| `created_by_user` | User | Many-to-One | Who registered the walk-in |

### Difference from Appointment

| Aspect | Appointment | WalkIn |
|--------|-------------|--------|
| `scheduled_at` | Required | Not applicable |
| Default status | SCHEDULED | CHECKED_IN |
| `booking_notes` | Available | Not applicable |
| `checked_in_at` | Tracked | Not applicable |
| `cancelled_at` | Tracked | Not applicable |

---

## Entity Relationship

```
┌─────────────┐       ┌─────────────┐
│   Customer  │       │   Service   │
├─────────────┤       ├─────────────┤
│ id (PK)     │       │ id (PK)     │
└─────────────┘       └─────────────┘
       ▲                     ▲
       │                     │
       │  ┌──────────────────┘
       │  │
┌──────┴──┴───┐       ┌─────────────┐
│ Appointment │       │    Staff    │
├─────────────┤       ├─────────────┤
│ id (PK)     │       │ id (PK)     │
│ customer_id │       └─────────────┘
│ service_id  │              ▲
│ staff_id    │──────────────┘
│ visit_id    │
└─────────────┘

┌─────────────┐
│   WalkIn    │  (Similar structure to Appointment)
├─────────────┤
│ id (PK)     │
│ customer_id │
│ service_id  │
│ staff_id    │
│ visit_id    │
└─────────────┘
```

---

## Conflict Detection

When creating appointments, check for conflicts:

```python
# Check if staff is already booked
conflicts = db.query(Appointment).filter(
    Appointment.assigned_staff_id == staff_id,
    Appointment.status.in_([
        AppointmentStatus.SCHEDULED,
        AppointmentStatus.CHECKED_IN,
        AppointmentStatus.IN_PROGRESS
    ]),
    # Time overlap check
    Appointment.scheduled_at < proposed_end_time,
    Appointment.scheduled_at + duration > proposed_start_time
).all()
```

---

## Privacy Considerations

For Staff role users:
- See full schedule with all appointments
- Customer info limited to **first name + ticket number**
- Phone numbers and full names hidden
- Cannot view revenue or totals
