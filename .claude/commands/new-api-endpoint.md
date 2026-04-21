---
description: "Scaffold a full-stack API endpoint: backend route, schema, model updates, tests, and frontend integration. Pass the resource name and action as arguments."
argument-hint: "[resource] [action] e.g. 'expenses approve'"
allowed-tools: Read, Grep, Glob, Bash, Edit, Write
---

# New API Endpoint: $ARGUMENTS

Scaffold a full-stack API endpoint for SalonOS following the established codebase conventions.

## Phase 1: Understand & Plan

1. **Parse arguments**: Extract the resource name and action from `$ARGUMENTS` (e.g., "expenses approve" → resource=expenses, action=approve).
2. **Read existing code** for this resource domain:
   - Route: `backend/app/api/{resource}.py`
   - Model: `backend/app/models/{resource}.py`
   - Schema: `backend/app/schemas/{resource}.py`
   - Tests: `backend/tests/unit/test_{resource}.py`
   - Frontend page: `frontend/src/app/dashboard/{resource}/page.tsx`
   - Frontend component: `frontend/src/components/{resource}/`
3. **Read the permission matrix** in `backend/app/auth/permissions.py` to check if this resource.action already exists.
4. List assumptions and **wait for user confirmation** before implementing.

## Phase 2: Backend Implementation

Follow these exact conventions:

### Route (in `backend/app/api/{resource}.py`)
```python
@router.post("/path", response_model=ResponseSchema, status_code=status.HTTP_2XX)
def action_name(
    request_data: RequestSchema,  # Pydantic validated
    current_user: User = Depends(require_permission("resource", "action")),
    db: Session = Depends(get_db)
):
    # Business logic
    # Money always in paise (int), IDs always ULID
    # Raise HTTPException for errors (404, 403, 409)
    pass
```

### Schema (in `backend/app/schemas/{resource}.py`)
- `Base` schema for shared fields
- `Create` schema for POST input
- `Update` schema with all fields Optional
- `Response` schema with `id`, timestamps, `class Config: from_attributes = True`
- `ListResponse` with pagination: `items`, `total`, `page`, `size`, `pages`

### Permissions
- Add the new action to `PermissionChecker.ROLE_PERMISSIONS` for appropriate roles (Owner, Receptionist, Staff).
- Use `require_permission("resource", "action")` in the route dependency.

## Phase 3: Tests (TDD — write BEFORE implementation if new endpoint)

In `backend/tests/unit/test_{resource}.py`:
- Test happy path with valid data
- Test permission denied (wrong role)
- Test 404 (resource not found)
- Test validation errors (bad input)
- Test money edge cases if applicable (paise rounding, zero, negative)

## Phase 4: Frontend Integration

### API call (using existing apiClient pattern)
```typescript
const { data } = await apiClient.post<ResponseType>(`/{resource}/{id}/action`, payload);
```

### Component updates
- Add button/form to the relevant component in `frontend/src/components/{resource}/`
- Use `useAuthStore().hasPermission("resource", "action")` for role-based visibility
- Money display: divide paise by 100 with `toFixed(2)`
- Use shadcn/ui components (Button, Dialog, Form)

### Store updates (if stateful)
- Follow Zustand patterns in `frontend/src/stores/`
- Interface → State → Actions → `create<Store>((set, get) => ({...}))`

## Phase 5: Verify

- Run backend tests: `uv run pytest backend/tests/unit/test_{resource}.py -v`
- Check TypeScript: `cd frontend && npx tsc --noEmit`
- Confirm permissions are consistent between backend and frontend
