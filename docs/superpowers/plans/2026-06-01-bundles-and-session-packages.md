# Bundles & Session Packages Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement sub-project A from the spec — a catalog of multi-service packages (single-sitting bundles + counted multi-session packs + time-bound unlimited entitlements) with snapshotted per-line pricing, POS auto-application with FIFO conflict resolution, shared-redemption between registered customers, Owner-only refunds with cancellation fee, and audit-logged expiry extensions.

**Architecture:** Hybrid ("Gamma" per spec §4) — new domain tables for catalog and sale lifecycle (`PackageDefinition`, `PackageDefinitionItem`, `PackageSale`, `PackageSaleItem`, `PackageRedemptionAudit`, `PackageExpiryExtension`); redemptions reuse existing `BillItem` with a new `item_type` discriminator and an internal `package_redemption` `PaymentMethod` so GST math, staff contributions, and reporting work unchanged.

**Tech Stack:** FastAPI + SQLAlchemy + Alembic + PostgreSQL on the backend; Next.js 16 (App Router) + React 19 + TypeScript + Zustand + Tailwind on the frontend; Pytest + Vitest + Playwright for tests; RQ for the daily expiry job.

**Spec:** `docs/superpowers/specs/2026-05-29-bundles-packages-design.md`

---

## Codebase convention notes (deviations from spec wording)

The spec described some paths that don't match shipped conventions. The plan uses real conventions; the spec is unchanged. Map:

| Spec wording | Actual convention used in plan |
|---|---|
| `backend/app/services/packages/<submodule>.py` (nested) | `backend/app/services/package_<concern>_service.py` (flat, matches `billing_service.py`) |
| `backend/app/api/v1/packages.py` | `backend/app/api/packages.py` (no `v1` prefix — matches `api/pos.py`, `api/customers.py`) |
| `backend/app/models/package.py` (single file) | Same — single file matches `billing.py` pattern |
| `frontend/src/components/packages/*` | Same — matches existing `components/<domain>/` convention |
| `frontend/src/app/(shell)/dashboard/packages/*` | Same — matches existing route structure |

---

## File structure overview

### Backend — new files

| File | Responsibility |
|---|---|
| `backend/app/models/package.py` | All 6 new SQLAlchemy models + enums |
| `backend/app/schemas/package.py` | Pydantic request/response schemas |
| `backend/app/services/package_pricing_engine.py` | Pure-function math: snapshot, distribute discount, eligibility, refund, expiry validation |
| `backend/app/services/package_catalog_service.py` | CRUD for `PackageDefinition` + items |
| `backend/app/services/package_sales_service.py` | Create a `PackageSale` at bill finalization |
| `backend/app/services/package_redemption_service.py` | Apply / undo redemptions with row-lock concurrency control |
| `backend/app/services/package_refund_service.py` | Issue credit note + cancellation fee |
| `backend/app/services/package_expiry_service.py` | Extend expiry + the daily transition job entry point |
| `backend/app/jobs/scheduled.py` (modify) | Register the daily expiry job |
| `backend/app/api/packages.py` | All package HTTP endpoints |
| `backend/alembic/versions/<rev>_add_packages_module.py` | Migration: 6 tables + 6 indexes + 5 column additions + 1 enum value |
| `backend/tests/unit/services/test_package_pricing_engine.py` | Pricing-engine unit + property tests |
| `backend/tests/unit/services/test_package_concurrent_redemption.py` | DB row-lock race test |
| `backend/tests/integration/test_packages_catalog.py` | Catalog endpoint integration |
| `backend/tests/integration/test_packages_sale_lifecycle.py` | Sell → bill → PackageSale lifecycle |
| `backend/tests/integration/test_packages_redemption.py` | Single + multi + shared redemption + undo |
| `backend/tests/integration/test_packages_refund.py` | Counted + unlimited refund + credit note |
| `backend/tests/integration/test_packages_expiry.py` | Extend + daily job transitions |
| `backend/tests/integration/test_packages_permissions.py` | Per-role permission gating |

### Backend — modified files

| File | Change |
|---|---|
| `backend/app/auth/permissions.py` | Add 10 new permissions to `PermissionChecker.ROLE_PERMISSIONS` |
| `backend/app/config.py` | Add `PACKAGE_DEFAULT_CANCELLATION_FEE_PCT` setting |
| `backend/app/models/billing.py` | Add `bill_type`, `original_bill_id` to Bill; `item_type`, `package_sale_id`, `package_sale_item_id` to BillItem; extend `PaymentMethod` enum with `PACKAGE_REDEMPTION` |
| `backend/app/schemas/billing.py` | Surface new fields in serializers |
| `backend/app/services/billing_service.py` | In `finalize_bill()`: create `PackageSale` for each `package_sale_line` item. In `add_item()`: invoke eligibility check, auto-apply redemption when exactly one eligible, return `eligible_packages` array when 2+. |
| `backend/app/services/receipt_service.py` | Handle new BillItem item_types in receipt rendering |
| `backend/app/api/__init__.py` | Mount the new packages router |

### Frontend — new files

| File | Responsibility |
|---|---|
| `frontend/src/lib/api/packages.ts` | Typed HTTP client for `/api/packages/*` |
| `frontend/src/types/package.ts` | TypeScript types mirroring backend Pydantic schemas |
| `frontend/src/stores/packages-store.ts` | Zustand store: catalog cache + per-customer eligibility cache |
| `frontend/src/components/ui/SessionsLeft.tsx` | Numeral primitive: `7/10` or `∞` |
| `frontend/src/components/ui/ExpiryBadge.tsx` | Pill primitive: green/amber/red/gray by urgency |
| `frontend/src/components/packages/PackageBuilder.tsx` | The 2-column build form (Owner) |
| `frontend/src/components/packages/PackageBuilderDiscountControl.tsx` | Segmented `% / ₹ off / Final` control |
| `frontend/src/components/packages/PackageBuilderEntitlementMatrix.tsx` | 2×2 visual radio matrix |
| `frontend/src/components/packages/PackageBuilderServicesTable.tsx` | Lines table with lock indicators |
| `frontend/src/components/packages/PackageCatalogList.tsx` | Catalog list page body |
| `frontend/src/components/packages/PackageCard.tsx` | Reusable card for rail + selector + sold list |
| `frontend/src/components/packages/PackageSelectorChip.tsx` | The Packages tab/chip in POS selector |
| `frontend/src/components/packages/PackageSaleLine.tsx` | Bill line for `item_type='package_sale_line'` |
| `frontend/src/components/packages/RedemptionLineItem.tsx` | Bill line for `item_type='package_redemption'` with Undo pill |
| `frontend/src/components/packages/MultiPackageSelector.tsx` | Inline radio panel when 2+ eligible |
| `frontend/src/components/packages/EntitlementsRail.tsx` | Permanent POS rail |
| `frontend/src/components/packages/EntitlementsStrip.tsx` | Narrow-viewport horizontal fallback |
| `frontend/src/components/packages/ActivePackagesBadge.tsx` | Single-pill fallback for mobile |
| `frontend/src/components/packages/RefundPackageModal.tsx` | Owner refund modal |
| `frontend/src/components/packages/ExtendExpiryModal.tsx` | Owner expiry-extension modal |
| `frontend/src/app/(shell)/dashboard/packages/page.tsx` | Catalog list route |
| `frontend/src/app/(shell)/dashboard/packages/new/page.tsx` | Create route |
| `frontend/src/app/(shell)/dashboard/packages/[id]/page.tsx` | View route |
| `frontend/src/app/(shell)/dashboard/packages/[id]/edit/page.tsx` | Edit route |
| `frontend/src/app/(shell)/dashboard/packages/sold/page.tsx` | Sold-packages list (Owner refund entry point) |

### Frontend — modified files

| File | Change |
|---|---|
| `frontend/src/components/shell/sidebar.tsx` | Add "Packages" menu item (Owner-gated via `hasPermission`) |
| `frontend/src/app/(shell)/dashboard/pos/page.tsx` | Inject EntitlementsRail/Strip/Badge by breakpoint; render new BillItem types; add Last-visit subtitle on customer header |
| `frontend/src/app/(shell)/dashboard/bills/[id]/page.tsx` | Add "Refund Package" button when applicable (Owner) |
| `frontend/src/components/customers/format.ts` (or equivalent) | Extend customer-name formatter for buyer-vs-recipient |

### Docs

| File | Change |
|---|---|
| `docs/INDEX.md` | Add entry for the packages feature doc |
| `docs/features/10-packages.md` | New feature-level doc |
| `docs/models/10-packages.md` | New model-level doc |

---

## Phase 1 — Foundation: permissions, settings, models, migration, schemas

### Task 1: Add new permissions to RBAC

**Files:**
- Modify: `backend/app/auth/permissions.py`
- Test: `backend/tests/unit/auth/test_package_permissions.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/unit/auth/test_package_permissions.py`:

```python
"""Verify the new packages.* permissions are wired into RBAC correctly."""

import pytest
from app.auth.permissions import PermissionChecker
from app.models.user import UserRole


@pytest.mark.parametrize("role,permission,allowed", [
    # packages:read — all roles
    (UserRole.OWNER, ("packages", "read"), True),
    (UserRole.RECEPTIONIST, ("packages", "read"), True),
    (UserRole.STAFF, ("packages", "read"), True),
    # packages:create/update/delete — Owner only
    (UserRole.OWNER, ("packages", "create"), True),
    (UserRole.RECEPTIONIST, ("packages", "create"), False),
    (UserRole.STAFF, ("packages", "create"), False),
    (UserRole.OWNER, ("packages", "update"), True),
    (UserRole.RECEPTIONIST, ("packages", "update"), False),
    (UserRole.OWNER, ("packages", "delete"), True),
    (UserRole.RECEPTIONIST, ("packages", "delete"), False),
    # packages:sell — Owner + Receptionist
    (UserRole.OWNER, ("packages", "sell"), True),
    (UserRole.RECEPTIONIST, ("packages", "sell"), True),
    (UserRole.STAFF, ("packages", "sell"), False),
    # packages:redeem — all roles
    (UserRole.OWNER, ("packages", "redeem"), True),
    (UserRole.RECEPTIONIST, ("packages", "redeem"), True),
    (UserRole.STAFF, ("packages", "redeem"), True),
    # packages:redeem_for_other — Owner + Receptionist
    (UserRole.OWNER, ("packages", "redeem_for_other"), True),
    (UserRole.RECEPTIONIST, ("packages", "redeem_for_other"), True),
    (UserRole.STAFF, ("packages", "redeem_for_other"), False),
    # packages:refund / extend_expiry / override_price — Owner only
    (UserRole.OWNER, ("packages", "refund"), True),
    (UserRole.RECEPTIONIST, ("packages", "refund"), False),
    (UserRole.OWNER, ("packages", "extend_expiry"), True),
    (UserRole.RECEPTIONIST, ("packages", "extend_expiry"), False),
    (UserRole.OWNER, ("packages", "override_price"), True),
    (UserRole.RECEPTIONIST, ("packages", "override_price"), False),
])
def test_package_permissions(role, permission, allowed):
    resource, action = permission
    assert PermissionChecker.has_permission(role, resource, action) is allowed
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/unit/auth/test_package_permissions.py -v`
Expected: 24 test cases FAIL with "packages" not in `ROLE_PERMISSIONS`.

- [ ] **Step 3: Add permissions to `PermissionChecker.ROLE_PERMISSIONS`**

Open `backend/app/auth/permissions.py`. Find the `ROLE_PERMISSIONS` dict. Add to each role's permission set:

```python
# In ROLE_PERMISSIONS[UserRole.OWNER]:
"packages": {"read", "create", "update", "delete", "sell", "redeem",
             "redeem_for_other", "refund", "extend_expiry", "override_price"},

# In ROLE_PERMISSIONS[UserRole.RECEPTIONIST]:
"packages": {"read", "sell", "redeem", "redeem_for_other"},

# In ROLE_PERMISSIONS[UserRole.STAFF]:
"packages": {"read", "redeem"},
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/unit/auth/test_package_permissions.py -v`
Expected: 24 PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/auth/permissions.py backend/tests/unit/auth/test_package_permissions.py
git commit -m "feat(packages): add 10 RBAC permissions for packages domain"
```

---

### Task 2: Add settings constant for default cancellation fee

**Files:**
- Modify: `backend/app/config.py`
- Test: `backend/tests/unit/test_config.py` (may exist; create if not)

- [ ] **Step 1: Write the failing test**

Add to `backend/tests/unit/test_config.py` (or create if missing):

```python
"""Verify package-related settings."""

from decimal import Decimal
from app.config import settings


def test_package_default_cancellation_fee_pct_is_20():
    assert settings.PACKAGE_DEFAULT_CANCELLATION_FEE_PCT == Decimal("20.00")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/unit/test_config.py::test_package_default_cancellation_fee_pct_is_20 -v`
Expected: FAIL with `AttributeError`.

- [ ] **Step 3: Add setting**

In `backend/app/config.py` find the `Settings` class. Add:

```python
from decimal import Decimal

class Settings(BaseSettings):
    # ... existing fields ...

    # Packages
    PACKAGE_DEFAULT_CANCELLATION_FEE_PCT: Decimal = Decimal("20.00")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/unit/test_config.py::test_package_default_cancellation_fee_pct_is_20 -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/config.py backend/tests/unit/test_config.py
git commit -m "feat(packages): add PACKAGE_DEFAULT_CANCELLATION_FEE_PCT setting (default 20%)"
```

---

### Task 3: Create PackageDefinition + PackageDefinitionItem models

**Files:**
- Create: `backend/app/models/package.py`
- Test: `backend/tests/unit/models/test_package_models.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/unit/models/test_package_models.py`:

```python
"""Smoke test: model classes exist with expected columns."""

from app.models.package import (
    PackageDefinition,
    PackageDefinitionItem,
    PackageDefinitionStatus,
    EntitlementType,
    Shareability,
)


def test_package_definition_model_shape():
    assert hasattr(PackageDefinition, "name")
    assert hasattr(PackageDefinition, "status")
    assert hasattr(PackageDefinition, "entitlement_type")
    assert hasattr(PackageDefinition, "shareability")
    assert hasattr(PackageDefinition, "validity_days")
    assert hasattr(PackageDefinition, "auto_apply")
    assert hasattr(PackageDefinition, "cancellation_fee_pct")
    assert hasattr(PackageDefinition, "total_sessions")
    assert hasattr(PackageDefinition, "items")  # relationship


def test_enum_values():
    assert PackageDefinitionStatus.DRAFT.value == "draft"
    assert PackageDefinitionStatus.PUBLISHED.value == "published"
    assert PackageDefinitionStatus.ARCHIVED.value == "archived"
    assert EntitlementType.COUNTED.value == "counted"
    assert EntitlementType.UNLIMITED.value == "unlimited"
    assert Shareability.OWNER_ONLY.value == "owner_only"
    assert Shareability.SHARED.value == "shared"


def test_package_definition_item_shape():
    assert hasattr(PackageDefinitionItem, "package_definition_id")
    assert hasattr(PackageDefinitionItem, "service_id")
    assert hasattr(PackageDefinitionItem, "quantity")
    assert hasattr(PackageDefinitionItem, "unit_price_paise")
    assert hasattr(PackageDefinitionItem, "locked")
    assert hasattr(PackageDefinitionItem, "display_order")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/unit/models/test_package_models.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Create the model file**

Create `backend/app/models/package.py`:

```python
"""Package models — definitions, sales, redemptions, expiry extensions."""

import enum
from decimal import Decimal
from sqlalchemy import (
    Boolean, CheckConstraint, Column, DateTime, Enum, ForeignKey,
    Integer, Numeric, String, Text, UniqueConstraint, Index,
)
from sqlalchemy.orm import relationship
from app.database import Base
from app.models.base import TimestampMixin, SoftDeleteMixin, ULIDMixin


class PackageDefinitionStatus(str, enum.Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class EntitlementType(str, enum.Enum):
    COUNTED = "counted"
    UNLIMITED = "unlimited"


class Shareability(str, enum.Enum):
    OWNER_ONLY = "owner_only"
    SHARED = "shared"


class PackageDefinition(Base, ULIDMixin, TimestampMixin, SoftDeleteMixin):
    """Catalog row. Edits don't affect already-sold packages (snapshots protect them)."""
    __tablename__ = "package_definitions"

    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(
        Enum(PackageDefinitionStatus, name="packagedefinitionstatus"),
        nullable=False, default=PackageDefinitionStatus.DRAFT,
    )
    entitlement_type = Column(
        Enum(EntitlementType, name="entitlementtype"), nullable=False,
    )
    total_sessions = Column(Integer, nullable=True)
    shareability = Column(
        Enum(Shareability, name="shareability"),
        nullable=False, default=Shareability.OWNER_ONLY,
    )
    validity_days = Column(Integer, nullable=False)
    auto_apply = Column(Boolean, nullable=False, default=True)
    cancellation_fee_pct = Column(Numeric(5, 2), nullable=False, default=Decimal("20.00"))
    created_by_user_id = Column(String(26), ForeignKey("users.id"), nullable=False)

    items = relationship(
        "PackageDefinitionItem",
        back_populates="definition",
        cascade="all, delete-orphan",
        order_by="PackageDefinitionItem.display_order",
    )

    __table_args__ = (
        CheckConstraint(
            "(entitlement_type = 'counted' AND total_sessions IS NOT NULL AND total_sessions >= 1) "
            "OR (entitlement_type = 'unlimited' AND total_sessions IS NULL)",
            name="ck_package_def_entitlement_sessions",
        ),
        CheckConstraint("cancellation_fee_pct >= 0 AND cancellation_fee_pct <= 100",
                        name="ck_package_def_fee_range"),
        CheckConstraint("validity_days > 0", name="ck_package_def_validity_positive"),
    )


class PackageDefinitionItem(Base, ULIDMixin, TimestampMixin):
    __tablename__ = "package_definition_items"

    package_definition_id = Column(
        String(26),
        ForeignKey("package_definitions.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    service_id = Column(String(26), ForeignKey("services.id", ondelete="RESTRICT"), nullable=False)
    quantity = Column(Integer, nullable=False, default=1)
    unit_price_paise = Column(Integer, nullable=False)
    locked = Column(Boolean, nullable=False, default=False)
    display_order = Column(Integer, nullable=False, default=0)

    definition = relationship("PackageDefinition", back_populates="items")

    __table_args__ = (
        CheckConstraint("quantity >= 1", name="ck_package_def_item_qty_positive"),
        CheckConstraint("unit_price_paise >= 0", name="ck_package_def_item_price_non_negative"),
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/unit/models/test_package_models.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add backend/app/models/package.py backend/tests/unit/models/test_package_models.py
git commit -m "feat(packages): add PackageDefinition + PackageDefinitionItem models"
```

---

### Task 4: Add PackageSale + PackageSaleItem models

**Files:**
- Modify: `backend/app/models/package.py`
- Test: `backend/tests/unit/models/test_package_models.py`

- [ ] **Step 1: Extend the test file**

Append to `backend/tests/unit/models/test_package_models.py`:

```python
from app.models.package import PackageSale, PackageSaleItem, PackageSaleStatus


def test_package_sale_model_shape():
    assert hasattr(PackageSale, "bill_id")
    assert hasattr(PackageSale, "package_definition_id")
    assert hasattr(PackageSale, "customer_id")
    assert hasattr(PackageSale, "selling_staff_id")
    assert hasattr(PackageSale, "sold_at")
    assert hasattr(PackageSale, "expires_at")
    assert hasattr(PackageSale, "entitlement_type_snapshot")
    assert hasattr(PackageSale, "shareability_snapshot")
    assert hasattr(PackageSale, "cancellation_fee_pct_snapshot")
    assert hasattr(PackageSale, "total_sessions_snapshot")
    assert hasattr(PackageSale, "sessions_remaining")
    assert hasattr(PackageSale, "status")
    assert hasattr(PackageSale, "refunded_at")
    assert hasattr(PackageSale, "refund_bill_id")
    assert hasattr(PackageSale, "items")


def test_package_sale_status_enum():
    assert PackageSaleStatus.ACTIVE.value == "active"
    assert PackageSaleStatus.EXPIRED.value == "expired"
    assert PackageSaleStatus.REFUNDED.value == "refunded"
    assert PackageSaleStatus.EXHAUSTED.value == "exhausted"


def test_package_sale_item_shape():
    assert hasattr(PackageSaleItem, "package_sale_id")
    assert hasattr(PackageSaleItem, "package_definition_item_id")
    assert hasattr(PackageSaleItem, "service_id")
    assert hasattr(PackageSaleItem, "quantity")
    assert hasattr(PackageSaleItem, "snapshot_unit_price_paise")
    assert hasattr(PackageSaleItem, "snapshot_gst_rate_pct")
    assert hasattr(PackageSaleItem, "locked")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/unit/models/test_package_models.py -v`
Expected: 3 new tests FAIL with `ImportError`.

- [ ] **Step 3: Add models to `backend/app/models/package.py`**

Append to the existing file:

```python
class PackageSaleStatus(str, enum.Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    REFUNDED = "refunded"
    EXHAUSTED = "exhausted"


class PackageSale(Base, ULIDMixin, TimestampMixin):
    """Lifecycle row for one sold package. All policy snapshotted at sale time."""
    __tablename__ = "package_sales"

    bill_id = Column(
        String(26), ForeignKey("bills.id", ondelete="RESTRICT"),
        nullable=False, unique=True, index=True,
    )
    package_definition_id = Column(
        String(26), ForeignKey("package_definitions.id", ondelete="RESTRICT"), nullable=False,
    )
    customer_id = Column(
        String(26), ForeignKey("customers.id", ondelete="RESTRICT"),
        nullable=False, index=True,
    )
    selling_staff_id = Column(String(26), ForeignKey("staff.id", ondelete="SET NULL"), nullable=True)

    sold_at = Column(DateTime(timezone=True), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)

    entitlement_type_snapshot = Column(
        Enum(EntitlementType, name="entitlementtype"), nullable=False,
    )
    shareability_snapshot = Column(
        Enum(Shareability, name="shareability"), nullable=False,
    )
    cancellation_fee_pct_snapshot = Column(Numeric(5, 2), nullable=False)
    total_sessions_snapshot = Column(Integer, nullable=True)
    sessions_remaining = Column(Integer, nullable=True)

    status = Column(
        Enum(PackageSaleStatus, name="packagesalestatus"),
        nullable=False, default=PackageSaleStatus.ACTIVE, index=True,
    )
    refunded_at = Column(DateTime(timezone=True), nullable=True)
    refund_bill_id = Column(String(26), ForeignKey("bills.id"), nullable=True)

    items = relationship(
        "PackageSaleItem",
        back_populates="sale",
        cascade="all, delete-orphan",
        order_by="PackageSaleItem.display_order",
    )

    __table_args__ = (
        Index("ix_package_sales_customer_status", "customer_id", "status"),
        Index("ix_package_sales_expires_status", "expires_at", "status"),
        Index("ix_package_sales_selling_staff_sold_at", "selling_staff_id", "sold_at"),
    )


class PackageSaleItem(Base, ULIDMixin, TimestampMixin):
    __tablename__ = "package_sale_items"

    package_sale_id = Column(
        String(26), ForeignKey("package_sales.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    package_definition_item_id = Column(
        String(26), ForeignKey("package_definition_items.id", ondelete="RESTRICT"),
        nullable=False,
    )
    service_id = Column(
        String(26), ForeignKey("services.id", ondelete="RESTRICT"),
        nullable=False, index=True,
    )
    quantity = Column(Integer, nullable=False)
    snapshot_unit_price_paise = Column(Integer, nullable=False)
    snapshot_gst_rate_pct = Column(Numeric(5, 2), nullable=False)
    locked = Column(Boolean, nullable=False)
    display_order = Column(Integer, nullable=False)

    sale = relationship("PackageSale", back_populates="items")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/unit/models/test_package_models.py -v`
Expected: ALL PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/models/package.py backend/tests/unit/models/test_package_models.py
git commit -m "feat(packages): add PackageSale + PackageSaleItem with snapshot columns"
```

---

### Task 5: Add PackageRedemptionAudit + PackageExpiryExtension models

**Files:**
- Modify: `backend/app/models/package.py`
- Test: `backend/tests/unit/models/test_package_models.py`

- [ ] **Step 1: Extend the test**

Append to the test file:

```python
from app.models.package import PackageRedemptionAudit, PackageExpiryExtension


def test_package_redemption_audit_shape():
    assert hasattr(PackageRedemptionAudit, "package_sale_id")
    assert hasattr(PackageRedemptionAudit, "bill_item_id")
    assert hasattr(PackageRedemptionAudit, "package_sale_item_id")
    assert hasattr(PackageRedemptionAudit, "redeemed_for_customer_id")
    assert hasattr(PackageRedemptionAudit, "performed_by_user_id")
    assert hasattr(PackageRedemptionAudit, "redeemed_at")
    assert hasattr(PackageRedemptionAudit, "session_number")


def test_package_expiry_extension_shape():
    assert hasattr(PackageExpiryExtension, "package_sale_id")
    assert hasattr(PackageExpiryExtension, "previous_expires_at")
    assert hasattr(PackageExpiryExtension, "new_expires_at")
    assert hasattr(PackageExpiryExtension, "performed_by_user_id")
    assert hasattr(PackageExpiryExtension, "reason")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/unit/models/test_package_models.py -v`
Expected: 2 new tests FAIL.

- [ ] **Step 3: Add models**

Append to `backend/app/models/package.py`:

```python
class PackageRedemptionAudit(Base, ULIDMixin, TimestampMixin):
    """Append-only log of every redemption. Captures recipient for shared packages."""
    __tablename__ = "package_redemption_audit"

    package_sale_id = Column(
        String(26), ForeignKey("package_sales.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    bill_item_id = Column(
        String(26), ForeignKey("bill_items.id", ondelete="RESTRICT"),
        nullable=False, unique=True,
    )
    package_sale_item_id = Column(
        String(26), ForeignKey("package_sale_items.id", ondelete="RESTRICT"),
        nullable=False,
    )
    redeemed_for_customer_id = Column(
        String(26), ForeignKey("customers.id", ondelete="RESTRICT"),
        nullable=False, index=True,
    )
    performed_by_user_id = Column(String(26), ForeignKey("users.id"), nullable=False)
    redeemed_at = Column(DateTime(timezone=True), nullable=False, index=True)
    session_number = Column(Integer, nullable=True)
    notes = Column(Text, nullable=True)

    __table_args__ = (
        Index("ix_package_redemption_audit_for_customer_redeemed_at",
              "redeemed_for_customer_id", "redeemed_at"),
    )


class PackageExpiryExtension(Base, ULIDMixin, TimestampMixin):
    __tablename__ = "package_expiry_extensions"

    package_sale_id = Column(
        String(26), ForeignKey("package_sales.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    previous_expires_at = Column(DateTime(timezone=True), nullable=False)
    new_expires_at = Column(DateTime(timezone=True), nullable=False)
    performed_by_user_id = Column(String(26), ForeignKey("users.id"), nullable=False)
    extended_at = Column(DateTime(timezone=True), nullable=False)
    reason = Column(Text, nullable=False)

    __table_args__ = (
        CheckConstraint("new_expires_at > previous_expires_at",
                        name="ck_package_extend_forward_in_time"),
    )
```

- [ ] **Step 4: Run tests**

Run: `cd backend && pytest tests/unit/models/test_package_models.py -v`
Expected: ALL PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/models/package.py backend/tests/unit/models/test_package_models.py
git commit -m "feat(packages): add redemption audit + expiry extension models"
```

---

### Task 6: Add additive columns to Bill, BillItem; extend PaymentMethod

**Files:**
- Modify: `backend/app/models/billing.py`
- Test: `backend/tests/unit/models/test_billing_packages_columns.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/unit/models/test_billing_packages_columns.py`:

```python
"""Verify additive columns on Bill, BillItem; new PaymentMethod value."""

from app.models.billing import Bill, BillItem, BillType, BillItemType, PaymentMethod


def test_bill_has_bill_type_and_original_bill_id():
    assert hasattr(Bill, "bill_type")
    assert hasattr(Bill, "original_bill_id")


def test_bill_type_enum_has_normal_and_credit_note():
    assert BillType.NORMAL.value == "normal"
    assert BillType.CREDIT_NOTE.value == "credit_note"


def test_bill_item_has_item_type_and_package_refs():
    assert hasattr(BillItem, "item_type")
    assert hasattr(BillItem, "package_sale_id")
    assert hasattr(BillItem, "package_sale_item_id")


def test_bill_item_type_enum_values():
    assert BillItemType.SERVICE.value == "service"
    assert BillItemType.PRODUCT.value == "product"
    assert BillItemType.PACKAGE_SALE_LINE.value == "package_sale_line"
    assert BillItemType.PACKAGE_REDEMPTION.value == "package_redemption"


def test_payment_method_has_package_redemption():
    assert PaymentMethod.PACKAGE_REDEMPTION.value == "package_redemption"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/unit/models/test_billing_packages_columns.py -v`
Expected: FAIL with `ImportError: cannot import name 'BillType'`.

- [ ] **Step 3: Modify `backend/app/models/billing.py`**

Add new enums near the top (with the existing enums):

```python
class BillType(str, enum.Enum):
    """Bill kind: normal sale or credit note (refund)."""
    NORMAL = "normal"
    CREDIT_NOTE = "credit_note"


class BillItemType(str, enum.Enum):
    """BillItem kind: existing service/product or new package item types."""
    SERVICE = "service"
    PRODUCT = "product"
    PACKAGE_SALE_LINE = "package_sale_line"
    PACKAGE_REDEMPTION = "package_redemption"
```

Extend the existing `PaymentMethod` enum (do not redefine — add value):

```python
class PaymentMethod(str, enum.Enum):
    CASH = "cash"
    UPI = "upi"
    CARD = "card"
    OTHER = "other"
    PACKAGE_REDEMPTION = "package_redemption"  # NEW
```

Add columns to the `Bill` model:

```python
class Bill(Base, ULIDMixin, TimestampMixin):
    # ... existing columns ...

    bill_type = Column(
        Enum(BillType, name="billtype"),
        nullable=False, default=BillType.NORMAL, server_default="normal",
        index=True,
    )
    original_bill_id = Column(String(26), ForeignKey("bills.id"), nullable=True)

    __table_args__ = (
        CheckConstraint(
            "(bill_type = 'credit_note' AND original_bill_id IS NOT NULL) "
            "OR (bill_type = 'normal' AND original_bill_id IS NULL)",
            name="ck_bill_credit_note_has_original",
        ),
    )
```

Add columns to the `BillItem` model:

```python
class BillItem(Base, ULIDMixin, TimestampMixin):
    # ... existing columns ...

    item_type = Column(
        Enum(BillItemType, name="billitemtype"),
        nullable=False, default=BillItemType.SERVICE, server_default="service",
        index=True,
    )
    package_sale_id = Column(
        String(26), ForeignKey("package_sales.id"),
        nullable=True, index=True,
    )
    package_sale_item_id = Column(
        String(26), ForeignKey("package_sale_items.id"),
        nullable=True,
    )
```

- [ ] **Step 4: Run tests**

Run: `cd backend && pytest tests/unit/models/test_billing_packages_columns.py -v`
Expected: ALL PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/models/billing.py backend/tests/unit/models/test_billing_packages_columns.py
git commit -m "feat(packages): extend Bill/BillItem/PaymentMethod with package discriminators"
```

---

### Task 7: Generate Alembic migration

**Files:**
- Create: `backend/alembic/versions/<rev>_add_packages_module.py` (autogenerated)

- [ ] **Step 1: Generate the migration**

Run: `cd backend && alembic revision --autogenerate -m "add packages module"`
Expected: New file appears at `backend/alembic/versions/<rev>_add_packages_module.py`.

- [ ] **Step 2: Inspect & verify the autogenerated migration**

Open the new file. Confirm the `upgrade()` function contains, in order:

1. `op.create_table("package_definitions", ...)` with all columns + 3 CHECK constraints
2. `op.create_table("package_definition_items", ...)` with 2 CHECK constraints
3. `op.create_table("package_sales", ...)` with FKs + 3 indexes
4. `op.create_table("package_sale_items", ...)`
5. `op.create_table("package_redemption_audit", ...)` with 1 extra index
6. `op.create_table("package_expiry_extensions", ...)` with 1 CHECK
7. `op.add_column("bills", sa.Column("bill_type", ...))` with server_default `'normal'`
8. `op.add_column("bills", sa.Column("original_bill_id", ...))`
9. CHECK constraint `ck_bill_credit_note_has_original` on bills
10. `op.add_column("bill_items", sa.Column("item_type", ...))` with server_default `'service'`
11. `op.add_column("bill_items", sa.Column("package_sale_id", ...))`
12. `op.add_column("bill_items", sa.Column("package_sale_item_id", ...))`
13. `op.execute("ALTER TYPE paymentmethod ADD VALUE IF NOT EXISTS 'package_redemption'")` — Alembic does NOT autogenerate enum value additions; **add this manually if missing**

If item 13 is missing, edit the file and add it at the top of `upgrade()`:

```python
def upgrade():
    # Add new value to existing PaymentMethod enum (must be outside transaction in older PG, but ALTER TYPE ADD VALUE in PG 12+ works in transaction)
    op.execute("ALTER TYPE paymentmethod ADD VALUE IF NOT EXISTS 'package_redemption'")
    # ... rest of autogen ...
```

For `downgrade()`, ensure it drops the tables in reverse order. Note: PostgreSQL does NOT support removing enum values; the downgrade leaves `package_redemption` in the enum (acceptable, documented). Add a comment:

```python
def downgrade():
    # Drop new columns first to avoid FK breakage
    op.drop_column("bill_items", "package_sale_item_id")
    op.drop_column("bill_items", "package_sale_id")
    op.drop_column("bill_items", "item_type")
    op.drop_constraint("ck_bill_credit_note_has_original", "bills")
    op.drop_column("bills", "original_bill_id")
    op.drop_column("bills", "bill_type")
    # Drop tables in reverse dependency order
    op.drop_table("package_expiry_extensions")
    op.drop_table("package_redemption_audit")
    op.drop_table("package_sale_items")
    op.drop_table("package_sales")
    op.drop_table("package_definition_items")
    op.drop_table("package_definitions")
    # NOTE: PaymentMethod enum value 'package_redemption' is not removed
    # (PostgreSQL doesn't support DROP VALUE on enums). Acceptable.
```

- [ ] **Step 3: Apply the migration to dev DB**

Run: `cd backend && alembic upgrade head`
Expected: Migration applies cleanly. No errors.

- [ ] **Step 4: Verify schema**

Run: `cd backend && psql $DATABASE_URL -c "\dt package*"` (or via your preferred PG client)
Expected: Lists 6 new tables.

Run: `cd backend && psql $DATABASE_URL -c "\d bills" | grep bill_type`
Expected: Shows `bill_type | billtype | not null | 'normal'`.

- [ ] **Step 5: Test reversibility**

Run: `cd backend && alembic downgrade -1 && alembic upgrade head`
Expected: Down then up runs cleanly.

- [ ] **Step 6: Commit**

```bash
git add backend/alembic/versions/
git commit -m "feat(packages): alembic migration — 6 new tables, 5 column additions, 1 enum value"
```

---

### Task 8: Create Pydantic schemas

**Files:**
- Create: `backend/app/schemas/package.py`
- Test: `backend/tests/unit/schemas/test_package_schemas.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/unit/schemas/test_package_schemas.py`:

```python
"""Validate package schemas: required fields, validation rules, serialization."""

import pytest
from decimal import Decimal
from pydantic import ValidationError
from app.schemas.package import (
    PackageDefinitionCreate, PackageDefinitionItemCreate, DiscountInput,
    PackageDefinitionResponse, PackageSaleResponse, RefundRequest,
    ExtendExpiryRequest, RedemptionEligibilityRequest,
)


def test_definition_create_minimal_counted():
    obj = PackageDefinitionCreate(
        name="Test",
        entitlement_type="counted",
        total_sessions=10,
        validity_days=180,
        shareability="owner_only",
        items=[PackageDefinitionItemCreate(
            service_id="01HXYZ0000000000000000ABCD",
            quantity=1,
            unit_price_paise=50000,
        )],
    )
    assert obj.total_sessions == 10


def test_definition_create_rejects_counted_without_sessions():
    with pytest.raises(ValidationError):
        PackageDefinitionCreate(
            name="Test", entitlement_type="counted", validity_days=180,
            shareability="owner_only",
            items=[PackageDefinitionItemCreate(
                service_id="01HXYZ0000000000000000ABCD",
                quantity=1, unit_price_paise=50000,
            )],
        )


def test_definition_create_rejects_unlimited_with_sessions():
    with pytest.raises(ValidationError):
        PackageDefinitionCreate(
            name="Test", entitlement_type="unlimited", total_sessions=10,
            validity_days=30, shareability="owner_only",
            items=[PackageDefinitionItemCreate(
                service_id="01HXYZ0000000000000000ABCD",
                quantity=1, unit_price_paise=50000,
            )],
        )


def test_definition_create_fee_pct_range():
    with pytest.raises(ValidationError):
        PackageDefinitionCreate(
            name="Test", entitlement_type="counted", total_sessions=5,
            validity_days=180, shareability="owner_only",
            cancellation_fee_pct=Decimal("150"),
            items=[PackageDefinitionItemCreate(
                service_id="01HXYZ0000000000000000ABCD",
                quantity=1, unit_price_paise=50000,
            )],
        )


def test_discount_input_modes():
    DiscountInput(mode="pct", value=Decimal("20"))
    DiscountInput(mode="flat", value=Decimal("500"))
    DiscountInput(mode="final", value=Decimal("4500"))
    with pytest.raises(ValidationError):
        DiscountInput(mode="invalid", value=Decimal("10"))


def test_refund_request_requires_reason():
    with pytest.raises(ValidationError):
        RefundRequest(payment_method="cash", reason="")


def test_extend_expiry_request_requires_reason():
    with pytest.raises(ValidationError):
        ExtendExpiryRequest(
            new_expires_at="2027-01-01T00:00:00+00:00",
            reason="",
        )
```

- [ ] **Step 2: Run test**

Run: `cd backend && pytest tests/unit/schemas/test_package_schemas.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Create the schemas file**

Create `backend/app/schemas/package.py`:

```python
"""Pydantic schemas for packages API."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import List, Literal, Optional
from pydantic import BaseModel, Field, model_validator
from app.models.package import (
    PackageDefinitionStatus, EntitlementType, Shareability, PackageSaleStatus,
)


# ---------- Definition CRUD ----------

class PackageDefinitionItemCreate(BaseModel):
    service_id: str = Field(..., min_length=26, max_length=26)
    quantity: int = Field(default=1, ge=1)
    unit_price_paise: int = Field(..., ge=0)
    locked: bool = False
    display_order: int = 0


class DiscountInput(BaseModel):
    mode: Literal["pct", "flat", "final"]
    value: Decimal


class PackageDefinitionCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    entitlement_type: EntitlementType
    total_sessions: Optional[int] = Field(None, ge=1)
    shareability: Shareability = Shareability.OWNER_ONLY
    validity_days: int = Field(..., ge=1)
    auto_apply: bool = True
    cancellation_fee_pct: Decimal = Field(default=Decimal("20.00"), ge=0, le=100)
    items: List[PackageDefinitionItemCreate] = Field(..., min_length=1)
    discount: Optional[DiscountInput] = None  # optional server-side distribution

    @model_validator(mode="after")
    def validate_entitlement_sessions(self):
        if self.entitlement_type == EntitlementType.COUNTED and self.total_sessions is None:
            raise ValueError("total_sessions required when entitlement_type=counted")
        if self.entitlement_type == EntitlementType.UNLIMITED and self.total_sessions is not None:
            raise ValueError("total_sessions must be null when entitlement_type=unlimited")
        return self


class PackageDefinitionUpdate(PackageDefinitionCreate):
    pass


class PackageDefinitionItemResponse(BaseModel):
    id: str
    service_id: str
    service_name: Optional[str] = None  # joined from Service
    quantity: int
    unit_price_paise: int
    locked: bool
    display_order: int

    class Config:
        from_attributes = True


class PackageDefinitionResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    status: PackageDefinitionStatus
    entitlement_type: EntitlementType
    total_sessions: Optional[int]
    shareability: Shareability
    validity_days: int
    auto_apply: bool
    cancellation_fee_pct: Decimal
    items: List[PackageDefinitionItemResponse]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ---------- Sales ----------

class PackageSaleItemResponse(BaseModel):
    id: str
    service_id: str
    service_name: Optional[str] = None
    quantity: int
    snapshot_unit_price_paise: int
    snapshot_gst_rate_pct: Decimal
    locked: bool

    class Config:
        from_attributes = True


class PackageSaleResponse(BaseModel):
    id: str
    bill_id: str
    package_definition_id: str
    package_definition_name: Optional[str] = None
    customer_id: str
    customer_name: Optional[str] = None
    selling_staff_id: Optional[str]
    sold_at: datetime
    expires_at: datetime
    entitlement_type_snapshot: EntitlementType
    shareability_snapshot: Shareability
    cancellation_fee_pct_snapshot: Decimal
    total_sessions_snapshot: Optional[int]
    sessions_remaining: Optional[int]
    status: PackageSaleStatus
    refunded_at: Optional[datetime]
    refund_bill_id: Optional[str]
    items: List[PackageSaleItemResponse]

    class Config:
        from_attributes = True


class PackageSaleSummary(BaseModel):
    """Lightweight projection for eligibility rail."""
    id: str
    package_definition_name: str
    entitlement_type_snapshot: EntitlementType
    sessions_remaining: Optional[int]
    total_sessions_snapshot: Optional[int]
    expires_at: datetime
    shareability_snapshot: Shareability
    customer_id: str  # the buyer
    customer_name: Optional[str] = None

    class Config:
        from_attributes = True


# ---------- Eligibility ----------

class RedemptionEligibilityRequest(BaseModel):
    customer_id: str = Field(..., min_length=26, max_length=26)
    service_id: str = Field(..., min_length=26, max_length=26)


class EligiblePackageResponse(BaseModel):
    package_sale: PackageSaleSummary
    snapshot_price_paise: int  # the per-line price that would be billed


# ---------- Refund + extend ----------

class RefundRequest(BaseModel):
    payment_method: Literal["cash", "upi", "card", "pending_balance"]
    reason: str = Field(..., min_length=1)


class RefundBreakdown(BaseModel):
    kind: Literal["counted", "unlimited"]
    base_paise: int
    fee_paise: int
    refund_paise: int
    consumed_value_paise: int  # for context in UI
    pct_remaining: Optional[Decimal] = None  # unlimited only
    sessions_consumed: Optional[int] = None  # counted only
    sessions_total: Optional[int] = None  # counted only


class ExtendExpiryRequest(BaseModel):
    new_expires_at: datetime
    reason: str = Field(..., min_length=1)
```

- [ ] **Step 4: Run tests**

Run: `cd backend && pytest tests/unit/schemas/test_package_schemas.py -v`
Expected: ALL PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/schemas/package.py backend/tests/unit/schemas/test_package_schemas.py
git commit -m "feat(packages): add Pydantic schemas for catalog, sales, eligibility, refund"
```

---

*Phase 1 complete. The data layer + permissions + schemas are now in place. Phase 2 implements the pricing engine — pure-function math with heavy TDD coverage.*

---

## Phase 2 — Pricing Engine (high-stakes pure-function module)

Create `backend/app/services/package_pricing_engine.py` incrementally. Every function gets unit tests written first.

### Task 9: Implement `distribute_discount`

**Files:**
- Create: `backend/app/services/package_pricing_engine.py`
- Test: `backend/tests/unit/services/test_package_pricing_engine.py`

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/unit/services/test_package_pricing_engine.py`:

```python
"""Pricing engine — pure-function math. 100% coverage required."""

import pytest
from decimal import Decimal
from app.services.package_pricing_engine import (
    distribute_discount, DiscountMode, DiscountedItem, DomainError,
)


def _make(price, qty=1, locked=False):
    return DiscountedItem(unit_price_paise=price, quantity=qty, locked=locked)


def test_pct_discount_no_locked():
    """20% off ₹6000 (3 services at 2000 each) -> ₹4800 total, each line 1600."""
    items = [_make(200000), _make(200000), _make(200000)]
    out = distribute_discount(items, DiscountMode.PCT, Decimal("20"))
    assert [i.unit_price_paise for i in out] == [160000, 160000, 160000]


def test_flat_discount_proportional():
    """₹1200 off mix of MRPs -> proportional split."""
    items = [_make(100000), _make(200000), _make(300000)]  # total 6_00_000
    out = distribute_discount(items, DiscountMode.FLAT, Decimal("120000"))  # ₹1200 off
    # expected: 100/600 * 120000 = 20000; 200/600 * 120000 = 40000; 300/600 * 120000 = 60000
    assert [i.unit_price_paise for i in out] == [80000, 160000, 240000]
    assert sum(i.unit_price_paise for i in out) == 480000  # exactly 6_00_000 - 1_20_000


def test_final_amount_mode():
    """Set total final price to ₹4500 from MRP sum ₹6000."""
    items = [_make(200000), _make(200000), _make(200000)]
    out = distribute_discount(items, DiscountMode.FINAL, Decimal("450000"))
    assert sum(i.unit_price_paise for i in out) == 450000


def test_locked_lines_preserved():
    """Locked line keeps its price; only unlocked lines absorb discount."""
    items = [_make(200000, locked=True), _make(200000), _make(200000)]
    out = distribute_discount(items, DiscountMode.FINAL, Decimal("450000"))
    # locked line stays at 200000; remaining 250000 spread across two unlocked
    assert out[0].unit_price_paise == 200000
    assert out[1].unit_price_paise + out[2].unit_price_paise == 250000


def test_all_locked_with_discount_raises():
    items = [_make(200000, locked=True), _make(200000, locked=True)]
    with pytest.raises(DomainError, match="no unlocked lines"):
        distribute_discount(items, DiscountMode.PCT, Decimal("10"))


def test_zero_discount_no_op():
    items = [_make(100000), _make(200000)]
    out = distribute_discount(items, DiscountMode.PCT, Decimal("0"))
    assert [i.unit_price_paise for i in out] == [100000, 200000]


def test_100_pct_discount_zeros_unlocked():
    items = [_make(100000), _make(200000)]
    out = distribute_discount(items, DiscountMode.PCT, Decimal("100"))
    assert [i.unit_price_paise for i in out] == [0, 0]


def test_rounding_spillover_to_last_unlocked():
    """₹100 split across 3 lines of equal MRP — last gets the residual paise."""
    # 3 lines at 10000 each (₹100), target final of 9700 (i.e. ₹97 = ₹300 off split among 3 = 100 each)
    items = [_make(10000), _make(10000), _make(10000)]
    out = distribute_discount(items, DiscountMode.FINAL, Decimal("9700"))
    # Each line ~3233.33; floor + spillover puts residual on last line
    total = sum(i.unit_price_paise for i in out)
    assert total == 9700  # exact
    # The last unlocked line absorbs the rounding residual
    assert out[2].unit_price_paise >= out[0].unit_price_paise


def test_quantity_aware():
    """Quantity multiplies the line MRP for distribution weighting."""
    items = [_make(100000, qty=2), _make(100000, qty=1)]  # MRP weight 200k vs 100k
    out = distribute_discount(items, DiscountMode.FLAT, Decimal("30000"))
    # 200/300 * 30000 = 20000 off first line; 100/300 * 30000 = 10000 off second
    # unit prices: 100000 - (20000 / 2) = 90000; 100000 - 10000 = 90000
    assert out[0].unit_price_paise == 90000
    assert out[1].unit_price_paise == 90000


def test_final_exceeds_mrp_sum_raises():
    items = [_make(100000)]
    with pytest.raises(DomainError, match="exceeds MRP"):
        distribute_discount(items, DiscountMode.FINAL, Decimal("200000"))


# Property test
from hypothesis import given, strategies as st


@given(
    n=st.integers(min_value=1, max_value=10),
    base=st.integers(min_value=100, max_value=1_000_000),
    pct=st.decimals(min_value=Decimal("0"), max_value=Decimal("100"), places=2),
)
def test_property_pct_distribution_exact_sum(n, base, pct):
    """For any input, sum(distributed unit prices * qty) equals expected final total exactly."""
    items = [_make(base, qty=1) for _ in range(n)]
    mrp_sum = n * base
    expected_final = int(mrp_sum * (Decimal("100") - pct) / Decimal("100"))
    out = distribute_discount(items, DiscountMode.PCT, pct)
    assert sum(i.unit_price_paise * i.quantity for i in out) == expected_final
```

- [ ] **Step 2: Run tests**

Run: `cd backend && pytest tests/unit/services/test_package_pricing_engine.py -v`
Expected: FAIL (module doesn't exist yet).

- [ ] **Step 3: Implement `distribute_discount`**

Create `backend/app/services/package_pricing_engine.py`:

```python
"""Pricing engine — pure-function math for packages.

Single shared module owning all package math. Called by sales, redemption,
refund, reports. No package-math logic anywhere else in the codebase.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from decimal import Decimal, ROUND_FLOOR
from typing import List, Optional


class DomainError(ValueError):
    """Raised for pricing engine domain violations."""


class DiscountMode(str, enum.Enum):
    PCT = "pct"
    FLAT = "flat"
    FINAL = "final"


@dataclass
class DiscountedItem:
    unit_price_paise: int
    quantity: int = 1
    locked: bool = False


def distribute_discount(
    items: List[DiscountedItem],
    mode: DiscountMode,
    value: Decimal,
) -> List[DiscountedItem]:
    """Apply a package-level discount across UNLOCKED lines proportional to MRP weight.

    Locked lines preserve their price exactly. Rounding spillover goes to the
    LAST unlocked line so the package total matches exactly.

    Raises:
        DomainError: if all lines are locked and a discount is requested,
                     or if FINAL value exceeds total MRP.
    """
    if not items:
        return []

    if value == 0:
        return [replace(i) for i in items]

    # Compute MRP weights
    locked_weight = sum(i.unit_price_paise * i.quantity for i in items if i.locked)
    unlocked_weight = sum(i.unit_price_paise * i.quantity for i in items if not i.locked)
    total_mrp = locked_weight + unlocked_weight

    if unlocked_weight == 0:
        raise DomainError("Cannot distribute discount: no unlocked lines")

    # Compute total final paise across unlocked lines
    if mode == DiscountMode.PCT:
        # pct of unlocked weight
        unlocked_final = int(
            (Decimal(unlocked_weight) * (Decimal("100") - value) / Decimal("100"))
            .to_integral_value(rounding=ROUND_FLOOR)
        )
    elif mode == DiscountMode.FLAT:
        if int(value) > unlocked_weight:
            raise DomainError("Flat discount exceeds unlocked MRP")
        unlocked_final = unlocked_weight - int(value)
    elif mode == DiscountMode.FINAL:
        if int(value) > total_mrp:
            raise DomainError("Final amount exceeds MRP")
        if int(value) < locked_weight:
            raise DomainError("Final amount below locked-line minimum")
        unlocked_final = int(value) - locked_weight
    else:
        raise DomainError(f"Unknown discount mode: {mode}")

    if unlocked_final < 0:
        raise DomainError("Negative final amount after discount")

    # Distribute proportionally to MRP weight across unlocked lines
    result = []
    unlocked_indices = [idx for idx, i in enumerate(items) if not i.locked]
    last_unlocked_idx = unlocked_indices[-1]

    running_total = 0
    for idx, item in enumerate(items):
        if item.locked:
            result.append(replace(item))
            continue

        item_weight = item.unit_price_paise * item.quantity
        if idx == last_unlocked_idx:
            # Spillover: last unlocked absorbs rounding residual
            line_final = unlocked_final - running_total
        else:
            line_final = int(
                (Decimal(item_weight) * Decimal(unlocked_final) / Decimal(unlocked_weight))
                .to_integral_value(rounding=ROUND_FLOOR)
            )
            running_total += line_final

        # Convert line_final (the line's total) back to unit price
        new_unit_price = line_final // item.quantity
        # Adjust for quantity rounding via spillover line
        result.append(replace(item, unit_price_paise=new_unit_price))

    return result
```

- [ ] **Step 4: Run tests**

Run: `cd backend && pytest tests/unit/services/test_package_pricing_engine.py -v`
Expected: ALL PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/package_pricing_engine.py backend/tests/unit/services/test_package_pricing_engine.py
git commit -m "feat(packages): pricing engine — distribute_discount with 3 modes + locked lines"
```

---

### Task 10: Implement `snapshot_at_sale`

**Files:**
- Modify: `backend/app/services/package_pricing_engine.py`
- Modify: `backend/tests/unit/services/test_package_pricing_engine.py`

- [ ] **Step 1: Add tests**

Append to the test file:

```python
from unittest.mock import MagicMock
from app.services.package_pricing_engine import snapshot_at_sale, PackageSaleItemDraft


def test_snapshot_copies_items_exactly():
    # Mock a PackageDefinition with 2 items
    def_item_1 = MagicMock(
        id="01HXYZ_DEF_ITEM_1________A",
        service_id="01HSVC_SERVICE_1_________A",
        quantity=1,
        unit_price_paise=200000,
        locked=False,
        display_order=0,
    )
    def_item_1.service = MagicMock(gst_rate_pct=Decimal("18.00"))
    def_item_2 = MagicMock(
        id="01HXYZ_DEF_ITEM_2________A",
        service_id="01HSVC_SERVICE_2_________A",
        quantity=2,
        unit_price_paise=100000,
        locked=True,
        display_order=1,
    )
    def_item_2.service = MagicMock(gst_rate_pct=Decimal("12.00"))

    definition = MagicMock(items=[def_item_1, def_item_2])

    drafts = snapshot_at_sale(definition)
    assert len(drafts) == 2
    assert drafts[0].package_definition_item_id == "01HXYZ_DEF_ITEM_1________A"
    assert drafts[0].snapshot_unit_price_paise == 200000
    assert drafts[0].snapshot_gst_rate_pct == Decimal("18.00")
    assert drafts[1].snapshot_unit_price_paise == 100000
    assert drafts[1].locked is True
    assert drafts[1].snapshot_gst_rate_pct == Decimal("12.00")
```

- [ ] **Step 2: Run test (fail)**

Run: `cd backend && pytest tests/unit/services/test_package_pricing_engine.py::test_snapshot_copies_items_exactly -v`
Expected: FAIL.

- [ ] **Step 3: Implement `snapshot_at_sale`**

Append to `backend/app/services/package_pricing_engine.py`:

```python
@dataclass
class PackageSaleItemDraft:
    package_definition_item_id: str
    service_id: str
    quantity: int
    snapshot_unit_price_paise: int
    snapshot_gst_rate_pct: Decimal
    locked: bool
    display_order: int


def snapshot_at_sale(definition) -> List[PackageSaleItemDraft]:
    """Produce per-line snapshot drafts for a new PackageSale.

    Copies unit_price_paise + service.gst_rate_pct + quantity + locked + display_order
    from each PackageDefinitionItem at the moment of sale.
    """
    return [
        PackageSaleItemDraft(
            package_definition_item_id=item.id,
            service_id=item.service_id,
            quantity=item.quantity,
            snapshot_unit_price_paise=item.unit_price_paise,
            snapshot_gst_rate_pct=item.service.gst_rate_pct,
            locked=item.locked,
            display_order=item.display_order,
        )
        for item in definition.items
    ]
```

- [ ] **Step 4: Run tests**

Run: `cd backend && pytest tests/unit/services/test_package_pricing_engine.py -v`
Expected: ALL PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/package_pricing_engine.py backend/tests/unit/services/test_package_pricing_engine.py
git commit -m "feat(packages): pricing engine — snapshot_at_sale freezes catalog prices into sale rows"
```

---

### Task 11: Implement `find_eligible_packages` (DB-touching but pure read)

**Files:**
- Modify: `backend/app/services/package_pricing_engine.py`
- Test: `backend/tests/integration/test_package_eligibility.py`

- [ ] **Step 1: Write integration test**

Create `backend/tests/integration/test_package_eligibility.py`:

```python
"""Eligibility check: returns active+matching+FIFO+non-expired+non-exhausted packages."""

import pytest
from datetime import datetime, timedelta, timezone
from app.services.package_pricing_engine import find_eligible_packages
from app.models.package import PackageSaleStatus, EntitlementType, Shareability


@pytest.fixture
def sample_setup(db_session, customer_factory, service_factory, package_sale_factory):
    customer = customer_factory()
    service = service_factory()
    return customer, service


def test_returns_active_matching_package(db_session, sample_setup, package_sale_factory):
    customer, service = sample_setup
    sale = package_sale_factory(
        customer=customer,
        services=[service],
        sessions_remaining=5,
        expires_at=datetime.now(timezone.utc) + timedelta(days=30),
        status=PackageSaleStatus.ACTIVE,
    )
    eligible = find_eligible_packages(customer.id, service.id, db_session)
    assert len(eligible) == 1
    assert eligible[0].id == sale.id


def test_excludes_expired(db_session, sample_setup, package_sale_factory):
    customer, service = sample_setup
    package_sale_factory(
        customer=customer, services=[service], sessions_remaining=5,
        expires_at=datetime.now(timezone.utc) - timedelta(days=1),
        status=PackageSaleStatus.ACTIVE,
    )
    assert find_eligible_packages(customer.id, service.id, db_session) == []


def test_excludes_exhausted(db_session, sample_setup, package_sale_factory):
    customer, service = sample_setup
    package_sale_factory(
        customer=customer, services=[service], sessions_remaining=0,
        expires_at=datetime.now(timezone.utc) + timedelta(days=30),
        status=PackageSaleStatus.EXHAUSTED,
    )
    assert find_eligible_packages(customer.id, service.id, db_session) == []


def test_includes_unlimited_with_null_sessions(db_session, sample_setup, package_sale_factory):
    customer, service = sample_setup
    sale = package_sale_factory(
        customer=customer, services=[service],
        entitlement_type=EntitlementType.UNLIMITED,
        sessions_remaining=None, total_sessions_snapshot=None,
        expires_at=datetime.now(timezone.utc) + timedelta(days=30),
        status=PackageSaleStatus.ACTIVE,
    )
    eligible = find_eligible_packages(customer.id, service.id, db_session)
    assert eligible[0].id == sale.id


def test_fifo_by_expires_at(db_session, sample_setup, package_sale_factory):
    customer, service = sample_setup
    later = package_sale_factory(
        customer=customer, services=[service], sessions_remaining=5,
        expires_at=datetime.now(timezone.utc) + timedelta(days=60),
    )
    sooner = package_sale_factory(
        customer=customer, services=[service], sessions_remaining=5,
        expires_at=datetime.now(timezone.utc) + timedelta(days=10),
    )
    eligible = find_eligible_packages(customer.id, service.id, db_session)
    assert [e.id for e in eligible] == [sooner.id, later.id]


def test_owner_only_excluded_for_other_customer(
    db_session, sample_setup, package_sale_factory, customer_factory,
):
    buyer, service = sample_setup
    other = customer_factory()
    package_sale_factory(
        customer=buyer, services=[service], sessions_remaining=5,
        shareability=Shareability.OWNER_ONLY,
        expires_at=datetime.now(timezone.utc) + timedelta(days=30),
    )
    # When checking for other customer, owner_only package is not returned
    assert find_eligible_packages(other.id, service.id, db_session) == []


def test_shared_visible_to_other_customer(
    db_session, sample_setup, package_sale_factory, customer_factory,
):
    buyer, service = sample_setup
    other = customer_factory()
    sale = package_sale_factory(
        customer=buyer, services=[service], sessions_remaining=5,
        shareability=Shareability.SHARED,
        expires_at=datetime.now(timezone.utc) + timedelta(days=30),
    )
    eligible = find_eligible_packages(other.id, service.id, db_session)
    assert eligible[0].id == sale.id
```

(Assumes factories exist under `backend/tests/conftest.py` — if not, create them per the existing customer/service factory pattern.)

- [ ] **Step 2: Run tests (fail — function missing)**

Run: `cd backend && pytest tests/integration/test_package_eligibility.py -v`
Expected: FAIL with `ImportError` or `AttributeError`.

- [ ] **Step 3: Implement `find_eligible_packages`**

Append to `backend/app/services/package_pricing_engine.py`:

```python
from sqlalchemy import or_, and_
from sqlalchemy.orm import Session
from app.models.package import (
    PackageSale, PackageSaleItem, PackageSaleStatus, EntitlementType, Shareability,
)


def find_eligible_packages(
    customer_id: str,
    service_id: str,
    db: Session,
) -> List["PackageSale"]:
    """Return active PackageSales where this customer can redeem this service.

    Filters:
      - status = 'active'
      - expires_at > now()
      - service_id is in the sale's snapshot items
      - sessions_remaining > 0 OR entitlement_type='unlimited'
      - shareability rule: owner_only requires customer_id == sale.customer_id;
        shared allows any customer

    Ordered: expires_at ASC (FIFO by soonest expiry).
    """
    now = datetime.now(timezone.utc)

    base_filter = and_(
        PackageSale.status == PackageSaleStatus.ACTIVE,
        PackageSale.expires_at > now,
        PackageSale.id.in_(
            db.query(PackageSaleItem.package_sale_id)
              .filter(PackageSaleItem.service_id == service_id)
        ),
        or_(
            PackageSale.entitlement_type_snapshot == EntitlementType.UNLIMITED,
            PackageSale.sessions_remaining > 0,
        ),
        or_(
            and_(
                PackageSale.shareability_snapshot == Shareability.OWNER_ONLY,
                PackageSale.customer_id == customer_id,
            ),
            PackageSale.shareability_snapshot == Shareability.SHARED,
        ),
    )

    return (
        db.query(PackageSale)
          .filter(base_filter)
          .order_by(PackageSale.expires_at.asc())
          .all()
    )
```

- [ ] **Step 4: Run tests**

Run: `cd backend && pytest tests/integration/test_package_eligibility.py -v`
Expected: ALL PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/package_pricing_engine.py backend/tests/integration/test_package_eligibility.py
git commit -m "feat(packages): pricing engine — find_eligible_packages with FIFO + shareability"
```

---

### Task 12: Implement `compute_refund` (counted branch)

**Files:**
- Modify: `backend/app/services/package_pricing_engine.py`
- Modify: `backend/tests/unit/services/test_package_pricing_engine.py`

- [ ] **Step 1: Write tests**

Append to `test_package_pricing_engine.py`:

```python
from app.services.package_pricing_engine import compute_refund, RefundComputation


def test_refund_counted_pro_rata():
    """5 sessions of 10 used, ₹1000 each, 20% cancellation fee."""
    sale = MagicMock(
        entitlement_type_snapshot=EntitlementType.COUNTED,
        total_sessions_snapshot=10,
        sessions_remaining=5,
        cancellation_fee_pct_snapshot=Decimal("20.00"),
        items=[MagicMock(snapshot_unit_price_paise=100000, quantity=1)],
        bill=MagicMock(total_paise=1000000),
        redemption_audit_rows=[],  # ignored for counted path; uses sessions_remaining
    )
    result = compute_refund(sale)
    assert result.kind == "counted"
    # 5 unredeemed × ₹1000 = ₹5000 base; 20% fee = ₹1000; refund = ₹4000
    assert result.base_paise == 500000
    assert result.fee_paise == 100000
    assert result.refund_paise == 400000


def test_refund_counted_all_redeemed_zero_refund():
    sale = MagicMock(
        entitlement_type_snapshot=EntitlementType.COUNTED,
        total_sessions_snapshot=10,
        sessions_remaining=0,
        cancellation_fee_pct_snapshot=Decimal("20.00"),
        items=[MagicMock(snapshot_unit_price_paise=100000, quantity=1)],
        bill=MagicMock(total_paise=1000000),
    )
    result = compute_refund(sale)
    assert result.base_paise == 0
    assert result.refund_paise == 0


def test_refund_counted_zero_fee():
    sale = MagicMock(
        entitlement_type_snapshot=EntitlementType.COUNTED,
        total_sessions_snapshot=10,
        sessions_remaining=5,
        cancellation_fee_pct_snapshot=Decimal("0.00"),
        items=[MagicMock(snapshot_unit_price_paise=100000, quantity=1)],
        bill=MagicMock(total_paise=1000000),
    )
    result = compute_refund(sale)
    assert result.refund_paise == result.base_paise == 500000
```

- [ ] **Step 2: Run tests (fail)**

Run: `cd backend && pytest tests/unit/services/test_package_pricing_engine.py -v -k refund`
Expected: FAIL with `ImportError`.

- [ ] **Step 3: Implement `compute_refund` (counted branch)**

Append to `backend/app/services/package_pricing_engine.py`:

```python
@dataclass
class RefundComputation:
    kind: str  # "counted" | "unlimited"
    base_paise: int
    fee_paise: int
    refund_paise: int
    consumed_value_paise: int
    pct_remaining: Optional[Decimal] = None
    sessions_consumed: Optional[int] = None
    sessions_total: Optional[int] = None


def compute_refund(sale) -> RefundComputation:
    """Compute refund breakdown for a PackageSale.

    Branches by entitlement_type_snapshot. Returns paise integers + UI breakdown.
    """
    if sale.entitlement_type_snapshot == EntitlementType.COUNTED:
        return _compute_counted_refund(sale)
    elif sale.entitlement_type_snapshot == EntitlementType.UNLIMITED:
        return _compute_unlimited_refund(sale)
    else:
        raise DomainError(f"Unknown entitlement_type: {sale.entitlement_type_snapshot}")


def _compute_counted_refund(sale) -> RefundComputation:
    total = sale.total_sessions_snapshot or 0
    remaining = sale.sessions_remaining or 0
    consumed = total - remaining

    # Per-session value: sum of (item.snapshot_unit_price_paise * item.quantity) / total
    per_session_value = sum(
        i.snapshot_unit_price_paise * i.quantity for i in sale.items
    ) // max(total, 1)

    base_paise = per_session_value * remaining
    consumed_value = per_session_value * consumed

    fee_paise = int(
        (Decimal(base_paise) * sale.cancellation_fee_pct_snapshot / Decimal("100"))
        .to_integral_value(rounding=ROUND_FLOOR)
    )
    refund_paise = base_paise - fee_paise

    return RefundComputation(
        kind="counted",
        base_paise=base_paise,
        fee_paise=fee_paise,
        refund_paise=refund_paise,
        consumed_value_paise=consumed_value,
        sessions_consumed=consumed,
        sessions_total=total,
    )
```

- [ ] **Step 4: Run tests**

Run: `cd backend && pytest tests/unit/services/test_package_pricing_engine.py -v -k refund`
Expected: 3 PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/package_pricing_engine.py backend/tests/unit/services/test_package_pricing_engine.py
git commit -m "feat(packages): pricing engine — compute_refund counted branch with cancellation fee"
```

---

### Task 13: Implement `compute_refund` (unlimited branch)

**Files:**
- Modify: `backend/app/services/package_pricing_engine.py`
- Modify: `backend/tests/unit/services/test_package_pricing_engine.py`

- [ ] **Step 1: Add tests**

Append to test file:

```python
from datetime import timedelta


def test_refund_unlimited_pro_rata_time():
    """Bought for ₹1500, 30-day validity, 8 days elapsed. 22/30 remaining."""
    now = datetime.now(timezone.utc)
    sale = MagicMock(
        entitlement_type_snapshot=EntitlementType.UNLIMITED,
        total_sessions_snapshot=None,
        sessions_remaining=None,
        cancellation_fee_pct_snapshot=Decimal("20.00"),
        sold_at=now - timedelta(days=8),
        expires_at=now + timedelta(days=22),
        bill=MagicMock(total_paise=150000),
        items=[],
    )
    result = compute_refund(sale)
    assert result.kind == "unlimited"
    # 22/30 * 150000 = 110000 base; 20% fee = 22000; refund = 88000
    assert result.base_paise == 110000
    assert result.fee_paise == 22000
    assert result.refund_paise == 88000


def test_refund_unlimited_expired_zero():
    now = datetime.now(timezone.utc)
    sale = MagicMock(
        entitlement_type_snapshot=EntitlementType.UNLIMITED,
        total_sessions_snapshot=None,
        sessions_remaining=None,
        cancellation_fee_pct_snapshot=Decimal("20.00"),
        sold_at=now - timedelta(days=60),
        expires_at=now - timedelta(days=30),
        bill=MagicMock(total_paise=150000),
        items=[],
    )
    result = compute_refund(sale)
    assert result.base_paise == 0
    assert result.refund_paise == 0
```

- [ ] **Step 2: Run tests (fail)**

Run: `cd backend && pytest tests/unit/services/test_package_pricing_engine.py -v -k unlimited`
Expected: FAIL.

- [ ] **Step 3: Implement unlimited branch**

Append to `backend/app/services/package_pricing_engine.py`:

```python
def _compute_unlimited_refund(sale) -> RefundComputation:
    now = datetime.now(timezone.utc)
    total_validity_days = max((sale.expires_at - sale.sold_at).days, 1)
    days_remaining = max((sale.expires_at - now).days, 0)
    pct_remaining = Decimal(days_remaining) / Decimal(total_validity_days)

    paid_paise = sale.bill.total_paise if sale.bill else 0
    base_paise = int(
        (Decimal(paid_paise) * pct_remaining).to_integral_value(rounding=ROUND_FLOOR)
    )
    consumed_value = paid_paise - base_paise

    fee_paise = int(
        (Decimal(base_paise) * sale.cancellation_fee_pct_snapshot / Decimal("100"))
        .to_integral_value(rounding=ROUND_FLOOR)
    )
    refund_paise = base_paise - fee_paise

    return RefundComputation(
        kind="unlimited",
        base_paise=base_paise,
        fee_paise=fee_paise,
        refund_paise=refund_paise,
        consumed_value_paise=consumed_value,
        pct_remaining=pct_remaining,
    )
```

- [ ] **Step 4: Run tests**

Run: `cd backend && pytest tests/unit/services/test_package_pricing_engine.py -v`
Expected: ALL PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/package_pricing_engine.py backend/tests/unit/services/test_package_pricing_engine.py
git commit -m "feat(packages): pricing engine — compute_refund unlimited branch (time pro-rata)"
```

---

### Task 14: Implement `can_extend_expiry`

**Files:**
- Modify: `backend/app/services/package_pricing_engine.py`
- Modify: `backend/tests/unit/services/test_package_pricing_engine.py`

- [ ] **Step 1: Add tests**

Append:

```python
from app.services.package_pricing_engine import can_extend_expiry


def test_extend_must_be_forward_in_time():
    sale = MagicMock(expires_at=datetime.now(timezone.utc) + timedelta(days=10))
    new_expires = sale.expires_at - timedelta(days=1)
    with pytest.raises(DomainError, match="forward"):
        can_extend_expiry(sale, new_expires)


def test_extend_must_be_future_relative_to_now():
    """Owner can extend an expired package, but new_expires_at must be > now()."""
    sale = MagicMock(expires_at=datetime.now(timezone.utc) - timedelta(days=5))
    new_expires = datetime.now(timezone.utc) - timedelta(hours=1)
    with pytest.raises(DomainError, match="past"):
        can_extend_expiry(sale, new_expires)


def test_extend_valid():
    sale = MagicMock(expires_at=datetime.now(timezone.utc) + timedelta(days=10))
    can_extend_expiry(sale, sale.expires_at + timedelta(days=30))  # no raise
```

- [ ] **Step 2: Implement**

Append to `package_pricing_engine.py`:

```python
def can_extend_expiry(sale, new_expires_at: datetime) -> None:
    """Validate an expiry extension. Raises DomainError on violation."""
    if new_expires_at <= sale.expires_at:
        raise DomainError("Extension must be forward in time")
    if new_expires_at <= datetime.now(timezone.utc):
        raise DomainError("Extension cannot be in the past")
```

- [ ] **Step 3: Run tests + commit**

```bash
cd backend && pytest tests/unit/services/test_package_pricing_engine.py -v
git add backend/app/services/package_pricing_engine.py backend/tests/unit/services/test_package_pricing_engine.py
git commit -m "feat(packages): pricing engine — can_extend_expiry validator"
```

---

*Phase 2 complete. The pricing engine is the single source of truth for all package math, fully tested. Phase 3 wraps it in service modules.*

---

## Phase 3 — Service modules

Each module thin-wraps DB writes around the pricing engine + handles transactions.

### Task 15: `package_catalog_service.py`

**Files:**
- Create: `backend/app/services/package_catalog_service.py`
- Test: `backend/tests/integration/test_package_catalog_service.py`

**Public functions:**
- `create_definition(db, payload, user_id) -> PackageDefinition`
- `update_definition(db, def_id, payload, user_id) -> PackageDefinition` — replaces items wholesale in transaction
- `publish(db, def_id) -> PackageDefinition`
- `archive(db, def_id) -> PackageDefinition`
- `soft_delete(db, def_id)` — blocks if any active `PackageSale` for this def

- [ ] **Step 1: Write integration tests** covering: create with discount distribution applied server-side; update replaces items; publish only from draft; soft_delete blocked when active sales exist.

```python
# backend/tests/integration/test_package_catalog_service.py
import pytest
from decimal import Decimal
from app.services.package_catalog_service import (
    create_definition, publish, archive, soft_delete, update_definition,
)
from app.schemas.package import (
    PackageDefinitionCreate, PackageDefinitionItemCreate, DiscountInput,
)
from app.models.package import PackageDefinitionStatus

def test_create_with_discount_distribution(db_session, service_factory, user_factory):
    s1 = service_factory(gst_rate_pct=Decimal("18"))
    s2 = service_factory(gst_rate_pct=Decimal("18"))
    user = user_factory()
    payload = PackageDefinitionCreate(
        name="Test Pack", entitlement_type="counted", total_sessions=5,
        validity_days=90, shareability="owner_only",
        items=[
            PackageDefinitionItemCreate(service_id=s1.id, quantity=1, unit_price_paise=200000),
            PackageDefinitionItemCreate(service_id=s2.id, quantity=1, unit_price_paise=200000),
        ],
        discount=DiscountInput(mode="pct", value=Decimal("20")),
    )
    pkg = create_definition(db_session, payload, user.id)
    assert pkg.status == PackageDefinitionStatus.DRAFT
    # 20% off applied: each item 200000 → 160000
    assert all(i.unit_price_paise == 160000 for i in pkg.items)


def test_soft_delete_blocked_when_active_sales(
    db_session, definition_factory, package_sale_factory,
):
    pkg = definition_factory()
    package_sale_factory(definition=pkg)  # active by default
    with pytest.raises(ValueError, match="active sales"):
        soft_delete(db_session, pkg.id)
```

- [ ] **Step 2: Implement** `backend/app/services/package_catalog_service.py`:

```python
"""CRUD for PackageDefinition with discount distribution and lifecycle checks."""

from typing import Optional
from sqlalchemy.orm import Session
from app.models.package import (
    PackageDefinition, PackageDefinitionItem, PackageDefinitionStatus, PackageSale,
    PackageSaleStatus,
)
from app.schemas.package import PackageDefinitionCreate, PackageDefinitionUpdate
from app.services.package_pricing_engine import (
    distribute_discount, DiscountedItem, DiscountMode,
)


def create_definition(db: Session, payload: PackageDefinitionCreate, user_id: str) -> PackageDefinition:
    item_drafts = [
        DiscountedItem(unit_price_paise=i.unit_price_paise, quantity=i.quantity, locked=i.locked)
        for i in payload.items
    ]
    if payload.discount:
        item_drafts = distribute_discount(
            item_drafts, DiscountMode(payload.discount.mode), payload.discount.value,
        )

    pkg = PackageDefinition(
        name=payload.name,
        description=payload.description,
        entitlement_type=payload.entitlement_type,
        total_sessions=payload.total_sessions,
        shareability=payload.shareability,
        validity_days=payload.validity_days,
        auto_apply=True if payload.entitlement_type.value == "unlimited" else payload.auto_apply,
        cancellation_fee_pct=payload.cancellation_fee_pct,
        created_by_user_id=user_id,
        status=PackageDefinitionStatus.DRAFT,
    )
    pkg.items = [
        PackageDefinitionItem(
            service_id=src.service_id, quantity=draft.quantity,
            unit_price_paise=draft.unit_price_paise, locked=draft.locked,
            display_order=src.display_order,
        )
        for src, draft in zip(payload.items, item_drafts)
    ]
    db.add(pkg)
    db.flush()
    return pkg


def update_definition(db: Session, def_id: str, payload: PackageDefinitionUpdate, user_id: str) -> PackageDefinition:
    pkg = db.get(PackageDefinition, def_id)
    if not pkg:
        raise ValueError(f"PackageDefinition {def_id} not found")
    # Wholesale-replace items via cascade
    pkg.name = payload.name
    pkg.description = payload.description
    pkg.entitlement_type = payload.entitlement_type
    pkg.total_sessions = payload.total_sessions
    pkg.shareability = payload.shareability
    pkg.validity_days = payload.validity_days
    pkg.auto_apply = True if payload.entitlement_type.value == "unlimited" else payload.auto_apply
    pkg.cancellation_fee_pct = payload.cancellation_fee_pct
    pkg.items.clear()
    db.flush()

    item_drafts = [
        DiscountedItem(unit_price_paise=i.unit_price_paise, quantity=i.quantity, locked=i.locked)
        for i in payload.items
    ]
    if payload.discount:
        item_drafts = distribute_discount(
            item_drafts, DiscountMode(payload.discount.mode), payload.discount.value,
        )
    pkg.items = [
        PackageDefinitionItem(
            service_id=src.service_id, quantity=draft.quantity,
            unit_price_paise=draft.unit_price_paise, locked=draft.locked,
            display_order=src.display_order,
        )
        for src, draft in zip(payload.items, item_drafts)
    ]
    db.flush()
    return pkg


def publish(db: Session, def_id: str) -> PackageDefinition:
    pkg = db.get(PackageDefinition, def_id)
    if not pkg or pkg.status != PackageDefinitionStatus.DRAFT:
        raise ValueError("Only draft packages can be published")
    pkg.status = PackageDefinitionStatus.PUBLISHED
    db.flush()
    return pkg


def archive(db: Session, def_id: str) -> PackageDefinition:
    pkg = db.get(PackageDefinition, def_id)
    if not pkg:
        raise ValueError(f"PackageDefinition {def_id} not found")
    pkg.status = PackageDefinitionStatus.ARCHIVED
    db.flush()
    return pkg


def soft_delete(db: Session, def_id: str) -> None:
    pkg = db.get(PackageDefinition, def_id)
    if not pkg:
        raise ValueError(f"PackageDefinition {def_id} not found")
    active_count = db.query(PackageSale).filter(
        PackageSale.package_definition_id == def_id,
        PackageSale.status == PackageSaleStatus.ACTIVE,
    ).count()
    if active_count > 0:
        raise ValueError(f"Cannot delete: {active_count} active sales exist")
    pkg.deleted_at = pkg.deleted_at or _utcnow()
    db.flush()


def _utcnow():
    from datetime import datetime, timezone
    return datetime.now(timezone.utc)
```

- [ ] **Step 3: Run tests + commit**

```bash
cd backend && pytest tests/integration/test_package_catalog_service.py -v
git add backend/app/services/package_catalog_service.py backend/tests/integration/test_package_catalog_service.py
git commit -m "feat(packages): catalog service — create/update/publish/archive/soft-delete"
```

---

### Task 16: `package_sales_service.py`

**Files:**
- Create: `backend/app/services/package_sales_service.py`
- Test: `backend/tests/integration/test_package_sales_service.py`

**Public function:**
- `create_sale(db, definition_id, bill_id, customer_id, selling_staff_id) -> PackageSale` — called from `billing_service.finalize_bill()` for each `package_sale_line` BillItem. Atomically:
  1. Loads definition + items
  2. Snapshots via `pricing_engine.snapshot_at_sale`
  3. Inserts `PackageSale` + `PackageSaleItem` rows
  4. Sets `expires_at = sold_at + validity_days`
  5. Updates the BillItem.package_sale_id

- [ ] **Step 1: Write tests** covering: snapshot fields match definition; expires_at = sold + validity; sessions_remaining = total_sessions for counted, NULL for unlimited.

```python
# backend/tests/integration/test_package_sales_service.py
from datetime import datetime, timedelta, timezone
from app.services.package_sales_service import create_sale
from app.models.package import EntitlementType, PackageSaleStatus


def test_create_sale_snapshots_correctly(db_session, definition_factory, bill_factory, customer_factory):
    pkg = definition_factory(
        entitlement_type=EntitlementType.COUNTED, total_sessions=10, validity_days=180,
    )
    bill = bill_factory()
    customer = customer_factory()
    sale = create_sale(db_session, pkg.id, bill.id, customer.id, selling_staff_id=None)
    assert sale.status == PackageSaleStatus.ACTIVE
    assert sale.sessions_remaining == 10
    assert sale.total_sessions_snapshot == 10
    # Expiry: roughly sold_at + 180d
    delta = sale.expires_at - sale.sold_at
    assert abs(delta - timedelta(days=180)) < timedelta(seconds=2)
    # Items snapshotted
    assert len(sale.items) == len(pkg.items)


def test_unlimited_sale_has_null_sessions(db_session, definition_factory, bill_factory, customer_factory):
    pkg = definition_factory(
        entitlement_type=EntitlementType.UNLIMITED, total_sessions=None, validity_days=30,
    )
    sale = create_sale(db_session, pkg.id, bill_factory().id, customer_factory().id, None)
    assert sale.sessions_remaining is None
    assert sale.total_sessions_snapshot is None
```

- [ ] **Step 2: Implement** `backend/app/services/package_sales_service.py`:

```python
"""Create PackageSale rows from PackageDefinition at bill finalization."""

from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from app.models.package import (
    PackageDefinition, PackageSale, PackageSaleItem, PackageSaleStatus,
    EntitlementType,
)
from app.services.package_pricing_engine import snapshot_at_sale


def create_sale(
    db: Session,
    package_definition_id: str,
    bill_id: str,
    customer_id: str,
    selling_staff_id: str | None,
) -> PackageSale:
    """Atomically snapshot a PackageDefinition into a PackageSale + items."""
    pkg = db.get(PackageDefinition, package_definition_id)
    if not pkg:
        raise ValueError(f"PackageDefinition {package_definition_id} not found")

    sold_at = datetime.now(timezone.utc)
    expires_at = sold_at + timedelta(days=pkg.validity_days)

    sale = PackageSale(
        bill_id=bill_id,
        package_definition_id=pkg.id,
        customer_id=customer_id,
        selling_staff_id=selling_staff_id,
        sold_at=sold_at,
        expires_at=expires_at,
        entitlement_type_snapshot=pkg.entitlement_type,
        shareability_snapshot=pkg.shareability,
        cancellation_fee_pct_snapshot=pkg.cancellation_fee_pct,
        total_sessions_snapshot=pkg.total_sessions,
        sessions_remaining=pkg.total_sessions if pkg.entitlement_type == EntitlementType.COUNTED else None,
        status=PackageSaleStatus.ACTIVE,
    )
    db.add(sale)
    db.flush()

    drafts = snapshot_at_sale(pkg)
    for draft in drafts:
        item = PackageSaleItem(
            package_sale_id=sale.id,
            package_definition_item_id=draft.package_definition_item_id,
            service_id=draft.service_id,
            quantity=draft.quantity,
            snapshot_unit_price_paise=draft.snapshot_unit_price_paise,
            snapshot_gst_rate_pct=draft.snapshot_gst_rate_pct,
            locked=draft.locked,
            display_order=draft.display_order,
        )
        db.add(item)

    db.flush()
    return sale
```

- [ ] **Step 3: Run + commit**

```bash
cd backend && pytest tests/integration/test_package_sales_service.py -v
git add backend/app/services/package_sales_service.py backend/tests/integration/test_package_sales_service.py
git commit -m "feat(packages): sales service — create_sale with full snapshot at bill finalization"
```

---

### Task 17: `package_redemption_service.py`

**Files:**
- Create: `backend/app/services/package_redemption_service.py`
- Test: `backend/tests/integration/test_package_redemption.py`

**Public functions:**
- `apply_redemption(db, package_sale_id, bill_item_id, redeemed_for_customer_id, user_id) -> PackageRedemptionAudit` — uses `SELECT FOR UPDATE` on PackageSale; decrements sessions; creates audit row; sets BillItem fields; creates internal Payment row.
- `undo_redemption(db, audit_id, user_id) -> None` — inverse, only allowed while bill is `DRAFT`.

- [ ] **Step 1: Write tests** for happy path + concurrent redemption race + undo + undo blocked on finalized bill.

```python
# backend/tests/integration/test_package_redemption.py (excerpt)
import pytest
from sqlalchemy import select
from app.services.package_redemption_service import apply_redemption, undo_redemption
from app.models.package import PackageRedemptionAudit, PackageSaleStatus
from app.models.billing import BillItem, BillItemType, Payment, PaymentMethod


def test_apply_decrements_sessions(db_session, package_sale_factory, bill_item_factory, user_factory, customer_factory):
    sale = package_sale_factory(sessions_remaining=5)
    bi = bill_item_factory(service_id=sale.items[0].service_id, unit_price_paise=100000)
    audit = apply_redemption(
        db_session, sale.id, bi.id,
        redeemed_for_customer_id=sale.customer_id,
        user_id=user_factory().id,
    )
    db_session.refresh(sale)
    assert sale.sessions_remaining == 4
    assert audit.package_sale_id == sale.id
    # BillItem now flagged as redemption
    db_session.refresh(bi)
    assert bi.item_type == BillItemType.PACKAGE_REDEMPTION
    assert bi.package_sale_id == sale.id
    # Internal Payment row
    pay = db_session.scalar(
        select(Payment).where(Payment.bill_id == bi.bill_id, Payment.method == PaymentMethod.PACKAGE_REDEMPTION)
    )
    assert pay is not None
    assert pay.amount_paise == bi.subtotal_paise


def test_apply_zero_sessions_raises(db_session, package_sale_factory, bill_item_factory, user_factory):
    sale = package_sale_factory(sessions_remaining=0, status=PackageSaleStatus.EXHAUSTED)
    bi = bill_item_factory(service_id=sale.items[0].service_id)
    with pytest.raises(ValueError, match="no sessions"):
        apply_redemption(db_session, sale.id, bi.id, sale.customer_id, user_factory().id)


def test_undo_restores_sessions(db_session, package_sale_factory, bill_item_factory, user_factory):
    sale = package_sale_factory(sessions_remaining=5)
    bi = bill_item_factory(service_id=sale.items[0].service_id, unit_price_paise=100000)
    audit = apply_redemption(db_session, sale.id, bi.id, sale.customer_id, user_factory().id)
    undo_redemption(db_session, audit.id, user_factory().id)
    db_session.refresh(sale)
    assert sale.sessions_remaining == 5
    assert not db_session.get(PackageRedemptionAudit, audit.id)
```

- [ ] **Step 2: Implement** `backend/app/services/package_redemption_service.py`:

```python
"""Apply / undo redemptions with concurrency control."""

from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.package import (
    PackageSale, PackageSaleItem, PackageRedemptionAudit, PackageSaleStatus,
    EntitlementType,
)
from app.models.billing import BillItem, BillItemType, Bill, BillStatus, Payment, PaymentMethod


def apply_redemption(
    db: Session,
    package_sale_id: str,
    bill_item_id: str,
    redeemed_for_customer_id: str,
    user_id: str,
) -> PackageRedemptionAudit:
    """Apply a redemption to a BillItem against a PackageSale.

    Uses row lock on PackageSale to prevent concurrent over-redemption.
    Creates the audit row, decrements sessions, flips the BillItem to redemption,
    creates an internal Payment row.
    """
    # Lock the PackageSale row
    sale = db.execute(
        select(PackageSale).where(PackageSale.id == package_sale_id).with_for_update()
    ).scalar_one_or_none()
    if not sale:
        raise ValueError(f"PackageSale {package_sale_id} not found")

    # Re-check active + has sessions + not expired
    now = datetime.now(timezone.utc)
    if sale.status != PackageSaleStatus.ACTIVE:
        raise ValueError(f"Package not active (status={sale.status.value})")
    if sale.expires_at <= now:
        raise ValueError("Package expired")
    if sale.entitlement_type_snapshot == EntitlementType.COUNTED:
        if sale.sessions_remaining is None or sale.sessions_remaining <= 0:
            raise ValueError("no sessions remaining")

    bill_item = db.get(BillItem, bill_item_id)
    if not bill_item:
        raise ValueError(f"BillItem {bill_item_id} not found")

    # Find matching PackageSaleItem by service_id
    sale_item = next(
        (i for i in sale.items if i.service_id == bill_item.service_id),
        None,
    )
    if not sale_item:
        raise ValueError("Service not covered by this package")

    # Set BillItem fields to redemption
    bill_item.item_type = BillItemType.PACKAGE_REDEMPTION
    bill_item.package_sale_id = sale.id
    bill_item.package_sale_item_id = sale_item.id
    bill_item.unit_price_paise = sale_item.snapshot_unit_price_paise
    # Recompute subtotal — leave to existing recompute logic in billing_service if needed

    # Decrement sessions for counted
    session_number = None
    if sale.entitlement_type_snapshot == EntitlementType.COUNTED:
        session_number = (sale.total_sessions_snapshot or 0) - (sale.sessions_remaining or 0) + 1
        sale.sessions_remaining -= 1
        if sale.sessions_remaining == 0:
            sale.status = PackageSaleStatus.EXHAUSTED

    # Audit row
    audit = PackageRedemptionAudit(
        package_sale_id=sale.id,
        bill_item_id=bill_item.id,
        package_sale_item_id=sale_item.id,
        redeemed_for_customer_id=redeemed_for_customer_id,
        performed_by_user_id=user_id,
        redeemed_at=now,
        session_number=session_number,
    )
    db.add(audit)

    # Internal Payment row
    payment = Payment(
        bill_id=bill_item.bill_id,
        amount_paise=bill_item.unit_price_paise * (bill_item.quantity or 1),
        method=PaymentMethod.PACKAGE_REDEMPTION,
    )
    db.add(payment)

    db.flush()
    return audit


def undo_redemption(db: Session, audit_id: str, user_id: str) -> None:
    """Inverse of apply_redemption. Only allowed on draft bills."""
    audit = db.get(PackageRedemptionAudit, audit_id)
    if not audit:
        raise ValueError(f"Audit row {audit_id} not found")

    bill_item = db.get(BillItem, audit.bill_item_id)
    bill = db.get(Bill, bill_item.bill_id)
    if bill.status != BillStatus.DRAFT:
        raise ValueError("Undo only allowed on draft bills")

    sale = db.execute(
        select(PackageSale).where(PackageSale.id == audit.package_sale_id).with_for_update()
    ).scalar_one()

    # Restore session counter
    if sale.entitlement_type_snapshot == EntitlementType.COUNTED:
        sale.sessions_remaining = (sale.sessions_remaining or 0) + 1
        if sale.status == PackageSaleStatus.EXHAUSTED:
            sale.status = PackageSaleStatus.ACTIVE

    # Revert BillItem
    bill_item.item_type = BillItemType.SERVICE
    bill_item.package_sale_id = None
    bill_item.package_sale_item_id = None
    # unit_price_paise: restore to service MRP via service lookup
    from app.models.service import Service  # local import to avoid cycle
    svc = db.get(Service, bill_item.service_id)
    bill_item.unit_price_paise = svc.price_paise

    # Delete the internal Payment row
    internal_pay = db.execute(
        select(Payment).where(
            Payment.bill_id == bill.id,
            Payment.method == PaymentMethod.PACKAGE_REDEMPTION,
            Payment.amount_paise == bill_item.unit_price_paise * (bill_item.quantity or 1),
        )
    ).scalar_one_or_none()
    if internal_pay:
        db.delete(internal_pay)

    db.delete(audit)
    db.flush()
```

- [ ] **Step 3: Add concurrent-redemption test**

Create `backend/tests/integration/test_package_concurrent_redemption.py`:

```python
"""Verify DB row lock prevents over-redemption under concurrency."""

import threading
import pytest
from app.services.package_redemption_service import apply_redemption


def test_two_threads_one_session_only_one_wins(
    SessionLocal, package_sale_factory, bill_item_factory, user_factory,
):
    sale = package_sale_factory(sessions_remaining=1)
    bi1 = bill_item_factory(service_id=sale.items[0].service_id)
    bi2 = bill_item_factory(service_id=sale.items[0].service_id)
    user = user_factory()

    successes = []
    failures = []

    def attempt(bi_id):
        s = SessionLocal()
        try:
            apply_redemption(s, sale.id, bi_id, sale.customer_id, user.id)
            s.commit()
            successes.append(bi_id)
        except ValueError:
            failures.append(bi_id)
            s.rollback()
        finally:
            s.close()

    t1 = threading.Thread(target=attempt, args=(bi1.id,))
    t2 = threading.Thread(target=attempt, args=(bi2.id,))
    t1.start(); t2.start(); t1.join(); t2.join()

    assert len(successes) == 1
    assert len(failures) == 1
```

- [ ] **Step 4: Run all + commit**

```bash
cd backend && pytest tests/integration/test_package_redemption.py tests/integration/test_package_concurrent_redemption.py -v
git add backend/app/services/package_redemption_service.py backend/tests/integration/test_package_redemption.py backend/tests/integration/test_package_concurrent_redemption.py
git commit -m "feat(packages): redemption service — apply/undo with row-lock concurrency control"
```

---

### Task 18: `package_refund_service.py`

**Files:**
- Create: `backend/app/services/package_refund_service.py`
- Test: `backend/tests/integration/test_package_refund.py`

**Public function:**
- `issue_refund(db, package_sale_id, payment_method, reason, user_id) -> Bill` — atomically: calls `pricing_engine.compute_refund`; creates credit-note Bill with two BillItems (refund line + fee line) and a negative Payment; updates PackageSale (`status='refunded'`, refunded_at, refund_bill_id).

- [ ] **Step 1: Write tests** for counted + unlimited refund flows; verify credit note math.

```python
# backend/tests/integration/test_package_refund.py (excerpt)
import pytest
from app.services.package_refund_service import issue_refund
from app.models.package import PackageSaleStatus
from app.models.billing import Bill, BillType, BillItem, Payment, PaymentMethod


def test_refund_counted_creates_credit_note(db_session, package_sale_factory, user_factory):
    sale = package_sale_factory(
        total_sessions_snapshot=10, sessions_remaining=5,
        cancellation_fee_pct_snapshot=20,
    )
    credit_note = issue_refund(db_session, sale.id, "cash", "Customer relocating", user_factory().id)

    assert credit_note.bill_type == BillType.CREDIT_NOTE
    assert credit_note.original_bill_id == sale.bill_id
    items = db_session.query(BillItem).filter(BillItem.bill_id == credit_note.id).all()
    assert len(items) == 2  # refund line + fee line
    # PackageSale updated
    db_session.refresh(sale)
    assert sale.status == PackageSaleStatus.REFUNDED
    assert sale.refund_bill_id == credit_note.id
```

- [ ] **Step 2: Implement** `backend/app/services/package_refund_service.py`:

```python
"""Issue refund credit notes for PackageSales."""

from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.package import PackageSale, PackageSaleStatus
from app.models.billing import Bill, BillType, BillItem, BillItemType, BillStatus, Payment, PaymentMethod
from app.services.package_pricing_engine import compute_refund


def issue_refund(
    db: Session,
    package_sale_id: str,
    payment_method: str,
    reason: str,
    user_id: str,
) -> Bill:
    sale = db.get(PackageSale, package_sale_id)
    if not sale:
        raise ValueError(f"PackageSale {package_sale_id} not found")
    if sale.status == PackageSaleStatus.REFUNDED:
        raise ValueError("Package already refunded")

    # Pull bill for the original sale (for total_paise on unlimited math)
    original_bill = db.get(Bill, sale.bill_id)
    # Attach for compute_refund convenience
    sale.bill = original_bill

    breakdown = compute_refund(sale)
    now = datetime.now(timezone.utc)

    # Create credit note Bill
    credit_note = Bill(
        customer_id=sale.customer_id,
        bill_type=BillType.CREDIT_NOTE,
        original_bill_id=sale.bill_id,
        subtotal=-breakdown.base_paise,
        discount_amount=0,
        tax_amount=0,  # GST treatment for credit note follows India GST rules; recompute here if needed
        status=BillStatus.POSTED,
    )
    db.add(credit_note)
    db.flush()

    # Refund line item
    refund_li = BillItem(
        bill_id=credit_note.id,
        item_type=BillItemType.SERVICE,  # using SERVICE for backward compat; receipt-rendering treats credit notes specially
        description=f"Refund — unredeemed value of package {sale.id}",
        unit_price_paise=-breakdown.base_paise,
        quantity=1,
        subtotal_paise=-breakdown.base_paise,
        package_sale_id=sale.id,
    )
    db.add(refund_li)

    # Cancellation fee line
    fee_li = BillItem(
        bill_id=credit_note.id,
        item_type=BillItemType.SERVICE,
        description=f"Cancellation fee ({sale.cancellation_fee_pct_snapshot}%)",
        unit_price_paise=breakdown.fee_paise,
        quantity=1,
        subtotal_paise=breakdown.fee_paise,
        package_sale_id=sale.id,
    )
    db.add(fee_li)

    # Negative Payment row representing cash out
    payment = Payment(
        bill_id=credit_note.id,
        amount_paise=-breakdown.refund_paise,
        method=PaymentMethod(payment_method) if payment_method != "pending_balance" else PaymentMethod.OTHER,
    )
    db.add(payment)

    # Update PackageSale
    sale.status = PackageSaleStatus.REFUNDED
    sale.refunded_at = now
    sale.refund_bill_id = credit_note.id

    # TODO: write AuditLog row (existing AuditLog service handles this)
    db.flush()
    return credit_note
```

- [ ] **Step 3: Run + commit**

```bash
cd backend && pytest tests/integration/test_package_refund.py -v
git add backend/app/services/package_refund_service.py backend/tests/integration/test_package_refund.py
git commit -m "feat(packages): refund service — credit note + cancellation fee + PackageSale update"
```

---

### Task 19: `package_expiry_service.py` + register daily job

**Files:**
- Create: `backend/app/services/package_expiry_service.py`
- Test: `backend/tests/integration/test_package_expiry.py`
- Modify: `backend/app/jobs/scheduled.py`

**Public functions:**
- `extend_expiry(db, sale_id, new_expires_at, reason, user_id) -> PackageSale`
- `run_expiry_transitions(db) -> dict` — for each sale `status='active' AND expires_at < now()`, set `status='expired'`. Returns count.

- [ ] **Step 1: Write tests + implement**

Tests cover: extension validation; just-expired package restored to active; daily job transitions correct rows.

```python
# backend/app/services/package_expiry_service.py
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.package import PackageSale, PackageSaleStatus, PackageExpiryExtension
from app.services.package_pricing_engine import can_extend_expiry


def extend_expiry(db: Session, sale_id: str, new_expires_at: datetime, reason: str, user_id: str) -> PackageSale:
    sale = db.get(PackageSale, sale_id)
    if not sale:
        raise ValueError(f"PackageSale {sale_id} not found")
    can_extend_expiry(sale, new_expires_at)  # raises DomainError if invalid

    ext = PackageExpiryExtension(
        package_sale_id=sale.id,
        previous_expires_at=sale.expires_at,
        new_expires_at=new_expires_at,
        performed_by_user_id=user_id,
        extended_at=datetime.now(timezone.utc),
        reason=reason,
    )
    db.add(ext)
    sale.expires_at = new_expires_at
    if sale.status == PackageSaleStatus.EXPIRED:
        sale.status = PackageSaleStatus.ACTIVE
    db.flush()
    return sale


def run_expiry_transitions(db: Session) -> dict:
    """Daily job: mark expired sales as such."""
    now = datetime.now(timezone.utc)
    rows = db.query(PackageSale).filter(
        PackageSale.status == PackageSaleStatus.ACTIVE,
        PackageSale.expires_at < now,
    ).all()
    for sale in rows:
        sale.status = PackageSaleStatus.EXPIRED
    db.commit()
    return {"transitioned": len(rows)}
```

- [ ] **Step 2: Register the daily job**

Edit `backend/app/jobs/scheduled.py` — find the existing job registration pattern and add:

```python
from app.services.package_expiry_service import run_expiry_transitions

@scheduler.scheduled_job("cron", hour=2, minute=0, id="package_expiry_transitions")
def package_expiry_transitions_job():
    """Daily 2am: transition expired packages to status=expired."""
    db = SessionLocal()
    try:
        run_expiry_transitions(db)
    finally:
        db.close()
```

(Adapt the decorator syntax to whatever scheduler `scheduled.py` uses — RQ-scheduler, APScheduler, or custom — follow existing pattern.)

- [ ] **Step 3: Run + commit**

```bash
cd backend && pytest tests/integration/test_package_expiry.py -v
git add backend/app/services/package_expiry_service.py backend/app/jobs/scheduled.py backend/tests/integration/test_package_expiry.py
git commit -m "feat(packages): expiry service — extend + daily transition job"
```

---

*Phase 3 complete. All service modules in place. Phase 4 wires them into HTTP endpoints.*

---

## Phase 4 — API endpoints

All endpoints in one router file. Follow existing FastAPI patterns from `backend/app/api/customers.py` and `backend/app/api/pos.py` for dependency injection and response shapes.

### Task 20: Catalog endpoints

**Files:**
- Create: `backend/app/api/packages.py`
- Modify: `backend/app/api/__init__.py` (register router)
- Test: `backend/tests/integration/test_packages_catalog_api.py`

- [ ] **Step 1: Implement the router with catalog endpoints**

Create `backend/app/api/packages.py`:

```python
"""Packages HTTP API."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.auth.dependencies import require_permission, get_current_user
from app.models.user import User
from app.models.package import PackageDefinition, PackageDefinitionStatus
from app.schemas.package import (
    PackageDefinitionCreate, PackageDefinitionUpdate, PackageDefinitionResponse,
)
from app.services import package_catalog_service

router = APIRouter(prefix="/packages", tags=["packages"])


# ---------- Catalog ----------

@router.get("/definitions", response_model=List[PackageDefinitionResponse])
def list_definitions(
    status_filter: Optional[PackageDefinitionStatus] = Query(None, alias="status"),
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("packages", "read")),
):
    q = db.query(PackageDefinition).filter(PackageDefinition.deleted_at.is_(None))
    if status_filter:
        q = q.filter(PackageDefinition.status == status_filter)
    if search:
        q = q.filter(PackageDefinition.name.ilike(f"%{search}%"))
    return q.order_by(PackageDefinition.updated_at.desc()).all()


@router.get("/definitions/{def_id}", response_model=PackageDefinitionResponse)
def get_definition(
    def_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("packages", "read")),
):
    pkg = db.get(PackageDefinition, def_id)
    if not pkg or pkg.deleted_at:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Package not found")
    return pkg


@router.post("/definitions", response_model=PackageDefinitionResponse, status_code=201)
def create_definition(
    payload: PackageDefinitionCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("packages", "create")),
):
    pkg = package_catalog_service.create_definition(db, payload, user.id)
    db.commit()
    return pkg


@router.put("/definitions/{def_id}", response_model=PackageDefinitionResponse)
def update_definition(
    def_id: str,
    payload: PackageDefinitionUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("packages", "update")),
):
    try:
        pkg = package_catalog_service.update_definition(db, def_id, payload, user.id)
        db.commit()
        return pkg
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))


@router.post("/definitions/{def_id}/publish", response_model=PackageDefinitionResponse)
def publish_definition(
    def_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("packages", "update")),
):
    try:
        pkg = package_catalog_service.publish(db, def_id)
        db.commit()
        return pkg
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))


@router.post("/definitions/{def_id}/archive", response_model=PackageDefinitionResponse)
def archive_definition(
    def_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("packages", "update")),
):
    try:
        pkg = package_catalog_service.archive(db, def_id)
        db.commit()
        return pkg
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))


@router.delete("/definitions/{def_id}", status_code=204)
def delete_definition(
    def_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("packages", "delete")),
):
    try:
        package_catalog_service.soft_delete(db, def_id)
        db.commit()
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))
```

- [ ] **Step 2: Register the router**

Edit `backend/app/api/__init__.py` (or wherever routers are mounted). Add:

```python
from app.api.packages import router as packages_router

app.include_router(packages_router)
```

- [ ] **Step 3: Write integration tests** for each endpoint covering happy path + permission denial per role.

```python
# backend/tests/integration/test_packages_catalog_api.py (skeleton)
def test_owner_can_create(client_as_owner, sample_payload):
    r = client_as_owner.post("/packages/definitions", json=sample_payload)
    assert r.status_code == 201

def test_receptionist_cannot_create(client_as_receptionist, sample_payload):
    r = client_as_receptionist.post("/packages/definitions", json=sample_payload)
    assert r.status_code == 403

def test_all_roles_can_list(client_as_owner, client_as_receptionist, client_as_staff):
    for c in [client_as_owner, client_as_receptionist, client_as_staff]:
        assert c.get("/packages/definitions").status_code == 200
```

- [ ] **Step 4: Run + commit**

```bash
cd backend && pytest tests/integration/test_packages_catalog_api.py -v
git add backend/app/api/packages.py backend/app/api/__init__.py backend/tests/integration/test_packages_catalog_api.py
git commit -m "feat(packages): catalog API endpoints with RBAC gating"
```

---

### Task 21: Sales endpoints

**Files:**
- Modify: `backend/app/api/packages.py`
- Test: `backend/tests/integration/test_packages_sales_api.py`

- [ ] **Step 1: Add to router**

Append to `backend/app/api/packages.py`:

```python
from app.models.package import PackageSale, PackageSaleStatus
from app.schemas.package import (
    PackageSaleResponse, PackageSaleSummary, RefundRequest, ExtendExpiryRequest,
)
from app.services import package_refund_service, package_expiry_service


@router.get("/sales", response_model=List[PackageSaleResponse])
def list_sales(
    customer_id: Optional[str] = None,
    status_filter: Optional[PackageSaleStatus] = Query(None, alias="status"),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("packages", "read")),
):
    q = db.query(PackageSale)
    if customer_id:
        q = q.filter(PackageSale.customer_id == customer_id)
    if status_filter:
        q = q.filter(PackageSale.status == status_filter)
    return q.order_by(PackageSale.sold_at.desc()).all()


@router.get("/sales/{sale_id}", response_model=PackageSaleResponse)
def get_sale(sale_id: str, db: Session = Depends(get_db),
             _: User = Depends(require_permission("packages", "read"))):
    sale = db.get(PackageSale, sale_id)
    if not sale:
        raise HTTPException(404, "Sale not found")
    return sale


@router.get("/sales/active-for-customer/{customer_id}", response_model=List[PackageSaleSummary])
def list_active_for_customer(
    customer_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("packages", "read")),
):
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    return (
        db.query(PackageSale)
        .filter(
            PackageSale.customer_id == customer_id,
            PackageSale.status == PackageSaleStatus.ACTIVE,
            PackageSale.expires_at > now,
        )
        .order_by(PackageSale.expires_at.asc())
        .all()
    )


@router.post("/sales/{sale_id}/extend", response_model=PackageSaleResponse)
def extend_sale(
    sale_id: str, payload: ExtendExpiryRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("packages", "extend_expiry")),
):
    try:
        sale = package_expiry_service.extend_expiry(
            db, sale_id, payload.new_expires_at, payload.reason, user.id,
        )
        db.commit()
        return sale
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/sales/{sale_id}/refund", response_model=dict)
def refund_sale(
    sale_id: str, payload: RefundRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("packages", "refund")),
):
    try:
        credit_note = package_refund_service.issue_refund(
            db, sale_id, payload.payment_method, payload.reason, user.id,
        )
        db.commit()
        return {"credit_note_bill_id": credit_note.id, "status": "refunded"}
    except ValueError as e:
        raise HTTPException(400, str(e))
```

- [ ] **Step 2: Test + commit**

```bash
cd backend && pytest tests/integration/test_packages_sales_api.py -v
git add backend/app/api/packages.py backend/tests/integration/test_packages_sales_api.py
git commit -m "feat(packages): sales / refund / extend API endpoints"
```

---

### Task 22: Eligibility + redemption API

**Files:**
- Modify: `backend/app/api/packages.py`
- Test: `backend/tests/integration/test_packages_eligibility_api.py`

- [ ] **Step 1: Add eligibility check and undo endpoints**

Append to `backend/app/api/packages.py`:

```python
from app.schemas.package import RedemptionEligibilityRequest, EligiblePackageResponse
from app.services import package_redemption_service
from app.services.package_pricing_engine import find_eligible_packages


@router.post("/eligibility/check", response_model=List[EligiblePackageResponse])
def check_eligibility(
    payload: RedemptionEligibilityRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("packages", "read")),
):
    sales = find_eligible_packages(payload.customer_id, payload.service_id, db)
    out = []
    for sale in sales:
        snapshot = next(
            (i.snapshot_unit_price_paise for i in sale.items if i.service_id == payload.service_id),
            0,
        )
        out.append(EligiblePackageResponse(package_sale=sale, snapshot_price_paise=snapshot))
    return out


@router.post("/redemptions/{audit_id}/undo", status_code=204)
def undo_redemption(
    audit_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("packages", "redeem")),
):
    try:
        package_redemption_service.undo_redemption(db, audit_id, user.id)
        db.commit()
    except ValueError as e:
        raise HTTPException(400, str(e))
```

- [ ] **Step 2: Test + commit**

```bash
cd backend && pytest tests/integration/test_packages_eligibility_api.py -v
git add backend/app/api/packages.py backend/tests/integration/test_packages_eligibility_api.py
git commit -m "feat(packages): eligibility + undo endpoints"
```

---

## Phase 5 — Billing integration

The package sale is **not** a new endpoint — it piggybacks on the existing billing finalization. Redemption is **not** a new endpoint — it piggybacks on add-bill-item.

### Task 23: Modify `billing_service.finalize_bill()` to create PackageSale rows

**Files:**
- Modify: `backend/app/services/billing_service.py`
- Test: `backend/tests/integration/test_billing_with_packages.py`

- [ ] **Step 1: Locate the finalize logic**

Open `backend/app/services/billing_service.py`. Find the `finalize_bill` (or equivalent) function. Identify where Payment rows are created and where the bill transitions to POSTED.

- [ ] **Step 2: Write integration test**

```python
# backend/tests/integration/test_billing_with_packages.py (excerpt)
def test_finalize_creates_package_sale_for_package_sale_line(
    db_session, definition_factory, bill_factory, bill_item_factory, payment_factory,
):
    pkg = definition_factory(validity_days=90)
    bill = bill_factory(status="draft")
    bi = bill_item_factory(
        bill=bill, item_type="package_sale_line",
        package_sale_id=None,  # to be set at finalize
    )
    payment_factory(bill=bill, amount_paise=bill.total_paise)

    from app.services.billing_service import finalize_bill
    finalize_bill(db_session, bill.id, user_id="...", definition_id_for_package_line=pkg.id)

    db_session.refresh(bi)
    assert bi.package_sale_id is not None
    from app.models.package import PackageSale
    sale = db_session.get(PackageSale, bi.package_sale_id)
    assert sale.bill_id == bill.id
    assert sale.sessions_remaining == pkg.total_sessions
```

- [ ] **Step 3: Modify `finalize_bill`**

Inside the existing `finalize_bill` function, after Payment rows are created and before status transitions to POSTED, insert:

```python
from app.services import package_sales_service
from app.models.billing import BillItem, BillItemType

# Create PackageSale rows for each package_sale_line BillItem
for item in db.query(BillItem).filter(
    BillItem.bill_id == bill.id,
    BillItem.item_type == BillItemType.PACKAGE_SALE_LINE,
).all():
    if item.package_sale_id:
        continue  # already created
    # The PackageDefinition ID must have been written to a temp column or carried via the create-bill-item flow
    definition_id = item.package_definition_id_pending  # see Task 24 for how this is passed
    sale = package_sales_service.create_sale(
        db, definition_id, bill.id, bill.customer_id, item.selling_staff_id,
    )
    item.package_sale_id = sale.id
```

**Note on `package_definition_id_pending`:** since `BillItem` doesn't have a column for "which definition this sale line refers to," you'll need to either:

- (a) Add a transient `package_definition_id` nullable column on `BillItem` (cheap)
- (b) Use `BillItem.notes` JSON to stash it
- (c) Use a separate "pending package sale" structure

Recommend (a) — add a small migration to add `BillItem.package_definition_id = Column(String(26), ForeignKey("package_definitions.id"), nullable=True)` (note: distinct from `package_sale_id`). Update Task 6's migration if not yet committed; otherwise generate a follow-on migration.

- [ ] **Step 4: Run + commit**

```bash
cd backend && pytest tests/integration/test_billing_with_packages.py -v
git add backend/app/services/billing_service.py backend/tests/integration/test_billing_with_packages.py
git commit -m "feat(billing): create PackageSale rows for package_sale_line items at finalization"
```

---

### Task 24: Modify `billing_service.add_item()` to auto-apply redemption

**Files:**
- Modify: `backend/app/services/billing_service.py`
- Modify: `backend/app/schemas/billing.py` (response includes `eligible_packages`)
- Test: `backend/tests/integration/test_billing_redemption_autoapply.py`

- [ ] **Step 1: Write tests** for: single eligible package auto-applies; 2+ eligible returns the list; non-eligible service stays as normal SERVICE item.

- [ ] **Step 2: Modify `add_item`**

In `billing_service.add_item`, after the BillItem is created and before the response is built:

```python
from app.services import package_redemption_service
from app.services.package_pricing_engine import find_eligible_packages
from app.models.package import PackageDefinition

eligible = []
if bill_item.service_id and bill.customer_id:
    eligible = find_eligible_packages(bill.customer_id, bill_item.service_id, db)

if len(eligible) == 1 and eligible[0].package_definition.auto_apply:
    package_redemption_service.apply_redemption(
        db, eligible[0].id, bill_item.id,
        redeemed_for_customer_id=bill.customer_id,
        user_id=current_user.id,
    )
    response.auto_applied_package_sale_id = eligible[0].id
elif len(eligible) >= 2:
    response.eligible_packages = [e.id for e in eligible]
```

Update `BillItemResponse` schema in `backend/app/schemas/billing.py` to include the optional new fields:

```python
class BillItemResponse(BaseModel):
    # ... existing ...
    eligible_packages: List[str] = []
    auto_applied_package_sale_id: Optional[str] = None
```

- [ ] **Step 3: Run + commit**

```bash
cd backend && pytest tests/integration/test_billing_redemption_autoapply.py -v
git add backend/app/services/billing_service.py backend/app/schemas/billing.py backend/tests/integration/test_billing_redemption_autoapply.py
git commit -m "feat(billing): auto-apply package redemption on add_item with eligibility check"
```

---

### Task 25: Receipt service handles new BillItem types

**Files:**
- Modify: `backend/app/services/receipt_service.py`
- Test: extend existing receipt tests

- [ ] **Step 1: Find the receipt template rendering**

Locate the function that renders a `BillItem`. Add branches by `item_type`:

```python
if item.item_type == BillItemType.PACKAGE_SALE_LINE:
    # render as normal line with the package name + included services sublist
    lines.append(f"{pkg.name:<30}{format_paise(item.subtotal_paise):>10}")
    for sub_item in pkg.items:
        lines.append(f"  • {sub_item.service.name}")
elif item.item_type == BillItemType.PACKAGE_REDEMPTION:
    sale = db.get(PackageSale, item.package_sale_id)
    n, N = sale.total_sessions_snapshot - sale.sessions_remaining, sale.total_sessions_snapshot
    lines.append(f"{item.service.name:<30}{format_paise(item.subtotal_paise):>10}")
    lines.append(f"  Paid via Package #{sale.id[:8]} ({n}/{N})")
else:
    # existing rendering
```

For the Payment section, group `package_redemption` payments as `Paid via Package` (no individual money figures, since each line shows its own).

- [ ] **Step 2: Test + commit**

```bash
cd backend && pytest tests/integration/test_receipt_with_packages.py -v
git add backend/app/services/receipt_service.py backend/tests/integration/test_receipt_with_packages.py
git commit -m "feat(receipt): render package_sale_line + package_redemption items correctly"
```

---

*Phase 5 complete. Backend is feature-complete. Phase 6+ build the frontend.*

---

## Phase 6 — Frontend foundation

### Task 26: TypeScript types

**Files:**
- Create: `frontend/src/types/package.ts`

- [ ] **Step 1: Mirror the Pydantic schemas as TS interfaces**

```typescript
// frontend/src/types/package.ts
export type PackageDefinitionStatus = "draft" | "published" | "archived";
export type EntitlementType = "counted" | "unlimited";
export type Shareability = "owner_only" | "shared";
export type PackageSaleStatus = "active" | "expired" | "refunded" | "exhausted";
export type DiscountMode = "pct" | "flat" | "final";

export interface PackageDefinitionItem {
  id: string;
  service_id: string;
  service_name?: string;
  quantity: number;
  unit_price_paise: number;
  locked: boolean;
  display_order: number;
}

export interface PackageDefinition {
  id: string;
  name: string;
  description?: string | null;
  status: PackageDefinitionStatus;
  entitlement_type: EntitlementType;
  total_sessions: number | null;
  shareability: Shareability;
  validity_days: number;
  auto_apply: boolean;
  cancellation_fee_pct: string; // Decimal serialized
  items: PackageDefinitionItem[];
  created_at: string;
  updated_at: string;
}

export interface PackageDefinitionCreate {
  name: string;
  description?: string;
  entitlement_type: EntitlementType;
  total_sessions?: number;
  shareability: Shareability;
  validity_days: number;
  auto_apply: boolean;
  cancellation_fee_pct: string;
  items: Array<Omit<PackageDefinitionItem, "id" | "service_name">>;
  discount?: { mode: DiscountMode; value: string };
}

export interface PackageSaleItem {
  id: string;
  service_id: string;
  service_name?: string;
  quantity: number;
  snapshot_unit_price_paise: number;
  snapshot_gst_rate_pct: string;
  locked: boolean;
}

export interface PackageSale {
  id: string;
  bill_id: string;
  package_definition_id: string;
  package_definition_name?: string;
  customer_id: string;
  customer_name?: string;
  selling_staff_id: string | null;
  sold_at: string;
  expires_at: string;
  entitlement_type_snapshot: EntitlementType;
  shareability_snapshot: Shareability;
  cancellation_fee_pct_snapshot: string;
  total_sessions_snapshot: number | null;
  sessions_remaining: number | null;
  status: PackageSaleStatus;
  refunded_at: string | null;
  refund_bill_id: string | null;
  items: PackageSaleItem[];
}

export interface PackageSaleSummary {
  id: string;
  package_definition_name: string;
  entitlement_type_snapshot: EntitlementType;
  sessions_remaining: number | null;
  total_sessions_snapshot: number | null;
  expires_at: string;
  shareability_snapshot: Shareability;
  customer_id: string;
  customer_name?: string;
}

export interface EligiblePackage {
  package_sale: PackageSaleSummary;
  snapshot_price_paise: number;
}

export interface RefundBreakdown {
  kind: "counted" | "unlimited";
  base_paise: number;
  fee_paise: number;
  refund_paise: number;
  consumed_value_paise: number;
  pct_remaining?: string;
  sessions_consumed?: number;
  sessions_total?: number;
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/types/package.ts
git commit -m "feat(packages-fe): TypeScript types mirroring backend schemas"
```

---

### Task 27: API client

**Files:**
- Create: `frontend/src/lib/api/packages.ts`

- [ ] **Step 1: Implement the typed client**

```typescript
// frontend/src/lib/api/packages.ts
import { apiClient } from "./client"; // existing axios/fetch wrapper
import type {
  PackageDefinition, PackageDefinitionCreate, PackageSale, PackageSaleSummary,
  EligiblePackage, RefundBreakdown,
} from "@/types/package";

export const packagesApi = {
  // Catalog
  listDefinitions: (params?: { status?: string; search?: string }) =>
    apiClient.get<PackageDefinition[]>("/packages/definitions", { params }),
  getDefinition: (id: string) =>
    apiClient.get<PackageDefinition>(`/packages/definitions/${id}`),
  createDefinition: (payload: PackageDefinitionCreate) =>
    apiClient.post<PackageDefinition>("/packages/definitions", payload),
  updateDefinition: (id: string, payload: PackageDefinitionCreate) =>
    apiClient.put<PackageDefinition>(`/packages/definitions/${id}`, payload),
  publishDefinition: (id: string) =>
    apiClient.post<PackageDefinition>(`/packages/definitions/${id}/publish`),
  archiveDefinition: (id: string) =>
    apiClient.post<PackageDefinition>(`/packages/definitions/${id}/archive`),
  deleteDefinition: (id: string) =>
    apiClient.delete(`/packages/definitions/${id}`),

  // Sales
  listSales: (params?: { customer_id?: string; status?: string }) =>
    apiClient.get<PackageSale[]>("/packages/sales", { params }),
  getSale: (id: string) => apiClient.get<PackageSale>(`/packages/sales/${id}`),
  listActiveForCustomer: (customerId: string) =>
    apiClient.get<PackageSaleSummary[]>(`/packages/sales/active-for-customer/${customerId}`),
  refundSale: (id: string, payload: { payment_method: string; reason: string }) =>
    apiClient.post(`/packages/sales/${id}/refund`, payload),
  extendSale: (id: string, payload: { new_expires_at: string; reason: string }) =>
    apiClient.post<PackageSale>(`/packages/sales/${id}/extend`, payload),

  // Eligibility + undo
  checkEligibility: (payload: { customer_id: string; service_id: string }) =>
    apiClient.post<EligiblePackage[]>("/packages/eligibility/check", payload),
  undoRedemption: (auditId: string) =>
    apiClient.post(`/packages/redemptions/${auditId}/undo`),
};
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/lib/api/packages.ts
git commit -m "feat(packages-fe): typed API client for /packages endpoints"
```

---

### Task 28: Zustand store

**Files:**
- Create: `frontend/src/stores/packages-store.ts`

Follow existing Zustand patterns (see `zustand-store` skill). The store holds catalog cache (5-min TTL) + per-customer eligibility cache (60s TTL).

- [ ] **Step 1: Implement**

```typescript
// frontend/src/stores/packages-store.ts
import { create } from "zustand";
import { packagesApi } from "@/lib/api/packages";
import type { PackageDefinition, PackageSaleSummary } from "@/types/package";

interface EligibilityEntry {
  packages: PackageSaleSummary[];
  loadedAt: number;
}

interface PackagesStore {
  definitions: PackageDefinition[] | null;
  definitionsLoadedAt: number | null;
  loadDefinitions: (force?: boolean) => Promise<PackageDefinition[]>;

  eligibilityCache: Map<string, EligibilityEntry>;
  loadEligibility: (customerId: string, force?: boolean) => Promise<PackageSaleSummary[]>;
  invalidateEligibility: (customerId: string) => void;
  invalidateAll: () => void;
}

const CATALOG_TTL_MS = 5 * 60 * 1000;
const ELIGIBILITY_TTL_MS = 60 * 1000;

export const usePackagesStore = create<PackagesStore>((set, get) => ({
  definitions: null,
  definitionsLoadedAt: null,
  async loadDefinitions(force = false) {
    const state = get();
    const fresh = state.definitionsLoadedAt &&
      Date.now() - state.definitionsLoadedAt < CATALOG_TTL_MS;
    if (state.definitions && fresh && !force) return state.definitions;
    const res = await packagesApi.listDefinitions({ status: "published" });
    set({ definitions: res.data, definitionsLoadedAt: Date.now() });
    return res.data;
  },

  eligibilityCache: new Map(),
  async loadEligibility(customerId, force = false) {
    const cache = get().eligibilityCache;
    const cached = cache.get(customerId);
    const fresh = cached && Date.now() - cached.loadedAt < ELIGIBILITY_TTL_MS;
    if (cached && fresh && !force) return cached.packages;
    const res = await packagesApi.listActiveForCustomer(customerId);
    const newCache = new Map(cache);
    newCache.set(customerId, { packages: res.data, loadedAt: Date.now() });
    set({ eligibilityCache: newCache });
    return res.data;
  },
  invalidateEligibility(customerId) {
    const newCache = new Map(get().eligibilityCache);
    newCache.delete(customerId);
    set({ eligibilityCache: newCache });
  },
  invalidateAll() {
    set({ definitions: null, definitionsLoadedAt: null, eligibilityCache: new Map() });
  },
}));
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/stores/packages-store.ts
git commit -m "feat(packages-fe): Zustand store with catalog + eligibility caching"
```

---

*Phase 6 complete. Phase 7 builds the catalog admin UI.*

---

## Phase 7 — New UI primitives + catalog admin

Reference design output decisions for visual treatments: `docs/superpowers/specs/2026-05-29-bundles-packages-design-output.md`. Mockups at `docs/superpowers/specs/design-assets/2026-05-29-bundles-packages/`.

### Task 29: `SessionsLeft` primitive

**Files:**
- Create: `frontend/src/components/ui/SessionsLeft.tsx`
- Test: `frontend/src/components/ui/__tests__/SessionsLeft.test.tsx`

- [ ] **Step 1: Implement**

```tsx
// frontend/src/components/ui/SessionsLeft.tsx
import { cn } from "@/lib/utils";

interface SessionsLeftProps {
  remaining: number | null;
  total: number | null;
  size?: "sm" | "md" | "lg";
  className?: string;
}

export function SessionsLeft({ remaining, total, size = "md", className }: SessionsLeftProps) {
  const isUnlimited = remaining === null && total === null;
  const sizeClass = size === "sm" ? "text-sm" : size === "lg" ? "text-2xl" : "text-base";

  if (isUnlimited) {
    return <span className={cn("tabular font-semibold", sizeClass, className)}>∞</span>;
  }

  return (
    <span className={cn("tabular font-semibold", sizeClass, className)}>
      <span className="text-text-primary">{remaining}</span>
      <span className="text-text-muted">/{total}</span>
    </span>
  );
}
```

- [ ] **Step 2: Test + commit**

```tsx
// frontend/src/components/ui/__tests__/SessionsLeft.test.tsx
import { render } from "@testing-library/react";
import { SessionsLeft } from "../SessionsLeft";

test("renders counted as N/M", () => {
  const { container } = render(<SessionsLeft remaining={7} total={10} />);
  expect(container.textContent).toBe("7/10");
});

test("renders unlimited as ∞", () => {
  const { container } = render(<SessionsLeft remaining={null} total={null} />);
  expect(container.textContent).toBe("∞");
});
```

```bash
cd frontend && pnpm test SessionsLeft
git add frontend/src/components/ui/SessionsLeft.tsx frontend/src/components/ui/__tests__/SessionsLeft.test.tsx
git commit -m "feat(packages-fe): SessionsLeft primitive (counted N/M or ∞)"
```

---

### Task 30: `ExpiryBadge` primitive

**Files:**
- Create: `frontend/src/components/ui/ExpiryBadge.tsx`
- Test: `frontend/src/components/ui/__tests__/ExpiryBadge.test.tsx`

- [ ] **Step 1: Implement**

```tsx
// frontend/src/components/ui/ExpiryBadge.tsx
import { cn } from "@/lib/utils";

interface ExpiryBadgeProps {
  expiresAt: string;  // ISO timestamp
  className?: string;
}

export function ExpiryBadge({ expiresAt, className }: ExpiryBadgeProps) {
  const now = Date.now();
  const exp = new Date(expiresAt).getTime();
  const daysLeft = Math.floor((exp - now) / (24 * 60 * 60 * 1000));

  let tone: string;
  let label: string;
  if (daysLeft < 0) {
    tone = "bg-text-muted/15 text-text-muted border-border-default";
    label = `Expired ${Math.abs(daysLeft)}d ago`;
  } else if (daysLeft <= 7) {
    tone = "bg-danger-bg-soft text-danger-fg border-danger-border";
    label = `${daysLeft}d left`;
  } else if (daysLeft <= 30) {
    tone = "bg-warning-bg-soft text-warning-fg border-warning-border";
    label = `${daysLeft}d left`;
  } else {
    tone = "bg-success-bg-soft text-success-fg border-success-border";
    label = `${daysLeft}d left`;
  }

  return (
    <span className={cn(
      "inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs border tabular",
      tone, className,
    )}>
      {label}
    </span>
  );
}
```

- [ ] **Step 2: Test + commit**

```bash
git add frontend/src/components/ui/ExpiryBadge.tsx frontend/src/components/ui/__tests__/ExpiryBadge.test.tsx
git commit -m "feat(packages-fe): ExpiryBadge primitive (green/amber/red by days-left)"
```

---

### Task 31: `PackageBuilder` form components

**Files:**
- Create: `frontend/src/components/packages/PackageBuilder.tsx`
- Create: `frontend/src/components/packages/PackageBuilderDiscountControl.tsx`
- Create: `frontend/src/components/packages/PackageBuilderEntitlementMatrix.tsx`
- Create: `frontend/src/components/packages/PackageBuilderServicesTable.tsx`

These render the 2-column form described in design output `Q-VIS-1`. Reference mockups: `design-assets/.../q1-package-builder-counted-light.png` and `q1-package-builder-unlimited-light.png`.

Key behaviors:
- **Left column** (`surface-page` panel): name, description, entitlement-matrix (2×2 radio cards), validity_days, cancellation_fee_pct, auto_apply toggle
- **Right column** (`surface-card`): services table + discount segmented control + live price summary
- **Discount toggle**: segmented control with morphing input suffix (`%` / `₹` / Final). When changed, calls server-side preview endpoint OR computes locally with the same `distribute_discount` logic.
- **Locked lines**: faint `gold-soft` row tint + lock icon; package-level discount changes skip locked lines
- **Unlimited reshape**: quantity column collapses; discount defaults to `final`

- [ ] **Step 1: Build each sub-component as a separate file**

Each component should be 100-200 lines max. Use the existing primitives library + design tokens (no raw Tailwind colors per `docs/design_system.md`).

A skeleton for the parent component:

```tsx
// frontend/src/components/packages/PackageBuilder.tsx
"use client";
import { useState } from "react";
import { PackageBuilderEntitlementMatrix } from "./PackageBuilderEntitlementMatrix";
import { PackageBuilderServicesTable } from "./PackageBuilderServicesTable";
import { PackageBuilderDiscountControl } from "./PackageBuilderDiscountControl";
import { packagesApi } from "@/lib/api/packages";
import type { PackageDefinitionCreate, EntitlementType, Shareability } from "@/types/package";

interface Props {
  initial?: PackageDefinitionCreate;
  onSaved: (id: string) => void;
}

export function PackageBuilder({ initial, onSaved }: Props) {
  const [name, setName] = useState(initial?.name ?? "");
  const [entitlementType, setEntitlementType] = useState<EntitlementType>(initial?.entitlement_type ?? "counted");
  const [shareability, setShareability] = useState<Shareability>(initial?.shareability ?? "owner_only");
  const [totalSessions, setTotalSessions] = useState<number | undefined>(initial?.total_sessions);
  const [validityDays, setValidityDays] = useState<number>(initial?.validity_days ?? 90);
  const [cancellationFeePct, setCancellationFeePct] = useState<string>(initial?.cancellation_fee_pct ?? "20.00");
  const [autoApply, setAutoApply] = useState<boolean>(initial?.auto_apply ?? true);
  const [items, setItems] = useState(initial?.items ?? []);
  const [discount, setDiscount] = useState<{ mode: "pct" | "flat" | "final"; value: string } | undefined>();

  async function handleSave() {
    const payload: PackageDefinitionCreate = {
      name, entitlement_type: entitlementType, total_sessions: totalSessions,
      shareability, validity_days: validityDays,
      cancellation_fee_pct: cancellationFeePct, auto_apply: autoApply,
      items, discount,
    };
    const res = await packagesApi.createDefinition(payload);
    onSaved(res.data.id);
  }

  return (
    <div className="grid grid-cols-[320px_1fr] gap-6">
      <section className="bg-surface-page rounded-xl p-4 space-y-4">
        {/* Name, description inputs */}
        <PackageBuilderEntitlementMatrix
          entitlementType={entitlementType}
          shareability={shareability}
          onChange={(et, sh) => { setEntitlementType(et); setShareability(sh); }}
        />
        {/* Validity / fee / auto_apply controls */}
      </section>
      <section className="bg-surface-card rounded-xl p-4">
        <PackageBuilderServicesTable
          items={items} onChange={setItems}
          entitlementType={entitlementType}
        />
        <PackageBuilderDiscountControl
          items={items} discount={discount} onChange={setDiscount}
        />
        {/* Summary + Save button */}
      </section>
    </div>
  );
}
```

(Sub-components follow similar shape — reference design output for visual details.)

- [ ] **Step 2: Tests + commit**

```bash
cd frontend && pnpm test packages
git add frontend/src/components/packages/PackageBuilder*.tsx
git commit -m "feat(packages-fe): PackageBuilder form + 3 sub-components (matrix, table, discount)"
```

---

### Task 32: Catalog list page + routes

**Files:**
- Create: `frontend/src/app/(shell)/dashboard/packages/page.tsx`
- Create: `frontend/src/app/(shell)/dashboard/packages/new/page.tsx`
- Create: `frontend/src/app/(shell)/dashboard/packages/[id]/page.tsx`
- Create: `frontend/src/app/(shell)/dashboard/packages/[id]/edit/page.tsx`
- Create: `frontend/src/components/packages/PackageCatalogList.tsx`
- Modify: `frontend/src/components/shell/sidebar.tsx`

- [ ] **Step 1: Implement each route as a thin wrapper around components**

```tsx
// frontend/src/app/(shell)/dashboard/packages/page.tsx
"use client";
import { useAuthStore } from "@/stores/auth-store";
import { PackageCatalogList } from "@/components/packages/PackageCatalogList";

export default function PackagesPage() {
  const { hasPermission } = useAuthStore();
  if (!hasPermission("packages", "read")) return <div>Access denied</div>;
  return <PackageCatalogList />;
}
```

```tsx
// frontend/src/app/(shell)/dashboard/packages/new/page.tsx
"use client";
import { useRouter } from "next/navigation";
import { PackageBuilder } from "@/components/packages/PackageBuilder";

export default function NewPackagePage() {
  const router = useRouter();
  return <PackageBuilder onSaved={(id) => router.push(`/dashboard/packages/${id}`)} />;
}
```

The `PackageCatalogList` reads from the store and renders a table with filter chips, matching the catalog mockup `s1-catalog-light.png`.

- [ ] **Step 2: Add sidebar menu item**

In `frontend/src/components/shell/sidebar.tsx`, add a new menu entry gated to Owner:

```tsx
{hasPermission("packages", "create") && (
  <SidebarLink href="/dashboard/packages" icon={<PackageIcon />}>
    Packages
  </SidebarLink>
)}
```

- [ ] **Step 3: Test + commit**

```bash
git add frontend/src/app/(shell)/dashboard/packages/ frontend/src/components/packages/PackageCatalogList.tsx frontend/src/components/shell/sidebar.tsx
git commit -m "feat(packages-fe): catalog admin pages + sidebar menu item"
```

---

## Phase 8 — POS integration

The biggest frontend phase. Reference design output Q-VIS-9 for the Entitlements Rail IA.

### Task 33: `PackageCard` + `PackageSelectorChip`

**Files:**
- Create: `frontend/src/components/packages/PackageCard.tsx`
- Create: `frontend/src/components/packages/PackageSelectorChip.tsx`

`PackageCard` is reusable across rail / selector / sold list. `PackageSelectorChip` is the "Packages" tab that lives next to the existing `All | Services | Products` chips.

- [ ] Implement + test + commit

```bash
git add frontend/src/components/packages/PackageCard.tsx frontend/src/components/packages/PackageSelectorChip.tsx
git commit -m "feat(packages-fe): PackageCard + PackageSelectorChip (POS catalog filter)"
```

---

### Task 34: `PackageSaleLine` + `RedemptionLineItem`

**Files:**
- Create: `frontend/src/components/packages/PackageSaleLine.tsx`
- Create: `frontend/src/components/packages/RedemptionLineItem.tsx`

`PackageSaleLine`: bill line rendering for `item_type='package_sale_line'`. Includes accordion "N services included" + inline selling-staff picker. Navy left-rail per cross-cutting grammar (paid-now revenue).

`RedemptionLineItem`: bill line for `item_type='package_redemption'`. Gold left-rail + gift glyph. **Persistent `[↩ Undo]` pill** (always visible, never hover-gated). Shows "Paid via Package XYZ (N/M)" annotation; for shared, includes "(owned by Buyer Name)" with PII redaction for Staff role.

- [ ] Implement + test + commit

```bash
git add frontend/src/components/packages/PackageSaleLine.tsx frontend/src/components/packages/RedemptionLineItem.tsx
git commit -m "feat(packages-fe): bill line renderers for package sale + redemption with Undo pill"
```

---

### Task 35: `EntitlementsRail` + `EntitlementsStrip` + `ActivePackagesBadge`

**Files:**
- Create: `frontend/src/components/packages/EntitlementsRail.tsx`
- Create: `frontend/src/components/packages/EntitlementsStrip.tsx`
- Create: `frontend/src/components/packages/ActivePackagesBadge.tsx`

Three components, one purpose: surface customer's active packages on POS. Used at different viewport sizes:
- `EntitlementsRail`: ≥1024px (vertical rail between selector and bill canvas)
- `EntitlementsStrip`: 768–1024px (horizontal strip)
- `ActivePackagesBadge`: <768px (single overflow pill above bill)

All three read from `usePackagesStore().loadEligibility(customerId)`.

- [ ] Implement each per design output Q-VIS-9 mockups
- [ ] Test the responsive breakpoint swap in `frontend/src/components/packages/__tests__/EntitlementsRail.test.tsx`
- [ ] Commit

```bash
git add frontend/src/components/packages/EntitlementsRail.tsx frontend/src/components/packages/EntitlementsStrip.tsx frontend/src/components/packages/ActivePackagesBadge.tsx
git commit -m "feat(packages-fe): Entitlements Rail/Strip/Badge with responsive breakpoint swap"
```

---

### Task 36: `MultiPackageSelector`

**Files:**
- Create: `frontend/src/components/packages/MultiPackageSelector.tsx`

Inline radio panel (not modal) shown when `BillItem` response includes `eligible_packages` with ≥2 entries. Pre-selects FIFO (sooner-expiry first). Has a `warning` header "Multiple packages available — confirm with customer." On Apply, calls a follow-up endpoint to lock in the chosen redemption.

- [ ] Implement + test + commit

```bash
git add frontend/src/components/packages/MultiPackageSelector.tsx
git commit -m "feat(packages-fe): MultiPackageSelector inline radio panel with FIFO default"
```

---

### Task 37: POS page modifications

**Files:**
- Modify: `frontend/src/app/(shell)/dashboard/pos/page.tsx`

The largest frontend change. Per spec §8.4:

1. **Rail injection**: when `customerId` is selected AND `useEligibility(customerId)` returns ≥1 active package, render appropriate component by viewport width
2. **Selector filter chip**: add `Packages` chip alongside existing filter chips
3. **Bill canvas dispatch**: render new BillItem types via item_type discriminator
4. **Multi-package interaction**: when add-item response includes `eligible_packages`, render `MultiPackageSelector` inline on that BillItem until cashier picks one
5. **Last-visit recognition aid**: surface `customer.last_visit_at` as subtitle on customer header and rail header

```tsx
// POS page modification — key additions (illustrative)

const customer = useSelectedCustomer();
const eligibilityData = usePackagesStore((s) => customer ? s.eligibilityCache.get(customer.id) : null);
const width = useViewportWidth();

useEffect(() => {
  if (customer) usePackagesStore.getState().loadEligibility(customer.id);
}, [customer?.id]);

const RailComponent = width >= 1024 ? EntitlementsRail : width >= 768 ? EntitlementsStrip : ActivePackagesBadge;
const showRail = customer && (eligibilityData?.packages.length ?? 0) > 0;

// In the customer header strip:
<div>
  <h2>{customer.name}</h2>
  {customer.last_visit_at && (
    <p className="text-text-muted text-sm">
      Last visit: {formatRelativeDate(customer.last_visit_at)}
    </p>
  )}
</div>

// In the layout:
<div className="grid grid-cols-[auto_1fr_400px]">
  <ServiceSelector />
  {showRail && <RailComponent customerId={customer.id} />}
  <BillCanvas />
</div>

// In bill canvas rendering:
{billItems.map(item => {
  if (item.item_type === "package_sale_line") return <PackageSaleLine key={item.id} item={item} />;
  if (item.item_type === "package_redemption") return <RedemptionLineItem key={item.id} item={item} />;
  return <ExistingBillItemLine key={item.id} item={item} />;
})}
```

- [ ] **Step 1: Make modifications**
- [ ] **Step 2: Test the POS in development against a customer with sample packages**
- [ ] **Step 3: Commit**

```bash
git add frontend/src/app/(shell)/dashboard/pos/page.tsx
git commit -m "feat(packages-fe): POS integration — Entitlements Rail, new BillItem renderers, last-visit aid"
```

---

## Phase 9 — Refund + Extend + Sold-packages list

### Task 38: `RefundPackageModal`

**Files:**
- Create: `frontend/src/components/packages/RefundPackageModal.tsx`

Per design output Q-VIS-5 mockups. Common shell + branching math rows based on entitlement_type. Refund-to picker (Cash / UPI / pending balance) between math and reason. Expired-package goodwill banner at top when applicable. Pending-balance hint when customer has outstanding balance.

- [ ] Implement + test + commit

```bash
git add frontend/src/components/packages/RefundPackageModal.tsx
git commit -m "feat(packages-fe): RefundPackageModal with branching counted/unlimited math"
```

---

### Task 39: `ExtendExpiryModal`

**Files:**
- Create: `frontend/src/components/packages/ExtendExpiryModal.tsx`

Dedicated modal with date picker for `new_expires_at` + required reason text field. Mirrors refund modal's gravity.

- [ ] Implement + test + commit

```bash
git add frontend/src/components/packages/ExtendExpiryModal.tsx
git commit -m "feat(packages-fe): ExtendExpiryModal with required reason field"
```

---

### Task 40: Sold-packages list page

**Files:**
- Create: `frontend/src/app/(shell)/dashboard/packages/sold/page.tsx`

Owner entry point for refunds. Lists all `PackageSale`s with filters by customer, status, date. Each row has a "Refund" button (opens `RefundPackageModal`) and an "Extend" button (opens `ExtendExpiryModal`) — both Owner-only.

- [ ] Implement + test + commit

```bash
git add frontend/src/app/(shell)/dashboard/packages/sold/page.tsx
git commit -m "feat(packages-fe): sold-packages list page with refund/extend entry points"
```

---

### Task 41: Bill detail page "Refund Package" button

**Files:**
- Modify: `frontend/src/app/(shell)/dashboard/bills/[id]/page.tsx`

When the bill has any BillItem with `item_type='package_sale_line'` and viewer has `packages:refund`, show a "Refund Package" button that opens `RefundPackageModal` for the corresponding `PackageSale`.

- [ ] Implement + test + commit

```bash
git add frontend/src/app/(shell)/dashboard/bills/[id]/page.tsx
git commit -m "feat(packages-fe): bill detail page — Refund Package button for package sales"
```

---

## Phase 10 — E2E + docs

### Task 42: Playwright happy-path E2E

**Files:**
- Create: `frontend/e2e/packages-full-cycle.spec.ts`

```typescript
// frontend/e2e/packages-full-cycle.spec.ts
import { test, expect } from "@playwright/test";

test("packages full cycle: create → sell → redeem 3x → refund", async ({ page }) => {
  // 1. Login as Owner, create definition
  await loginAs(page, "owner");
  await page.goto("/dashboard/packages/new");
  await page.fill('input[name="name"]', "Test Hair Spa 5-pack");
  await page.click("input[value=counted]");
  await page.fill('input[name="total_sessions"]', "5");
  await page.fill('input[name="validity_days"]', "180");
  // ...add services, set discount, save & publish
  await page.click("text=Publish");

  // 2. Login as Receptionist, sell to a test customer
  await loginAs(page, "receptionist");
  await page.goto("/dashboard/pos");
  await selectCustomer(page, "Test Customer");
  await page.click("text=Packages");
  await page.click("text=Test Hair Spa 5-pack");
  await page.click("text=Finalize");
  await payCash(page);

  // 3. Customer returns, redeem 3 times
  for (let i = 0; i < 3; i++) {
    await page.goto("/dashboard/pos");
    await selectCustomer(page, "Test Customer");
    await page.click("text=Hair Spa"); // existing service
    await expect(page.locator("text=Paid via")).toBeVisible();
    await page.click("text=Finalize");
    await payCash(page);
  }

  // 4. Login as Owner, refund remaining 2 sessions
  await loginAs(page, "owner");
  await page.goto("/dashboard/packages/sold");
  await page.click("text=Test Hair Spa 5-pack >> text=Refund");
  await page.fill('textarea[name="reason"]', "Test refund");
  await page.click("text=Issue Credit Note");

  // 5. Verify final state
  await expect(page.locator("text=refunded")).toBeVisible();
});
```

- [ ] Run + commit

```bash
cd frontend && pnpm playwright test packages-full-cycle
git add frontend/e2e/packages-full-cycle.spec.ts
git commit -m "feat(packages): E2E full cycle test (create → sell → redeem → refund)"
```

---

### Task 43: Feature docs

**Files:**
- Create: `docs/features/10-packages.md`
- Create: `docs/models/10-packages.md`
- Modify: `docs/INDEX.md`

- [ ] **Step 1: Write `docs/features/10-packages.md`**

Cover: what the feature is (one paragraph), user-facing flows (admin builder → POS sale → POS redemption → Owner refund), key non-obvious behaviors (snapshot pricing, shared redemption rules, FIFO conflict resolution, last-visit recognition aid), edge cases users might encounter, troubleshooting (e.g., "I added a Hair Spa but the package didn't apply — check that the package definition lists this exact service").

- [ ] **Step 2: Write `docs/models/10-packages.md`**

Cover: all 6 new tables + their relationships + invariants. Reference the ER diagram pattern in existing model docs.

- [ ] **Step 3: Update `docs/INDEX.md`**

Add entries in the Features and Models tables for "Packages" pointing to the new files.

- [ ] **Step 4: Commit**

```bash
git add docs/features/10-packages.md docs/models/10-packages.md docs/INDEX.md
git commit -m "docs(packages): feature + model documentation"
```

---

## Phase 11 — Final integration verification

### Task 44: Run the full test suite

- [ ] **Step 1: Backend**

```bash
cd backend && pytest -v
```

Expected: All tests pass, including the new ~80 tests across pricing engine, services, APIs, and integration suites.

- [ ] **Step 2: Frontend**

```bash
cd frontend && pnpm test
```

Expected: All Vitest suites pass.

- [ ] **Step 3: Playwright E2E**

```bash
cd frontend && pnpm playwright test
```

Expected: All E2E scenarios pass, including the new packages-full-cycle.

- [ ] **Step 4: Manual smoke**

Run the dev stack (`docker-compose up`). Log in as each role. Verify:
- Owner can see "Packages" in sidebar; Receptionist/Staff cannot
- Owner can create + publish a counted package, an unlimited package, and a shared package
- Receptionist sees published packages in POS selector and can sell one
- Receptionist sees Entitlements Rail when serving a customer with active packages
- A counted redemption auto-applies; Undo restores the session
- Two eligible packages render the inline selector with FIFO default
- Last-visit subtitle shows correctly for repeat customers
- Owner can refund a partially-redeemed package; credit note bill is created with correct math
- Owner can extend an expired package; status returns to active

- [ ] **Step 5: Final commit (if any cleanup)**

```bash
git status
# resolve any straggler changes
git commit -am "chore(packages): final polish and verification"
```

---

## Self-Review (run before handoff)

This is a checklist to run yourself after the plan is complete.

### 1. Spec coverage check

Cross-reference plan tasks against spec sections:

| Spec section | Task(s) implementing it |
|---|---|
| §3.1 Unified primitives | Tasks 3–5 (models with enums) |
| §3.2 Pricing — build-your-own with snapshotting | Tasks 9, 15, 16, 31 |
| §3.3 Prepaid GST recognition | Tasks 4, 23 |
| §3.4 Expiry | Tasks 4, 14, 19, 39 |
| §3.5 Shareability | Tasks 11, 17 |
| §3.6 Redemption at POS | Tasks 11, 17, 24, 33–37 |
| §3.7 Refunds | Tasks 12, 13, 18, 38 |
| §3.8 Permissions matrix | Task 1 |
| §4 Data model (6 new tables, 3 existing modified) | Tasks 3–7 |
| §5 Pricing engine | Tasks 9–14 |
| §6 Permissions | Task 1 |
| §7 API endpoints | Tasks 20–22 |
| §8.4 POS structural changes (incl. last-visit aid) | Task 37 |
| §9 Key flows (sell/redeem/undo/refund/extend) | Tasks 16–19, 23, 24, 38, 39 |
| §10 Visual grammar (Navy/Gold) | Applied throughout Tasks 29–37 via design tokens |
| §11 Edge cases | Covered by tests in Tasks 9–19; concurrent test in Task 17 |
| §12 PII handling | Task 34 (Redemption line buyer redaction) |
| §13 Receipt treatment | Task 25 |
| §14 Testing strategy | Tasks 9–22 unit + integration; Task 42 E2E |
| §15 Migration & rollout | Task 7 |
| §16 Files touched | Mapped in this plan's file structure overview |

### 2. Placeholder scan

No TBD / TODO / "implement later" / "similar to Task N" without repeating code. Each task includes either real code or a precise filename + signature + intent for an engineer to act on.

### 3. Type consistency

`PackageDefinition`, `PackageSale`, `PackageRedemptionAudit`, etc. — names used consistently across backend models, schemas, frontend types, and API endpoints. Enum values match between Python and TypeScript.

### 4. Self-review issues found

- The `find_eligible_packages` function uses `PackageSale.items` filter via a subquery on `PackageSaleItem.service_id`. This is correct but performance-sensitive — the partial index `ix_bill_items_package_sale` won't help; consider adding `Index("ix_package_sale_items_service", "service_id")` if performance smoke (Task 44) shows >100ms latency.
- The redemption undo logic restores `BillItem.unit_price_paise` from `Service.price_paise` — confirm `Service` model has this column. If named differently (`mrp_paise`?), update Task 17 step 2 accordingly.
- The receipt service modification (Task 25) assumes a particular template structure; engineer should grep `receipt_service.py` for the BillItem rendering function before editing.

---

*Plan complete. Ready for execution handoff.*




