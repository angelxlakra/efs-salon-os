---
description: "TDD bug-fix workflow: investigate root cause, write a failing test, implement fix, verify. Pass a description of the bug as the argument."
argument-hint: "[bug description]"
allowed-tools: Read, Grep, Glob, Bash, Edit, Write
---

# Fix Bug: $ARGUMENTS

Follow the SalonOS TDD bug-fix workflow. Never skip directly to a fix — always reproduce first.

## Step 1: Investigate

1. **Search the codebase** for code related to the bug description.
2. **Read relevant files** — understand the current behavior and identify the root cause.
3. **Check for related tests** that already exist:
   - Backend: `backend/tests/unit/test_*.py`
   - Frontend: `frontend/src/**/*.test.tsx`
4. **Identify the root cause** — explain what's happening and why.
5. **List affected files** and potential side effects of the fix.

## Step 2: Write a Failing Test

Write a test that **reproduces the bug** and currently fails:

**Backend (pytest)**:
```python
def test_bug_description(db_session, auth_headers):
    """Regression test: [describe the bug]"""
    # Setup: create the conditions that trigger the bug
    # Act: perform the action that causes the bug
    # Assert: verify the EXPECTED behavior (this should FAIL now)
```

**Frontend (Jest/RTL)**:
```typescript
it('should [expected behavior]', () => {
  // Arrange: render component with bug-triggering props
  // Act: trigger the action
  // Assert: check expected outcome (should FAIL now)
});
```

Run the test to **confirm it fails**: `uv run pytest backend/tests/unit/test_*.py -k "test_name" -v`

## Step 3: Implement the Fix

- Make the **minimal change** needed to fix the bug.
- Do NOT refactor surrounding code or add unrelated improvements.
- Pay special attention to:
  - Money values in paise (integer arithmetic, no floats)
  - Timezone handling (UTC storage, IST display)
  - Permission checks (Owner vs Receptionist vs Staff)
  - Soft-delete filters (`deleted_at.is_(None)`)
  - ULID format for IDs

## Step 4: Verify

1. **Re-run the failing test** — it should now pass.
2. **Run the full test suite** for the affected module: `uv run pytest backend/tests/unit/test_{module}.py -v`
3. **Check for regressions** in related functionality.
4. **Summarize**: What was the root cause? What was the fix? What test prevents regression?
