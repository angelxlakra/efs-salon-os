# Buy-and-Use-Immediately Package Flow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let a single POS cart **sell a v2 package AND redeem that package's own services in the same checkout** — the customer pays the package price and walks out with the included services applied, without a prior purchase.

**Architecture:** A service line can be flagged to redeem from a package being *sold in the same bill* (by its **definition id**, since the `PackageSale` doesn't exist yet). At posting, `_create_package_sales_for_bill` creates the sale first, then a new pass applies redemptions for those flagged service lines against the just-created sale. The frontend treats a `package_sale` cart line as an eligibility source, computing its budget from the definition's blocks, and allocates redemptions against it after owned packages.

**Tech Stack:** FastAPI 0.115 / SQLAlchemy 2.0 / Alembic / Pydantic v2 / pytest (backend); Next.js 16 / React 19 / Zustand / Vitest (frontend).

**Heads at plan-write time:** alembic `w6x7y8z9a0b1`. Backend tests:
```bash
cd backend && REDIS_URL=redis://localhost:6379/0 \
  DATABASE_URL="postgresql+psycopg://salon_user:change_me_123@127.0.0.1:5432/salon_test_db" \
  SECRET_KEY=test SALON_NAME=t SALON_ADDRESS=t GSTIN=t uv run pytest <path> -q
```
Frontend tests: `cd frontend && PATH="$HOME/.nvm/versions/node/v22.20.0/bin:$PATH" ./node_modules/.bin/vitest run --config vitest.config.mts <path>`.

**Key invariants (already true):**
- `PackageSale` is created at POSTING via `_create_package_sales_for_bill` (billing_service.py:1842), called from every path that sets `BillStatus.POSTED` (lines 441, 1040, 1211, 1615).
- Owned-package redemptions run at **draft** create_bill via `redemption_intents` → `apply_redemption(package_sale_id=...)`.
- `apply_redemption` is quantity-aware and budget-aware (block counter / global pool / per-line cap); `find_eligible_packages` + `check_eligibility` expose `line_remaining` + `shared_budget_key` + `shared_remaining`.
- `create_sale` projects a v2 definition's blocks onto `PackageSaleItem`s + `PackageSaleBlock` counters via `_block_sale_lines`.

**Decision — when the immediate redemption commits:** at **posting**, NOT at draft. The sale only exists once posted, and redeeming against an unpaid bundle makes no sense. This means an immediate-redemption service line stays a normal `SERVICE` (charged) on a draft bill and flips to `PACKAGE_REDEMPTION` (free, covered by an internal payment) when the bill posts. The cart preview shows it free; the draft bill momentarily shows it charged until posted (acceptable — drafts aren't customer-facing receipts).

---

## File Structure

**Backend — modified**
- `backend/app/models/billing.py` — add `BillItem.redeem_from_definition_id` (the cart-package definition a service line redeems from)
- `backend/app/schemas/billing.py` — `BillItemCreate.redeem_from_definition_id` field
- `backend/app/services/billing_service.py` — pass the new field into `BillItem`; new redemption pass inside `_create_package_sales_for_bill`
- `backend/alembic/versions/x7y8z9a0b1c2_billitem_redeem_from_definition.py` — migration (new)

**Frontend — modified**
- `frontend/src/lib/packages/definition-budget.ts` — **new**: pure helper computing per-service redeemable budget from a `PackageDefinition`'s blocks
- `frontend/src/stores/cart-store.ts` — `CartItem.redemption` gains an optional `fromDefinitionId` (redeem from a cart package, not an owned sale)
- `frontend/src/hooks/usePackageAutoRedeem.ts` — after owned packages, allocate remaining service-line units against cart `package_sale` lines using `definition-budget`
- `frontend/src/components/pos/payment-modal.tsx` — emit `redeem_from_definition_id` for those lines
- `frontend/src/components/pos/cart-sidebar.tsx` — badge copy ("Free with this package")

**Tests**
- `backend/tests/integration/test_buy_and_use_package.py` — **new**: end-to-end (sell + immediate redeem at posting)
- `frontend/src/lib/packages/__tests__/definition-budget.test.ts` — **new**
- `frontend/src/stores/__tests__/cart-redemption.test.ts` — extend

---

## Task Sequencing Logic

Backend substrate first (column → schema → service write → posting redemption), each independently committable and testable; then the frontend budget helper, allocation, and payload. The money-critical posting pass (Task 3) is TDD'd against a full sell-and-post integration test.

---

### Task 1: BillItem column + migration

**Files:**
- Modify: `backend/app/models/billing.py` (after `package_locked_choices`, ~line 264)
- Create: `backend/alembic/versions/x7y8z9a0b1c2_billitem_redeem_from_definition.py`

- [ ] **Step 1: Add the model column.** In `backend/app/models/billing.py`, right after the `package_locked_choices` column:

```python
    # Buy-and-use-immediately: a SERVICE line that should be redeemed from a
    # package SOLD IN THE SAME BILL (its PackageSale doesn't exist until posting,
    # so we reference the definition; settlement resolves it to the new sale).
    redeem_from_definition_id = Column(
        String(26), ForeignKey("package_definitions.id", ondelete="RESTRICT"),
        nullable=True, index=True,
    )
```

- [ ] **Step 2: Write the migration.**

```python
"""Add BillItem.redeem_from_definition_id for buy-and-use-immediately.

Revision ID: x7y8z9a0b1c2
Revises: w6x7y8z9a0b1
Create Date: 2026-06-16
"""

from alembic import op
import sqlalchemy as sa

revision = "x7y8z9a0b1c2"
down_revision = "w6x7y8z9a0b1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "bill_items",
        sa.Column("redeem_from_definition_id", sa.String(26),
                  sa.ForeignKey("package_definitions.id", ondelete="RESTRICT"),
                  nullable=True),
    )
    op.create_index(
        "ix_bill_items_redeem_from_definition_id", "bill_items",
        ["redeem_from_definition_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_bill_items_redeem_from_definition_id", "bill_items")
    op.drop_column("bill_items", "redeem_from_definition_id")
```

- [ ] **Step 3: Verify chain + apply to test DB.**

Run: `cd backend && uv run alembic heads`
Expected: `x7y8z9a0b1c2 (head)`
(Test DB is built from metadata via `create_all`, so the model column alone makes it available to tests; apply to dev DB with `docker exec salon-api sh -c 'cd /app && alembic upgrade head'` before live testing.)

- [ ] **Step 4: Commit**

```bash
git add backend/app/models/billing.py backend/alembic/versions/x7y8z9a0b1c2_billitem_redeem_from_definition.py
git commit -m "feat(billing): BillItem.redeem_from_definition_id for buy-and-use packages"
```

---

### Task 2: Accept the field through the bill-create schema + service

**Files:**
- Modify: `backend/app/schemas/billing.py` (`BillItemCreate`, ~line 25-48)
- Modify: `backend/app/services/billing_service.py` (`create_bill` service branch, ~line 551-566)
- Test: `backend/tests/integration/test_billing_cart_redemption.py` (extend)

- [ ] **Step 1: Write the failing test** (append to `test_billing_cart_redemption.py`):

```python
def test_bill_item_create_schema_preserves_redeem_from_definition_id():
    """The API schema must carry redeem_from_definition_id to the service."""
    from app.schemas.billing import BillItemCreate
    dumped = BillItemCreate(
        service_id="01HXX" + "A" * 21,
        redeem_from_definition_id="01HZZ" + "C" * 21,
    ).model_dump()
    assert dumped.get("redeem_from_definition_id") == "01HZZ" + "C" * 21
```

- [ ] **Step 2: Run, verify it fails** (field unknown → dropped by Pydantic).

Run: `... uv run pytest tests/integration/test_billing_cart_redemption.py::test_bill_item_create_schema_preserves_redeem_from_definition_id -q`
Expected: FAIL (`assert None == ...`).

- [ ] **Step 3: Add the schema field.** In `backend/app/schemas/billing.py`, inside `BillItemCreate`, after `package_sale_id`:

```python
    # Buy-and-use-immediately: redeem this service from a package being SOLD in
    # the same cart (by definition id; resolved to the new sale at posting).
    redeem_from_definition_id: Optional[str] = Field(None, min_length=26, max_length=26)
```

- [ ] **Step 4: Thread it into the BillItem in `create_bill`.** In `backend/app/services/billing_service.py`, in the service-line branch that builds `bill_item_data` (the dict with `"service_id": service.id, ...`), add a key:

```python
                    "redeem_from_definition_id": item.get("redeem_from_definition_id"),
```

(The dict is later splatted into `BillItem(**item_data)` at ~line 677, so the column is set directly. A normal service line passes `None`.)

- [ ] **Step 5: Run the schema test (pass) + the existing cart-redemption file.**

Run: `... uv run pytest tests/integration/test_billing_cart_redemption.py -q`
Expected: PASS (the intra-file duplicate-category error on the 2nd test is pre-existing pollution; run tests individually to confirm green).

- [ ] **Step 6: Commit**

```bash
git add backend/app/schemas/billing.py backend/app/services/billing_service.py backend/tests/integration/test_billing_cart_redemption.py
git commit -m "feat(billing): accept redeem_from_definition_id on service lines"
```

---

### Task 3: Redeem flagged lines at posting (money-critical)

**Files:**
- Modify: `backend/app/services/billing_service.py` (`_create_package_sales_for_bill`, ~line 1842-1875)
- Create: `backend/tests/integration/test_buy_and_use_package.py`

**Design:** `_create_package_sales_for_bill` already creates a `PackageSale` per `PACKAGE_SALE_LINE` and sets `item.package_sale_id`. After that loop, build a `{definition_id: sale_id}` map from the just-created sales, then for every `SERVICE` bill item with `redeem_from_definition_id` set, call `apply_redemption` against the matching sale. `apply_redemption` already validates coverage (service must be in the sale's items), budget, and quantity — so an over-claim raises and aborts the post.

- [ ] **Step 1: Write the failing integration test.**

```python
"""Buy a v2 package and redeem its services in the same bill at posting."""

from app.services.billing_service import BillingService
from app.schemas.billing import BillItemCreate
from app.models.billing import BillItemType, Payment, PaymentMethod, BillStatus
from app.schemas.package import PackageDefinitionCreate
from app.models.package import Shareability
from app.services.package_catalog_service import create_definition, publish


def _make_service(db_session, suffix, price):
    from app.models.service import Service, ServiceCategory
    cat = ServiceCategory(name=f"Cat{suffix}", display_order=1, is_active=True)
    db_session.add(cat); db_session.flush()
    svc = Service(category_id=cat.id, name=f"Svc{suffix}", base_price=price,
                  duration_minutes=30, is_active=True, display_order=1)
    db_session.add(svc); db_session.flush()
    return svc


def test_buy_package_and_redeem_its_service_same_bill(
    db_session, customer_factory, test_user
):
    eyebrow = _make_service(db_session, "EB", 3000)
    pkg = create_definition(db_session, PackageDefinitionCreate(
        name="Basic Care", validity_days=1, shareability=Shareability.OWNER_ONLY,
        blocks=[{"id": "b1", "kind": "items", "bonus": False,
                 "rows": [{"service_id": eyebrow.id, "quantity": "1",
                           "unit_price_paise": 3000}]}],
        final_price_paise=2500,
    ), test_user.id)
    publish(db_session, pkg.id)
    customer = customer_factory()

    svc = BillingService(db_session)
    # Cart: the package line + the eyebrow service redeemed from it.
    items = [
        BillItemCreate(package_definition_id=pkg.id).model_dump(),
        BillItemCreate(service_id=eyebrow.id, quantity=1,
                       redeem_from_definition_id=pkg.id).model_dump(),
    ]
    bill = svc.create_bill(items=items, created_by_id=test_user.id,
                           customer_id=customer.id)

    # On the DRAFT bill the service is still a normal charge (sale not yet made).
    eb_line = next(i for i in bill.items if i.service_id == eyebrow.id)
    assert eb_line.item_type == BillItemType.SERVICE

    # Post the bill (pay the package price). Use the lowest-level post helper.
    svc._create_package_sales_for_bill(bill, test_user.id)
    db_session.flush()

    # Now the eyebrow line is redeemed from the newly-created sale.
    db_session.refresh(eb_line)
    assert eb_line.item_type == BillItemType.PACKAGE_REDEMPTION
    assert eb_line.package_sale_id is not None
    # An internal redemption payment covers it.
    pay = (db_session.query(Payment)
           .filter(Payment.bill_id == bill.id,
                   Payment.payment_method == PaymentMethod.PACKAGE_REDEMPTION)
           .first())
    assert pay is not None


def test_redeem_from_definition_not_in_bill_is_ignored_safely(
    db_session, customer_factory, test_user
):
    """A flagged line whose package isn't sold in this bill stays charged."""
    eyebrow = _make_service(db_session, "EB2", 3000)
    pkg = create_definition(db_session, PackageDefinitionCreate(
        name="Care2", validity_days=1, shareability=Shareability.OWNER_ONLY,
        blocks=[{"id": "b1", "kind": "items", "bonus": False,
                 "rows": [{"service_id": eyebrow.id, "quantity": "1",
                           "unit_price_paise": 3000}]}],
        final_price_paise=2500,
    ), test_user.id)
    publish(db_session, pkg.id)
    customer = customer_factory()
    svc = BillingService(db_session)
    bill = svc.create_bill(
        items=[BillItemCreate(service_id=eyebrow.id, quantity=1,
                              redeem_from_definition_id=pkg.id).model_dump()],
        created_by_id=test_user.id, customer_id=customer.id,
    )
    svc._create_package_sales_for_bill(bill, test_user.id)
    db_session.flush()
    line = next(i for i in bill.items if i.service_id == eyebrow.id)
    assert line.item_type == BillItemType.SERVICE  # no matching sale → still charged
```

- [ ] **Step 2: Run, verify both fail** (no posting redemption yet; first test's eyebrow stays SERVICE after post).

Run: `... uv run pytest tests/integration/test_buy_and_use_package.py -q`
Expected: FAIL on the first test (`PACKAGE_REDEMPTION != SERVICE`).

- [ ] **Step 3: Implement the posting redemption pass.** In `_create_package_sales_for_bill`, after the existing loop that creates sales, append:

```python
        # Buy-and-use-immediately: redeem service lines flagged to draw from a
        # package SOLD in this same bill, now that the sale exists.
        from app.services import package_redemption_service
        sale_by_definition = {
            i.package_definition_id: i.package_sale_id
            for i in bill.items
            if i.item_type == BillItemType.PACKAGE_SALE_LINE and i.package_sale_id
        }
        for item in bill.items:
            if (
                item.item_type == BillItemType.SERVICE
                and item.redeem_from_definition_id
                and item.redeem_from_definition_id in sale_by_definition
            ):
                package_redemption_service.apply_redemption(
                    db=self.db,
                    package_sale_id=sale_by_definition[item.redeem_from_definition_id],
                    bill_item_id=item.id,
                    redeemed_for_customer_id=bill.customer_id,
                    user_id=user_id,
                )
                self.db.flush()
```

(A flagged line whose definition isn't sold in this bill is simply skipped — stays a charged `SERVICE`, satisfying the second test.)

- [ ] **Step 4: Run, verify both pass.** Then run the broader package + billing suites individually to confirm no regression:

Run: `... uv run pytest tests/integration/test_buy_and_use_package.py tests/integration/test_billing_cart_redemption.py tests/integration/test_package_redemption.py -q`
Expected: PASS (ignore the known intra-file duplicate-category pollution when files are batched).

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/billing_service.py backend/tests/integration/test_buy_and_use_package.py
git commit -m "feat(billing): redeem same-cart package services at posting"
```

---

### Task 4: Frontend — per-service budget from a definition

**Files:**
- Create: `frontend/src/lib/packages/definition-budget.ts`
- Test: `frontend/src/lib/packages/__tests__/definition-budget.test.ts`

This mirrors the backend `_block_sale_lines` budget logic but reads a `PackageDefinition`'s blocks (what the cart has before any sale exists). Returns, per service_id, a `lineRemaining` and a `sharedBudgetKey`/`sharedRemaining` so the cart allocator (Task 5) treats a cart package exactly like an owned one.

- [ ] **Step 1: Write the failing test.**

```typescript
import { describe, expect, it } from "vitest";
import { definitionServiceBudgets } from "@/lib/packages/definition-budget";
import type { PackageBlock } from "@/types/package";

const items = (rows: Array<[string, number]>): PackageBlock => ({
  id: "i", kind: "items", bonus: false,
  rows: rows.map(([service_id, qty]) => ({
    service_id, service_name: service_id, quantity: String(qty), unit_price_paise: 3000,
  })),
});

describe("definitionServiceBudgets", () => {
  it("gives each fixed-items service its own cap + a shared global pool", () => {
    const b = definitionServiceBudgets("def1", [items([["eyebrow", 1], ["upperlip", 1]])]);
    expect(b.get("eyebrow")).toEqual({
      lineRemaining: 1, sharedKey: "def1:pool", sharedRemaining: 2,
    });
    expect(b.get("upperlip")!.lineRemaining).toBe(1);
  });

  it("gives a choice@visit block its own shared counter (no per-line cap)", () => {
    const block: PackageBlock = {
      id: "c", kind: "choice", bonus: false, picks: "2", choose_at: "visit",
      rows: [
        { service_id: "a", service_name: "A", unit_price_paise: 1 },
        { service_id: "b", service_name: "B", unit_price_paise: 1 },
      ],
    };
    const b = definitionServiceBudgets("def1", [block]);
    expect(b.get("a")).toEqual({
      lineRemaining: 9999, sharedKey: "def1:block:c", sharedRemaining: 2,
    });
  });
});
```

- [ ] **Step 2: Run, verify it fails** (module missing).

- [ ] **Step 3: Implement.**

```typescript
// frontend/src/lib/packages/definition-budget.ts
// Per-service redeemable budget derived from a PackageDefinition's blocks —
// the cart-side mirror of the backend _block_sale_lines mapping, so a package
// being SOLD in the cart can be an eligibility source before its sale exists.

import type { PackageBlock } from "@/types/package";

const UNLIMITED = 9999;

export interface ServiceBudget {
  lineRemaining: number;
  sharedKey: string | null;
  sharedRemaining: number;
}

const num = (v: string) => {
  const n = parseInt(v);
  return Number.isFinite(n) ? n : 0;
};

export function definitionServiceBudgets(
  definitionId: string,
  blocks: PackageBlock[]
): Map<string, ServiceBudget> {
  const out = new Map<string, ServiceBudget>();
  // Global pool = Σ over fixed-items qty + choice@purchase picks (mirrors backend).
  let pool = 0;
  for (const b of blocks) {
    if (b.kind === "items") for (const r of b.rows) pool += num(r.quantity) || 1;
    else if (b.kind === "choice" && b.choose_at === "purchase") pool += num(b.picks);
  }
  const poolKey = `${definitionId}:pool`;

  blocks.forEach((b, idx) => {
    if (b.kind === "items") {
      for (const r of b.rows) {
        out.set(r.service_id, {
          lineRemaining: num(r.quantity) || 1,
          sharedKey: poolKey,
          sharedRemaining: pool,
        });
      }
    } else if (b.kind === "choice" && b.choose_at === "purchase") {
      // Purchase-locked: each option a single-use line drawing the global pool.
      for (const r of b.rows) {
        out.set(r.service_id, { lineRemaining: 1, sharedKey: poolKey, sharedRemaining: pool });
      }
    } else if (b.kind === "choice") {
      // choice@visit: independent shared counter of `picks`.
      const key = `${definitionId}:block:${b.id}`;
      for (const r of b.rows) {
        out.set(r.service_id, { lineRemaining: UNLIMITED, sharedKey: key, sharedRemaining: num(b.picks) });
      }
    } else if (b.kind === "pool") {
      const key = `${definitionId}:block:${b.id}`;
      for (const r of b.rows) {
        out.set(r.service_id, { lineRemaining: UNLIMITED, sharedKey: key, sharedRemaining: num(b.sessions) });
      }
    } else if (b.kind === "unlimited") {
      for (const r of b.rows) {
        out.set(r.service_id, { lineRemaining: UNLIMITED, sharedKey: null, sharedRemaining: UNLIMITED });
      }
    }
    // credit: no service redemption
    void idx;
  });
  return out;
}
```

- [ ] **Step 4: Run, verify pass.**

- [ ] **Step 5: Commit** `feat(packages): per-service budget from a definition`

---

### Task 5: Frontend — allocate against cart packages too

**Files:**
- Modify: `frontend/src/stores/cart-store.ts` (`CartItem.redemption` type)
- Modify: `frontend/src/hooks/usePackageAutoRedeem.ts`
- Test: `frontend/src/stores/__tests__/cart-redemption.test.ts` (extend — assert the math; the hook itself is integration-tested in-app)

- [ ] **Step 1: Extend the redemption type.** In `cart-store.ts`, the `redemption` object on `CartItem`:

```typescript
  redemption?: {
    packageSaleId: string | null;   // owned package (null when redeeming from a cart package)
    fromDefinitionId?: string;      // cart package being sold this checkout
    packageName: string;
    coveredQuantity: number;
  } | null;
```

(`packageSaleId` becomes nullable; `chargedUnits` and all cart math already key only off `coveredQuantity`, so no math change is needed.)

- [ ] **Step 2: Allocate cart packages after owned ones in the hook.** In `usePackageAutoRedeem.ts`, after the owned-package `allocate(...)` assigns redemptions, run a SECOND allocation pass over still-uncovered service-line units against each cart `package_sale` line's budget (from `definitionServiceBudgets`). Full replacement of the `allocate` body:

```typescript
    function allocate(lines: typeof serviceLines) {
      const lineBudget = new Map<string, number>();
      const sharedBudget = new Map<string, number>();
      for (const sid of new Set(lines.map((l) => l.serviceId!))) {
        const e = eligByService.current.get(sid);
        if (!e) continue;
        lineBudget.set(sid, e.lineRemaining);
        if (e.sharedKey && !sharedBudget.has(e.sharedKey)) sharedBudget.set(e.sharedKey, e.sharedRemaining);
      }

      // Cart packages being sold this checkout — budgets from their definitions.
      const cartPkgs = items.filter((it) => it.kind === "package_sale" && it.packageDefinitionId);
      const cartBudgets = cartPkgs.map((p) => {
        const def = definitions?.find((d) => d.id === p.packageDefinitionId);
        return {
          definitionId: p.packageDefinitionId!,
          packageName: p.packageName ?? "Package",
          budgets: def?.blocks ? definitionServiceBudgets(def.id, def.blocks) : new Map(),
        };
      });
      const cartLineBudget = new Map<string, number>();   // `${defId}:${sid}`
      const cartSharedBudget = new Map<string, number>(); // sharedKey

      for (const line of lines) {
        const sid = line.serviceId!;
        let coveredByOwned = 0;
        let next:
          | { packageSaleId: string | null; fromDefinitionId?: string; packageName: string; coveredQuantity: number }
          | null = null;

        // 1) Owned package first.
        const e = eligByService.current.get(sid);
        if (e) {
          const lineLeft = lineBudget.get(sid) ?? 0;
          const poolLeft = e.sharedKey ? sharedBudget.get(e.sharedKey) ?? 0 : Infinity;
          coveredByOwned = Math.min(line.quantity, lineLeft, poolLeft);
          if (coveredByOwned > 0) {
            next = { packageSaleId: e.packageSaleId, packageName: e.packageName, coveredQuantity: coveredByOwned };
            lineBudget.set(sid, lineLeft - coveredByOwned);
            if (e.sharedKey) sharedBudget.set(e.sharedKey, poolLeft - coveredByOwned);
          }
        }

        // 2) Cart package covers the remaining units.
        let remaining = line.quantity - coveredByOwned;
        if (remaining > 0) {
          for (const cp of cartBudgets) {
            const sb = cp.budgets.get(sid);
            if (!sb) continue;
            const lk = `${cp.definitionId}:${sid}`;
            if (!cartLineBudget.has(lk)) cartLineBudget.set(lk, sb.lineRemaining);
            const sk = sb.sharedKey;
            if (sk && !cartSharedBudget.has(sk)) cartSharedBudget.set(sk, sb.sharedRemaining);
            const lineLeft = cartLineBudget.get(lk)!;
            const poolLeft = sk ? cartSharedBudget.get(sk)! : Infinity;
            const cover = Math.min(remaining, lineLeft, poolLeft);
            if (cover > 0) {
              cartLineBudget.set(lk, lineLeft - cover);
              if (sk) cartSharedBudget.set(sk, poolLeft - cover);
              next = {
                packageSaleId: null,
                fromDefinitionId: cp.definitionId,
                packageName: cp.packageName,
                coveredQuantity: coveredByOwned + cover,
              };
              remaining -= cover;
              break;
            }
          }
        }

        const cur = line.redemption ?? null;
        const same =
          (cur === null && next === null) ||
          (!!cur && !!next &&
            cur.packageSaleId === next.packageSaleId &&
            (cur.fromDefinitionId ?? null) === (next.fromDefinitionId ?? null) &&
            cur.coveredQuantity === next.coveredQuantity);
        if (!same) setLineRedemption(line.id, next);
      }
    }
```

Add at the top of the hook: `const definitions = useCartStore.getState; ` — NO; instead read the published definitions the cart already loads. Import and subscribe:

```typescript
import { usePackagesStore } from "@/stores/packages-store";
// inside the hook:
const definitions = usePackagesStore((s) => s.definitions);
```

and add `definitions` to the effect dependency array.

- [ ] **Step 3: Extend the cart-store test** (`cart-redemption.test.ts`) — a redeemed line with `packageSaleId: null, fromDefinitionId, coveredQuantity` still excludes covered units:

```typescript
  it("treats a cart-package redemption like any other for charged units", () => {
    const store = useCartStore.getState();
    store.addItem(svc({ serviceId: "s1", unitPrice: 3000, quantity: 1 }));
    const line = useCartStore.getState().items.find((i) => i.serviceId === "s1")!;
    store.setLineRedemption(line.id, {
      packageSaleId: null, fromDefinitionId: "def1", packageName: "Basic Care", coveredQuantity: 1,
    });
    expect(useCartStore.getState().getSubtotal()).toBe(0);
  });
```

- [ ] **Step 4: Run frontend tests + `tsc --noEmit`.**

Run: `cd frontend && PATH="$HOME/.nvm/versions/node/v22.20.0/bin:$PATH" ./node_modules/.bin/vitest run --config vitest.config.mts src/stores src/lib`
Expected: PASS. `tsc` clean (ignore the pre-existing dashboard/e2e errors).

- [ ] **Step 5: Commit** `feat(pos): redeem services from a package being bought in the same cart`

---

### Task 6: Frontend — send the flag + label the line

**Files:**
- Modify: `frontend/src/components/pos/payment-modal.tsx` (`buildBillPayload`, the service branch added previously)
- Modify: `frontend/src/components/pos/cart-sidebar.tsx` (redemption badge)

- [ ] **Step 1: Emit the field in `buildBillPayload`.** In the redeemed-portion object (the `covered > 0` push), make it send EITHER the owned sale id OR the cart-definition id:

```typescript
          if (covered > 0) {
            out.push({
              service_id: item.serviceId,
              quantity: covered,
              unit_price: item.unitPrice,
              discount: 0,
              ...(item.redemption!.packageSaleId
                ? { package_sale_id: item.redemption!.packageSaleId }
                : { redeem_from_definition_id: item.redemption!.fromDefinitionId }),
              ...staffFields,
            });
          }
```

- [ ] **Step 2: Badge copy.** In `cart-sidebar.tsx`, where the redemption badge text is built, distinguish the cart-package case:

```tsx
                      {item.redemption.fromDefinitionId
                        ? `Free with this package · ${item.redemption.packageName}`
                        : item.redemption.coveredQuantity < item.quantity
                          ? `${item.redemption.coveredQuantity} of ${item.quantity} free · ${item.redemption.packageName}`
                          : `Redeemed · ${item.redemption.packageName}`}
```

- [ ] **Step 3: Run `tsc --noEmit` + lint the two files.** Expected: clean (warnings only).

- [ ] **Step 4: Manual verification in-app** (after rebuilding `salon-api` + `salon-frontend`):
  1. Sell-and-use: add the "Basic Care Package" line + its Eyebrow service to one cart with a customer → Eyebrow shows "Free with this package", Grand Total = package price only.
  2. Post the bill → the Eyebrow line settles as a redemption (free), the package as its sale; the new `PackageSale` shows the remaining services still available.
  3. Over-claim guard: add a service the package covers once, twice → 2nd is charged.

- [ ] **Step 5: Commit** `feat(pos): wire buy-and-use payload + cart label`

---

### Task 7: Docs

**Files:**
- Modify: `docs/models/10-packages.md`

- [ ] **Step 1:** Under the v2 sell/redeem section, add a paragraph: buy-and-use-immediately lets a service line carry `redeem_from_definition_id`; on a draft bill it's a normal charge, and at posting `_create_package_sales_for_bill` creates the sale then redeems the flagged lines against it (validated by `apply_redemption` for coverage + budget + quantity). The cart previews it free by allocating against the cart package's definition budget after owned packages.
- [ ] **Step 2: Commit** `docs(packages): buy-and-use-immediately flow`

---

## Top Risks (carry into review)

1. **Posting-order correctness (Task 3)** — sales MUST be created before the redemption pass. Both happen inside `_create_package_sales_for_bill` in that order; never split them across methods.
2. **Double redemption** — a service line must not be redeemed twice (once as owned at draft, once as cart at posting). The frontend assigns each line EITHER `packageSaleId` (owned, drafted) OR `fromDefinitionId` (cart, posting), never both; the backend draft pass only acts on `package_sale_id`, the posting pass only on `redeem_from_definition_id`.
3. **Over-claim at posting raises mid-post** — `apply_redemption` raises if the service isn't covered or budget is exceeded, aborting the post. The frontend caps optimistically (Task 5), so this should be rare, but the abort must roll back cleanly (caller owns the transaction — it does).
4. **Multiple same-definition packages in one cart** — `sale_by_definition` keeps the LAST sale per definition; if two identical packages are sold, only one is targeted. Acceptable for v1; note it (a flagged line picks one). Selling two different definitions works.
5. **Repost / void interaction** — `_create_package_sales_for_bill` runs on every POSTED transition and guards on `not item.package_sale_id`; the new redemption pass guards on `item.item_type == SERVICE` (a redeemed line becomes `PACKAGE_REDEMPTION`, so it won't re-redeem). Verify a void→repost doesn't double-apply.

## Self-Review Notes

- **Spec coverage:** sell+redeem same cart (Tasks 1-6), posting-time creation order (Task 3), cart preview (Tasks 4-5), payload (Task 6), docs (Task 7). ✓
- **Type consistency:** `redeem_from_definition_id` (backend column + schema + payload key) and `fromDefinitionId`/`packageSaleId: string|null` (frontend redemption) are used identically across tasks. `definitionServiceBudgets` / `ServiceBudget` shapes match the hook in Task 5. ✓
- **Money path:** every redemption still flows through the single `apply_redemption` (budget/quantity/coverage validated); the bill total includes the package price; internal payments cover redeemed services. ✓
