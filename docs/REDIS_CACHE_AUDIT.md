# Redis Cache Invalidation Audit - SalonOS Backend

## Overview

The SalonOS backend uses a Redis-based `CacheService` singleton (`app/services/cache_service.py`) for caching frequently-accessed data. The service supports `get`, `get_json`, `set` (with TTL), `delete`, `delete_pattern`, and `exists` operations.

**Audit Result**: Out of ~95 mutation endpoints, only **5 properly invalidate cache**. The remaining **~90 endpoints perform no cache invalidation** after modifying data.

---

## Current Cache Architecture

### Cache Keys & TTLs

| Cache Key Pattern | TTL | Location | Purpose |
|---|---|---|---|
| `settings:singleton` | 3600s (1h) | `services/settings_service.py` | Salon settings (name, address, colors, etc.) |
| `catalog:categories:active=*` | 1800s (30m) | `api/catalog.py` | Service categories listing |
| `dashboard:metrics:{date}` | 60s | `services/accounting_service.py` | Dashboard revenue/tax metrics |
| `dashboard:comparison:{date}` | 60s | `services/accounting_service.py` | Day-over-day comparison |
| `dashboard:hourly:{date}` | 60s | `services/accounting_service.py` | Hourly revenue breakdown |
| `dashboard:trends:{days}:{date}` | 300s (5m) | `services/accounting_service.py` | Multi-day trend data |
| `dashboard:top_services:{date}:{limit}` | 60s | `services/accounting_service.py` | Top performing services |
| `dashboard:staff_performance:{date}` | 60s | `services/accounting_service.py` | Staff performance metrics |
| `idempotency:*` | 86400s (24h) | `services/idempotency_service.py` | Bill creation duplicate prevention |
| `refresh_token:*`, `blacklist:*` | Varies | `auth/session.py` | Auth tokens (uses Redis directly, not CacheService) |

### Files Using Cache Invalidation (Correct)

| File | Invalidation Call | Trigger |
|---|---|---|
| `api/catalog.py:160` | `cache.delete_pattern("catalog:categories:*")` | Category created |
| `api/catalog.py:286` | `cache.delete_pattern("catalog:categories:*")` | Category updated |
| `api/catalog.py:354` | `cache.delete_pattern("catalog:categories:*")` | Category deleted |
| `api/catalog.py:927` | `cache.delete_pattern("catalog:categories:*")` | Bulk import |
| `services/settings_service.py:109` | `cache.delete(SETTINGS_CACHE_KEY)` | Settings updated |
| `services/settings_service.py:151` | `cache.delete(SETTINGS_CACHE_KEY)` | Settings reset |

### Files NOT Using Cache Invalidation (Problem)

Every other mutation endpoint in the backend.

---

## Part 1: Catalog - Services, Addons, Staff Templates (CRITICAL)

**Impact**: Outdated service prices shown in POS for up to 30 minutes. Deleted services still appear. New services not visible.

### Services (6 endpoints missing)

| File | Line | Operation | HTTP | Missing Invalidation |
|---|---|---|---|---|
| `api/catalog.py` | 421-472 | Create service | `POST /services` | `catalog:categories:*` |
| `api/catalog.py` | 531-591 | Update service | `PATCH /services/{id}` | `catalog:categories:*` |
| `api/catalog.py` | 594-633 | Delete service | `DELETE /services/{id}` | `catalog:categories:*` |

### Addons (3 endpoints missing)

| File | Line | Operation | HTTP | Missing Invalidation |
|---|---|---|---|---|
| `api/catalog.py` | 637-686 | Create addon | `POST /services/{id}/addons` | `catalog:categories:*` |
| `api/catalog.py` | 689-735 | Update addon | `PATCH /addons/{id}` | `catalog:categories:*` |
| `api/catalog.py` | 738-771 | Delete addon | `DELETE /addons/{id}` | `catalog:categories:*` |

### Staff Templates (3 endpoints missing)

| File | Line | Operation | HTTP | Missing Invalidation |
|---|---|---|---|---|
| `api/catalog.py` | 1113-1199 | Create template | `POST /services/{id}/staff-templates` | `catalog:categories:*` |
| `api/catalog.py` | 1242-1305 | Update template | `PATCH /services/{id}/staff-templates/{id}` | `catalog:categories:*` |
| `api/catalog.py` | 1308-1350 | Delete template | `DELETE /services/{id}/staff-templates/{id}` | `catalog:categories:*` |

### Fix

Add after each `db.commit()` + `db.refresh()`:
```python
from app.services.cache_service import cache
cache.delete_pattern("catalog:categories:*")
```

---

## Part 2: Dashboard Metrics - Stale After Billing Operations (CRITICAL)

**Impact**: Dashboard shows outdated revenue, tax, and performance data for up to 60 seconds after any financial transaction. Real-time monitoring unreliable.

### POS/Billing Endpoints (8 endpoints missing)

| File | Line | Operation | HTTP | Should Invalidate |
|---|---|---|---|---|
| `api/pos.py` | 49-137 | Create bill | `POST /bills` | `dashboard:*` |
| `api/pos.py` | 140-221 | Add payment | `POST /bills/{id}/payments` | `dashboard:*` |
| `api/pos.py` | 224-314 | Update payment | `PATCH /bills/{id}/payments/{id}` | `dashboard:*` |
| `api/pos.py` | 317-375 | Delete payment | `DELETE /bills/{id}/payments/{id}` | `dashboard:*` |
| `api/pos.py` | 478-539 | Complete bill | `POST /bills/{id}/complete` | `dashboard:*` |
| `api/pos.py` | 542-601 | Collect pending | `POST /pending-payments/collect` | `dashboard:*` |
| `api/pos.py` | 650-705 | Void bill | `POST /bills/{id}/void` | `dashboard:*` |
| `api/pos.py` | 708-775 | Refund bill | `POST /bills/{id}/refund` | `dashboard:*` |

### Fix

Add after each billing mutation's `db.commit()`:
```python
from app.services.cache_service import cache
cache.delete_pattern("dashboard:*")
```

**Note**: Dashboard cache TTL is only 60s, so this is less critical than catalog (30m TTL). However, for a real-time POS dashboard, stale data for even 60s after a sale is confusing.

---

## Part 3: Expense & Purchase Operations (HIGH)

**Impact**: Dashboard P&L and expense reports show stale data. Purchase invoices affecting inventory not reflected.

### Expenses (2 endpoints missing)

| File | Line | Operation | HTTP | Should Invalidate |
|---|---|---|---|---|
| `api/expenses.py` | 29-78 | Create expense | `POST /expenses` | `dashboard:*` |
| `api/expenses.py` | 218+ | Update expense | `PATCH /expenses/{id}` | `dashboard:*` |

### Purchases (6 endpoints missing)

| File | Line | Operation | HTTP | Should Invalidate |
|---|---|---|---|---|
| `api/purchases.py` | 31-45 | Create supplier | `POST /suppliers` | None needed currently |
| `api/purchases.py` | 100+ | Update supplier | `PATCH /suppliers/{id}` | None needed currently |
| `api/purchases.py` | 122+ | Create invoice | `POST /invoices` | `dashboard:*` |
| `api/purchases.py` | 294+ | Update invoice | `PATCH /invoices/{id}` | `dashboard:*` |
| `api/purchases.py` | 394+ | Edit invoice | `POST /invoices/{id}/edit` | `dashboard:*` |
| `api/purchases.py` | 475+ | Receive inventory | `POST /invoices/{id}/receive` | `dashboard:*` |
| `api/purchases.py` | 595+ | Supplier payment | `POST /payments` | `dashboard:*` |

---

## Part 4: Appointments & Walk-ins (MEDIUM)

**Impact**: Dashboard appointment counts stale. Not currently cached individually, but appointment mutations affect dashboard metrics.

### Appointments (7 endpoints missing)

| File | Line | Operation | HTTP | Should Invalidate |
|---|---|---|---|---|
| `api/appointments.py` | 229+ | Create appointment | `POST /appointments` | `dashboard:*` |
| `api/appointments.py` | 412+ | Update appointment | `PATCH /appointments/{id}` | `dashboard:*` |
| `api/appointments.py` | 478+ | Delete appointment | `DELETE /appointments/{id}` | `dashboard:*` |
| `api/appointments.py` | 519+ | Check-in | `POST /appointments/{id}/check-in` | `dashboard:*` |
| `api/appointments.py` | 566+ | Start | `POST /appointments/{id}/start` | `dashboard:*` |
| `api/appointments.py` | 627+ | Complete | `POST /appointments/{id}/complete` | `dashboard:*` |
| `api/appointments.py` | 684+ | Update notes | `PATCH /appointments/{id}/notes` | None needed |

### Walk-ins (7 endpoints missing)

| File | Line | Operation | HTTP | Should Invalidate |
|---|---|---|---|---|
| `api/appointments.py` | 728+ | Create walk-in | `POST /walkins` | `dashboard:*` |
| `api/appointments.py` | 885+ | Bulk walk-in | `POST /walkins/bulk` | `dashboard:*` |
| `api/appointments.py` | 1094+ | Update customer | `PATCH /walkins/session/{id}/customer` | None needed |
| `api/appointments.py` | 1284+ | Start walk-in | `POST /walkins/{id}/start` | `dashboard:*` |
| `api/appointments.py` | 1341+ | Complete walk-in | `POST /walkins/{id}/complete` | `dashboard:*` |
| `api/appointments.py` | 1398+ | Update notes | `PATCH /walkins/{id}/notes` | None needed |
| `api/appointments.py` | 1440+ | Cancel walk-in | `POST /walkins/{id}/cancel` | `dashboard:*` |

---

## Part 5: Inventory Operations (MEDIUM)

**Impact**: Currently no inventory data is cached for reads, so no stale data risk. However, inventory changes can affect dashboard metrics (stock-based cost calculations).

### Inventory (7 endpoints, no caching exists)

| File | Line | Operation | HTTP | Notes |
|---|---|---|---|---|
| `api/inventory.py` | 43-57 | Create supplier | `POST /suppliers` | No read cache exists |
| `api/inventory.py` | 59-76 | Update supplier | `PATCH /suppliers/{id}` | No read cache exists |
| `api/inventory.py` | 85-98 | Create category | `POST /categories` | No read cache exists |
| `api/inventory.py` | 142-159 | Create SKU | `POST /skus` | No read cache exists |
| `api/inventory.py` | 176-197 | Update SKU | `PATCH /skus/{id}` | No read cache exists |
| `api/inventory.py` | 201-229 | Create change request | `POST /change-requests` | No read cache exists |
| `api/inventory.py` | 259-354 | Approve change request | `POST /change-requests/{id}/approve` | Affects stock levels |
| `api/inventory.py` | 356-378 | Reject change request | `POST /change-requests/{id}/reject` | No read cache exists |

**Recommendation**: No immediate cache invalidation needed since inventory data isn't cached for reads. Consider adding read caching + invalidation in the future for performance.

---

## Part 6: Users, Staff, Customers (LOW)

**Impact**: These entities are not cached for reads currently, so no stale data issue. Low priority.

### Users (4 endpoints, no caching exists)

| File | Line | Operation | HTTP |
|---|---|---|---|
| `api/users.py` | 53-110 | Create user | `POST /users` |
| `api/users.py` | 126-181 | Update user | `PATCH /users/{id}` |
| `api/users.py` | 183-212 | Delete user | `DELETE /users/{id}` |
| `api/users.py` | 214-260 | Reset password | `POST /users/{id}/reset-password` |

### Staff (3 endpoints, no caching exists)

| File | Line | Operation | HTTP |
|---|---|---|---|
| `api/staff.py` | 143-170 | Create staff | `POST /staff` |
| `api/staff.py` | 198-235 | Update staff | `PATCH /staff/{id}` |
| `api/staff.py` | 238-275 | Delete staff | `DELETE /staff/{id}` |

### Customers (3 endpoints, no caching exists)

| File | Line | Operation | HTTP |
|---|---|---|---|
| `api/customers.py` | 55-75 | Create customer | `POST /customers` |
| `api/customers.py` | 153-187 | Update customer | `PATCH /customers/{id}` |
| `api/customers.py` | 189-205 | Delete customer | `DELETE /customers/{id}` |

### Attendance (3 endpoints, no caching exists)

| File | Line | Operation | HTTP |
|---|---|---|---|
| `api/attendance.py` | 33+ | Create attendance | `POST /attendance` |
| `api/attendance.py` | 388+ | Update attendance | `PATCH /attendance/{id}` |
| `api/attendance.py` | 503+ | Self-mark attendance | `POST /attendance/my-attendance/mark` |

**Recommendation**: No immediate action needed. Add caching + invalidation when these endpoints become performance bottlenecks.

---

## Properly Handled Systems

| System | Cache Key | Invalidation | Status |
|---|---|---|---|
| Settings | `settings:singleton` | `delete()` on update/reset | Correct |
| Catalog Categories | `catalog:categories:*` | `delete_pattern()` on CRUD + bulk import | Correct |
| Auth Sessions | `refresh_token:*`, `blacklist:*` | TTL-based + explicit revocation | Correct (uses Redis directly) |
| Idempotency | `idempotency:*` | 24h TTL auto-cleanup | Acceptable |

---

## Recommended Fix Order

### Phase 1: Critical (Stale cached data actively served)

1. **Catalog services/addons/templates** - 12 endpoints in `api/catalog.py`
   - Add `cache.delete_pattern("catalog:categories:*")` after mutations
   - Impact: Fixes stale service prices in POS (up to 30m stale)

2. **Dashboard after billing** - 8 endpoints in `api/pos.py`
   - Add `cache.delete_pattern("dashboard:*")` after billing mutations
   - Impact: Fixes stale revenue/tax metrics (up to 60s stale)

### Phase 2: High (Dashboard affected by non-billing mutations)

3. **Dashboard after expenses** - 2 endpoints in `api/expenses.py`
4. **Dashboard after purchases** - 5 endpoints in `api/purchases.py`
5. **Dashboard after appointments** - ~10 endpoints in `api/appointments.py`

### Phase 3: Future (No read caching exists yet)

6. **Inventory** - Add read caching + invalidation when needed
7. **Users/Staff/Customers** - Add read caching + invalidation when needed
8. **Attendance** - Add read caching + invalidation when needed

---

## Implementation Pattern

Use the existing cache service. Every mutation endpoint that affects cached data should add invalidation after `db.commit()`:

```python
# In api/catalog.py (services, addons, templates)
from app.services.cache_service import cache

@router.post("/services", ...)
def create_service(...):
    # ... existing code ...
    db.commit()
    db.refresh(service)

    # ADD: Invalidate catalog cache
    cache.delete_pattern("catalog:categories:*")

    return service
```

```python
# In api/pos.py (all billing mutations)
from app.services.cache_service import cache

@router.post("/bills/{bill_id}/payments", ...)
def add_payment(...):
    # ... existing code ...
    db.commit()

    # ADD: Invalidate dashboard cache
    cache.delete_pattern("dashboard:*")

    return response
```

---

## Summary Statistics

| Category | Total Mutations | With Invalidation | Missing | Priority |
|---|---|---|---|---|
| Catalog Categories | 4 | 4 | 0 | N/A (done) |
| Catalog Services | 3 | 0 | 3 | CRITICAL |
| Catalog Addons | 3 | 0 | 3 | CRITICAL |
| Catalog Staff Templates | 3 | 0 | 3 | CRITICAL |
| Settings | 2 | 2 | 0 | N/A (done) |
| POS/Billing | 8 | 0 | 8 | CRITICAL |
| Expenses | 2 | 0 | 2 | HIGH |
| Purchases | 7 | 0 | 5* | HIGH |
| Appointments | 7 | 0 | 6* | HIGH |
| Walk-ins | 7 | 0 | 5* | HIGH |
| Inventory | 8 | 0 | 0** | LOW |
| Users | 4 | 0 | 0** | LOW |
| Staff | 3 | 0 | 0** | LOW |
| Customers | 3 | 0 | 0** | LOW |
| Attendance | 3 | 0 | 0** | LOW |
| Auth | 4 | 4 | 0 | N/A (done) |
| **TOTAL** | **~71** | **~10** | **~35** | |

\* Only endpoints affecting dashboard metrics need invalidation
\** No read caching exists for these entities, so no invalidation needed yet

---

**Audit Date**: February 2026
**Status**: Phase 1 fixes needed immediately
