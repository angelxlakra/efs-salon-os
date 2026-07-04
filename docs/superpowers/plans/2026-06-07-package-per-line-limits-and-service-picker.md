# Package Per-Line Limits & Service Picker Fix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add per-line redemption caps to package definitions (e.g. "12-session pass, max 3 Facials, max 2 Hair Spas, Haircut/Wash unlimited within the global pool") AND fix the broken Package Builder service input so users pick real services from a searchable dropdown instead of typing free text that submits the typed string as the `service_id`.

**Architecture:**

1. **Backend:** Add `max_redemptions INTEGER NULL` to `package_definition_items` (cap) and both `max_redemptions INTEGER NULL` + `remaining INTEGER NULL` to `package_sale_items` (snapshotted cap + runtime counter). Eligibility query filters on `remaining > 0 OR max_redemptions IS NULL`. `apply_redemption` decrements the per-line `remaining` alongside the global `sessions_remaining`; `undo_redemption` restores both.
2. **Frontend:** Build a new `ServicePicker` component wrapping the existing V2 `Combobox` primitive, backed by a `useServicesList()` hook that GETs `/catalog/services` once and caches. Replace the plain `<input>` in `PackageBuilderServicesTable` with `ServicePicker` and add a per-line "Limit" input. Hydrate `service_name` and `max_redemptions` on the Edit page so existing definitions round-trip cleanly.

**Tech Stack:**
- Backend: FastAPI 0.115, SQLAlchemy 2.0, Alembic, Pydantic v2, pytest
- Frontend: Next.js 16, React 19, TypeScript, shadcn/ui Combobox (cmdk 1.1), Vitest + Testing Library
- Migration alembic head at plan-write time: `edc2fc235e3b`

---

## File Structure

**New files**

- `backend/alembic/versions/m6n7o8p9q0r1_add_package_item_max_redemptions.py` — migration adding the 3 new nullable columns + 2 CHECK constraints
- `frontend/src/lib/api/services.ts` — typed wrapper around `/catalog/services` list endpoint
- `frontend/src/hooks/useServicesList.ts` — React hook that fetches and caches the active services list
- `frontend/src/components/packages/ServicePicker.tsx` — Combobox-based picker that returns `{service_id, service_name}`
- `frontend/src/components/packages/__tests__/ServicePicker.test.tsx`
- `frontend/src/components/packages/__tests__/PackageBuilderServicesTable.test.tsx`

**Modified files**

- `backend/app/models/package.py:78-103, 188-223` — add `max_redemptions` column to `PackageDefinitionItem`, add `max_redemptions`+`remaining` to `PackageSaleItem`, add CHECK constraints
- `backend/app/schemas/package.py:16-22, 54-63, 84-94` — add `max_redemptions` to create/response schemas for definition items + sale items
- `backend/app/services/package_catalog_service.py:32-43` — pass `max_redemptions` through `_build_items`
- `backend/app/services/package_sales_service.py:58-69` — snapshot `max_redemptions` into `PackageSaleItem`, initialise `remaining`
- `backend/app/services/package_eligibility.py:41-64` — filter eligibility on `(max_redemptions IS NULL OR remaining > 0)`
- `backend/app/services/package_redemption_service.py:53-77, 138-152` — enforce + decrement per-line `remaining` on apply, restore on undo
- `frontend/src/types/package.ts:9-17, 51-59` — add `max_redemptions?: number | null` and (for sale items) `remaining?: number | null`
- `frontend/src/components/packages/PackageBuilderServicesTable.tsx:1-175` — replace plain `<input>` with `ServicePicker`, add per-line Limit input, update grid template
- `frontend/src/components/packages/PackageBuilder.tsx:56-101` — hydrate `service_name` + `max_redemptions` from `initial`, pass `max_redemptions` to payload, drop the `it.service_id || it.service_name` fallback

**Test files**

- `backend/tests/unit/models/test_package_models.py` (extend)
- `backend/tests/unit/schemas/test_package_schemas.py` (extend)
- `backend/tests/integration/test_package_sales_service.py` (extend)
- `backend/tests/integration/test_package_eligibility.py` (extend)
- `backend/tests/integration/test_package_redemption.py` (extend)
- `backend/tests/conftest.py:422-461, 470-560` — extend factories to accept `max_redemptions`

---

## Task Sequencing Logic

Backend-first, bottom-up:
- Tasks 1–3 land the schema substrate (migration → model → Pydantic) and are independently committable.
- Tasks 4–7 thread `max_redemptions` through the four backend services (catalog write, sales snapshot, eligibility read, redemption write).
- Tasks 8–9 wire the frontend data layer (services API client + hook).
- Task 10 builds `ServicePicker` standalone with tests.
- Tasks 11–12 swap the builder UI over.
- Task 13 verifies end-to-end with both example schemes from the spec.

Every task has at least one failing test written before the implementation. Every task ends with a commit.

---

## Task 1: Alembic migration — add columns + constraints

**Files:**
- Create: `backend/alembic/versions/m6n7o8p9q0r1_add_package_item_max_redemptions.py`

- [ ] **Step 1: Generate the migration file with hand-written content** (do NOT use `--autogenerate`; we want explicit control over the down_revision and the CHECK constraints).

Create `backend/alembic/versions/m6n7o8p9q0r1_add_package_item_max_redemptions.py`:

```python
"""Add max_redemptions to package items and remaining to package_sale_items.

Revision ID: m6n7o8p9q0r1
Revises: edc2fc235e3b
Create Date: 2026-06-07

Adds per-line redemption caps to package definitions:
  - package_definition_items.max_redemptions  (nullable, the cap)
  - package_sale_items.max_redemptions        (snapshot of the cap at sale)
  - package_sale_items.remaining              (runtime counter; null = uncapped)

null on max_redemptions means "no per-line cap; this line draws from the
global sessions_remaining pool only."
"""

from alembic import op
import sqlalchemy as sa

revision = "m6n7o8p9q0r1"
down_revision = "edc2fc235e3b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "package_definition_items",
        sa.Column("max_redemptions", sa.Integer(), nullable=True),
    )
    op.create_check_constraint(
        "ck_package_def_item_max_redemptions_positive",
        "package_definition_items",
        "max_redemptions IS NULL OR max_redemptions >= 1",
    )

    op.add_column(
        "package_sale_items",
        sa.Column("max_redemptions", sa.Integer(), nullable=True),
    )
    op.add_column(
        "package_sale_items",
        sa.Column("remaining", sa.Integer(), nullable=True),
    )
    op.create_check_constraint(
        "ck_package_sale_item_max_redemptions_positive",
        "package_sale_items",
        "max_redemptions IS NULL OR max_redemptions >= 1",
    )
    op.create_check_constraint(
        "ck_package_sale_item_remaining_non_negative",
        "package_sale_items",
        "remaining IS NULL OR remaining >= 0",
    )
    op.create_check_constraint(
        "ck_package_sale_item_remaining_matches_cap",
        "package_sale_items",
        "(max_redemptions IS NULL AND remaining IS NULL) "
        "OR (max_redemptions IS NOT NULL AND remaining IS NOT NULL)",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_package_sale_item_remaining_matches_cap",
        "package_sale_items",
        type_="check",
    )
    op.drop_constraint(
        "ck_package_sale_item_remaining_non_negative",
        "package_sale_items",
        type_="check",
    )
    op.drop_constraint(
        "ck_package_sale_item_max_redemptions_positive",
        "package_sale_items",
        type_="check",
    )
    op.drop_column("package_sale_items", "remaining")
    op.drop_column("package_sale_items", "max_redemptions")
    op.drop_constraint(
        "ck_package_def_item_max_redemptions_positive",
        "package_definition_items",
        type_="check",
    )
    op.drop_column("package_definition_items", "max_redemptions")
```

- [ ] **Step 2: Run the migration and confirm head moved**

Run:
```bash
cd backend && uv run alembic upgrade head
uv run alembic heads
```

Expected: `m6n7o8p9q0r1 (head)`

- [ ] **Step 3: Round-trip downgrade then upgrade to confirm reversibility**

Run:
```bash
cd backend && uv run alembic downgrade -1
uv run alembic current
uv run alembic upgrade head
uv run alembic current
```

Expected: downgrade lands on `edc2fc235e3b`, upgrade returns to `m6n7o8p9q0r1`. No exceptions.

- [ ] **Step 4: Commit**

```bash
git add backend/alembic/versions/m6n7o8p9q0r1_add_package_item_max_redemptions.py
git commit -m "feat(packages-db): add max_redemptions per-line cap columns"
```

---

## Task 2: Model changes — `PackageDefinitionItem` + `PackageSaleItem`

**Files:**
- Modify: `backend/app/models/package.py:78-103, 188-223`
- Test: `backend/tests/unit/models/test_package_models.py`

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/unit/models/test_package_models.py`:

```python
def test_package_definition_item_max_redemptions_defaults_null(db_session, test_user):
    """A definition item without max_redemptions stores NULL."""
    from app.models.package import (
        PackageDefinition, PackageDefinitionItem, EntitlementType, Shareability,
        PackageDefinitionStatus,
    )
    from decimal import Decimal
    pkg = PackageDefinition(
        name="t", status=PackageDefinitionStatus.DRAFT,
        entitlement_type=EntitlementType.COUNTED, total_sessions=5,
        shareability=Shareability.OWNER_ONLY, validity_days=30,
        auto_apply=True, cancellation_fee_pct=Decimal("20.00"),
        created_by_user_id=test_user.id,
    )
    db_session.add(pkg)
    db_session.flush()
    item = PackageDefinitionItem(
        package_definition_id=pkg.id,
        service_id="01HXYZ0000000000000000ABCD",
        quantity=1, unit_price_paise=10000, locked=False, display_order=0,
    )
    db_session.add(item)
    db_session.flush()
    assert item.max_redemptions is None


def test_package_definition_item_max_redemptions_rejects_zero(db_session, test_user):
    """The CHECK constraint rejects max_redemptions=0."""
    from sqlalchemy.exc import IntegrityError
    from app.models.package import (
        PackageDefinition, PackageDefinitionItem, EntitlementType, Shareability,
        PackageDefinitionStatus,
    )
    from decimal import Decimal
    pkg = PackageDefinition(
        name="t", status=PackageDefinitionStatus.DRAFT,
        entitlement_type=EntitlementType.COUNTED, total_sessions=5,
        shareability=Shareability.OWNER_ONLY, validity_days=30,
        auto_apply=True, cancellation_fee_pct=Decimal("20.00"),
        created_by_user_id=test_user.id,
    )
    db_session.add(pkg)
    db_session.flush()
    item = PackageDefinitionItem(
        package_definition_id=pkg.id,
        service_id="01HXYZ0000000000000000ABCD",
        quantity=1, unit_price_paise=10000, locked=False, display_order=0,
        max_redemptions=0,
    )
    db_session.add(item)
    with pytest.raises(IntegrityError):
        db_session.flush()
    db_session.rollback()


def test_package_sale_item_remaining_must_match_cap_presence(db_session):
    """remaining must be NULL iff max_redemptions is NULL."""
    from sqlalchemy.exc import IntegrityError
    from app.models.package import PackageSaleItem
    from decimal import Decimal
    # Stand-alone insert — we don't need a parent sale for this constraint check.
    bad = PackageSaleItem(
        package_sale_id="01HXXXXXXXXXXXXXXXXXXXXXXX",
        package_definition_item_id="01HXXXXXXXXXXXXXXXXXXXXXXY",
        service_id="01HXXXXXXXXXXXXXXXXXXXXXXZ",
        quantity=1, snapshot_unit_price_paise=10000,
        snapshot_gst_rate_pct=Decimal("0"), locked=False, display_order=0,
        max_redemptions=3, remaining=None,
    )
    db_session.add(bad)
    with pytest.raises(IntegrityError):
        db_session.flush()
    db_session.rollback()
```

Make sure the existing import block at the top of the file already imports `pytest`. If not, add `import pytest` at the top.

- [ ] **Step 2: Run tests to confirm they fail with the expected reason**

Run:
```bash
cd backend && uv run pytest tests/unit/models/test_package_models.py::test_package_definition_item_max_redemptions_defaults_null tests/unit/models/test_package_models.py::test_package_definition_item_max_redemptions_rejects_zero tests/unit/models/test_package_models.py::test_package_sale_item_remaining_must_match_cap_presence -v
```
Expected: all three FAIL with `AttributeError: 'PackageDefinitionItem' object has no attribute 'max_redemptions'` (or similar).

- [ ] **Step 3: Implement model columns**

Edit `backend/app/models/package.py`. In the `PackageDefinitionItem` class (currently lines 78–103), add the new column right after `display_order` (line 90) and a CHECK constraint:

```python
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
    max_redemptions = Column(Integer, nullable=True)  # null = no per-line cap

    definition = relationship("PackageDefinition", back_populates="items")
    service = relationship("Service")

    @property
    def service_name(self) -> str | None:
        return self.service.name if self.service else None

    __table_args__ = (
        CheckConstraint("quantity >= 1", name="ck_package_def_item_qty_positive"),
        CheckConstraint("unit_price_paise >= 0", name="ck_package_def_item_price_non_negative"),
        CheckConstraint(
            "max_redemptions IS NULL OR max_redemptions >= 1",
            name="ck_package_def_item_max_redemptions_positive",
        ),
    )
```

In the `PackageSaleItem` class (currently lines 188–223), add the two columns after `display_order` (line 207) and the matching CHECK constraints:

```python
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
    max_redemptions = Column(Integer, nullable=True)  # null = no per-line cap
    remaining = Column(Integer, nullable=True)        # null iff max_redemptions is null

    sale = relationship("PackageSale", back_populates="items")
    service = relationship("Service")

    @property
    def service_name(self) -> str | None:
        return self.service.name if self.service else None

    __table_args__ = (
        CheckConstraint("quantity >= 1", name="ck_package_sale_item_qty_positive"),
        CheckConstraint("snapshot_unit_price_paise >= 0", name="ck_package_sale_item_price_non_negative"),
        CheckConstraint(
            "max_redemptions IS NULL OR max_redemptions >= 1",
            name="ck_package_sale_item_max_redemptions_positive",
        ),
        CheckConstraint(
            "remaining IS NULL OR remaining >= 0",
            name="ck_package_sale_item_remaining_non_negative",
        ),
        CheckConstraint(
            "(max_redemptions IS NULL AND remaining IS NULL) "
            "OR (max_redemptions IS NOT NULL AND remaining IS NOT NULL)",
            name="ck_package_sale_item_remaining_matches_cap",
        ),
        Index("ix_package_sale_items_service_id_sale_id", "service_id", "package_sale_id"),
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run:
```bash
cd backend && uv run pytest tests/unit/models/test_package_models.py -v
```
Expected: PASS (all tests in the file, including the three new ones).

- [ ] **Step 5: Commit**

```bash
git add backend/app/models/package.py backend/tests/unit/models/test_package_models.py
git commit -m "feat(packages-db): model columns for per-line redemption caps"
```

---

## Task 3: Pydantic schemas — accept and serialise `max_redemptions`

**Files:**
- Modify: `backend/app/schemas/package.py:16-22, 54-63, 84-94`
- Test: `backend/tests/unit/schemas/test_package_schemas.py`

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/unit/schemas/test_package_schemas.py`:

```python
def test_definition_item_create_accepts_max_redemptions():
    item = PackageDefinitionItemCreate(
        service_id="01HXYZ0000000000000000ABCD",
        quantity=1,
        unit_price_paise=10000,
        max_redemptions=3,
    )
    assert item.max_redemptions == 3


def test_definition_item_create_defaults_max_redemptions_null():
    item = PackageDefinitionItemCreate(
        service_id="01HXYZ0000000000000000ABCD",
        quantity=1,
        unit_price_paise=10000,
    )
    assert item.max_redemptions is None


def test_definition_item_create_rejects_zero_max_redemptions():
    with pytest.raises(ValidationError):
        PackageDefinitionItemCreate(
            service_id="01HXYZ0000000000000000ABCD",
            quantity=1, unit_price_paise=10000,
            max_redemptions=0,
        )
```

- [ ] **Step 2: Run tests to verify they fail**

Run:
```bash
cd backend && uv run pytest tests/unit/schemas/test_package_schemas.py -v -k max_redemptions
```
Expected: all three FAIL — `max_redemptions` is not a known field.

- [ ] **Step 3: Implement schema fields**

In `backend/app/schemas/package.py`, modify `PackageDefinitionItemCreate` (currently lines 16–22):

```python
class PackageDefinitionItemCreate(BaseModel):
    service_id: str = Field(..., min_length=26, max_length=26)
    quantity: int = Field(default=1, ge=1)
    unit_price_paise: int = Field(..., ge=0)
    locked: bool = False
    display_order: int = 0
    max_redemptions: Optional[int] = Field(default=None, ge=1)
```

Modify `PackageDefinitionItemResponse` (currently lines 54–63):

```python
class PackageDefinitionItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    service_id: str
    service_name: Optional[str] = None
    quantity: int
    unit_price_paise: int
    locked: bool
    display_order: int
    max_redemptions: Optional[int] = None
```

Modify `PackageSaleItemResponse` (currently lines 84–94):

```python
class PackageSaleItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    service_id: str
    service_name: Optional[str] = None
    quantity: int
    snapshot_unit_price_paise: int
    snapshot_gst_rate_pct: Decimal
    locked: bool
    max_redemptions: Optional[int] = None
    remaining: Optional[int] = None
```

- [ ] **Step 4: Run tests to confirm pass**

Run:
```bash
cd backend && uv run pytest tests/unit/schemas/test_package_schemas.py -v
```
Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add backend/app/schemas/package.py backend/tests/unit/schemas/test_package_schemas.py
git commit -m "feat(packages-api): schema fields for per-line max_redemptions"
```

---

## Task 4: Catalog service — thread `max_redemptions` through create/update

**Files:**
- Modify: `backend/app/services/package_catalog_service.py:32-43`
- Test: `backend/tests/integration/test_package_catalog_service.py`

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/integration/test_package_catalog_service.py`:

```python
def test_create_definition_persists_per_line_max_redemptions(
    db_session, service_factory, test_user,
):
    """create_definition stores max_redemptions on each PackageDefinitionItem."""
    from app.schemas.package import (
        PackageDefinitionCreate, PackageDefinitionItemCreate,
    )
    from app.services.package_catalog_service import create_definition

    svc_a = service_factory(base_price=100000)
    svc_b = service_factory(base_price=50000)
    payload = PackageDefinitionCreate(
        name="Salon Royal Pass",
        entitlement_type="counted",
        total_sessions=12,
        validity_days=180,
        shareability="owner_only",
        cancellation_fee_pct="20.00",
        items=[
            PackageDefinitionItemCreate(
                service_id=svc_a.id, quantity=1, unit_price_paise=100000,
                max_redemptions=3,
            ),
            PackageDefinitionItemCreate(
                service_id=svc_b.id, quantity=1, unit_price_paise=50000,
                max_redemptions=None,
            ),
        ],
    )
    pkg = create_definition(db_session, payload, user_id=test_user.id)
    db_session.flush()
    by_svc = {it.service_id: it for it in pkg.items}
    assert by_svc[svc_a.id].max_redemptions == 3
    assert by_svc[svc_b.id].max_redemptions is None
```

- [ ] **Step 2: Run test to confirm failure**

Run:
```bash
cd backend && uv run pytest tests/integration/test_package_catalog_service.py::test_create_definition_persists_per_line_max_redemptions -v
```
Expected: FAIL — `PackageDefinitionItem` instance has `max_redemptions=None` regardless of payload (because `_build_items` ignores the field).

- [ ] **Step 3: Implement passthrough**

In `backend/app/services/package_catalog_service.py`, modify `_build_items` (currently lines 32–43):

```python
def _build_items(payload_items, item_drafts):
    """Zip payload items with discounted drafts into ORM objects."""
    return [
        PackageDefinitionItem(
            service_id=src.service_id,
            quantity=draft.quantity,
            unit_price_paise=draft.unit_price_paise,
            locked=draft.locked,
            display_order=src.display_order,
            max_redemptions=src.max_redemptions,
        )
        for src, draft in zip(payload_items, item_drafts, strict=True)
    ]
```

- [ ] **Step 4: Run tests to confirm pass**

Run:
```bash
cd backend && uv run pytest tests/integration/test_package_catalog_service.py -v
```
Expected: PASS for all tests in the file.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/package_catalog_service.py backend/tests/integration/test_package_catalog_service.py
git commit -m "feat(packages): catalog service writes max_redemptions to items"
```

---

## Task 5: Sales service — snapshot cap and initialise `remaining`

**Files:**
- Modify: `backend/app/services/package_sales_service.py:58-69`
- Test: `backend/tests/integration/test_package_sales_service.py`

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/integration/test_package_sales_service.py`:

```python
def test_create_sale_snapshots_max_redemptions_and_initialises_remaining(
    db_session, service_factory, customer_factory, test_user,
):
    """When a PackageDefinitionItem has max_redemptions, the snapshot
    PackageSaleItem stores max_redemptions and remaining = max_redemptions.
    For items without a cap, both columns stay null."""
    from app.models.billing import Bill, BillStatus, BillType
    from app.models.package import (
        PackageDefinition, PackageDefinitionItem, PackageDefinitionStatus,
        EntitlementType, Shareability,
    )
    from app.services.package_sales_service import create_sale
    from decimal import Decimal

    svc_a = service_factory(base_price=100000)
    svc_b = service_factory(base_price=50000)
    customer = customer_factory()

    pkg = PackageDefinition(
        name="Royal", status=PackageDefinitionStatus.PUBLISHED,
        entitlement_type=EntitlementType.COUNTED, total_sessions=12,
        shareability=Shareability.OWNER_ONLY, validity_days=180,
        auto_apply=True, cancellation_fee_pct=Decimal("20.00"),
        created_by_user_id=test_user.id,
    )
    pkg.items = [
        PackageDefinitionItem(
            service_id=svc_a.id, quantity=1, unit_price_paise=100000,
            locked=False, display_order=0, max_redemptions=3,
        ),
        PackageDefinitionItem(
            service_id=svc_b.id, quantity=1, unit_price_paise=50000,
            locked=False, display_order=1, max_redemptions=None,
        ),
    ]
    db_session.add(pkg)
    db_session.flush()

    bill = Bill(
        customer_id=customer.id, subtotal=150000, discount_amount=0,
        tax_amount=27000, cgst_amount=13500, sgst_amount=13500,
        total_amount=177000, rounded_total=177000, rounding_adjustment=0,
        status=BillStatus.POSTED, bill_type=BillType.NORMAL,
        created_by=test_user.id,
    )
    db_session.add(bill)
    db_session.flush()

    sale = create_sale(
        db_session, package_definition_id=pkg.id, bill_id=bill.id,
        customer_id=customer.id, selling_staff_id=None,
    )
    by_svc = {it.service_id: it for it in sale.items}
    assert by_svc[svc_a.id].max_redemptions == 3
    assert by_svc[svc_a.id].remaining == 3
    assert by_svc[svc_b.id].max_redemptions is None
    assert by_svc[svc_b.id].remaining is None
```

- [ ] **Step 2: Run test to confirm failure**

Run:
```bash
cd backend && uv run pytest tests/integration/test_package_sales_service.py::test_create_sale_snapshots_max_redemptions_and_initialises_remaining -v
```
Expected: FAIL — both columns are null on the new sale item because `create_sale` doesn't copy them.

- [ ] **Step 3: Implement snapshot copy**

In `backend/app/services/package_sales_service.py`, modify the loop body (currently lines 58–69):

```python
    for def_item in pkg.items:
        item = PackageSaleItem(
            package_sale_id=sale.id,
            package_definition_item_id=def_item.id,
            service_id=def_item.service_id,
            quantity=def_item.quantity,
            snapshot_unit_price_paise=def_item.unit_price_paise,
            snapshot_gst_rate_pct=Decimal("0"),
            locked=def_item.locked,
            display_order=def_item.display_order,
            max_redemptions=def_item.max_redemptions,
            remaining=def_item.max_redemptions,  # initial counter == cap; null if uncapped
        )
        db.add(item)
```

- [ ] **Step 4: Run tests to confirm pass**

Run:
```bash
cd backend && uv run pytest tests/integration/test_package_sales_service.py -v
```
Expected: PASS for all tests in the file.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/package_sales_service.py backend/tests/integration/test_package_sales_service.py
git commit -m "feat(packages): snapshot max_redemptions and seed remaining at sale time"
```

---

## Task 6: Eligibility query — filter out per-line-exhausted lines

**Files:**
- Modify: `backend/app/services/package_eligibility.py:41-64`
- Test: `backend/tests/integration/test_package_eligibility.py`

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/integration/test_package_eligibility.py`:

```python
def test_find_eligible_packages_excludes_per_line_exhausted(
    db_session, service_factory, customer_factory, package_sale_factory,
):
    """A sale whose PackageSaleItem.remaining = 0 for the requested service
    is NOT returned by find_eligible_packages, even when sessions_remaining > 0
    on the parent sale."""
    from app.services.package_eligibility import find_eligible_packages
    from app.models.package import PackageSaleItem

    svc = service_factory(base_price=100000)
    customer = customer_factory()
    sale = package_sale_factory(
        customer=customer, services=[svc],
        sessions_remaining=8, total_sessions_snapshot=10,
    )
    # Manually exhaust the per-line cap on the matching item
    sale_item = db_session.query(PackageSaleItem).filter_by(
        package_sale_id=sale.id, service_id=svc.id,
    ).one()
    sale_item.max_redemptions = 2
    sale_item.remaining = 0
    db_session.flush()

    results = find_eligible_packages(customer.id, svc.id, db_session)
    assert results == []


def test_find_eligible_packages_includes_uncapped_lines(
    db_session, service_factory, customer_factory, package_sale_factory,
):
    """Lines with max_redemptions=NULL stay eligible regardless."""
    from app.services.package_eligibility import find_eligible_packages
    svc = service_factory(base_price=100000)
    customer = customer_factory()
    sale = package_sale_factory(
        customer=customer, services=[svc],
        sessions_remaining=5, total_sessions_snapshot=10,
    )
    # Default fixture creates items with max_redemptions=NULL — assert no regression
    results = find_eligible_packages(customer.id, svc.id, db_session)
    assert len(results) == 1
    assert results[0].id == sale.id
```

- [ ] **Step 2: Run tests to confirm failure**

Run:
```bash
cd backend && uv run pytest tests/integration/test_package_eligibility.py::test_find_eligible_packages_excludes_per_line_exhausted tests/integration/test_package_eligibility.py::test_find_eligible_packages_includes_uncapped_lines -v
```
Expected: `test_find_eligible_packages_excludes_per_line_exhausted` FAILS (sale still returned because nothing filters on `remaining`). `test_find_eligible_packages_includes_uncapped_lines` should already PASS (regression guard).

- [ ] **Step 3: Implement filter**

In `backend/app/services/package_eligibility.py`, modify the subquery inside `find_eligible_packages` (currently lines 41–64):

```python
    return (
        db.query(PackageSale)
          .filter(and_(
              PackageSale.status == PackageSaleStatus.ACTIVE,
              PackageSale.expires_at > now,
              PackageSale.id.in_(
                  db.query(PackageSaleItem.package_sale_id)
                    .filter(
                        PackageSaleItem.service_id == service_id,
                        or_(
                            PackageSaleItem.max_redemptions.is_(None),
                            PackageSaleItem.remaining > 0,
                        ),
                    )
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
          ))
          .order_by(PackageSale.expires_at.asc())
          .all()
    )
```

- [ ] **Step 4: Run tests to confirm pass**

Run:
```bash
cd backend && uv run pytest tests/integration/test_package_eligibility.py -v
```
Expected: PASS for all tests in the file.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/package_eligibility.py backend/tests/integration/test_package_eligibility.py
git commit -m "feat(packages): eligibility filters per-line-exhausted sale items"
```

---

## Task 7: Redemption service — enforce + decrement per-line `remaining`

**Files:**
- Modify: `backend/app/services/package_redemption_service.py:53-77, 138-152`
- Test: `backend/tests/integration/test_package_redemption.py`

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/integration/test_package_redemption.py`:

```python
def test_apply_decrements_per_line_remaining(
    db_session, service_factory, customer_factory, package_sale_factory,
    bill_item_factory, user_factory,
):
    """apply_redemption decrements both sessions_remaining AND
    PackageSaleItem.remaining when a per-line cap is set."""
    from app.services.package_redemption_service import apply_redemption
    from app.models.package import PackageSaleItem
    svc = service_factory(base_price=100000)
    customer = customer_factory()
    sale = package_sale_factory(
        customer=customer, services=[svc],
        sessions_remaining=5, total_sessions_snapshot=5,
    )
    sale_item = db_session.query(PackageSaleItem).filter_by(
        package_sale_id=sale.id, service_id=svc.id,
    ).one()
    sale_item.max_redemptions = 2
    sale_item.remaining = 2
    db_session.flush()
    bi = bill_item_factory(service_id=svc.id, base_price=100000)
    user = user_factory()

    apply_redemption(
        db_session, sale.id, bi.id,
        redeemed_for_customer_id=customer.id, user_id=user.id,
    )
    db_session.refresh(sale)
    db_session.refresh(sale_item)
    assert sale.sessions_remaining == 4
    assert sale_item.remaining == 1


def test_apply_rejects_when_per_line_remaining_is_zero(
    db_session, service_factory, customer_factory, package_sale_factory,
    bill_item_factory, user_factory,
):
    """apply_redemption raises when per-line remaining hit 0, even with
    global sessions_remaining > 0."""
    import pytest
    from app.services.package_redemption_service import apply_redemption
    from app.models.package import PackageSaleItem
    svc = service_factory(base_price=100000)
    customer = customer_factory()
    sale = package_sale_factory(
        customer=customer, services=[svc],
        sessions_remaining=5, total_sessions_snapshot=5,
    )
    sale_item = db_session.query(PackageSaleItem).filter_by(
        package_sale_id=sale.id, service_id=svc.id,
    ).one()
    sale_item.max_redemptions = 2
    sale_item.remaining = 0
    db_session.flush()
    bi = bill_item_factory(service_id=svc.id, base_price=100000)
    user = user_factory()

    with pytest.raises(ValueError, match="per-line limit"):
        apply_redemption(
            db_session, sale.id, bi.id,
            redeemed_for_customer_id=customer.id, user_id=user.id,
        )


def test_undo_restores_per_line_remaining(
    db_session, service_factory, customer_factory, package_sale_factory,
    bill_item_factory, user_factory,
):
    """undo_redemption increments PackageSaleItem.remaining back when
    the original apply had decremented it."""
    from app.services.package_redemption_service import apply_redemption, undo_redemption
    from app.models.package import PackageSaleItem, PackageRedemptionAudit
    from app.models.billing import Bill, BillStatus
    svc = service_factory(base_price=100000)
    customer = customer_factory()
    sale = package_sale_factory(
        customer=customer, services=[svc],
        sessions_remaining=5, total_sessions_snapshot=5,
    )
    sale_item = db_session.query(PackageSaleItem).filter_by(
        package_sale_id=sale.id, service_id=svc.id,
    ).one()
    sale_item.max_redemptions = 2
    sale_item.remaining = 2
    db_session.flush()
    bi = bill_item_factory(service_id=svc.id, base_price=100000)
    # Force its bill to DRAFT so undo is allowed
    bill = db_session.get(Bill, bi.bill_id)
    bill.status = BillStatus.DRAFT
    db_session.flush()
    user = user_factory()
    audit = apply_redemption(
        db_session, sale.id, bi.id,
        redeemed_for_customer_id=customer.id, user_id=user.id,
    )
    db_session.refresh(sale_item)
    assert sale_item.remaining == 1

    undo_redemption(db_session, audit.id, user_id=user.id)
    db_session.refresh(sale_item)
    assert sale_item.remaining == 2
```

- [ ] **Step 2: Run tests to confirm failure**

Run:
```bash
cd backend && uv run pytest tests/integration/test_package_redemption.py::test_apply_decrements_per_line_remaining tests/integration/test_package_redemption.py::test_apply_rejects_when_per_line_remaining_is_zero tests/integration/test_package_redemption.py::test_undo_restores_per_line_remaining -v
```
Expected: all three FAIL — `remaining` stays unchanged because the service doesn't touch it.

- [ ] **Step 3: Implement the per-line enforcement and counter updates**

In `backend/app/services/package_redemption_service.py`:

**3a.** In `apply_redemption`, after the line `if not sale_item: raise ValueError("Service not covered by this package")` (currently around line 59), add a per-line cap check. Then in the COUNTED-decrement block (currently lines 70–76) also decrement `sale_item.remaining`. The full updated block (replacing lines 53–77):

```python
    # Match by service_id to find the PackageSaleItem
    sale_item = next(
        (i for i in sale.items if i.service_id == bill_item.service_id),
        None,
    )
    if not sale_item:
        raise ValueError("Service not covered by this package")

    # Per-line cap check (independent of global sessions_remaining)
    if sale_item.max_redemptions is not None and (sale_item.remaining or 0) <= 0:
        raise ValueError("per-line limit reached for this service")

    # Update BillItem — set price to the snapshotted package price
    bill_item.item_type = BillItemType.PACKAGE_REDEMPTION
    bill_item.package_sale_id = sale.id
    bill_item.package_sale_item_id = sale_item.id
    bill_item.base_price = sale_item.snapshot_unit_price_paise
    bill_item.line_total = bill_item.base_price * bill_item.quantity

    # Decrement sessions (COUNTED only) and per-line remaining (if capped)
    session_number = None
    if sale.entitlement_type_snapshot == EntitlementType.COUNTED:
        session_number = (
            (sale.total_sessions_snapshot or 0) - (sale.sessions_remaining or 0) + 1
        )
        sale.sessions_remaining -= 1
        if sale.sessions_remaining == 0:
            sale.status = PackageSaleStatus.EXHAUSTED
    if sale_item.max_redemptions is not None:
        sale_item.remaining -= 1
```

**3b.** In `undo_redemption`, after the existing `sale.sessions_remaining` restore block (currently lines 148–152), also restore `sale_item.remaining`. The full updated block (replacing lines 138–172):

```python
    # Restore BillItem to original service price
    from app.models.service import Service  # local import avoids circular dependency
    svc = db.get(Service, bill_item.service_id)
    original_price = svc.base_price if svc else bill_item.base_price
    bill_item.item_type = BillItemType.SERVICE
    bill_item.package_sale_id = None
    bill_item.package_sale_item_id = None
    bill_item.base_price = original_price
    bill_item.line_total = original_price * bill_item.quantity

    # Restore session counter
    if sale.entitlement_type_snapshot == EntitlementType.COUNTED:
        sale.sessions_remaining = (sale.sessions_remaining or 0) + 1
        if sale.status == PackageSaleStatus.EXHAUSTED:
            sale.status = PackageSaleStatus.ACTIVE

    # Restore per-line remaining (if the original apply had a per-line cap)
    sale_item = db.get(__import__("app.models.package", fromlist=["PackageSaleItem"]).PackageSaleItem,
                       audit.package_sale_item_id)
    if sale_item is not None and sale_item.max_redemptions is not None:
        sale_item.remaining = (sale_item.remaining or 0) + 1

    # NOTE: Payment is matched by (bill_id, payment_method, amount). This triple is not
    # unique if two redemptions of equal value occur on the same bill. A future migration
    # should add payment_id to PackageRedemptionAudit to make the lookup exact.
    internal_pay = db.execute(
        select(Payment).where(
            Payment.bill_id == bill.id,
            Payment.payment_method == PaymentMethod.PACKAGE_REDEMPTION,
            Payment.amount == expected_payment_amount,
        )
    ).scalar_one_or_none()
    if internal_pay is None:
        raise ValueError(
            "Internal PACKAGE_REDEMPTION payment row not found — data integrity problem. "
            "Undo aborted to avoid partial state."
        )
    db.delete(internal_pay)

    db.delete(audit)
    db.flush()
```

The `__import__` form avoids adding a new top-level import (which would require diffing the import block). If the reviewer prefers a cleaner top-level import, replace with `from app.models.package import PackageSaleItem` at the module top and use `db.get(PackageSaleItem, audit.package_sale_item_id)`.

- [ ] **Step 4: Run tests to confirm pass**

Run:
```bash
cd backend && uv run pytest tests/integration/test_package_redemption.py -v
```
Expected: PASS for all tests in the file (the three new ones + all existing).

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/package_redemption_service.py backend/tests/integration/test_package_redemption.py
git commit -m "feat(packages): enforce + track per-line redemption limits"
```

---

## Task 8: Frontend types — extend `PackageDefinitionItem` and `PackageSaleItem`

**Files:**
- Modify: `frontend/src/types/package.ts:9-17, 51-59, 35-46`

- [ ] **Step 1: Edit types**

In `frontend/src/types/package.ts`, modify the three interfaces:

```typescript
export interface PackageDefinitionItem {
  id: string;
  service_id: string;
  service_name?: string;
  quantity: number;
  unit_price_paise: number;
  locked: boolean;
  display_order: number;
  max_redemptions?: number | null;
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
  max_redemptions?: number | null;
  remaining?: number | null;
}
```

- [ ] **Step 2: Type-check**

Run:
```bash
cd frontend && PATH="/Users/angelxlakra/.nvm/versions/node/v22.20.0/bin:$PATH" npx tsc --noEmit
```
Expected: no NEW type errors (the existing 162 pre-existing errors from the V2 Phase 0 work are unrelated and should not increase).

- [ ] **Step 3: Commit**

```bash
git add frontend/src/types/package.ts
git commit -m "feat(packages-fe): types for per-line max_redemptions + remaining"
```

---

## Task 9: Services list API client + cache hook

**Files:**
- Create: `frontend/src/lib/api/services.ts`
- Create: `frontend/src/hooks/useServicesList.ts`

- [ ] **Step 1: Create the typed API client**

Create `frontend/src/lib/api/services.ts`:

```typescript
import { apiClient } from "@/lib/api/client";

export interface ServiceListItem {
  id: string;
  name: string;
  base_price: number;
  is_active: boolean;
  category_id: string | null;
  display_order: number;
}

interface ServiceListResponse {
  services: ServiceListItem[];
  total: number;
}

export const servicesApi = {
  list: () =>
    apiClient.get<ServiceListResponse>("/catalog/services", {
      params: { sort_by: "display_order" },
    }),
};
```

Note: the apiClient path/method may differ slightly — confirm by reading [packages.ts](frontend/src/lib/api/packages.ts) for the existing import convention. If `apiClient` is exported from a different module, use the same import line as that file.

- [ ] **Step 2: Create the hook**

Create `frontend/src/hooks/useServicesList.ts`:

```typescript
"use client";
import { useEffect, useState } from "react";
import { servicesApi, type ServiceListItem } from "@/lib/api/services";

export interface UseServicesListResult {
  services: ServiceListItem[];
  loading: boolean;
  error: string | null;
}

let cache: ServiceListItem[] | null = null;
let inflight: Promise<ServiceListItem[]> | null = null;

async function fetchOnce(): Promise<ServiceListItem[]> {
  if (cache) return cache;
  if (!inflight) {
    inflight = servicesApi.list().then((res) => {
      cache = res.data.services;
      inflight = null;
      return cache;
    });
  }
  return inflight;
}

export function useServicesList(): UseServicesListResult {
  const [services, setServices] = useState<ServiceListItem[]>(cache ?? []);
  const [loading, setLoading] = useState<boolean>(cache === null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    if (cache) return;
    fetchOnce()
      .then((list) => {
        if (active) {
          setServices(list);
          setLoading(false);
        }
      })
      .catch((e) => {
        if (active) {
          setError(e?.message ?? "Failed to load services");
          setLoading(false);
        }
      });
    return () => {
      active = false;
    };
  }, []);

  return { services, loading, error };
}
```

The module-level `cache`/`inflight` deduplicates the network call across mounts. Acceptable here because the services list rarely changes mid-session; the user can refresh the page if they add a service in another tab.

- [ ] **Step 3: Type-check**

Run:
```bash
cd frontend && PATH="/Users/angelxlakra/.nvm/versions/node/v22.20.0/bin:$PATH" npx tsc --noEmit
```
Expected: no new errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/lib/api/services.ts frontend/src/hooks/useServicesList.ts
git commit -m "feat(packages-fe): services list API client with in-memory cache"
```

---

## Task 10: `ServicePicker` component

**Files:**
- Create: `frontend/src/components/packages/ServicePicker.tsx`
- Create: `frontend/src/components/packages/__tests__/ServicePicker.test.tsx`

- [ ] **Step 1: Write the failing test**

Create `frontend/src/components/packages/__tests__/ServicePicker.test.tsx`:

```tsx
import { render, screen, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi, beforeEach } from "vitest";

vi.mock("@/hooks/useServicesList", () => ({
  useServicesList: () => ({
    services: [
      { id: "01HSVC00000000000000HAIR", name: "Haircut", base_price: 50000, is_active: true, category_id: null, display_order: 0 },
      { id: "01HSVC00000000000000WASH", name: "Hair Wash", base_price: 10000, is_active: true, category_id: null, display_order: 1 },
    ],
    loading: false,
    error: null,
  }),
}));

import { ServicePicker } from "../ServicePicker";

describe("ServicePicker", () => {
  beforeEach(() => {
    // jsdom polyfills needed by the Combobox primitive
    if (!Element.prototype.scrollIntoView) {
      Element.prototype.scrollIntoView = vi.fn();
    }
    if (!(Element.prototype as { hasPointerCapture?: unknown }).hasPointerCapture) {
      (Element.prototype as { hasPointerCapture: (id: number) => boolean }).hasPointerCapture = () => false;
    }
    if (!(Element.prototype as { releasePointerCapture?: unknown }).releasePointerCapture) {
      (Element.prototype as { releasePointerCapture: (id: number) => void }).releasePointerCapture = () => {};
    }
  });

  it("renders the selected service's name in the trigger", () => {
    render(<ServicePicker value="01HSVC00000000000000HAIR" onChange={() => {}} />);
    expect(screen.getByRole("button")).toHaveTextContent("Haircut");
  });

  it("calls onChange with both id and name when an option is picked", async () => {
    const onChange = vi.fn();
    render(<ServicePicker value={null} onChange={onChange} />);
    await userEvent.click(screen.getByRole("button"));
    await userEvent.click(screen.getByText("Hair Wash"));
    expect(onChange).toHaveBeenCalledWith({
      service_id: "01HSVC00000000000000WASH",
      service_name: "Hair Wash",
    });
  });
});
```

- [ ] **Step 2: Run the test to confirm it fails**

Run:
```bash
cd frontend && PATH="/Users/angelxlakra/.nvm/versions/node/v22.20.0/bin:$PATH" npm test -- ServicePicker --run
```
Expected: FAIL — `ServicePicker` not exported.

- [ ] **Step 3: Implement the component**

Create `frontend/src/components/packages/ServicePicker.tsx`:

```tsx
"use client";
import * as React from "react";
import { Combobox, type ComboboxOption } from "@/components/ui/combobox";
import { useServicesList } from "@/hooks/useServicesList";

interface Props {
  value: string | null;
  onChange: (picked: { service_id: string; service_name: string } | null) => void;
  disabled?: boolean;
  className?: string;
}

export function ServicePicker({ value, onChange, disabled, className }: Props) {
  const { services, loading, error } = useServicesList();

  const options: ComboboxOption[] = React.useMemo(
    () =>
      services
        .filter((s) => s.is_active)
        .map((s) => ({ value: s.id, label: s.name })),
    [services]
  );

  function handleChange(next: string | null) {
    if (next === null) {
      onChange(null);
      return;
    }
    const svc = services.find((s) => s.id === next);
    if (!svc) return;
    onChange({ service_id: svc.id, service_name: svc.name });
  }

  return (
    <Combobox
      options={options}
      value={value}
      onChange={handleChange}
      placeholder={loading ? "Loading…" : error ? "Failed to load" : "Pick a service"}
      searchPlaceholder="Search services…"
      emptyMessage="No matching service."
      disabled={disabled || loading || !!error}
      className={className}
    />
  );
}
```

- [ ] **Step 4: Run tests to verify pass**

Run:
```bash
cd frontend && PATH="/Users/angelxlakra/.nvm/versions/node/v22.20.0/bin:$PATH" npm test -- ServicePicker --run
```
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/packages/ServicePicker.tsx frontend/src/components/packages/__tests__/ServicePicker.test.tsx
git commit -m "feat(packages-fe): ServicePicker component (Combobox + services hook)"
```

---

## Task 11: `PackageBuilderServicesTable` — swap in ServicePicker + add Limit input

**Files:**
- Modify: `frontend/src/components/packages/PackageBuilderServicesTable.tsx:1-175`
- Create: `frontend/src/components/packages/__tests__/PackageBuilderServicesTable.test.tsx`

- [ ] **Step 1: Write the failing test**

Create `frontend/src/components/packages/__tests__/PackageBuilderServicesTable.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi, beforeEach } from "vitest";

vi.mock("@/hooks/useServicesList", () => ({
  useServicesList: () => ({
    services: [
      { id: "01HSVC00000000000000HAIR", name: "Haircut", base_price: 50000, is_active: true, category_id: null, display_order: 0 },
    ],
    loading: false,
    error: null,
  }),
}));

import { PackageBuilderServicesTable } from "../PackageBuilderServicesTable";

beforeEach(() => {
  if (!Element.prototype.scrollIntoView) Element.prototype.scrollIntoView = vi.fn();
  if (!(Element.prototype as { hasPointerCapture?: unknown }).hasPointerCapture) {
    (Element.prototype as { hasPointerCapture: (id: number) => boolean }).hasPointerCapture = () => false;
  }
});

describe("PackageBuilderServicesTable", () => {
  it("emits onChange with service_id when a service is picked", async () => {
    const onChange = vi.fn();
    render(
      <PackageBuilderServicesTable items={[]} onChange={onChange} entitlementType="counted" />
    );
    await userEvent.click(screen.getByRole("button", { name: /add service/i }));
    // The new row's picker trigger appears
    const triggers = screen.getAllByRole("button");
    const picker = triggers.find((b) => b.textContent?.includes("Pick a service"));
    expect(picker).toBeDefined();
    await userEvent.click(picker!);
    await userEvent.click(screen.getByText("Haircut"));
    expect(onChange).toHaveBeenLastCalledWith([
      expect.objectContaining({
        service_id: "01HSVC00000000000000HAIR",
        service_name: "Haircut",
      }),
    ]);
  });

  it("emits max_redemptions when the Limit input changes", async () => {
    const onChange = vi.fn();
    render(
      <PackageBuilderServicesTable
        items={[{
          service_id: "01HSVC00000000000000HAIR",
          service_name: "Haircut",
          quantity: 1,
          unit_price_paise: 50000,
          locked: false,
          display_order: 0,
          max_redemptions: null,
        }]}
        onChange={onChange}
        entitlementType="counted"
      />
    );
    const limitInput = screen.getByLabelText(/limit/i);
    await userEvent.type(limitInput, "3");
    expect(onChange).toHaveBeenLastCalledWith([
      expect.objectContaining({ max_redemptions: 3 }),
    ]);
  });
});
```

- [ ] **Step 2: Run test to confirm it fails**

Run:
```bash
cd frontend && PATH="/Users/angelxlakra/.nvm/versions/node/v22.20.0/bin:$PATH" npm test -- PackageBuilderServicesTable --run
```
Expected: FAIL — current table has a text input, not a ServicePicker, and no Limit input.

- [ ] **Step 3: Rewrite the table component**

Replace the entire contents of `frontend/src/components/packages/PackageBuilderServicesTable.tsx` with:

```tsx
"use client";
import { Lock, Unlock, Trash2, Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { ServicePicker } from "./ServicePicker";
import type { EntitlementType } from "@/types/package";

interface LineItem {
  service_id: string;
  service_name: string;
  quantity: number;
  unit_price_paise: number;
  locked: boolean;
  display_order: number;
  max_redemptions: number | null;
}

interface Props {
  items: LineItem[];
  onChange: (items: LineItem[]) => void;
  entitlementType: EntitlementType;
}

function paise(rupees: string): number {
  return Math.round(parseFloat(rupees || "0") * 100);
}

function rupees(p: number): string {
  return (p / 100).toFixed(2);
}

const inlineInput =
  "h-7 rounded-md border border-border-default bg-surface-card px-2 text-sm text-text-primary placeholder:text-text-muted " +
  "focus-visible:outline-none focus-visible:border-accent focus-visible:shadow-[var(--shadow-focus)] " +
  "disabled:opacity-50 disabled:cursor-not-allowed w-full";

export function PackageBuilderServicesTable({ items, onChange, entitlementType }: Props) {
  const isUnlimited = entitlementType === "unlimited";

  function update(index: number, patch: Partial<LineItem>) {
    const next = items.map((item, i) => (i === index ? { ...item, ...patch } : item));
    onChange(next);
  }

  function remove(index: number) {
    onChange(items.filter((_, i) => i !== index));
  }

  function addRow() {
    onChange([
      ...items,
      {
        service_id: "",
        service_name: "",
        quantity: 1,
        unit_price_paise: 0,
        locked: false,
        display_order: items.length,
        max_redemptions: null,
      },
    ]);
  }

  const total = items.reduce(
    (s, i) => s + i.unit_price_paise * (isUnlimited ? 1 : i.quantity),
    0
  );

  // Column template: Service | Qty (counted only) | Price | Limit | Lock | Delete
  const gridCols = isUnlimited
    ? "grid-cols-[1fr_100px_72px_40px_32px]"
    : "grid-cols-[1fr_48px_100px_72px_40px_32px]";

  return (
    <div className="space-y-2">
      <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
        Included services
      </p>

      {/* Header */}
      <div
        className={cn(
          "grid gap-2 text-[10px] font-medium text-muted-foreground uppercase",
          gridCols
        )}
      >
        <span>Service</span>
        {!isUnlimited && <span className="text-center">Qty</span>}
        <span className="text-right">Price (₹)</span>
        <span className="text-center">Limit</span>
        <span className="text-center">Lock</span>
        <span />
      </div>

      {/* Rows */}
      {items.map((item, i) => (
        <div
          key={i}
          className={cn(
            "grid gap-2 items-center rounded-lg border px-2 py-1.5",
            gridCols,
            item.locked
              ? "bg-amber-50 dark:bg-amber-950/20 border-amber-200 dark:border-amber-800"
              : "border-border"
          )}
        >
          {/* Service picker */}
          <ServicePicker
            value={item.service_id || null}
            onChange={(picked) =>
              update(i, {
                service_id: picked?.service_id ?? "",
                service_name: picked?.service_name ?? "",
              })
            }
            className="h-7"
          />

          {/* Qty (hidden for unlimited) */}
          {!isUnlimited && (
            <input
              type="number"
              min={1}
              value={item.quantity}
              onChange={(e) => update(i, { quantity: parseInt(e.target.value) || 1 })}
              className={cn(inlineInput, "text-center")}
            />
          )}

          {/* Price */}
          <input
            type="number"
            step="0.01"
            min={0}
            value={rupees(item.unit_price_paise)}
            onChange={(e) => update(i, { unit_price_paise: paise(e.target.value) })}
            className={cn(inlineInput, "text-right")}
          />

          {/* Limit (per-line redemption cap; empty = no cap) */}
          <input
            aria-label={`Limit for ${item.service_name || "row " + (i + 1)}`}
            type="number"
            min={1}
            placeholder="—"
            value={item.max_redemptions ?? ""}
            onChange={(e) => {
              const raw = e.target.value.trim();
              update(i, {
                max_redemptions: raw === "" ? null : Math.max(1, parseInt(raw) || 1),
              });
            }}
            className={cn(inlineInput, "text-center")}
          />

          {/* Lock toggle */}
          <button
            type="button"
            onClick={() => update(i, { locked: !item.locked })}
            className="flex items-center justify-center h-7 w-7 rounded text-muted-foreground hover:text-foreground"
          >
            {item.locked ? <Lock size={14} /> : <Unlock size={14} />}
          </button>

          {/* Delete */}
          <button
            type="button"
            onClick={() => remove(i)}
            className="flex items-center justify-center h-7 w-7 rounded text-muted-foreground hover:text-danger-fg"
          >
            <Trash2 size={14} />
          </button>
        </div>
      ))}

      <Button type="button" variant="outline" size="sm" onClick={addRow} className="w-full">
        <Plus size={14} className="mr-1" /> Add service
      </Button>

      <div className="flex justify-between items-center pt-2 border-t border-border-subtle">
        <span className="text-sm text-muted-foreground">Package MRP</span>
        <span className="text-sm font-semibold tabular-nums">
          ₹{(total / 100).toFixed(2)}
        </span>
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Run tests to confirm pass**

Run:
```bash
cd frontend && PATH="/Users/angelxlakra/.nvm/versions/node/v22.20.0/bin:$PATH" npm test -- PackageBuilderServicesTable ServicePicker --run
```
Expected: all tests in both files PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/packages/PackageBuilderServicesTable.tsx frontend/src/components/packages/__tests__/PackageBuilderServicesTable.test.tsx
git commit -m "feat(packages-fe): ServicePicker + per-line Limit input in builder"
```

---

## Task 12: `PackageBuilder` — payload + hydration

**Files:**
- Modify: `frontend/src/components/packages/PackageBuilder.tsx:56-101`

- [ ] **Step 1: Update LineItem interface and the hydration block**

In `frontend/src/components/packages/PackageBuilder.tsx`, modify the `LineItem` interface (lines 21–28) and the `useState` initializer (lines 56–65) and the payload mapper (lines 81–101). The full updated sections:

```tsx
interface LineItem {
  service_id: string;
  service_name: string;
  quantity: number;
  unit_price_paise: number;
  locked: boolean;
  display_order: number;
  max_redemptions: number | null;
}
```

```tsx
  const [items, setItems] = useState<LineItem[]>(
    (initial?.items ?? []).map((it, i) => ({
      service_id: it.service_id,
      service_name: (it as { service_name?: string }).service_name ?? "",
      quantity: it.quantity,
      unit_price_paise: it.unit_price_paise,
      locked: it.locked,
      display_order: it.display_order ?? i,
      max_redemptions: it.max_redemptions ?? null,
    }))
  );
```

```tsx
    const payload: PackageDefinitionCreate = {
      name: name.trim(),
      description: description || undefined,
      entitlement_type: entitlementType,
      total_sessions:
        entitlementType === "counted" ? parseInt(totalSessions) || 10 : undefined,
      shareability,
      validity_days: parseInt(validityDays) || 90,
      cancellation_fee_pct: cancellationFeePct,
      auto_apply: autoApply,
      items: items.map((it, i) => ({
        service_id: it.service_id,
        quantity: entitlementType === "unlimited" ? 1 : it.quantity,
        unit_price_paise: it.unit_price_paise,
        locked: it.locked,
        display_order: i,
        max_redemptions: it.max_redemptions,
      })),
      discount,
    };

    // Block save if any line lacks a service_id (broken state from manual typing
    // shouldn't reach the backend — Pydantic rejects non-ULID strings anyway,
    // but a friendly toast is better than a 422).
    if (items.some((it) => !it.service_id)) {
      toast.error("Pick a service for every line");
      return;
    }
```

The `if (items.some((it) => !it.service_id))` block must come BEFORE the `setSaving(true)` call. Place it immediately after the existing `if (items.length === 0)` validation (around line 76 of the original file). Remove the old `service_id: it.service_id || it.service_name` fallback — there is no excuse for it now that the picker enforces a ULID.

- [ ] **Step 2: Type-check + run any existing PackageBuilder tests**

Run:
```bash
cd frontend && PATH="/Users/angelxlakra/.nvm/versions/node/v22.20.0/bin:$PATH" npx tsc --noEmit
PATH="/Users/angelxlakra/.nvm/versions/node/v22.20.0/bin:$PATH" npm test -- packages --run
```
Expected: no new type errors. All package-component tests PASS.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/packages/PackageBuilder.tsx
git commit -m "feat(packages-fe): hydrate + send max_redemptions; block save on missing service"
```

---

## Task 13: End-to-end verification — both example schemes

**Files:**
- Test: `backend/tests/integration/test_billing_with_packages.py` (extend)

- [ ] **Step 1: Write integration tests for both example schemes**

Append to `backend/tests/integration/test_billing_with_packages.py`:

```python
def test_salon_royal_pass_per_line_caps_with_global_pool(
    db_session, service_factory, customer_factory, test_user,
    bill_item_factory,
):
    """Spec scheme A: 12 total sessions, Facial≤3, HairSpa≤2, Haircut & Wash uncapped.
    Redeeming 3 Facials should exhaust the Facial line but NOT touch the others;
    a 4th Facial should be rejected with 'per-line limit reached'.
    Meanwhile sessions_remaining decreases from 12→9."""
    import pytest
    from datetime import datetime, timezone, timedelta
    from app.models.billing import Bill, BillStatus, BillType
    from app.models.package import (
        PackageDefinition, PackageDefinitionItem, PackageDefinitionStatus,
        EntitlementType, Shareability, PackageSaleItem,
    )
    from app.services.package_sales_service import create_sale
    from app.services.package_redemption_service import apply_redemption
    from app.services.package_eligibility import find_eligible_packages
    from decimal import Decimal

    facial = service_factory(base_price=200000)
    spa = service_factory(base_price=300000)
    haircut = service_factory(base_price=50000)
    wash = service_factory(base_price=10000)
    customer = customer_factory()

    pkg = PackageDefinition(
        name="Salon Royal Pass", status=PackageDefinitionStatus.PUBLISHED,
        entitlement_type=EntitlementType.COUNTED, total_sessions=12,
        shareability=Shareability.OWNER_ONLY, validity_days=180,
        auto_apply=True, cancellation_fee_pct=Decimal("20.00"),
        created_by_user_id=test_user.id,
    )
    pkg.items = [
        PackageDefinitionItem(service_id=facial.id, quantity=1, unit_price_paise=150000,
                              locked=False, display_order=0, max_redemptions=3),
        PackageDefinitionItem(service_id=spa.id, quantity=1, unit_price_paise=200000,
                              locked=False, display_order=1, max_redemptions=2),
        PackageDefinitionItem(service_id=haircut.id, quantity=1, unit_price_paise=40000,
                              locked=False, display_order=2, max_redemptions=None),
        PackageDefinitionItem(service_id=wash.id, quantity=1, unit_price_paise=8000,
                              locked=False, display_order=3, max_redemptions=None),
    ]
    db_session.add(pkg)
    db_session.flush()

    bill = Bill(
        customer_id=customer.id, subtotal=1000000, discount_amount=0,
        tax_amount=180000, cgst_amount=90000, sgst_amount=90000,
        total_amount=1180000, rounded_total=1180000, rounding_adjustment=0,
        status=BillStatus.POSTED, bill_type=BillType.NORMAL,
        created_by=test_user.id,
    )
    db_session.add(bill)
    db_session.flush()
    sale = create_sale(
        db_session, package_definition_id=pkg.id, bill_id=bill.id,
        customer_id=customer.id, selling_staff_id=None,
    )

    # Redeem 3 Facials
    for _ in range(3):
        bi = bill_item_factory(service_id=facial.id, base_price=200000)
        apply_redemption(db_session, sale.id, bi.id,
                         redeemed_for_customer_id=customer.id, user_id=test_user.id)
    db_session.refresh(sale)
    assert sale.sessions_remaining == 9

    facial_si = db_session.query(PackageSaleItem).filter_by(
        package_sale_id=sale.id, service_id=facial.id).one()
    assert facial_si.remaining == 0

    # 4th Facial: eligibility query must NOT return this sale for Facial
    assert find_eligible_packages(customer.id, facial.id, db_session) == []

    # Direct apply_redemption call also rejects it
    bi = bill_item_factory(service_id=facial.id, base_price=200000)
    with pytest.raises(ValueError, match="per-line limit"):
        apply_redemption(db_session, sale.id, bi.id,
                         redeemed_for_customer_id=customer.id, user_id=test_user.id)

    # But Haircut is still redeemable (uncapped line) — sessions_remaining drops to 8
    bi = bill_item_factory(service_id=haircut.id, base_price=50000)
    apply_redemption(db_session, sale.id, bi.id,
                     redeemed_for_customer_id=customer.id, user_id=test_user.id)
    db_session.refresh(sale)
    assert sale.sessions_remaining == 8


def test_glow_and_refresh_unlimited_with_per_line_cap(
    db_session, service_factory, customer_factory, test_user,
    bill_item_factory,
):
    """Spec scheme B: unlimited package, Facial≤2, Hair Wash uncapped.
    2 Facials + N Hair Wash all succeed; 3rd Facial is rejected."""
    import pytest
    from datetime import datetime, timezone, timedelta
    from app.models.billing import Bill, BillStatus, BillType
    from app.models.package import (
        PackageDefinition, PackageDefinitionItem, PackageDefinitionStatus,
        EntitlementType, Shareability,
    )
    from app.services.package_sales_service import create_sale
    from app.services.package_redemption_service import apply_redemption
    from decimal import Decimal

    facial = service_factory(base_price=200000)
    wash = service_factory(base_price=10000)
    customer = customer_factory()

    pkg = PackageDefinition(
        name="Glow & Refresh", status=PackageDefinitionStatus.PUBLISHED,
        entitlement_type=EntitlementType.UNLIMITED, total_sessions=None,
        shareability=Shareability.OWNER_ONLY, validity_days=90,
        auto_apply=True, cancellation_fee_pct=Decimal("20.00"),
        created_by_user_id=test_user.id,
    )
    pkg.items = [
        PackageDefinitionItem(service_id=facial.id, quantity=1, unit_price_paise=150000,
                              locked=False, display_order=0, max_redemptions=2),
        PackageDefinitionItem(service_id=wash.id, quantity=1, unit_price_paise=8000,
                              locked=False, display_order=1, max_redemptions=None),
    ]
    db_session.add(pkg)
    db_session.flush()

    bill = Bill(
        customer_id=customer.id, subtotal=300000, discount_amount=0,
        tax_amount=54000, cgst_amount=27000, sgst_amount=27000,
        total_amount=354000, rounded_total=354000, rounding_adjustment=0,
        status=BillStatus.POSTED, bill_type=BillType.NORMAL,
        created_by=test_user.id,
    )
    db_session.add(bill)
    db_session.flush()
    sale = create_sale(
        db_session, package_definition_id=pkg.id, bill_id=bill.id,
        customer_id=customer.id, selling_staff_id=None,
    )

    # 2 Facials succeed
    for _ in range(2):
        bi = bill_item_factory(service_id=facial.id, base_price=200000)
        apply_redemption(db_session, sale.id, bi.id,
                         redeemed_for_customer_id=customer.id, user_id=test_user.id)

    # 3rd Facial rejected
    bi = bill_item_factory(service_id=facial.id, base_price=200000)
    with pytest.raises(ValueError, match="per-line limit"):
        apply_redemption(db_session, sale.id, bi.id,
                         redeemed_for_customer_id=customer.id, user_id=test_user.id)

    # Hair Wash: 5 in a row, all succeed (no per-line cap, no global pool)
    for _ in range(5):
        bi = bill_item_factory(service_id=wash.id, base_price=10000)
        apply_redemption(db_session, sale.id, bi.id,
                         redeemed_for_customer_id=customer.id, user_id=test_user.id)
    db_session.refresh(sale)
    assert sale.sessions_remaining is None  # unlimited
```

- [ ] **Step 2: Run the new tests**

Run:
```bash
cd backend && uv run pytest tests/integration/test_billing_with_packages.py::test_salon_royal_pass_per_line_caps_with_global_pool tests/integration/test_billing_with_packages.py::test_glow_and_refresh_unlimited_with_per_line_cap -v
```
Expected: both PASS.

- [ ] **Step 3: Run the full backend test suite to catch regressions**

Run:
```bash
cd backend && uv run pytest tests/ -v --tb=short
```
Expected: no new failures vs. pre-Task-1 baseline. (Existing pre-existing failures unrelated to packages are OK if you can confirm they exist on `main` too — run `git stash` + `pytest` on `main` as a control if in doubt.)

- [ ] **Step 4: Run the full frontend test suite**

Run:
```bash
cd frontend && PATH="/Users/angelxlakra/.nvm/versions/node/v22.20.0/bin:$PATH" npm test -- --run
```
Expected: no new failures.

- [ ] **Step 5: Commit**

```bash
git add backend/tests/integration/test_billing_with_packages.py
git commit -m "test(packages): end-to-end coverage for Royal Pass and Glow & Refresh schemes"
```

---

## Task 14: Documentation update

**Files:**
- Modify: `docs/models/10-packages.md`
- Modify: `docs/features/10-packages.md`

- [ ] **Step 1: Add `max_redemptions` and `remaining` to the `PackageDefinitionItem` and `PackageSaleItem` tables in `docs/models/10-packages.md`.**

In the `PackageDefinitionItem` table (currently around lines 47–61), add a row:

```markdown
| `max_redemptions` | `Integer` | Nullable; per-line redemption cap. NULL means no per-line cap; this line draws from the global `sessions_remaining` pool only. |
```

In the `PackageSaleItem` table (currently around lines 94–110), add two rows:

```markdown
| `max_redemptions` | `Integer` | Nullable; snapshot of the per-line cap at sale time. |
| `remaining` | `Integer` | Nullable; runtime per-line counter. NULL iff `max_redemptions` is NULL. Decremented by `apply_redemption`; restored by `undo_redemption`. |
```

Also append a paragraph after the existing `Invariants` block for `PackageSale`:

```markdown
### Per-line caps (added 2026-06-07)

A `PackageSaleItem` may carry an optional `max_redemptions` cap independent of the package's global `sessions_remaining`. When set, redemption requires BOTH `sessions_remaining > 0` (if counted) AND `remaining > 0`. Per-line caps coexist with unlimited packages: `entitlement_type=unlimited` + `max_redemptions=2` means "no overall limit, but at most 2 of this service per package."
```

- [ ] **Step 2: Add a new "Per-line limits" subsection in `docs/features/10-packages.md`.**

After the existing "Key non-obvious behaviors" → "FIFO conflict resolution" block (currently around line 65), insert:

```markdown
### Per-line redemption caps

Each service line in a package definition may carry an optional `max_redemptions` cap. This lets owners model schemes like "12-session pass, max 3 Facials, max 2 Hair Spas, Haircut & Hair Wash unlimited within the 12-session pool." When a per-line cap is set, the global session pool is still required (for counted packages) AND the per-line counter must be > 0. Leaving the field blank in the Package Builder means "no per-line cap; this line draws from the global pool only."

For unlimited packages, per-line caps still work and let owners offer "unlimited Hair Wash + max 2 Facials" packages without a global pool.
```

- [ ] **Step 3: Commit**

```bash
git add docs/models/10-packages.md docs/features/10-packages.md
git commit -m "docs(packages): per-line redemption caps + service picker fix"
```

---

## Self-Review Notes

**Spec coverage check:**
- ✅ Service picker fix → Tasks 9, 10, 11, 12
- ✅ Per-line session limits → Tasks 1–7, 13
- ✅ Overall cap + per-line cap together → Task 13 (Salon Royal Pass test exercises exactly this)

**Type consistency check:**
- Backend `max_redemptions` is `Integer NULL` everywhere; Pydantic uses `Optional[int]`; TypeScript uses `number | null`.
- Backend `remaining` lives only on `PackageSaleItem` (runtime); never on `PackageDefinitionItem` (definition is the cap, not the counter).
- Frontend `LineItem` interface adds `max_redemptions: number | null` (non-optional in component state but serialised as nullable to backend).

**Risk callouts for the implementer:**
1. **Pre-existing TS errors:** the V2 Phase 0 work left ~162 type errors in V1 pages. Don't try to fix them — only ensure your edits don't add new ones.
2. **`db.refresh(sale)` after redemption:** if a test asserts on `sale.sessions_remaining` after `apply_redemption`, call `db_session.refresh(sale)` first because SQLAlchemy may have cached the pre-update value.
3. **Combobox quirks:** the V2 `Combobox` is wrapped in a Radix Popover and has a custom wheel-scroll fix. Don't unwrap it — `ServicePicker` should compose, not reach inside.
4. **`__import__` trick in Task 7 step 3b:** the inline import in `undo_redemption` is to avoid disturbing the existing import block. The implementer may prefer adding `PackageSaleItem` to the top-level import — that's fine, just keep it as one atomic change.
5. **Edit page hydration:** `PackageBuilder.tsx` reads `it.service_name` from `initial.items`. The backend `PackageDefinitionItemResponse` already exposes `service_name` (Task 3 confirmed), but the TypeScript `PackageDefinitionItem` type was updated in Task 8 to include `service_name?: string`. If the implementer skipped Task 8 they'll see a TS error here — that's the type system catching the dependency, which is the right outcome.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-06-07-package-per-line-limits-and-service-picker.md`. Two execution options:

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration.

**2. Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints.

Which approach?
