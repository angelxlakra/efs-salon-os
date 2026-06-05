# Bundles & Session Packages — Sub-Project A

**Date:** 2026-05-29
**Status:** Approved (engineering spec) — implementation plan to follow via `writing-plans` skill
**Companion files:**
- Brief (input to design): `2026-05-29-bundles-packages-frontend-design-brief.md`
- Design output: `2026-05-29-bundles-packages-design-output.md`
- Design open-questions (resolved): `2026-05-29-bundles-packages-design-open-questions.md`
- Mockups: `design-assets/2026-05-29-bundles-packages/` (35 PNGs)

---

## 1. Goal

Introduce **packages** as a first-class transactional primitive in SalonOS: pre-paid, multi-service or unlimited entitlements that customers buy once and redeem over time. Covers single-sitting bundles (e.g. "Bridal Glam = Hair + Makeup + Nails @ ₹5,200"), counted multi-session packs (e.g. "10 × Hair Spa @ ₹6,000, valid 180 days"), and unlimited time-bound entitlements (e.g. "Unlimited hair wash, valid 30 days @ ₹1,500"). Includes per-package shareability between registered customers (family/friends), auto-application at POS with conflict resolution, Owner-only refunds with cancellation fee, and audit-logged expiry extensions.

This is the foundation for sub-project B (memberships with recurring billing), sub-project C (customer 360 + tabbed profile), sub-project D (loyalty tiering), and sub-project E (AI recommendations).

---

## 2. Scope

### 2.1 In scope (sub-project A)

- New `PackageDefinition` catalog (admin CRUD, Owner-only)
- POS integration: sell a package, redeem against active packages, multi-package conflict resolution, Entitlements Rail
- Snapshotted per-line pricing with three discount input modes (% / ₹ off / Final amount) and per-line override
- Counted vs Unlimited entitlement types; Owner-only vs Shared shareability
- Hard expiry with Owner-only audit-logged extension
- Refund with configurable cancellation fee, accessible from the sale's Bill detail page (`/dashboard/bills/[id]`) — credit-note flow
- Internal payment method `package_redemption` for the zero-cash redemption case
- Per-package GST recognition at sale (prepaid)
- New backend permissions per the matrix in §6
- New primitives in the UI library: `SessionsLeft`, `ExpiryBadge`
- Background job: daily expiry status transition + reminder-flag flip
- Alembic migration (additive, reversible)

### 2.2 Out of scope (deferred to other sub-projects)

| Concern | Deferred to |
|---|---|
| Recurring / auto-renewing billing (subscriptions) | **Sub-project B** (Memberships) — same entitlement model, layered billing cadence |
| Customer profile promotion (dialog → tabbed page) + Packages tab + Overview tab | **Sub-project C** (Customer 360) — design output's customer-side mockups are pre-baked input |
| Loyalty tiering (Bronze/Silver/Gold/Platinum) | **Sub-project D** — tier badge slot reserved next to customer name |
| AI recommendations on POS / appointments | **Sub-project E** — Overview-rail slot reserved |
| Package transferability between customers (true transfer of ownership) | Not planned — shared redemption per §3.5 covers the family use case |
| Offers / promotions (rule-based discounts, e.g. "20% off Tuesdays") | Separate later sub-project — distinct from catalog primitives |
| First-time-selling coachmark for receptionists | Deferred — UI is discoverable; revisit with usage data |
| Recipient = unregistered guest | Not allowed — recipient must be a registered Customer (quick-create flow available) |
| 80mm thermal-receipt template changes | Adjacent — receipt shows snapshotted price + "Paid via package XYZ" annotation (see §13) |

### 2.3 Explicitly preserved (do not change)

- Receptionist mental model: select customer → add items → take payment → close bill
- Existing keyboard shortcuts, command palette, accessibility hooks
- 80mm receipt format
- FastAPI billing endpoints beyond the new additive `BillItem.item_type` discriminator
- All current Bill / BillItem / Payment / BillItemStaffContribution semantics for non-package transactions

---

## 3. Locked product decisions (canonical reference)

These were brainstormed and approved in Q1–Q11; see brief §3 for the full narrative. Listed here as the spec's authoritative source.

### 3.1 Primitives — unified schema

One `PackageDefinition` covers four legal combinations of two orthogonal axes:

| | Shareable | Owner-only |
|---|---|---|
| **Counted** | "10 Hair Spa, family can use" | "10 personalized facial sessions" |
| **Unlimited** | "Unlimited foot massage 30d, share with family" | "Unlimited hair wash monthly (personal)" |

A "bundle" (single-sitting combo) = `entitlement_type=counted`, `total_sessions=1`, multiple `PackageDefinitionItem` rows with `quantity≥1`. A single redemption consumes all included services together.

### 3.2 Pricing — build-your-own with snapshotted per-line prices

- Admin adds services, sees running MRP total
- Admin applies package-level discount via segmented control: `%` / `₹ off` / Final amount
- System auto-distributes proportional to MRP across unlocked lines
- Admin can override any line's price; that line becomes locked. Further redistribution skips locked lines.
- **At sale, per-line prices are snapshotted into `PackageSaleItem` rows.** Service MRP changes later don't affect existing sales.

### 3.3 GST — prepaid recognition

- Selling a package creates a normal `Bill` (full tax invoice, per-service GST from snapshots)
- Redemptions are `BillItem`s carrying the snapshotted per-line price
- Redemption payment uses internal `Payment.payment_method='package_redemption'` (zero customer cash at redemption visit; staff commissions and revenue reports work normally)
- Refunds issue credit-note bills (`Bill.bill_type='credit_note'`) linked to the original sale

### 3.4 Expiry

- Per-package `validity_days` snapshotted to `PackageSale.expires_at` at sale
- Hard expiry: redemption refused after `expires_at`
- Owner-only "Extend Expiry" dedicated modal with required reason → `PackageExpiryExtension` audit row, `PackageSale.status` returns to `active`
- 30-day pre-expiry reminder flag computed by daily job

### 3.5 Shareability

- Per-package `shareability` enum (`owner_only` default | `shared`)
- Shared: any registered Customer can be the recipient at redemption (quick-create flow inline)
- `PackageRedemptionAudit` captures buyer, recipient, performed-by-user per redemption
- Bill UI shows "Paid via Package XYZ (owned by [Buyer])" when recipient ≠ buyer
- PII redaction: Staff sees buyer as first-name-only (matches `customers:read` PII tier)

### 3.6 Redemption at POS

- Default auto-apply per-package `auto_apply` flag (default true; forced true for unlimited)
- Single eligible package: silent auto-apply with persistent `[↩ Undo]` pill
- Multiple eligible packages: inline radio panel (not modal), FIFO-by-expiry pre-selected, "Confirm with customer" warning header — silent override (no reason field) per Open-Q5
- Exact service match only — no category fallback, no cashier substitution
- Bundles sold + redeemed in same visit: **always two steps** (sale line, then redemption lines) per Open-Q4

### 3.7 Refunds

- Owner-only via `packages:refund` (mirrors `bills:refund`)
- Configurable `cancellation_fee_pct` per package (default 20% in `settings.package_default_cancellation_fee_pct`)
- Refund math branches by entitlement type:
  - Counted: `refund_paise = sum(unredeemed_sessions × snapshot_unit_price_paise) × (1 - cancellation_fee_pct/100)`
  - Unlimited: `refund_paise = paid_paise × (days_remaining / total_validity_days) × (1 - cancellation_fee_pct/100)`
- Refund-to picker: Cash | UPI | Adjust pending balance — **defaults to Cash** with a "Customer has ₹X pending — net against it?" hint when applicable (Open-Q9)
- Expired packages: refund allowed at Owner discretion with `warning` banner at top of modal body
- Credit-note bill written; original sale's `PackageSale.status` → `refunded`, `refund_bill_id` populated, `refunded_at` set

### 3.8 Access matrix

See §6 for full permission listing.

---

## 4. Data Model

Architecture: **Hybrid (Gamma)** — clean catalog/sale domain in new tables; redemptions reuse `BillItem` with a discriminator. See companion brief §4 and the original brainstorm transcript for rationale.

### 4.1 New tables

#### `PackageDefinition`

The catalog row. Editable by Owner; edits don't affect already-sold packages (snapshots protect them).

```python
class PackageDefinition(Base, TimestampMixin, SoftDeleteMixin, ULIDMixin):
    __tablename__ = "package_definitions"

    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(Enum(PackageDefinitionStatus), nullable=False, default="draft")
    # enum values: draft | published | archived

    entitlement_type = Column(Enum(EntitlementType), nullable=False)
    # enum values: counted | unlimited

    total_sessions = Column(Integer, nullable=True)
    # required if entitlement_type='counted'; null if 'unlimited'
    # CHECK constraint: (entitlement_type='counted' AND total_sessions IS NOT NULL AND total_sessions >= 1)
    #                OR (entitlement_type='unlimited' AND total_sessions IS NULL)

    shareability = Column(Enum(Shareability), nullable=False, default="owner_only")
    # enum values: owner_only | shared

    validity_days = Column(Integer, nullable=False)  # CHECK > 0

    auto_apply = Column(Boolean, nullable=False, default=True)
    # forced True at write time if entitlement_type='unlimited'

    cancellation_fee_pct = Column(Numeric(5, 2), nullable=False, default=Decimal("20.00"))
    # CHECK 0 <= cancellation_fee_pct <= 100

    created_by_user_id = Column(String(26), ForeignKey("users.id"), nullable=False)

    items = relationship("PackageDefinitionItem", back_populates="definition",
                         cascade="all, delete-orphan", order_by="PackageDefinitionItem.display_order")
```

#### `PackageDefinitionItem`

Per-service rows in the catalog. Carry the discounted per-service price (the "snapshot price at definition time"). Snapshotted again at sale into `PackageSaleItem`.

```python
class PackageDefinitionItem(Base, TimestampMixin, ULIDMixin):
    __tablename__ = "package_definition_items"

    package_definition_id = Column(String(26), ForeignKey("package_definitions.id", ondelete="CASCADE"),
                                   nullable=False, index=True)
    service_id = Column(String(26), ForeignKey("services.id", ondelete="RESTRICT"), nullable=False)

    quantity = Column(Integer, nullable=False, default=1)  # CHECK >= 1
    # for bundles: total_sessions=1 with multiple items at quantity>=1 (e.g. "2 manicures + 1 facial")
    # for multi-session packs: usually quantity=1 (one redemption = one service)

    unit_price_paise = Column(Integer, nullable=False)  # the discounted per-service price
    locked = Column(Boolean, nullable=False, default=False)
    # whether package-level discount redistribution touches this line

    display_order = Column(Integer, nullable=False, default=0)
```

#### `PackageSale`

The lifecycle row for one sold package. **Snapshots all policy at sale time** so subsequent definition edits don't retroactively affect customers.

```python
class PackageSale(Base, TimestampMixin, ULIDMixin):
    __tablename__ = "package_sales"

    bill_id = Column(String(26), ForeignKey("bills.id", ondelete="RESTRICT"),
                     nullable=False, unique=True, index=True)
    # 1:1 with the original tax invoice. unique constraint enforces it.

    package_definition_id = Column(String(26), ForeignKey("package_definitions.id", ondelete="RESTRICT"),
                                   nullable=False)
    customer_id = Column(String(26), ForeignKey("customers.id", ondelete="RESTRICT"),
                         nullable=False, index=True)
    selling_staff_id = Column(String(26), ForeignKey("staff.id", ondelete="SET NULL"), nullable=True)

    sold_at = Column(DateTime(timezone=True), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)

    # SNAPSHOT COLUMNS — copied from PackageDefinition at sale time
    entitlement_type_snapshot = Column(Enum(EntitlementType), nullable=False)
    shareability_snapshot = Column(Enum(Shareability), nullable=False)
    cancellation_fee_pct_snapshot = Column(Numeric(5, 2), nullable=False)
    total_sessions_snapshot = Column(Integer, nullable=True)  # null for unlimited

    sessions_remaining = Column(Integer, nullable=True)
    # null for unlimited; for counted, starts at total_sessions_snapshot, decremented on redemption

    status = Column(Enum(PackageSaleStatus), nullable=False, default="active", index=True)
    # enum values: active | expired | refunded | exhausted

    refunded_at = Column(DateTime(timezone=True), nullable=True)
    refund_bill_id = Column(String(26), ForeignKey("bills.id"), nullable=True)

    items = relationship("PackageSaleItem", back_populates="sale",
                         cascade="all, delete-orphan", order_by="PackageSaleItem.display_order")
```

#### `PackageSaleItem`

The snapshotted per-line pricing for a specific sale. Source of truth for redemption pricing and refund math.

```python
class PackageSaleItem(Base, TimestampMixin, ULIDMixin):
    __tablename__ = "package_sale_items"

    package_sale_id = Column(String(26), ForeignKey("package_sales.id", ondelete="CASCADE"),
                             nullable=False, index=True)
    package_definition_item_id = Column(String(26), ForeignKey("package_definition_items.id",
                                                                ondelete="RESTRICT"), nullable=False)
    service_id = Column(String(26), ForeignKey("services.id", ondelete="RESTRICT"), nullable=False, index=True)

    quantity = Column(Integer, nullable=False)
    snapshot_unit_price_paise = Column(Integer, nullable=False)
    snapshot_gst_rate_pct = Column(Numeric(5, 2), nullable=False)
    locked = Column(Boolean, nullable=False)  # preserved for audit
    display_order = Column(Integer, nullable=False)
```

#### `PackageRedemptionAudit`

Append-only log of every redemption. Captures recipient identity for shared packages and the link to the consumed `BillItem`.

```python
class PackageRedemptionAudit(Base, TimestampMixin, ULIDMixin):
    __tablename__ = "package_redemption_audit"

    package_sale_id = Column(String(26), ForeignKey("package_sales.id", ondelete="CASCADE"),
                             nullable=False, index=True)
    bill_item_id = Column(String(26), ForeignKey("bill_items.id", ondelete="RESTRICT"),
                          nullable=False, unique=True)
    # unique ensures one audit row per redemption BillItem; cascade is RESTRICT to prevent BillItem
    # deletion silently dropping the audit trail

    package_sale_item_id = Column(String(26), ForeignKey("package_sale_items.id", ondelete="RESTRICT"),
                                  nullable=False)
    # which line in the package was consumed (matters for bundles with multiple service types)

    redeemed_for_customer_id = Column(String(26), ForeignKey("customers.id", ondelete="RESTRICT"),
                                       nullable=False, index=True)
    # may differ from package_sale.customer_id (the buyer) when shareability='shared'

    performed_by_user_id = Column(String(26), ForeignKey("users.id"), nullable=False)
    redeemed_at = Column(DateTime(timezone=True), nullable=False, index=True)
    session_number = Column(Integer, nullable=True)
    # 1..N for counted (n-of-N at time of redemption); null for unlimited

    notes = Column(Text, nullable=True)
```

#### `PackageExpiryExtension`

Audit log for Owner-only extend actions.

```python
class PackageExpiryExtension(Base, TimestampMixin, ULIDMixin):
    __tablename__ = "package_expiry_extensions"

    package_sale_id = Column(String(26), ForeignKey("package_sales.id", ondelete="CASCADE"),
                             nullable=False, index=True)
    previous_expires_at = Column(DateTime(timezone=True), nullable=False)
    new_expires_at = Column(DateTime(timezone=True), nullable=False)  # CHECK > previous_expires_at
    performed_by_user_id = Column(String(26), ForeignKey("users.id"), nullable=False)
    extended_at = Column(DateTime(timezone=True), nullable=False)
    reason = Column(Text, nullable=False)  # required
```

### 4.2 Existing tables modified (additive only)

#### `Bill`

```python
# additive columns
bill_type = Column(Enum(BillType), nullable=False, default="normal", server_default="normal", index=True)
# enum values: normal | credit_note

original_bill_id = Column(String(26), ForeignKey("bills.id"), nullable=True)
# populated only when bill_type='credit_note'; CHECK: original_bill_id IS NOT NULL iff bill_type='credit_note'
```

#### `BillItem`

```python
# additive columns
item_type = Column(Enum(BillItemType), nullable=False, default="service", server_default="service", index=True)
# enum values: service | product | package_sale_line | package_redemption

package_sale_id = Column(String(26), ForeignKey("package_sales.id"), nullable=True, index=True)
# populated when item_type IN ('package_sale_line', 'package_redemption')

package_sale_item_id = Column(String(26), ForeignKey("package_sale_items.id"), nullable=True)
# populated when item_type='package_redemption' only (sale_line refs the parent PackageSale only)
```

#### `Payment`

```python
# enum extension — no schema change beyond the enum value
class PaymentMethod(enum.Enum):
    CASH = "cash"
    UPI = "upi"
    CARD = "card"
    PENDING_BALANCE = "pending_balance"
    # ...existing values...
    PACKAGE_REDEMPTION = "package_redemption"  # NEW
```

### 4.3 Indexes (beyond declared `index=True` above)

```sql
CREATE INDEX ix_package_sales_customer_status
  ON package_sales (customer_id, status);

CREATE INDEX ix_package_sales_expires_status
  ON package_sales (expires_at, status);

CREATE INDEX ix_package_sales_selling_staff_sold_at
  ON package_sales (selling_staff_id, sold_at);

CREATE INDEX ix_package_redemption_audit_for_customer_redeemed_at
  ON package_redemption_audit (redeemed_for_customer_id, redeemed_at);

CREATE INDEX ix_bill_items_package_sale
  ON bill_items (package_sale_id)
  WHERE package_sale_id IS NOT NULL;

CREATE INDEX ix_bills_credit_notes
  ON bills (bill_type, created_at)
  WHERE bill_type != 'normal';
```

### 4.4 Constraints summary

| Constraint | Purpose |
|---|---|
| `PackageDefinition` CHECK: counted ⇒ total_sessions ≥ 1; unlimited ⇒ total_sessions IS NULL | Schema-enforces the legal entitlement combinations |
| `PackageDefinition` CHECK: 0 ≤ cancellation_fee_pct ≤ 100 | Bounds the fee |
| `PackageDefinition` CHECK: validity_days > 0 | Prevent zero/negative validity |
| `PackageDefinitionItem` CHECK: quantity ≥ 1 | Quantity is per-redemption count |
| `PackageSale.bill_id` UNIQUE | Enforces 1:1 PackageSale ↔ originating Bill invariant |
| `PackageRedemptionAudit.bill_item_id` UNIQUE | One audit row per redemption BillItem; no double-booking |
| `PackageExpiryExtension` CHECK: new_expires_at > previous_expires_at | Extension is forward in time |
| `Bill` CHECK: `original_bill_id IS NOT NULL` iff `bill_type='credit_note'` | Credit notes always reference an original |

---

## 5. Pricing Engine (`backend/app/services/packages/pricing_engine.py`)

Single shared module owning all package math. Called by sales, redemption, refund, reports, and future appointments/recommendations modules. **No package-math logic anywhere else in the codebase.**

### 5.1 Public functions

```python
def snapshot_at_sale(definition: PackageDefinition) -> List[PackageSaleItemDraft]:
    """
    Produce the per-line snapshot rows for a new PackageSale.
    Copies unit_price_paise + service.gst_rate_pct + quantity + locked + display_order
    from each PackageDefinitionItem at the moment of sale.
    """

def distribute_discount(
    items: List[PackageDefinitionItemDraft],
    mode: Literal["pct", "flat", "final"],
    value: Decimal,
) -> List[PackageDefinitionItemDraft]:
    """
    Apply a package-level discount across UNLOCKED lines proportional to MRP.
    Locked lines preserved exactly.
    Rounding: distributes paise spillover to the LAST unlocked line so totals are exact.
    Raises DomainError if all lines are locked and a discount is requested.
    """

def find_eligible_packages(
    customer_id: ULID,
    service_id: ULID,
    db: Session,
) -> List[PackageSale]:
    """
    Returns active, non-expired, non-exhausted PackageSales whose snapshotted items
    include service_id AND that are accessible to this customer (owner_only requires
    customer_id == package_sale.customer_id; shared requires the customer to merely
    be a registered Customer — caller decides recipient).

    Ordering: FIFO by expires_at ASC (earliest expiry first).
    Filters: status='active', sessions_remaining > 0 OR entitlement_type='unlimited',
             expires_at > now(), service_id ∈ snapshot items, soft-delete checks.
    """

def compute_refund(sale: PackageSale) -> RefundComputation:
    """
    Branches by entitlement_type_snapshot:

    Counted:
      unredeemed_sessions = total_sessions_snapshot - len(valid_redemptions)
        where 'valid' excludes redemptions on voided/refunded bills
      base_paise = sum(item.snapshot_unit_price_paise * item.quantity * (unredeemed_sessions / total_sessions_snapshot))
        — distributed proportionally if bundle has multiple item types
      fee_paise = round(base_paise * cancellation_fee_pct_snapshot / 100)
      refund_paise = base_paise - fee_paise

    Unlimited:
      total_validity_days = (expires_at - sold_at).days
      days_remaining = max(0, (expires_at - now()).days)
      pct_remaining = days_remaining / total_validity_days
      base_paise = round(bill.total_paise * pct_remaining)
      fee_paise = round(base_paise * cancellation_fee_pct_snapshot / 100)
      refund_paise = base_paise - fee_paise

    Returns RefundComputation with: base_paise, fee_paise, refund_paise,
    breakdown (the per-line consumed/unredeemed values for the UI), and
    a 'kind' tag for the UI to render the right math block.
    """

def can_extend_expiry(sale: PackageSale, new_expires_at: datetime) -> None:
    """Validates new_expires_at > sale.expires_at AND new_expires_at > now(). Raises DomainError otherwise."""
```

### 5.2 Rounding & money invariants

All money in paise (INTEGER). The discount distribution function is the ONLY place where rounding decisions are made. Rule:

1. Compute each unlocked line's discounted price using exact rational arithmetic
2. Floor each result to paise
3. Recompute the total; the spillover (difference between requested total and floored sum) is added to the LAST unlocked line so the package total matches exactly

Property test: `sum(item.unit_price_paise * item.quantity for item in distributed_items) == requested_total_paise` for all inputs.

---

## 6. Permissions (`backend/app/auth/permissions.py`)

Add to `PermissionChecker.ROLE_PERMISSIONS`:

| Permission | Owner | Receptionist | Staff |
|---|---|---|---|
| `packages:read` | ✓ | ✓ | ✓ (with PII redaction matching `customers:read`) |
| `packages:create` | ✓ | — | — |
| `packages:update` | ✓ | — | — |
| `packages:delete` | ✓ | — | — |
| `packages:sell` | ✓ | ✓ | — |
| `packages:redeem` | ✓ | ✓ | ✓ |
| `packages:redeem_for_other` | ✓ | ✓ | — |
| `packages:refund` | ✓ | — | — |
| `packages:extend_expiry` | ✓ | — | — |
| `packages:override_price` | ✓ | — | — |

Frontend `useAuthStore.hasPermission()` mirrors the matrix. Every new component that exposes a gated action calls `hasPermission()`; every backend route uses `require_permission()`.

---

## 7. Backend API surface (`backend/app/api/v1/packages.py`)

All routes mounted at `/api/v1/packages` unless noted. Requests/responses use Pydantic schemas in `backend/app/schemas/package.py`.

### 7.1 Catalog (Owner only except `GET`)

| Method | Path | Permission | Purpose |
|---|---|---|---|
| `GET` | `/definitions` | `packages:read` | List package definitions; query params: `status`, `entitlement_type`, `shareability`, `search` |
| `GET` | `/definitions/{id}` | `packages:read` | Get a single definition + items |
| `POST` | `/definitions` | `packages:create` | Create. Body includes items[]; runs `distribute_discount` server-side if `discount` field provided so server-validated final prices match client display |
| `PUT` | `/definitions/{id}` | `packages:update` | Update. Items replaced wholesale (delete + insert) inside transaction. Banner warning shown in UI before submit. |
| `POST` | `/definitions/{id}/publish` | `packages:update` | Transition draft → published |
| `POST` | `/definitions/{id}/archive` | `packages:update` | Transition to archived (won't appear in POS selector; existing sales unaffected) |
| `DELETE` | `/definitions/{id}` | `packages:delete` | Soft delete. Blocked if any `PackageSale.status='active'` for this definition |

### 7.2 Sales

| Method | Path | Permission | Purpose |
|---|---|---|---|
| `GET` | `/sales` | `packages:read` | List sales; filters: `customer_id`, `status`, `selling_staff_id`, date range |
| `GET` | `/sales/{id}` | `packages:read` | Single sale + items + redemption audit |
| `GET` | `/sales/active-for-customer/{customer_id}` | `packages:read` | Active packages for Entitlements Rail; returns sales with `status='active'`, `expires_at > now()`, and either unlimited or `sessions_remaining > 0` |
| `POST` | `/sales/{id}/extend` | `packages:extend_expiry` | Owner-only. Body: `new_expires_at`, `reason`. Creates `PackageExpiryExtension` audit row. |
| `POST` | `/sales/{id}/refund` | `packages:refund` | Owner-only. Body: `payment_method`, `reason`. Computes refund via pricing engine, writes credit-note Bill, updates PackageSale. Transactional. |

### 7.3 POS-side eligibility & redemption (used by existing billing endpoints)

The redemption itself is performed by **the existing billing endpoints** when a BillItem is added — no new endpoint. The billing endpoint internally:

1. Adds the BillItem
2. Calls `find_eligible_packages(customer_id, service_id)` if `auto_apply` is desired
3. If exactly one eligible, decorates the BillItem with `item_type='package_redemption'`, `package_sale_id`, `package_sale_item_id`; writes `PackageRedemptionAudit`; decrements `sessions_remaining` (atomic with the BillItem create using row lock); writes `Payment(method='package_redemption', amount=item.subtotal_paise)`
4. If multiple eligible, returns the list in the response for the UI to render the inline selector; client picks one and re-submits

Companion eligibility-only endpoint for the rail:

| Method | Path | Permission | Purpose |
|---|---|---|---|
| `POST` | `/eligibility/check` | `packages:read` | Body: `customer_id`, `service_id`. Returns list of eligible PackageSales for the inline selector. Idempotent, no side effects. |

### 7.4 Undo

| Method | Path | Permission | Purpose |
|---|---|---|---|
| `POST` | `/redemptions/{audit_id}/undo` | `packages:redeem` | Atomic inverse: increments `sessions_remaining`, deletes the `PackageRedemptionAudit` row, converts the `BillItem` back to `item_type='service'` with normal pricing, removes the `Payment(method='package_redemption')` row. Allowed only if the parent Bill is still in `draft` status (not yet paid/closed). |

### 7.5 Reporting (read-only)

| Method | Path | Permission | Purpose |
|---|---|---|---|
| `GET` | `/reports/sales-summary` | `packages:read` | Aggregate package sales by date range, definition, selling staff |
| `GET` | `/reports/redemption-rates` | `packages:read` | Per-definition redemption rate (redeemed / sold sessions) for KPI dashboards |

---

## 8. Frontend Architecture

### 8.1 New routes

```
frontend/src/app/(shell)/dashboard/
  packages/
    page.tsx                          # Catalog list (Owner-gated to actions; Receptionist read-only)
    [id]/page.tsx                     # View / edit a published package (delegates to PackageBuilder)
    [id]/edit/page.tsx                # Explicit edit screen
    new/page.tsx                      # Create via PackageBuilder

  packages/sold/
    page.tsx                          # List of all PackageSales — Owner refund entry point
                                       # (filters by customer, status, date range)
```

Note: customer-side surfaces (Active Packages section on `/dashboard/customers/[id]`) are **deferred to sub-project C**. In sub-project A, refunds are accessed from `/dashboard/packages/sold` or from the original sale's `/dashboard/bills/[id]` page via a new "Refund Package" action button (visible only when bill has `package_sale_id` set on a line item and viewer has `packages:refund`).

### 8.2 New components (`frontend/src/components/packages/`)

| Component | Purpose |
|---|---|
| `PackageBuilder.tsx` | The 2-column build-your-own form (Q-VIS-1); reused by `new/page.tsx` and `[id]/edit/page.tsx` |
| `PackageBuilderDiscountControl.tsx` | Segmented control + input for `% / ₹ off / Final amount` |
| `PackageBuilderEntitlementMatrix.tsx` | 2×2 visual radio matrix |
| `PackageBuilderServicesTable.tsx` | The services table with lock indicators, per-line prices, redistribution |
| `PackageCatalogList.tsx` | Catalog list page body |
| `PackageCard.tsx` | Reusable card (used in Entitlements Rail, selector, sold-list) |
| `EntitlementsRail.tsx` | The permanent POS rail (Q-VIS-9 Direction A) — collapses to strip below 1024px |
| `EntitlementsStrip.tsx` | Horizontal strip fallback for narrow viewports |
| `PackageSelectorChip.tsx` | The Packages tab/chip in the POS service selector |
| `PackageSaleLine.tsx` | Bill line rendering for `item_type='package_sale_line'` with services accordion |
| `RedemptionLineItem.tsx` | Bill line rendering for `item_type='package_redemption'` with persistent Undo pill, gold rail, gift glyph |
| `MultiPackageSelector.tsx` | Inline radio panel when 2+ packages eligible |
| `ActivePackagesBadge.tsx` | Compact badge fallback for layouts not using the rail |
| `RefundPackageModal.tsx` | Owner refund modal with branching math rows |
| `ExtendExpiryModal.tsx` | Owner expiry-extension modal with required reason field |

### 8.3 New primitives (`frontend/src/components/ui/`)

Per the design output's "proposed primitive addition":

| Primitive | Purpose |
|---|---|
| `SessionsLeft.tsx` | Numeral rendering for counted (`7/10`) or unlimited (`∞`); uses `db-num` editorial numeral recipe |
| `ExpiryBadge.tsx` | Pill that colors by urgency: green (`>30d`), amber (`8–30d`), red (`≤7d`), gray (expired) |

These are reused across `EntitlementsRail`, `PackageCard`, `RefundPackageModal`, and (in sub-project C) the customer profile Packages tab.

### 8.4 POS page structural changes (`/dashboard/pos`)

Per Open-Q3 (b) — customer profile deferred to C — the only structural change to existing pages in sub-project A is the POS itself, per design Direction A (Entitlements Rail):

| Change | Description |
|---|---|
| Rail injection | When `customerId` is selected and `useEligibility(customerId)` returns ≥1 active package, render `<EntitlementsRail>` between the service selector and bill canvas. Rail is absent for idle and no-customer-packages states. |
| Responsive collapse | At viewport `<1024px`, swap rail for `<EntitlementsStrip>` (horizontal). At `<768px`, swap strip for `<ActivePackagesBadge>` (single pill above bill). |
| Selector filter chips | Add `Packages` chip to the existing `All / Services / Products` filter row. Selecting it filters the selector to published `PackageDefinition`s rendered as `<PackageCard>` items. |
| Bill canvas line rendering | `BillItem.item_type` discriminator chooses the renderer: `service`/`product` → existing; `package_sale_line` → `<PackageSaleLine>`; `package_redemption` → `<RedemptionLineItem>`. |
| Multi-package interaction | When billing endpoint returns `eligible_packages: [a, b, ...]`, render `<MultiPackageSelector>` inline on the just-added BillItem until cashier picks one. |
| **Last-visit recognition aid** | Whenever a customer is selected on POS, surface `Customer.last_visit_at` as a small subtitle in the customer header strip and on the Entitlements Rail header. Format: `"Last visit: 12 days ago"` (using existing `formatRelativeDate` helper). When `last_visit_at IS NULL` or `> 90 days`: display `"First/new visit"` or `"Returning after 3 months"` respectively. **Intent**: gives reception a passive recognition signal so a "regular" feels familiar and an unexpected gap or impossible frequency (e.g. "Last visit: 2 hours ago") becomes a visible behavioral anomaly without requiring active anomaly-detection infrastructure. Zero new data — `last_visit_at` already exists on `Customer`. |

### 8.5 Bill detail page (`/dashboard/bills/[id]`)

Single addition: a "Refund Package" action button (Owner-only) when any BillItem on the bill has `item_type='package_sale_line'`. Clicking opens `<RefundPackageModal>` for the corresponding `PackageSale`.

### 8.6 State (Zustand)

New store: `frontend/src/stores/packages-store.ts`

```ts
interface PackagesStore {
  // catalog cache (TTL: 5 min)
  definitions: PackageDefinition[] | null
  definitionsLoadedAt: number | null
  loadDefinitions: () => Promise<void>

  // eligibility cache (per customer, TTL: 60s, invalidated on any redemption or sale on that customer)
  eligibilityCache: Map<CustomerId, { packages: PackageSaleSummary[]; loadedAt: number }>
  loadEligibility: (customerId: CustomerId) => Promise<PackageSaleSummary[]>
  invalidateEligibility: (customerId: CustomerId) => void

  // active-packages summary for the rail
  activeForCustomer: (customerId: CustomerId) => PackageSaleSummary[]
}
```

Follow existing Zustand conventions (see `zustand-store` skill).

---

## 9. Key Flows

### 9.1 Sell a package

```
Receptionist on POS, customer selected
  → clicks Packages chip in selector
  → selects a PackageCard
  → BillItem added with item_type='package_sale_line', package_sale_id=null (set at finalization)
  → cashier picks selling_staff inline on the line
  → cashier finalizes bill, takes payment
  → BillingService.finalize_bill():
      - existing logic creates Payment rows
      - NEW: for each BillItem with item_type='package_sale_line':
          - call PackageSalesService.create_sale(definition_id, bill_id, customer_id, selling_staff_id)
              which atomically:
                1. snapshots definition + items via pricing_engine.snapshot_at_sale()
                2. inserts PackageSale row with all snapshot columns + expires_at = now + validity_days
                3. inserts PackageSaleItem rows from snapshot
                4. updates BillItem.package_sale_id to the new PackageSale.id
      - existing receipt printing logic runs unchanged (snapshotted per-line prices roll up into GST breakdown)
  → invalidate eligibilityCache for this customer
```

### 9.2 Redeem a session (single eligible)

```
Receptionist on POS, customer with 1 eligible package
  → adds a service to the bill (existing flow)
  → BillingService.add_item():
      - existing validation
      - NEW: call pricing_engine.find_eligible_packages(customer_id, service_id)
      - if exactly 1 result AND package.auto_apply:
          - lock package_sale row (SELECT FOR UPDATE)
          - re-check sessions_remaining > 0 OR unlimited
          - re-check expires_at > now()
          - set BillItem.item_type='package_redemption', package_sale_id, package_sale_item_id
          - set BillItem.unit_price_paise = sale_item.snapshot_unit_price_paise (NOT zero)
          - decrement sessions_remaining (if counted)
          - insert PackageRedemptionAudit row (recipient = bill.customer_id by default)
          - insert Payment(method='package_redemption', amount_paise=BillItem.subtotal_paise,
                          bill_item_id=BillItem.id) so the line nets to zero customer cash
          - if sessions_remaining == 0: set PackageSale.status='exhausted'
      - if 2+ results: return BillItem + eligible_packages[] in the response
        (UI renders MultiPackageSelector inline; cashier picks; client calls another endpoint to re-do step above with a forced package_sale_id)
  → existing staff-contribution logic runs against BillItem.subtotal_paise (snapshot price) — staff get fair credit
```

### 9.3 Redeem for a non-owner (shared package)

Same as 9.2 but with two changes:

1. Eligibility check includes packages where `shareability='shared'` AND `package_sale.customer_id != bill.customer_id` (the bill's customer is the recipient, not the buyer)
2. The UI prompts cashier to confirm recipient (defaulting to bill customer); recipient identity is captured into `PackageRedemptionAudit.redeemed_for_customer_id`
3. Permission check: `require_permission('packages', 'redeem_for_other')` — Staff role denied

### 9.4 Undo a redemption

```
Cashier on POS, redemption line just appeared
  → clicks [↩ Undo] pill
  → POST /api/v1/packages/redemptions/{audit_id}/undo
      atomically:
        1. lock package_sale row (SELECT FOR UPDATE)
        2. verify parent Bill is still in 'draft' status (else 400)
        3. delete PackageRedemptionAudit row
        4. delete Payment(method='package_redemption', bill_item_id=...)
        5. update BillItem.item_type='service', clear package_sale_id and package_sale_item_id
        6. increment sessions_remaining (if counted)
        7. if PackageSale.status was 'exhausted', restore to 'active'
  → UI re-renders bill line as a normal paid service line
```

### 9.5 Refund

```
Owner on /dashboard/bills/[id] (sale bill) OR /dashboard/packages/sold
  → clicks "Refund Package"
  → RefundPackageModal opens; client calls GET /api/v1/packages/sales/{id} for current state
  → modal renders math via pricing_engine.compute_refund (server-rendered breakdown), refund-to picker,
    reason field
  → if customer has pending_balance > 0, modal shows hint "Customer has ₹X pending — net against it?"
    (one-click swap of refund-to to "Adjust pending balance")
  → Owner enters reason, clicks Refund
  → POST /api/v1/packages/sales/{id}/refund
      atomically (single DB transaction):
        1. recompute refund via pricing_engine.compute_refund (server-side authoritative)
        2. create Bill row with bill_type='credit_note', original_bill_id=sale.bill_id, customer_id, sold_at=now()
        3. create two BillItem rows on the credit-note bill:
             - "Refund unredeemed value" — amount_paise = -base_paise
             - "Cancellation fee" — amount_paise = +fee_paise (positive = revenue)
           net total of credit note = -refund_paise (money out)
        4. create Payment row on credit note:
             - amount_paise = -refund_paise (negative for cash out)
             - method = picker selection
             - if "Adjust pending balance": create PendingPaymentCollection adjustment instead
        5. update PackageSale: status='refunded', refunded_at=now(), refund_bill_id=credit_note.id
        6. audit: insert AuditLog row capturing user, reason, before/after status
  → eligibilityCache invalidated for buyer
  → printed credit-note receipt (existing receipt printing already handles negative bills)
```

### 9.6 Extend expiry

```
Owner on /dashboard/packages/sold or /dashboard/bills/[id]
  → clicks "Extend Expiry" on a package row
  → ExtendExpiryModal opens with current expires_at, date picker for new_expires_at, required reason text
  → Owner submits
  → POST /api/v1/packages/sales/{id}/extend body: { new_expires_at, reason }
      atomically:
        1. validate via pricing_engine.can_extend_expiry()
        2. insert PackageExpiryExtension row capturing prev/new + user + reason
        3. update PackageSale.expires_at = new_expires_at
        4. if status='expired', restore to 'active'
  → eligibilityCache invalidated for buyer
```

### 9.7 Daily expiry job (RQ)

`backend/app/services/packages/expiry_job.py`, scheduled hourly via existing RQ scheduler:

```python
def run_expiry_transitions():
    """
    For each PackageSale with status='active' AND expires_at < now():
      - set status='expired'
      - log AuditLog event
    For each PackageSale with status='active' AND now() < expires_at < now() + 30 days:
      - flag in cache as 'expiring_soon' for UI badge (transient cache, not a DB column)
    """
```

---

## 10. Cross-cutting visual grammar (from design output)

Anchored as a system rule for this and future packages-related sub-projects:

| Signal | Token | Meaning |
|---|---|---|
| **Navy** (`accent-default` `#1c104c` / gold on dark) | "What's being paid **now**" — primary actions, package **sale** lines, focus rings |
| **Gold** (`gold-default` `#c9a96e`) | "What the customer **already owns**" — packages, entitlements, redemption lines, store credit |
| **Success green** (`success-*`) | Reserved for existing "booked/confirmed" semantics — not reused for packages |
| **Amber warning** (`warning-*`) | Expiry urgency + "confirm with customer" moments |
| **Danger red** (`danger-*`) | Refund / pending-balance / cancellation-fee figures |

**Non-negotiables across every surface:**

- Tabular numerals on every money/count/time (`.tabular` utility)
- Touch targets ≥44px on POS surfaces
- Redemption lines render at **full strength** (real services, just paid earlier) — gold left-rail + gift glyph, never dimmed
- PII redaction for Staff role is visually explicit (eye-off icon + "Limited view" badge)
- Both themes shipped for every surface
- All motion ≤180ms; respects `prefers-reduced-motion`

---

## 11. Edge cases & their handling

| # | Edge case | Handling |
|---|---|---|
| 1 | Two cashiers redeem the last session simultaneously | DB row lock (`SELECT FOR UPDATE`) on `PackageSale` inside redemption transaction; second cashier gets `409 NO_SESSIONS_REMAINING` |
| 2 | Customer with active package soft-deleted | `Customer.soft_delete()` precondition: no `PackageSale.status='active'` where `customer_id = self.id` AND no `PackageRedemptionAudit.redeemed_for_customer_id = self.id` with `redeemed_at > now() - 30d`. Friendly error with count. |
| 3 | Service in package def soft-deleted | New sales blocked (UI banner on def edit; API returns 422 on sell). Existing sales redeem normally (snapshot `service_id` is restrict FK, can't cascade delete). |
| 4 | Bill voided before finalization | `PackageSale` created only inside `BillingService.finalize_bill()` transaction; void path never invokes it. No orphans. |
| 5 | Refund where some redemptions are on voided bills | `compute_refund` filters `PackageRedemptionAudit` rows whose linked `BillItem.bill.status != 'voided'`. Voided redemptions don't count as consumed. |
| 6 | Package def edited after sale | Snapshot fields on `PackageSale` / `PackageSaleItem` are untouched. Edit form shows warning banner before submit. |
| 7 | Auto-apply → Undo before bill finalized | Atomic inverse per §9.4; sessions counter restored exactly. |
| 8 | Bundle with multiple service types redeemed across two visits | NOT SUPPORTED — bundles are `total_sessions=1`, all items consumed in one redemption transaction. If admin needs multi-visit, they create a counted package with `total_sessions>1` instead. UI prevents partial redemption of a bundle. |
| 9 | Bundle (total_sessions=1) consumed across multiple service lines on one bill | **Policy**: bundles must be redeemed entirely in a single bill — all included service items get added to one bill in one UI transaction. **Mechanism**: UI selecting a bundle for redemption auto-adds all included service lines as `package_redemption` BillItems referencing the same `package_sale_id`. At finalization, `sessions_remaining` is decremented exactly once (from 1 to 0) regardless of how many BillItems carry the bundle's `package_sale_id`. One `PackageRedemptionAudit` row per BillItem. **Cross-bill case explicitly not supported**: once any item of a bundle is redeemed (sessions_remaining=0), adding remaining bundle items to a later bill is rejected — the cashier must use a multi-session counted pack instead of a bundle if cross-visit consumption is desired. |
| 10 | Expired package shown in POS | Eligibility check excludes; rail shows in muted "Expired" state with "Request Owner override" inline; cashier-initiated extend opens `ExtendExpiryModal` (Owner-only, so error if cashier role) |
| 11 | Customer record merged (deduplication) | Existing customer-merge migration script extended: `UPDATE PackageSale.customer_id` + `UPDATE PackageRedemptionAudit.redeemed_for_customer_id` to surviving customer. Audit row written. |
| 12 | Owner extends just-expired package | `ExtendExpiryModal` accepts current `expires_at < now()`; new must be `> now()` (pricing_engine.can_extend_expiry validates). `PackageSale.status` returns to `active`. |
| 13 | Multi-package conflict where one has 0 sessions left | `find_eligible_packages` excludes (`sessions_remaining > 0 OR unlimited`); rail shows them as `exhausted` for visibility but never auto-applies |
| 14 | Unlimited package nearing expiry, many redemptions in last day | No restriction; every redemption a normal audit row. Reports may show unusual volume — fine, that's the data telling the truth. |
| 15 | Refund on exhausted package | Allowed (goodwill case). `compute_refund` returns `base_paise=0`, `refund_paise=0`. Modal renders "Nothing to refund" with explanatory copy + Cancel CTA. |
| 16 | Two packages auto-apply on the same bill (different services) | Independent — each redemption is its own atomic operation. Rail updates to show both consumed. |
| 17 | Shared package, recipient is brand-new customer | Quick-create flow (existing `customers:create`) opens inline in `MultiPackageSelector`'s recipient picker; returns new `customer_id`. |
| 18 | Auto-apply against a service with existing staff template | `BillItemStaffContribution` rows created via existing service-template logic from `BillItem.unit_price_paise` (snapshot price). Package redemption doesn't disturb staff attribution code path. |

---

## 12. PII handling

Staff role has `customers:read` with first-name-only PII (existing rule). For packages:

| Surface | Owner / Receptionist | Staff |
|---|---|---|
| Buyer name on redemption line (shared) | "Rajesh Kumar" | "Rajesh K." |
| Phone numbers on redemption audit views | Visible | Hidden |
| Cancellation reason / extend reason | Visible | Hidden |
| Refund amounts and credit-note bills | Visible | Hidden (financial PII — matches `view_totals` gating) |
| Eligibility rail entries (own customer) | Full info | Full info (Staff can see their own bill's customer's packages) |
| Last-visit date (POS customer header, rail header) | Visible (relative format: "12 days ago") | Visible — visit date is behavioral, not financial PII; no amounts disclosed |

Frontend helper: extend existing `formatCustomerName(customer, role)` to handle the buyer-vs-recipient case. Visual "Limited view" badge in any view where redaction is active.

---

## 13. Receipt treatment (adjacent)

The 80mm thermal receipt template is out of scope to redesign, but the new BillItem.item_type values change what shows up. Per Open-Q10:

- `package_sale_line`: prints as a normal line "Bridal Glam Package — ₹5,200" with included services as a sub-list (small font)
- `package_redemption`: prints the service with the snapshotted price, followed by an annotation line: `  Paid via Package #ABC123 (n/N)` (in italic small font). The Payment section shows the `package_redemption` payment method as "Paid via Package" (no money figure since it's already shown on the line).

Total line on the receipt always shows what the customer paid AT THIS VISIT (cash + UPI + card + pending — NOT including `package_redemption` amounts) so the customer sees the right number to settle.

Receipt-template implementation lives in the `receipt-printing` skill's domain — referencing here so the integration is intentional, not surprising.

---

## 14. Testing strategy

Following the `testing-workflow` skill (TDD, money in paise, race conditions, permissions).

### 14.1 Unit tests (`tests/services/packages/`)

**`test_pricing_engine.py`** — 100% coverage (highest-stakes module):

- Distribution: % / ₹ / Final modes; locked-line behavior; rounding spillover; all-locked error; zero-discount no-op
- Snapshot: definition → sale_item rows match exactly
- Eligibility: filters expired, exhausted, soft-deleted, wrong shareability; FIFO ordering
- Refund counted: math correctness, edge cases (0 redeemed, all redeemed, fee=0, fee=100)
- Refund unlimited: time-remaining math, expired returns 0, fee branch
- `can_extend_expiry` validation

**`test_concurrent_redemption.py`** — two-thread test using real DB row lock; exactly one succeeds; second gets domain error. NOT mocked.

### 14.2 Integration tests (`tests/api/v1/`)

- Full sale lifecycle: define → publish → POS sell → Bill created → Payment → PackageSale + PackageSaleItem present with correct snapshots
- Full redemption: customer with active package → add service to bill → BillItem becomes `package_redemption` → Payment(method='package_redemption') exists → audit row written → sessions decremented
- Multi-package: 2 eligible → response includes both → client selects → re-submit → exactly one consumed
- Shared redemption: package owned by A, redeemed for B → bill is on B's record, audit links A as buyer and B as recipient
- Undo: redemption → undo → sessions restored, BillItem reverted, payment deleted; second undo returns 404
- Refund counted: sale + 3 redemptions → refund → credit-note bill exists, math correct, status='refunded'
- Refund unlimited: time-remaining math, refund-to=Cash and refund-to=AdjustPendingBalance both work
- Extend expiry: extend → audit row + new expires_at; extend on expired package restores status='active'
- Expiry job: insert past-expiry sale → run job → status='expired'; insert near-expiry → status unchanged, eligibility check still returns it

### 14.3 Permission tests (one per endpoint per role)

For every new endpoint: Owner allowed, Receptionist per matrix, Staff per matrix. Existing `tests/auth/` patterns.

### 14.4 Property-based tests (`hypothesis`)

- **Counted refund invariant**: `refund_paise + fee_paise + sum(consumed_session_values) == paid_paise` (within ±N paise tolerance for N lines)
- **Unlimited refund range**: `0 ≤ refund_paise ≤ paid_paise × (1 - fee_pct/100)` for any inputs
- **Discount distribution**: `sum(item.unit_price_paise * item.quantity) == requested_final_total_paise` for any input shape (% / flat / final, any mix of locked/unlocked)

### 14.5 Frontend tests (`frontend/src/**/__tests__/`)

Vitest + React Testing Library:

- `PackageBuilder`: discount toggle re-renders, locked line stays, final total matches
- `MultiPackageSelector`: FIFO default, radio change updates selection
- `EntitlementsRail`: empty / 1 / many / expiring states render distinctly; responsive breakpoint swap to strip then badge
- `RedemptionLineItem`: shared-package buyer attribution; Staff PII redaction renders "Rajesh K."
- `RefundPackageModal`: counted vs unlimited math layouts; "net against pending" hint appears when applicable
- `ExtendExpiryModal`: reason field required; submit disabled until provided

### 14.6 E2E (Playwright) — one full cycle

1. Owner creates "Test Hair Spa 5-pack" definition
2. Receptionist sells to Customer A
3. Customer A returns over 3 visits; each Receptionist adds Hair Spa; system auto-applies
4. Owner refunds remaining 2 sessions
5. Verify: `status='refunded'`, `sessions_remaining=2` at time of refund, credit note exists with correct amounts, audit log complete

### 14.7 Performance smoke

- "Customer with 5 active packages opens POS" — eligibility check + rail render <100ms with realistic dataset (10K customers, 500 active packages)
- "End-of-day report including package sales" — <2s for one month of typical data

---

## 15. Migration & rollout

### 15.1 Alembic migration

Single migration: `alembic/versions/<rev>_add_packages_module.py`

Operations (in order):

1. Create 5 new tables with constraints (`package_definitions`, `package_definition_items`, `package_sales`, `package_sale_items`, `package_redemption_audit`, `package_expiry_extensions`)
2. Create the 6 new indexes
3. Add `bill_type` and `original_bill_id` columns to `bills` (default `'normal'`)
4. Add `item_type`, `package_sale_id`, `package_sale_item_id` columns to `bill_items` (default `'service'`)
5. Extend `PaymentMethod` enum with `'package_redemption'` value
6. Add CHECK constraints listed in §4.4

**Reversibility**: full downgrade reverses each step; no data loss because all changes are additive.

**Backfill**: none required. Existing `bills` and `bill_items` rows pick up default enum values.

Refer to the `alembic-migration` skill for the exact migration scaffold.

### 15.2 Backend rollout

1. Migration applied
2. `PermissionChecker.ROLE_PERMISSIONS` updated
3. New endpoints deployed (no consumers yet — safe)
4. Background job registered with RQ
5. Tests pass in CI

### 15.3 Frontend rollout

1. New routes shipped; menu item "Packages" added (Owner-only — hidden for other roles via `hasPermission`)
2. POS modifications shipped behind no flag — additive (no eligibility = old behavior exactly)
3. New components live in their directory; no impact on existing pages

### 15.4 Data backfill

None. No existing customer has a package; the feature is greenfield.

### 15.5 Operational concerns

- **Settings**: add `PACKAGE_DEFAULT_CANCELLATION_FEE_PCT` to `backend/app/config.py` (default `Decimal("20.00")`); update `settings:update` endpoint to allow Owner to change
- **Backups**: existing nightly `pg_dump` to B2 covers the new tables automatically (no script change needed)
- **Audit log**: extend existing `AuditLog` events with new actions (`package.sold`, `package.refunded`, `package.extended`, `package.redeemed`, `package.def_published`)

---

## 16. Files touched (summary)

### Backend

| File | Change |
|---|---|
| `backend/app/models/package.py` | NEW — 6 new models |
| `backend/app/models/billing.py` | MODIFY — add bill_type, original_bill_id to Bill; item_type, package_sale_id, package_sale_item_id to BillItem |
| `backend/app/models/payment.py` | MODIFY — extend PaymentMethod enum |
| `backend/app/services/packages/__init__.py` | NEW |
| `backend/app/services/packages/catalog.py` | NEW |
| `backend/app/services/packages/pricing_engine.py` | NEW |
| `backend/app/services/packages/sales.py` | NEW |
| `backend/app/services/packages/redemption.py` | NEW |
| `backend/app/services/packages/refund.py` | NEW |
| `backend/app/services/packages/expiry_job.py` | NEW |
| `backend/app/services/billing/finalize.py` | MODIFY — invoke PackageSalesService.create_sale for package_sale_line BillItems |
| `backend/app/services/billing/add_item.py` | MODIFY — invoke eligibility check, auto-apply redemption when single eligible |
| `backend/app/api/v1/packages.py` | NEW — all package endpoints |
| `backend/app/api/v1/bills.py` | MODIFY — response of add_item to include eligible_packages[] when 2+ |
| `backend/app/schemas/package.py` | NEW |
| `backend/app/auth/permissions.py` | MODIFY — add 10 new permissions |
| `backend/app/config.py` | MODIFY — PACKAGE_DEFAULT_CANCELLATION_FEE_PCT |
| `alembic/versions/<rev>_add_packages_module.py` | NEW |
| `tests/services/packages/*` | NEW — full suite |
| `tests/api/v1/test_packages.py` | NEW |
| `tests/auth/test_packages_permissions.py` | NEW |

### Frontend

| File | Change |
|---|---|
| `frontend/src/app/(shell)/dashboard/packages/page.tsx` | NEW |
| `frontend/src/app/(shell)/dashboard/packages/[id]/page.tsx` | NEW |
| `frontend/src/app/(shell)/dashboard/packages/[id]/edit/page.tsx` | NEW |
| `frontend/src/app/(shell)/dashboard/packages/new/page.tsx` | NEW |
| `frontend/src/app/(shell)/dashboard/packages/sold/page.tsx` | NEW |
| `frontend/src/app/(shell)/dashboard/pos/page.tsx` | MODIFY — inject EntitlementsRail; render new BillItem types |
| `frontend/src/app/(shell)/dashboard/bills/[id]/page.tsx` | MODIFY — add "Refund Package" action when applicable |
| `frontend/src/components/packages/*` | NEW — see §8.2 |
| `frontend/src/components/ui/SessionsLeft.tsx` | NEW |
| `frontend/src/components/ui/ExpiryBadge.tsx` | NEW |
| `frontend/src/stores/packages-store.ts` | NEW |
| `frontend/src/lib/api/packages.ts` | NEW — typed API client |
| `frontend/src/components/shell/sidebar.tsx` | MODIFY — add Packages menu item (Owner-gated) |
| `frontend/src/components/customers/format.ts` (or equivalent) | MODIFY — extend formatCustomerName for buyer-vs-recipient |
| `frontend/src/components/**/__tests__/*` | NEW — Vitest suites |

### Docs

| File | Change |
|---|---|
| `docs/INDEX.md` | MODIFY — add entry for packages feature doc |
| `docs/features/10-packages.md` | NEW — feature-level documentation |
| `docs/models/10-packages.md` | NEW — model-level documentation |
| `docs/design_system.md` | **SEPARATE TASK** — sync stale tokens to live `tokens.css` (spawned as out-of-band cleanup) |

---

## 17. Out-of-scope follow-ups (intentional spawn targets)

These are not blockers but should be spawned as separate sessions:

1. **Update `docs/design_system.md`** to match shipped tokens (Navy + Gold, Cormorant + DM Sans, cream surfaces). The brief I wrote cited the stale doc, which caused confusion in the design round.
2. **Add the receipt-printing template branch** for `package_redemption` and `package_sale_line` BillItem types — see §13.
3. **First-time-selling coachmark** for receptionists on the Packages chip — deferred from Open-Q6.
4. **Stronger security layers for unlimited / shared package redemption** — deferred by product decision after explicit threat modeling. Sub-project A ships with the existing audit-log and the **last-visit recognition aid** in §8.4 as a passive behavioral signal. If real-world misuse emerges (visible via daily revenue audit by Owner, anomaly in redemption frequency, customer complaints), the deferred layers to add — in rough order of leverage — are: (a) configurable per-day/per-week redemption caps on `PackageDefinition` (very strong, small surface), (b) Owner-facing anomaly-detection daily job (reactive but low-friction), (c) OTP-per-redemption via an SMS gateway (cryptographically strong, requires new SMS infrastructure dependency), and (d) customer photo on profile (depends on sub-project C's customer-profile work). None of these are required for sub-project A to function, but the design space has been explored and documented here so future implementation can move quickly without re-deriving the threat model.

---

## 18. References

- Brief: `2026-05-29-bundles-packages-frontend-design-brief.md`
- Design output: `2026-05-29-bundles-packages-design-output.md`
- Design open questions (all resolved in this spec): `2026-05-29-bundles-packages-design-open-questions.md`
- Mockups: `design-assets/2026-05-29-bundles-packages/`
- Architecture: SalonOS backend spec `docs/architecture/04-backend-spec.md`
- Existing billing model: `docs/models/03-billing.md`
- Existing multi-staff services pattern: `docs/features/01-multi-staff-services.md`
- RBAC reference: `rbac-permissions` skill
- TDD workflow: `testing-workflow` skill
- Alembic patterns: `alembic-migration` skill
- Receipt printing: `receipt-printing` skill
- Zustand patterns: `zustand-store` skill
- Money / GST: `gst-money-handling` skill
- Original brainstorm decisions: Q1–Q11 in conversation history (no transcript file; decisions are captured in §3 of this spec and in the brief's §3 as canonical reference)
