# Package Choice Groups & Pool-Exempt Unlimited Lines Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let a package contain (a) *choice groups* — several service lines sharing one redemption budget ("2 facials chosen from Aroma/Lotus/Kanpeki") — and (b) *pool-exempt unlimited lines* — services redeemable without limit inside a counted package, surviving exhaustion until expiry ("unlimited hair washes").

**Architecture:** New `package_definition_choice_groups` table + `choice_group_id`/`pool_exempt` on definition items; mirrored snapshot table `package_sale_choice_groups` with a runtime `remaining` counter + `sale_choice_group_id`/`pool_exempt` on sale items. Redemption becomes a three-way branch (pool-exempt / group member / standalone) guarded by the existing `SELECT FOR UPDATE` on the PackageSale row. Pricing counts each group ONCE at `group.quantity × max(member price)` and pool-exempt lines at 0 (their snapshot price is 0 — free perk).

**Product decisions (confirmed with owner):**
- Pool-exempt lines stay redeemable while the sale is ACTIVE **or EXHAUSTED**, until `expires_at`.
- Group redemptions decrement BOTH the group counter and the global session pool.
- Group MRP weight = `quantity × MAX(member unit price)` (salon never under-charges; owner adjusts headline price via the existing discount).
- A line is EITHER a group member OR has its own `max_redemptions` (never both). `pool_exempt` lines have neither.

**Tech Stack:** FastAPI 0.115 / SQLAlchemy 2.0 / Alembic / Pydantic v2 / pytest (backend); Next.js 16 / React 19 / Vitest + Testing Library (frontend).

**Heads at plan-write time:** alembic `r1s2t3u4v5w6`. Backend tests run with:
```bash
cd backend && REDIS_URL=redis://localhost:6379/0 \
  DATABASE_URL="postgresql+psycopg://salon_user:change_me_123@127.0.0.1:5432/salon_test_db" \
  SECRET_KEY=test SALON_NAME=t SALON_ADDRESS=t GSTIN=t uv run pytest <path> -q
```
Frontend tests: `cd frontend && ./node_modules/.bin/vitest run --config vitest.config.mts <path>` (Node ≥ 20; default shell node is 16 — use `PATH="$HOME/.nvm/versions/node/v22.20.0/bin:$PATH"`).

---

## File Structure

**New files**
- `backend/alembic/versions/s2t3u4v5w6x7_add_choice_groups_and_pool_exempt.py` — migration
- `backend/tests/unit/services/test_package_group_pricing.py` — pure pricing tests
- `frontend/src/components/packages/ChoiceGroupEditor.tsx` — builder UI for groups
- `frontend/src/components/packages/__tests__/ChoiceGroupEditor.test.tsx`

**Modified files**
- `backend/app/models/package.py` — 2 new model classes, 4 new columns, constraints, pricing properties
- `backend/app/services/package_pricing_engine.py` — group-aware weight collapse + refund dedupe
- `backend/app/schemas/package.py` — choice groups in create/response schemas, `pool_exempt`
- `backend/app/services/package_catalog_service.py` — persist groups, validation
- `backend/app/services/package_sales_service.py` — snapshot groups + flags
- `backend/app/services/package_redemption_service.py` — three-way redemption branch + undo
- `backend/app/services/package_eligibility.py` — pool-exempt/group-aware query
- `frontend/src/types/package.ts` — group + pool_exempt types
- `frontend/src/components/packages/PackageBuilderServicesTable.tsx` — group/unlimited per-line controls
- `frontend/src/components/packages/PackageBuilder.tsx` — group state + payload
- `frontend/src/components/packages/PackageBuilderDiscountControl.tsx` — take `totalPaise` prop (group-aware MRP)
- `frontend/src/app/(shell)/dashboard/packages/[id]/edit/page.tsx` — round-trip groups
- `docs/models/10-packages.md` — schema docs

**Test files (extend)**
- `backend/tests/integration/test_package_catalog_service.py`
- `backend/tests/integration/test_package_redemption_service.py`
- `backend/tests/integration/test_package_eligibility.py`
- `backend/tests/integration/test_package_refund.py`
- `frontend/src/components/packages/__tests__/PackageBuilderServicesTable.test.tsx`

---

## Task Sequencing Logic

Backend-first, bottom-up, each phase independently committable:
- Task 1–2: schema substrate (migration + models + constraints), zero behavior change.
- Task 3: pure pricing math (no DB) — everything downstream depends on these numbers.
- Task 4: catalog write path (schemas + service + validation).
- Task 5: sale snapshot.
- Task 6: redemption apply/undo (highest risk — money + concurrency).
- Task 7: eligibility query.
- Task 8: refund dedupe.
- Task 9–11: frontend (types/API → builder UI → edit round-trip).
- Task 12: docs + full review pipeline.

---

### Task 1: Migration

**Files:**
- Create: `backend/alembic/versions/s2t3u4v5w6x7_add_choice_groups_and_pool_exempt.py`

- [ ] **Step 1: Write the migration**

```python
"""Add choice groups and pool-exempt flags to packages.

Revision ID: s2t3u4v5w6x7
Revises: r1s2t3u4v5w6
Create Date: 2026-06-12

Choice groups: several definition lines share one redemption budget.
Pool-exempt lines: redeemable without limit inside a counted package,
surviving EXHAUSTED status until expiry.

All new columns nullable / defaulted — existing rows behave identically.
"""

from alembic import op
import sqlalchemy as sa

revision = "s2t3u4v5w6x7"
down_revision = "r1s2t3u4v5w6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "package_definition_choice_groups",
        sa.Column("id", sa.String(26), primary_key=True),
        sa.Column(
            "package_definition_id", sa.String(26),
            sa.ForeignKey("package_definitions.id", ondelete="CASCADE"),
            nullable=False, index=True,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.CheckConstraint("quantity >= 1", name="ck_def_choice_group_qty"),
        sa.UniqueConstraint("package_definition_id", "name",
                            name="uq_def_choice_group_name"),
    )
    op.create_table(
        "package_sale_choice_groups",
        sa.Column("id", sa.String(26), primary_key=True),
        sa.Column(
            "package_sale_id", sa.String(26),
            sa.ForeignKey("package_sales.id", ondelete="CASCADE"),
            nullable=False, index=True,
        ),
        sa.Column(
            "definition_choice_group_id", sa.String(26),
            sa.ForeignKey("package_definition_choice_groups.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("remaining", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.CheckConstraint("remaining >= 0", name="ck_sale_choice_group_remaining"),
        sa.CheckConstraint("quantity >= 1", name="ck_sale_choice_group_qty"),
    )
    op.add_column(
        "package_definition_items",
        sa.Column("choice_group_id", sa.String(26),
                  sa.ForeignKey("package_definition_choice_groups.id",
                                ondelete="RESTRICT"),
                  nullable=True),
    )
    op.add_column(
        "package_definition_items",
        sa.Column("pool_exempt", sa.Boolean(), nullable=False,
                  server_default=sa.false()),
    )
    op.create_check_constraint(
        "ck_def_item_group_xor_cap", "package_definition_items",
        "NOT (choice_group_id IS NOT NULL AND max_redemptions IS NOT NULL)",
    )
    op.create_check_constraint(
        "ck_def_item_pool_exempt_plain", "package_definition_items",
        "NOT (pool_exempt AND (choice_group_id IS NOT NULL "
        "OR max_redemptions IS NOT NULL))",
    )
    op.add_column(
        "package_sale_items",
        sa.Column("sale_choice_group_id", sa.String(26),
                  sa.ForeignKey("package_sale_choice_groups.id",
                                ondelete="RESTRICT"),
                  nullable=True),
    )
    op.add_column(
        "package_sale_items",
        sa.Column("pool_exempt", sa.Boolean(), nullable=False,
                  server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("package_sale_items", "pool_exempt")
    op.drop_column("package_sale_items", "sale_choice_group_id")
    op.drop_constraint("ck_def_item_pool_exempt_plain",
                       "package_definition_items", type_="check")
    op.drop_constraint("ck_def_item_group_xor_cap",
                       "package_definition_items", type_="check")
    op.drop_column("package_definition_items", "pool_exempt")
    op.drop_column("package_definition_items", "choice_group_id")
    op.drop_table("package_sale_choice_groups")
    op.drop_table("package_definition_choice_groups")
```

- [ ] **Step 2: Verify chain**

Run: `cd backend && uv run alembic heads`
Expected: `s2t3u4v5w6x7 (head)`

- [ ] **Step 3: Commit**

```bash
git add backend/alembic/versions/s2t3u4v5w6x7_add_choice_groups_and_pool_exempt.py
git commit -m "feat(packages): migration for choice groups and pool-exempt lines"
```

---

### Task 2: Models

**Files:**
- Modify: `backend/app/models/package.py`
- Test: `backend/tests/unit/models/test_package_models.py` (extend)

- [ ] **Step 1: Write failing tests** (append to `backend/tests/unit/models/test_package_models.py`, following the file's existing fixture style)

```python
def test_definition_item_group_xor_cap(db_session, package_definition_factory):
    """A line cannot be both a group member and individually capped."""
    import pytest
    from sqlalchemy.exc import IntegrityError
    from app.models.package import PackageDefinitionChoiceGroup, PackageDefinitionItem

    pkg = package_definition_factory()
    group = PackageDefinitionChoiceGroup(
        package_definition_id=pkg.id, name="Facial choice", quantity=2,
    )
    db_session.add(group)
    db_session.flush()
    item = pkg.items[0]
    item.choice_group_id = group.id
    item.max_redemptions = 3  # forbidden combination
    with pytest.raises(IntegrityError):
        db_session.flush()
    db_session.rollback()


def test_pool_exempt_must_be_plain(db_session, package_definition_factory):
    """pool_exempt lines cannot have a cap or group."""
    import pytest
    from sqlalchemy.exc import IntegrityError

    pkg = package_definition_factory()
    item = pkg.items[0]
    item.pool_exempt = True
    item.max_redemptions = 5
    with pytest.raises(IntegrityError):
        db_session.flush()
    db_session.rollback()
```

- [ ] **Step 2: Run tests, verify they fail** (model classes/columns don't exist yet)

- [ ] **Step 3: Add models** in `backend/app/models/package.py`:

After `PackageDefinition`, add:

```python
class PackageDefinitionChoiceGroup(Base, ULIDMixin, TimestampMixin):
    """N redemptions shared across a set of member lines ("choose 2 facials")."""
    __tablename__ = "package_definition_choice_groups"

    package_definition_id = Column(
        String(26), ForeignKey("package_definitions.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    name = Column(String(255), nullable=False)
    quantity = Column(Integer, nullable=False)
    display_order = Column(Integer, nullable=False, default=0)

    definition = relationship("PackageDefinition", back_populates="choice_groups")
    items = relationship("PackageDefinitionItem", back_populates="choice_group")

    __table_args__ = (
        CheckConstraint("quantity >= 1", name="ck_def_choice_group_qty"),
        Index("uq_def_choice_group_name", "package_definition_id", "name", unique=True),
    )
```

On `PackageDefinition`, add the relationship:

```python
    choice_groups = relationship(
        "PackageDefinitionChoiceGroup",
        back_populates="definition",
        cascade="all, delete-orphan",
        order_by="PackageDefinitionChoiceGroup.display_order",
    )
```

On `PackageDefinitionItem`, add columns + constraints + relationship:

```python
    choice_group_id = Column(
        String(26),
        ForeignKey("package_definition_choice_groups.id", ondelete="RESTRICT"),
        nullable=True,
    )
    pool_exempt = Column(Boolean, nullable=False, default=False)

    choice_group = relationship("PackageDefinitionChoiceGroup", back_populates="items")
```

and to its `__table_args__` (create the tuple if absent):

```python
        CheckConstraint(
            "NOT (choice_group_id IS NOT NULL AND max_redemptions IS NOT NULL)",
            name="ck_def_item_group_xor_cap",
        ),
        CheckConstraint(
            "NOT (pool_exempt AND (choice_group_id IS NOT NULL "
            "OR max_redemptions IS NOT NULL))",
            name="ck_def_item_pool_exempt_plain",
        ),
```

After `PackageSale`, add:

```python
class PackageSaleChoiceGroup(Base, ULIDMixin, TimestampMixin):
    """Runtime budget counter for a choice group on one sale."""
    __tablename__ = "package_sale_choice_groups"

    package_sale_id = Column(
        String(26), ForeignKey("package_sales.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    definition_choice_group_id = Column(
        String(26),
        ForeignKey("package_definition_choice_groups.id", ondelete="RESTRICT"),
        nullable=False,
    )
    name = Column(String(255), nullable=False)
    quantity = Column(Integer, nullable=False)
    # Guarded by the SELECT FOR UPDATE on the parent PackageSale row —
    # NEVER mutate without holding that lock (see apply_redemption).
    remaining = Column(Integer, nullable=False)

    sale = relationship("PackageSale", back_populates="choice_groups")

    __table_args__ = (
        CheckConstraint("remaining >= 0", name="ck_sale_choice_group_remaining"),
        CheckConstraint("quantity >= 1", name="ck_sale_choice_group_qty"),
    )
```

On `PackageSale`, add: `choice_groups = relationship("PackageSaleChoiceGroup", back_populates="sale", cascade="all, delete-orphan")`

On `PackageSaleItem`, add:

```python
    sale_choice_group_id = Column(
        String(26), ForeignKey("package_sale_choice_groups.id", ondelete="RESTRICT"),
        nullable=True,
    )
    pool_exempt = Column(Boolean, nullable=False, default=False)
```

- [ ] **Step 4: Run tests, verify pass.** Also run the whole existing package model/catalog test files to confirm no regression.

- [ ] **Step 5: Commit** `feat(packages): choice group + pool-exempt models`

---

### Task 3: Pricing engine (pure functions)

**Files:**
- Modify: `backend/app/services/package_pricing_engine.py`
- Modify: `backend/app/models/package.py` (`final_price_paise`, `effective_item_prices`)
- Test: Create `backend/tests/unit/services/test_package_group_pricing.py`

Pricing rules:
- **Standalone line** weight = `unit_price × qty` (unchanged).
- **Group** weight = `MAX(member unit_price) × group.quantity`, counted ONCE. Member lines snapshot at the group's (discounted) representative unit price.
- **Pool-exempt line** weight = 0; snapshot price = 0.

- [ ] **Step 1: Write failing tests**

```python
"""Pure unit tests for group-aware package pricing."""
from decimal import Decimal
from app.services.package_pricing_engine import (
    PricingLine, price_lines, DiscountMode,
)


def line(price, qty=1, group=None, pool_exempt=False, locked=False):
    return PricingLine(
        unit_price_paise=price, quantity=qty, locked=locked,
        group_key=group, group_quantity=None, pool_exempt=pool_exempt,
    )


def test_group_counted_once_at_max_price():
    # 2 haircuts @2500 + group "facial" x2 from {2200, 2500, 2749}
    lines = [
        line(250000, qty=2),
        line(220000, group="facial"),
        line(250000, group="facial"),
        line(274900, group="facial"),
    ]
    result = price_lines(lines, groups={"facial": 2}, mode=None, value=None)
    # MRP = 2*250000 + 2*274900 = 1049800
    assert result.gross_total_paise == 1049800
    # No discount: standalone keeps price; every group member gets max price
    assert result.unit_prices_paise == [250000, 274900, 274900, 274900]


def test_pool_exempt_is_free():
    lines = [line(250000, qty=2), line(50000, pool_exempt=True)]
    result = price_lines(lines, groups={}, mode=None, value=None)
    assert result.gross_total_paise == 500000
    assert result.unit_prices_paise == [250000, 0]


def test_final_discount_distributes_over_group_once():
    lines = [
        line(250000, qty=2),                      # weight 500000
        line(220000, group="facial"),
        line(274900, group="facial"),             # group weight 549800
    ]
    result = price_lines(
        lines, groups={"facial": 2}, mode=DiscountMode.FINAL,
        value=Decimal("799900"),
    )
    # Gross 1049800 → final 799900 distributed by weight
    assert result.final_total_paise == 799900
    # Both group members carry the SAME discounted representative price
    assert result.unit_prices_paise[1] == result.unit_prices_paise[2]
    # Standalone line total + group rep price * group qty == final (±qty rounding)
    standalone_total = result.unit_prices_paise[0] * 2
    group_total = result.unit_prices_paise[1] * 2
    assert abs((standalone_total + group_total) - 799900) <= 2
```

- [ ] **Step 2: Run, verify fail** (`PricingLine`/`price_lines` undefined).

- [ ] **Step 3: Implement** in `package_pricing_engine.py`:

```python
@dataclass(frozen=True)
class PricingLine:
    unit_price_paise: int
    quantity: int
    locked: bool
    group_key: Optional[str]       # None = standalone
    group_quantity: Optional[int]  # unused on input; here for symmetry
    pool_exempt: bool


@dataclass(frozen=True)
class PricingResult:
    gross_total_paise: int
    final_total_paise: int
    unit_prices_paise: List[int]   # same order as input lines


def price_lines(
    lines: List[PricingLine],
    groups: dict,                  # group_key -> group quantity
    mode: Optional[DiscountMode],
    value: Optional[Decimal],
) -> PricingResult:
    """Group-aware pricing: collapse each group to ONE weighted entry
    (max member price × group qty), pool-exempt lines weigh 0, then run
    distribute_discount over the collapsed entries and spread results back.
    """
    # Build collapsed entries: list of (kind, key_or_index, DiscountedItem)
    collapsed: List[DiscountedItem] = []
    entry_map: List[tuple] = []  # parallel: ("line", i) | ("group", key)
    seen_groups: set = set()
    for i, ln in enumerate(lines):
        if ln.pool_exempt:
            continue
        if ln.group_key is not None:
            if ln.group_key in seen_groups:
                continue
            seen_groups.add(ln.group_key)
            members = [l for l in lines if l.group_key == ln.group_key]
            rep_price = max(m.unit_price_paise for m in members)
            collapsed.append(DiscountedItem(
                unit_price_paise=rep_price,
                quantity=groups[ln.group_key],
                locked=any(m.locked for m in members),
            ))
            entry_map.append(("group", ln.group_key))
        else:
            collapsed.append(DiscountedItem(
                unit_price_paise=ln.unit_price_paise,
                quantity=ln.quantity,
                locked=ln.locked,
            ))
            entry_map.append(("line", i))

    gross = sum(e.unit_price_paise * e.quantity for e in collapsed)

    if mode is not None and collapsed:
        discounted = distribute_discount(collapsed, mode, value)
    else:
        discounted = collapsed

    # Exact final total (mirror PackageDefinition.final_price_paise rules)
    if mode is None:
        final_total = gross
    elif mode == DiscountMode.PCT:
        final_total = int(Decimal(gross) * (Decimal("100") - value) / Decimal("100"))
    elif mode == DiscountMode.FLAT:
        final_total = gross - _paise(value)
    else:
        final_total = _paise(value)

    # Spread back to per-input-line unit prices
    group_price = {
        key: d.unit_price_paise
        for (kind, key), d in zip(entry_map, discounted) if kind == "group"
    }
    line_price = {
        idx: d.unit_price_paise
        for (kind, idx), d in zip(entry_map, discounted) if kind == "line"
    }
    unit_prices: List[int] = []
    for i, ln in enumerate(lines):
        if ln.pool_exempt:
            unit_prices.append(0)
        elif ln.group_key is not None:
            unit_prices.append(group_price[ln.group_key])
        else:
            unit_prices.append(line_price[i])
    return PricingResult(
        gross_total_paise=gross,
        final_total_paise=final_total,
        unit_prices_paise=unit_prices,
    )
```

- [ ] **Step 4: Rewire `PackageDefinition.effective_item_prices` and `final_price_paise`** in `backend/app/models/package.py` to delegate:

```python
    def _pricing_lines(self):
        from app.services.package_pricing_engine import PricingLine
        group_name = {g.id: g.name for g in self.choice_groups}
        return [
            PricingLine(
                unit_price_paise=i.unit_price_paise,
                quantity=i.quantity,
                locked=i.locked,
                group_key=group_name.get(i.choice_group_id),
                group_quantity=None,
                pool_exempt=i.pool_exempt,
            )
            for i in self.items
        ]

    def _price(self):
        from app.services.package_pricing_engine import price_lines, DiscountMode
        groups = {g.name: g.quantity for g in self.choice_groups}
        mode = DiscountMode(self.discount_mode) if self.discount_mode else None
        return price_lines(self._pricing_lines(), groups, mode, self.discount_value)

    def effective_item_prices(self) -> list[int]:
        """Per-item unit prices with discount applied (paise). Group members
        carry the group's representative price; pool-exempt lines are 0."""
        return self._price().unit_prices_paise

    @property
    def final_price_paise(self) -> int:
        """Effective selling price of the whole package (paise)."""
        return self._price().final_total_paise
```

(Delete the old bodies of both members; the gross/pct/flat/final math now lives in `price_lines`.)

- [ ] **Step 5: Run new tests + ALL existing package tests** (catalog service tests assert `final_price_paise` values — they must still pass since standalone-only definitions collapse to the old math).

- [ ] **Step 6: Commit** `feat(packages): group-aware pricing engine`

---

### Task 4: Schemas + catalog service

**Files:**
- Modify: `backend/app/schemas/package.py`
- Modify: `backend/app/services/package_catalog_service.py`
- Test: `backend/tests/integration/test_package_catalog_service.py` (extend)

API contract: groups are referenced **by name** in the payload (frontend never invents ULIDs); the service maps names → rows.

- [ ] **Step 1: Write failing tests**

```python
def test_create_with_choice_group_and_pool_exempt(db_session, user_factory):
    svc_a = _make_service(db_session, "GA")   # facials
    svc_b = _make_service(db_session, "GB")
    svc_h = _make_service(db_session, "GH")   # haircut
    svc_w = _make_service(db_session, "GW")   # wash
    user = user_factory()
    payload = PackageDefinitionCreate(
        name="Freedom Pack",
        entitlement_type=EntitlementType.COUNTED,
        total_sessions=4,
        validity_days=90,
        shareability=Shareability.OWNER_ONLY,
        choice_groups=[ChoiceGroupCreate(name="Facial choice", quantity=2)],
        items=[
            PackageDefinitionItemCreate(service_id=svc_h.id, quantity=2,
                                        unit_price_paise=250000, max_redemptions=2),
            PackageDefinitionItemCreate(service_id=svc_a.id, quantity=1,
                                        unit_price_paise=220000,
                                        choice_group_name="Facial choice"),
            PackageDefinitionItemCreate(service_id=svc_b.id, quantity=1,
                                        unit_price_paise=250000,
                                        choice_group_name="Facial choice"),
            PackageDefinitionItemCreate(service_id=svc_w.id, quantity=1,
                                        unit_price_paise=50000, pool_exempt=True),
        ],
    )
    pkg = create_definition(db_session, payload, user.id)
    assert len(pkg.choice_groups) == 1
    group = pkg.choice_groups[0]
    assert group.quantity == 2
    members = [i for i in pkg.items if i.choice_group_id == group.id]
    assert len(members) == 2
    wash = next(i for i in pkg.items if i.pool_exempt)
    assert wash.unit_price_paise == 50000  # gross stored even though free
    # MRP: 2*250000 (haircut) + 2*250000 (group max) + 0 (wash) = 1000000
    assert pkg.final_price_paise == 1000000


def test_unknown_group_name_rejected(db_session, user_factory):
    svc = _make_service(db_session, "GX")
    user = user_factory()
    payload = _counted_payload(items=[
        PackageDefinitionItemCreate(service_id=svc.id, quantity=1,
                                    unit_price_paise=100000,
                                    choice_group_name="Nope"),
    ])
    with pytest.raises(ValueError, match="Unknown choice group"):
        create_definition(db_session, payload, user.id)


def test_update_replaces_choice_groups(db_session, user_factory):
    svc1 = _make_service(db_session, "GU1")
    svc2 = _make_service(db_session, "GU2")
    user = user_factory()
    pkg = create_definition(db_session, _counted_payload(items=[
        PackageDefinitionItemCreate(service_id=svc1.id, quantity=1,
                                    unit_price_paise=100000),
    ]), user.id)
    update_payload = PackageDefinitionUpdate(
        name="Updated", entitlement_type=EntitlementType.COUNTED,
        total_sessions=2, validity_days=60,
        shareability=Shareability.OWNER_ONLY,
        choice_groups=[ChoiceGroupCreate(name="Pick one", quantity=1)],
        items=[
            PackageDefinitionItemCreate(service_id=svc1.id, quantity=1,
                                        unit_price_paise=100000,
                                        choice_group_name="Pick one"),
            PackageDefinitionItemCreate(service_id=svc2.id, quantity=1,
                                        unit_price_paise=120000,
                                        choice_group_name="Pick one"),
        ],
    )
    updated = update_definition(db_session, pkg.id, update_payload)
    assert len(updated.choice_groups) == 1
    assert all(i.choice_group_id for i in updated.items)
```

(Import `ChoiceGroupCreate` alongside existing schema imports; add `pytest` import if missing.)

- [ ] **Step 2: Run, verify fail.**

- [ ] **Step 3: Schemas** in `backend/app/schemas/package.py`:

```python
class ChoiceGroupCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    quantity: int = Field(..., ge=1)
    display_order: int = 0


class ChoiceGroupResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    quantity: int
    display_order: int
```

Extend `PackageDefinitionItemCreate` with:

```python
    choice_group_name: Optional[str] = None
    pool_exempt: bool = False

    @model_validator(mode="after")
    def validate_flags(self) -> "PackageDefinitionItemCreate":
        if self.choice_group_name and self.max_redemptions is not None:
            raise ValueError("A group member cannot also have its own limit")
        if self.pool_exempt and (self.choice_group_name or self.max_redemptions):
            raise ValueError("An unlimited line cannot have a limit or group")
        return self
```

Extend `PackageDefinitionCreate` with `choice_groups: List[ChoiceGroupCreate] = []`, and its validator: every `choice_group_name` used by an item must exist in `choice_groups`, group names unique, every declared group must have ≥ 2 members (a 1-member group is just a capped line), and `pool_exempt` items only allowed when `entitlement_type == COUNTED`.

Extend `PackageDefinitionItemResponse` with `choice_group_id: Optional[str] = None` and `pool_exempt: bool = False`. Extend `PackageDefinitionResponse` with `choice_groups: List[ChoiceGroupResponse] = []`.

- [ ] **Step 4: Catalog service** — in `create_definition` and `update_definition`:

```python
    # after constructing pkg (create) / clearing items (update):
    from app.models.package import PackageDefinitionChoiceGroup
    groups_by_name = {}
    pkg.choice_groups = []
    for g in payload.choice_groups:
        row = PackageDefinitionChoiceGroup(
            name=g.name, quantity=g.quantity, display_order=g.display_order,
        )
        pkg.choice_groups.append(row)
        groups_by_name[g.name] = row
    db.flush()  # materialise group ids before items reference them
```

and in `_build_items(payload_items, groups_by_name)`:

```python
        choice_group_id=(
            groups_by_name[src.choice_group_name].id
            if src.choice_group_name else None
        ),
        pool_exempt=src.pool_exempt,
```

raising `ValueError(f"Unknown choice group: {src.choice_group_name}")` when the name is missing from the map. `update_definition` clears `pkg.choice_groups` the same way it clears items (set `pkg.choice_groups = []` + flush BEFORE inserting new ones; the RESTRICT FK from old sale snapshots means groups referenced by sales cannot be hard-deleted — mirror the existing items pattern, and if the delete fails due to sold references, surface `ValueError("Cannot restructure groups on a package with sales")`).

`_validate_discount` must now collapse via `price_lines` weights — simplest correct form: skip the dry-run when there are choice groups OR pool-exempt lines and instead validate `final/flat ≤ gross` using `price_lines(...).gross_total_paise`.

- [ ] **Step 5: Run tests, verify pass. Run the full catalog + API test files.**

- [ ] **Step 6: Commit** `feat(packages): choice groups in schemas and catalog service`

---

### Task 5: Sale snapshot

**Files:**
- Modify: `backend/app/services/package_sales_service.py`
- Test: `backend/tests/integration/test_package_catalog_service.py` or `test_package_sales_service.py` (extend)

- [ ] **Step 1: Failing test**

```python
def test_create_sale_snapshots_groups_and_pool_exempt(
    db_session, user_factory, customer_factory, bill_factory
):
    from app.services.package_sales_service import create_sale
    # Build "Freedom Pack" exactly as in test_create_with_choice_group_and_pool_exempt
    # (haircut max2 @2500x2, two facials in group qty2, pool-exempt wash) …
    pkg = _make_freedom_pack(db_session, user_factory())  # extract shared helper
    publish(db_session, pkg.id)
    customer = customer_factory()
    bill = bill_factory(customer_id=customer.id)

    sale = create_sale(db_session, pkg.id, bill.id, customer.id, None)

    assert len(sale.choice_groups) == 1
    sg = sale.choice_groups[0]
    assert (sg.quantity, sg.remaining) == (2, 2)
    members = [i for i in sale.items if i.sale_choice_group_id == sg.id]
    assert len(members) == 2
    # Group members snapshot at the SAME representative discounted price
    assert len({m.snapshot_unit_price_paise for m in members}) == 1
    wash = next(i for i in sale.items if i.pool_exempt)
    assert wash.snapshot_unit_price_paise == 0
```

- [ ] **Step 2: Run, verify fail.**

- [ ] **Step 3: Implement** in `create_sale`, before the item loop:

```python
    from app.models.package import PackageSaleChoiceGroup
    sale_group_by_def_group: dict[str, str] = {}
    for g in pkg.choice_groups:
        sg = PackageSaleChoiceGroup(
            package_sale_id=sale.id,
            definition_choice_group_id=g.id,
            name=g.name, quantity=g.quantity, remaining=g.quantity,
        )
        db.add(sg)
        db.flush()
        sale_group_by_def_group[g.id] = sg.id
```

and in the item loop add:

```python
            sale_choice_group_id=sale_group_by_def_group.get(def_item.choice_group_id),
            pool_exempt=def_item.pool_exempt,
```

(`effective_prices` already comes from `pkg.effective_item_prices()` — Task 3 makes it group-aware, so no further price change here.)

- [ ] **Step 4: Run tests; commit** `feat(packages): snapshot choice groups onto sales`

---

### Task 6: Redemption apply/undo (HIGHEST RISK — money + concurrency)

**Files:**
- Modify: `backend/app/services/package_redemption_service.py`
- Test: `backend/tests/integration/test_package_redemption_service.py` (extend)

Semantics:
- **pool-exempt line:** redeemable while status ∈ {ACTIVE, EXHAUSTED} and not expired. No sessions check, no decrement, `session_number=None`. Payment amount will be 0 (snapshot price 0) — keep the Payment row for audit symmetry.
- **group member:** requires `group.remaining > 0` AND global `sessions_remaining > 0`; decrements both.
- **standalone:** unchanged.

- [ ] **Step 1: Failing tests** (use the existing redemption test fixtures/factories in the file; sketch below shows assertions, adapt setup to the file's helpers)

```python
def test_redeem_group_member_decrements_group_and_pool(...):
    # sale: pool=4, group(qty=2) with facials A and B
    apply_redemption(db, sale.id, bill_item_for(A).id, customer.id, user.id)
    assert sale.sessions_remaining == 3
    assert sale.choice_groups[0].remaining == 1
    apply_redemption(db, sale.id, bill_item_for(B).id, customer.id, user.id)
    assert sale.choice_groups[0].remaining == 0
    with pytest.raises(ValueError, match="choice group budget exhausted"):
        apply_redemption(db, sale.id, bill_item_for(A2).id, customer.id, user.id)

def test_pool_exempt_redeems_after_exhaustion(...):
    # consume all 4 pool sessions → status EXHAUSTED
    ...
    audit = apply_redemption(db, sale.id, wash_bill_item.id, customer.id, user.id)
    assert sale.sessions_remaining == 0          # untouched
    assert sale.status == PackageSaleStatus.EXHAUSTED  # untouched
    assert audit.session_number is None

def test_pool_exempt_blocked_after_expiry(...):
    # freeze/advance past expires_at → ValueError("Package expired")

def test_undo_group_redemption_restores_both(...):
    audit = apply_redemption(...)   # group member
    undo_redemption(db, audit.id, user.id)
    assert sale.sessions_remaining == 4
    assert sale.choice_groups[0].remaining == 2

def test_undo_pool_exempt_restores_nothing(...):
    audit = apply_redemption(...)   # pool-exempt wash on EXHAUSTED sale
    undo_redemption(db, audit.id, user.id)
    assert sale.sessions_remaining == 0
    assert sale.status == PackageSaleStatus.EXHAUSTED
```

- [ ] **Step 2: Run, verify fail.**

- [ ] **Step 3: Implement.** In `apply_redemption`, restructure the guard sequence (bill_item + sale_item must resolve BEFORE the status/sessions gates so flags can relax them):

```python
    # ... after locking sale and loading bill_item ...
    sale_item = next(
        (i for i in sale.items if i.service_id == bill_item.service_id), None,
    )
    if not sale_item:
        raise ValueError("Service not covered by this package")

    # 1. Status gate: EXHAUSTED is allowed ONLY for pool-exempt lines
    if sale.status == PackageSaleStatus.EXHAUSTED and sale_item.pool_exempt:
        pass  # unlimited perk survives exhaustion until expiry
    elif sale.status != PackageSaleStatus.ACTIVE:
        raise ValueError(f"Package not active (status={sale.status.value})")

    # 2. Expiry gate (unchanged, applies to everything)
    if sale.expires_at <= now:
        raise ValueError("Package expired")

    # 3. Budget gates — three-way branch
    group = None
    if sale_item.pool_exempt:
        pass  # no budget
    elif sale_item.sale_choice_group_id is not None:
        group = next(
            g for g in sale.choice_groups if g.id == sale_item.sale_choice_group_id
        )
        if group.remaining <= 0:
            raise ValueError("choice group budget exhausted for this package")
        if sale.entitlement_type_snapshot == EntitlementType.COUNTED and (
            not sale.sessions_remaining or sale.sessions_remaining <= 0
        ):
            raise ValueError("no sessions remaining")
    else:
        if sale.entitlement_type_snapshot == EntitlementType.COUNTED and (
            not sale.sessions_remaining or sale.sessions_remaining <= 0
        ):
            raise ValueError("no sessions remaining")
        if sale_item.remaining is not None and sale_item.remaining <= 0:
            raise ValueError("Per-line redemption cap exhausted for this service")
```

Decrement block becomes:

```python
    session_number = None
    if not sale_item.pool_exempt:
        if sale.entitlement_type_snapshot == EntitlementType.COUNTED:
            session_number = (
                (sale.total_sessions_snapshot or 0) - (sale.sessions_remaining or 0) + 1
            )
            sale.sessions_remaining -= 1
            if sale.sessions_remaining == 0:
                sale.status = PackageSaleStatus.EXHAUSTED
        if group is not None:
            group.remaining -= 1            # safe: sale row is locked
        elif sale_item.remaining is not None:
            sale_item.remaining -= 1
```

In `undo_redemption`, replace the restore block:

```python
    sale_item = db.get(PackageSaleItem, audit.package_sale_item_id)
    if sale_item is not None and not sale_item.pool_exempt:
        if sale.entitlement_type_snapshot == EntitlementType.COUNTED:
            sale.sessions_remaining = (sale.sessions_remaining or 0) + 1
            if sale.status == PackageSaleStatus.EXHAUSTED:
                sale.status = PackageSaleStatus.ACTIVE
        if sale_item.sale_choice_group_id is not None:
            group = db.get(PackageSaleChoiceGroup, sale_item.sale_choice_group_id)
            group.remaining += 1
        elif sale_item.remaining is not None:
            sale_item.remaining += 1
```

(Import `PackageSaleChoiceGroup`. Note the existing session-restore block is REPLACED — pool-exempt undo must not credit a session.)

- [ ] **Step 4: Run new + ALL existing redemption tests.**

- [ ] **Step 5: Commit** `feat(packages): group + pool-exempt redemption and undo`

---

### Task 7: Eligibility query

**Files:**
- Modify: `backend/app/services/package_eligibility.py`
- Test: `backend/tests/integration/test_package_eligibility.py` (extend)

- [ ] **Step 1: Failing tests**

```python
def test_group_member_eligible_until_group_exhausted(...):
    # group qty=1; redeem facial A → facial B no longer eligible
def test_pool_exempt_eligible_when_exhausted(...):
    # consume pool → EXHAUSTED; wash still eligible, haircut not
def test_pool_exempt_not_eligible_when_expired(...):
```

- [ ] **Step 2: Run, verify fail.**

- [ ] **Step 3: Rewrite the query.** Join sale items so per-line flags can relax the sale-level gates:

```python
    from app.models.package import PackageSaleChoiceGroup

    line_ok = or_(
        PackageSaleItem.pool_exempt.is_(True),
        and_(
            PackageSaleItem.sale_choice_group_id.isnot(None),
            PackageSaleItem.sale_choice_group_id.in_(
                db.query(PackageSaleChoiceGroup.id)
                  .filter(PackageSaleChoiceGroup.remaining > 0)
            ),
        ),
        and_(
            PackageSaleItem.sale_choice_group_id.is_(None),
            PackageSaleItem.pool_exempt.is_(False),
            or_(
                PackageSaleItem.max_redemptions.is_(None),
                PackageSaleItem.remaining > 0,
            ),
        ),
    )

    matching_sales = (
        db.query(PackageSaleItem.package_sale_id)
          .filter(PackageSaleItem.service_id == service_id)
          .filter(line_ok)
    )
    pool_exempt_sales = (
        db.query(PackageSaleItem.package_sale_id)
          .filter(PackageSaleItem.service_id == service_id)
          .filter(PackageSaleItem.pool_exempt.is_(True))
    )

    return (
        db.query(PackageSale)
          .filter(and_(
              # EXHAUSTED allowed only when the matching line is pool-exempt
              or_(
                  PackageSale.status == PackageSaleStatus.ACTIVE,
                  and_(
                      PackageSale.status == PackageSaleStatus.EXHAUSTED,
                      PackageSale.id.in_(pool_exempt_sales),
                  ),
              ),
              PackageSale.expires_at > now,
              PackageSale.id.in_(matching_sales),
              # Sessions gate also bypassed for pool-exempt matches
              or_(
                  PackageSale.entitlement_type_snapshot == EntitlementType.UNLIMITED,
                  PackageSale.sessions_remaining > 0,
                  PackageSale.id.in_(pool_exempt_sales),
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

- [ ] **Step 4: Run new + ALL existing eligibility tests** (the docstring filter list must be updated too).

- [ ] **Step 5: Commit** `feat(packages): eligibility for groups and pool-exempt lines`

---

### Task 8: Refund dedupe (money-critical)

**Files:**
- Modify: `backend/app/services/package_pricing_engine.py` (`_compute_counted_refund`)
- Test: `backend/tests/integration/test_package_refund.py` (extend)

`session_value_paise` currently sums `snapshot_unit_price_paise × quantity` over ALL sale items. With groups, the 3 member lines each hold the representative price — summing triple-counts. Pool-exempt lines snapshot at 0, so they're inert automatically.

- [ ] **Step 1: Failing test**

```python
def test_counted_refund_counts_each_group_once(...):
    # Freedom Pack sale (group qty=2, members snapshot at the same rep price R,
    # haircut line H qty 2, wash 0). Expected per-session value:
    #   H*2 + R*2 + 0   — NOT H*2 + R*3
```

- [ ] **Step 2: Run, verify fail** (value inflated by the extra member line).

- [ ] **Step 3: Implement** in `_compute_counted_refund`:

```python
    session_value_paise = 0
    seen_groups: set = set()
    for i in sale.items:
        if i.pool_exempt:
            continue
        group_id = getattr(i, "sale_choice_group_id", None)
        if group_id is not None:
            if group_id in seen_groups:
                continue
            seen_groups.add(group_id)
            group = next(g for g in sale.choice_groups if g.id == group_id)
            session_value_paise += i.snapshot_unit_price_paise * group.quantity
        else:
            session_value_paise += i.snapshot_unit_price_paise * i.quantity
```

- [ ] **Step 4: Run new + ALL refund tests; commit** `fix(packages): refund counts choice groups once`

---

### Task 9: Frontend types + payload

**Files:**
- Modify: `frontend/src/types/package.ts`
- Modify: `frontend/src/components/packages/PackageBuilder.tsx` (payload only)

- [ ] **Step 1:** Add to `types/package.ts`:

```typescript
export interface ChoiceGroup {
  id: string;
  name: string;
  quantity: number;
  display_order: number;
}

export interface ChoiceGroupCreate {
  name: string;
  quantity: number;
  display_order?: number;
}
```

Extend `PackageDefinitionItem` with `choice_group_id: string | null; pool_exempt: boolean;`, `PackageDefinition` with `choice_groups: ChoiceGroup[];`, and `PackageDefinitionCreate` with `choice_groups?: ChoiceGroupCreate[];` plus per-item `choice_group_name?: string | null; pool_exempt?: boolean;` (extend the `items` element type accordingly — the current `Omit<...>` needs `choice_group_id` added to the omit list and the two new fields added).

- [ ] **Step 2:** In `PackageBuilder.handleSave`, include `choice_groups` and per-item `choice_group_name`/`pool_exempt` in the payload (wired fully in Task 10). Run `tsc --noEmit` — only pre-existing errors allowed. Commit `feat(packages): frontend types for choice groups`.

---

### Task 10: Builder UI

**Files:**
- Create: `frontend/src/components/packages/ChoiceGroupEditor.tsx`
- Create: `frontend/src/components/packages/__tests__/ChoiceGroupEditor.test.tsx`
- Modify: `frontend/src/components/packages/PackageBuilderServicesTable.tsx`
- Modify: `frontend/src/components/packages/PackageBuilder.tsx`
- Modify: `frontend/src/components/packages/PackageBuilderDiscountControl.tsx`

UI design (keep boring and obvious for non-technical staff):
- A "Choice groups" section above the services table: add/remove groups, each with a name + "pick N" quantity (NumericCell pattern from the table).
- Each service line gets an "Entitlement" select with options: `Normal` / `Unlimited` / one per defined group (e.g. `Group: Facial choice`). Selecting a group disables that line's Qty + Limit inputs (group owns the budget; qty forced to 1). Selecting Unlimited disables Qty + Limit and shows a "FREE" badge on price-effect (price input stays — gross is still recorded).
- MRP shown must be group-aware: groups counted once at `max(member price) × group qty`, unlimited lines 0. Extract a tested helper:

```typescript
// frontend/src/components/packages/packagePricing.ts  (new file)
import type { LineItem } from "./PackageBuilderServicesTable";

export function grossTotalPaise(
  items: Array<LineItem & { choice_group_name?: string | null; pool_exempt?: boolean }>,
  groups: Array<{ name: string; quantity: number }>,
): number {
  let total = 0;
  const groupMax = new Map<string, number>();
  for (const it of items) {
    if (it.pool_exempt) continue;
    if (it.choice_group_name) {
      const prev = groupMax.get(it.choice_group_name) ?? 0;
      groupMax.set(it.choice_group_name, Math.max(prev, it.unit_price_paise));
    } else {
      total += it.unit_price_paise * it.quantity;
    }
  }
  for (const g of groups) {
    total += (groupMax.get(g.name) ?? 0) * g.quantity;
  }
  return total;
}
```

- `PackageBuilderDiscountControl` changes its prop from `items` to `totalPaise: number` (computed by the parent via `grossTotalPaise`) — update its internals (`totalPaise` was previously derived from `items.reduce`) and its tests' Harness accordingly.

- [ ] **Step 1: Failing tests** for `grossTotalPaise` (groups counted once at max, unlimited = 0, standalone unchanged) and for the table (selecting a group via the Entitlement select emits `choice_group_name` and forces `quantity: 1, max_redemptions: null`; selecting Unlimited emits `pool_exempt: true`).

- [ ] **Step 2: Implement.** `LineItem` gains `choice_group_name: string | null` and `pool_exempt: boolean`. `PackageBuilder` keeps `const [choiceGroups, setChoiceGroups] = useState<ChoiceGroupCreate[]>(initial?.choice_groups ?? [])`, renders `<ChoiceGroupEditor groups={choiceGroups} onChange={setChoiceGroups} />` above the services table, passes `groups` into the table for the per-line select, and sends both in the payload. Renaming or deleting a group must clear `choice_group_name` on orphaned lines (do it in the `onChange` handler in `PackageBuilder`, not inside the editor).

- [ ] **Step 3: Run all frontend package tests + `tsc --noEmit`.**

- [ ] **Step 4: Commit** `feat(packages): builder UI for choice groups and unlimited lines`

---

### Task 11: Edit round-trip

**Files:**
- Modify: `frontend/src/app/(shell)/dashboard/packages/[id]/edit/page.tsx`

- [ ] **Step 1:** Map API response → builder state: `choice_groups: d.choice_groups.map(g => ({name: g.name, quantity: g.quantity, display_order: g.display_order}))`, and per item resolve `choice_group_name` from `choice_group_id` via a `Map(d.choice_groups.map(g => [g.id, g.name]))`, plus `pool_exempt: it.pool_exempt`.

- [ ] **Step 2:** Manually verify in the running app: create the Freedom Pack (2 haircuts + facial group of 3 pick-2 + unlimited wash, final price), save, reopen Edit, confirm every value round-trips. Run `tsc`. Commit `feat(packages): edit round-trip for choice groups`.

---

### Task 12: Docs + review pipeline

- [ ] **Step 1:** Update `docs/models/10-packages.md`: new tables, columns, the three-way redemption semantics, the EXHAUSTED-but-pool-exempt rule, the group pricing rule (max member price), the lock invariant ("group counters are mutated only under the PackageSale row lock").
- [ ] **Step 2:** Run the FULL backend package suite + full frontend package suite one more time.
- [ ] **Step 3:** Run the review pipeline: `@code-reviewer` → `@security-auditor` → `@tester` on the complete diff.
- [ ] **Step 4:** Commit docs; final commit message `docs(packages): choice groups + unlimited lines`.

---

## Top Risks (carry into review)

1. **Refund triple-count (Task 8)** — over-refunds real cash if missed; the test in Task 8 is the guard.
2. **Eligibility blocking the unlimited perk (Task 7)** — EXHAUSTED + pool-exempt must stay redeemable; covered by `test_pool_exempt_eligible_when_exhausted`.
3. **Group counter concurrency (Task 6)** — group `remaining` is only safe under the sale-row `SELECT FOR UPDATE`; the `CHECK remaining >= 0` is the last-resort guard. Never touch the counter outside `apply_redemption`/`undo_redemption`.
4. **Undo restoring the wrong budget (Task 6)** — keyed off `audit.package_sale_item_id` + snapshot flags; pool-exempt undo must restore nothing.
5. **Group restructuring on sold packages (Task 4)** — RESTRICT FKs make hard-deleting referenced groups fail; surface a clean ValueError. Snapshots keep already-sold packages on their original semantics.
