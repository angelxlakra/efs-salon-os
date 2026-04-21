---
name: rbac-permissions
description: "Reference for SalonOS RBAC permission system. Use when adding new permissions, checking role access, or ensuring frontend/backend permission consistency."
allowed-tools: Read, Grep, Glob
---

# RBAC Permissions Reference

SalonOS uses a resource.action permission model with 3 roles. Permissions must be consistent between backend (PermissionChecker) and frontend (hasPermission).

## Roles

| Role | Description | Scope |
|------|-------------|-------|
| **Owner** | Full access to everything | All resources, all actions |
| **Receptionist** | Day-to-day operations | Billing, appointments, walk-ins, limited inventory/accounting |
| **Staff** | Minimal, own-work only | View own schedule, create/read bills, start/complete walk-ins |

## Permission Matrix

Source of truth: `backend/app/auth/permissions.py` → `PermissionChecker.ROLE_PERMISSIONS`

| Resource | Owner | Receptionist | Staff |
|----------|-------|--------------|-------|
| **billing** | create, read, update, refund, discount, view_totals | create, read, discount, view_totals | create, read |
| **appointments** | create, read, update, delete, assign_staff | create, read, update, assign_staff | — |
| **walkins** | create, read, update, delete, start, complete | create, read, update, start, complete | create, read, start, complete |
| **inventory** | create, read, update, approve, view_costs | read, request | — |
| **accounting** | view_dashboard, view_profit, export, manage_drawer | view_dashboard, manage_drawer | — |
| **users** | create, read, update, delete | — | — |
| **settings** | read, update | — | — |
| **expenses** | create, read, update, delete, approve | create, read | — |
| **customers** | create, read, update, delete | create, read, update | read |
| **services** | create, read, update, delete | read | read, mark_complete |
| **reports** | view_all, export | view_basic | — |
| **attendance** | create, read, update | create, read | view_own |
| **purchases** | create, read, update, delete, approve | create, read | — |
| **reconciliation** | create, read, approve | create, read | — |

## Backend Implementation

### Permission check (most common)
```python
from app.auth.dependencies import require_permission

@router.post("/resource")
def create_resource(
    current_user: User = Depends(require_permission("resource", "action")),
    db: Session = Depends(get_db)
):
    pass
```

### Role check (for role-specific logic beyond permissions)
```python
from app.auth.dependencies import require_owner, require_owner_or_receptionist

@router.delete("/users/{id}")
def delete_user(
    current_user: User = Depends(require_owner),  # Owner only
    db: Session = Depends(get_db)
):
    pass
```

### Adding a new permission
1. Add to `PermissionChecker.ROLE_PERMISSIONS` in `backend/app/auth/permissions.py`
2. Use `require_permission("resource", "new_action")` in the route
3. Add matching frontend check (see below)

## Frontend Implementation

### Component-level permission gating
```typescript
import { useAuthStore } from '@/stores/auth-store';

function MyComponent() {
  const { hasPermission } = useAuthStore();

  return (
    <>
      {/* Hide entire sections by role */}
      {hasPermission('billing', 'refund') && (
        <Button onClick={handleRefund}>Refund</Button>
      )}

      {/* Hide financial data from Staff */}
      {hasPermission('billing', 'view_totals') && (
        <span>Total: {formatMoney(total)}</span>
      )}
    </>
  );
}
```

### Page-level access control
```typescript
// In dashboard page
const { user } = useAuthStore();

if (user?.role !== 'owner') {
  return <div>Access denied</div>;
}
```

## PII Privacy Rules

| Data | Owner | Receptionist | Staff |
|------|-------|-------------|-------|
| Customer full name | Yes | Yes | First name only |
| Customer phone | Yes | Yes | No |
| Customer email | Yes | Yes | No |
| Financial totals | Yes | Yes | No |
| Staff salary | Yes | No | Own only |

Backend helper: `PermissionChecker.can_view_customer_pii(role)`
Backend helper: `PermissionChecker.can_view_financials(role)`

## Consistency Checklist

When adding/changing permissions, verify BOTH sides:

- [ ] Backend: `PermissionChecker.ROLE_PERMISSIONS` updated
- [ ] Backend: Route uses `require_permission()` or `require_role()`
- [ ] Frontend: Component uses `hasPermission()` to show/hide UI
- [ ] Frontend: API error handler shows "Access denied" for 403 responses
- [ ] Tests: Permission denied test case exists for unauthorized roles
