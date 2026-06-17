# 10 — Packages Models

Six new tables added in migration `l5m6n7o8p9q0_add_packages_module`.

---

## Entity Relationship

```
PackageDefinition (1) ──── (N) PackageDefinitionItem
     │
     │  bill_id (1:1)
PackageSale ─────────────────── Bill (original sale bill)
     │
     │  (1) ──── (N) PackageSaleItem
     │  (1) ──── (N) PackageRedemptionAudit
     │  (1) ──── (N) PackageExpiryExtension
     │
     └── refund_bill_id → Bill (credit note, nullable)
```

---

## PackageDefinition

**Table**: `package_definitions`
**Purpose**: Catalog row. Edits to this row do not affect already-sold packages (all pricing is snapshotted at sale time).

| Column | Type | Notes |
|---|---|---|
| `id` | `String(26)` | ULID PK |
| `name` | `String(255)` | Required |
| `description` | `Text` | Optional |
| `status` | `Enum` | `draft` → `published` → `archived` |
| `entitlement_type` | `Enum` | `counted` or `unlimited` |
| `total_sessions` | `Integer` | Required when counted; NULL when unlimited |
| `shareability` | `Enum` | `owner_only` or `shared` |
| `validity_days` | `Integer` | Must be > 0 |
| `auto_apply` | `Boolean` | Auto-redeem when exactly 1 eligible package |
| `cancellation_fee_pct` | `Numeric(5,2)` | 0–100; default 20.00 |
| `discount_mode` | `String(8)` | Optional: `pct` \| `flat` \| `final`. NULL = no discount |
| `discount_value` | `Numeric(12,2)` | Paise for flat/final, percentage for pct. Paired with `discount_mode` |
| `blocks` | `JSONB` | Package Builder v2 entitlement-block stack. NULL = v1 (items-based) package |
| `stored_price_paise` | `Integer` | v2 builder-computed sell price. NULL = derive from items+discount |
| `created_by_user_id` | `FK → users.id` | |

**Constraints**: `ck_package_def_entitlement_sessions` enforces counted↔total_sessions pairing **for v1 rows** (relaxed: any row with non-NULL `blocks` is exempt, since v2 packages have no sessions envelope); `ck_package_def_discount_pair` enforces mode↔value pairing.

**Package Builder v2 (since 2026-06)**: the v2 builder models a package as a stack of
**entitlement blocks** (`items` · `choice` · `unlimited` · `pool` · `credit`) instead of
a flat items list. The block stack is stored as JSON in `blocks` and the builder's
computed sell price in `stored_price_paise` (which `final_price_paise` returns verbatim
when set). v2 packages persist with **empty `items`**. **Selling + redemption are wired** (since
2026-06-13): a `package_sale_line` BillItem carries `package_definition_id` +
`package_locked_choices`; at settlement `create_sale` projects the block stack onto the
existing session-pool model via `_block_sale_lines`:

| Block | Sale mapping | Budget |
|---|---|---|
| items | one capped line/row (max = qty) | global pool (Σ qty) |
| choice @purchase | single-use line per **locked** service | global pool (picks) |
| choice @visit | **independent counter** of `picks`, shared across options | own `package_sale_blocks` row |
| pool | **independent counter** of `sessions`, shared across services | own `package_sale_blocks` row |
| unlimited | `pool_exempt` free lines (survive EXHAUSTED to expiry) | none (unlimited) |
| credit | *skipped — wallet redemption not yet modelled* | none |

**Independent block counters (since 2026-06-14):** choice @visit and pool blocks each
get a `package_sale_blocks` row — `remaining` is a budget shared across that block's
option lines (use any option, N times total, any day), wholly separate from the global
session pool. Governed lines carry `sale_block_id` and are excluded from
`total_sessions`. `apply_redemption`/`undo_redemption` decrement/restore the block
counter under the sale-row lock; `find_eligible_packages` keeps such lines eligible
while the block has budget (and past EXHAUSTED, like pool-exempt lines).

**Buy-and-use-immediately (since 2026-06-16):** one cart can sell a v2 package AND redeem
its services in the same checkout. Because the `PackageSale` is created at POSTING, a
service line carries `BillItem.redeem_from_definition_id` (the package's *definition* id,
not a sale id). On a draft bill it stays a normal charged `SERVICE`; at posting,
`_create_package_sales_for_bill` creates the sale first, then a second pass redeems each
flagged service line against the new sale via `apply_redemption` (which validates
coverage + budget + quantity, so an over-claim raises and aborts the post). The POS cart
previews this by allocating against the cart package's *definition* budget
(`definitionServiceBudgets`, the cart-side mirror of `_block_sale_lines`) **after** owned
packages; the payload sends `redeem_from_definition_id` for those lines (vs
`package_sale_id` for owned-package redemptions).

New columns: `package_sale_items.pool_exempt` (unlimited lines bypass the session pool +
EXHAUSTED gate; honoured in apply/undo redemption + eligibility), and
`package_sale_items.package_definition_item_id` is now **nullable** (v2 lines have no
definition item). **Known gaps:** per-visit choice is a *soft* budget (the global pool
caps the true total but a single option could be over-redeemed), credit blocks aren't
redeemable yet, and counted-refund value for v2 sales is approximate. v1 packages
untouched.

**Discount persistence (since 2026-06)**: items store **gross** (entered) prices and the
package-level discount lives on the definition, so edits round-trip exactly what was
entered. The discount is applied by `distribute_discount` at **sale time** (snapshot
prices on `PackageSaleItem`) and exposed read-only as `final_price_paise` on the API
response. Definitions created before this change have NULL discount and already-net
item prices, which remain correct as-is.

---

## PackageDefinitionItem

**Table**: `package_definition_items`
**Purpose**: One row per service line in a package definition.

| Column | Type | Notes |
|---|---|---|
| `package_definition_id` | `FK → package_definitions.id` | CASCADE delete |
| `service_id` | `FK → services.id` | RESTRICT |
| `quantity` | `Integer` | ≥ 1 |
| `unit_price_paise` | `Integer` | ≥ 0; GROSS (entered) price. The discounted effective price is snapshotted to PackageSaleItem at sale |
| `locked` | `Boolean` | Locked lines are skipped during package-level discount distribution |
| `display_order` | `Integer` | |
| `max_redemptions` | `Integer` | Optional. Per-line cap: max times this line can be redeemed across the package's lifetime. `NULL` = no per-line cap (draws from global sessions pool only). CHECK >= 1. |

---

## PackageSale

**Table**: `package_sales`
**Purpose**: Lifecycle row for one sold package. All policy is snapshotted at sale time.

| Column | Type | Notes |
|---|---|---|
| `bill_id` | `FK → bills.id` (unique) | RESTRICT; 1:1 with the sale bill |
| `package_definition_id` | `FK → package_definitions.id` | RESTRICT |
| `customer_id` | `FK → customers.id` | RESTRICT |
| `selling_staff_id` | `FK → staff.id` | SET NULL |
| `sold_at` | `DateTime(tz=True)` | |
| `expires_at` | `DateTime(tz=True)` | Indexed; updated by extend_expiry |
| `entitlement_type_snapshot` | `Enum` | Frozen at sale |
| `shareability_snapshot` | `Enum` | Frozen at sale |
| `cancellation_fee_pct_snapshot` | `Numeric(5,2)` | Frozen at sale |
| `total_sessions_snapshot` | `Integer` | NULL for unlimited |
| `sessions_remaining` | `Integer` | NULL for unlimited; decrements on redemption |
| `status` | `Enum` | `active` → `exhausted` / `expired` / `refunded` |
| `refunded_at` | `DateTime` | Set on refund |
| `refund_bill_id` | `FK → bills.id` | Links to credit note |

**Indexes**: `(customer_id, status)`, `(expires_at, status)` — used by eligibility and daily expiry job.

**Invariants**:
- `sessions_remaining` must be `≥ 0` (never goes negative; SELECT FOR UPDATE prevents races).
- `bill_id` is unique (one sale per bill).
- `status` = `exhausted` iff `sessions_remaining` = 0.

---

## PackageSaleItem

**Table**: `package_sale_items`
**Purpose**: Per-service snapshot at sale time. One row per `PackageDefinitionItem`.

| Column | Type | Notes |
|---|---|---|
| `package_sale_id` | `FK → package_sales.id` | CASCADE delete |
| `package_definition_item_id` | `FK → package_definition_items.id` | RESTRICT |
| `service_id` | `FK → services.id` | RESTRICT; used by eligibility query |
| `snapshot_unit_price_paise` | `Integer` | Locked at sale |
| `snapshot_gst_rate_pct` | `Numeric(5,2)` | Always `0.00` (tax-inclusive prices) |
| `locked` | `Boolean` | |
| `display_order` | `Integer` | |
| `max_redemptions` | `Integer` | Optional. Snapshot of the definition item's cap at sale time. `NULL` = uncapped. |
| `remaining` | `Integer` | Optional. Redemption counter that decrements on each use. Starts equal to `max_redemptions`; `NULL` iff `max_redemptions` is `NULL`. CHECK >= 0. |

**Index**: `(service_id, package_sale_id)` — covering index for eligibility sub-query.

### Per-line cap invariants

- `max_redemptions` and `remaining` are always NULL together or NOT NULL together
  (enforced by `ck_package_sale_item_remaining_matches_cap`).
- `remaining` starts equal to `max_redemptions` at sale time (snapshotted in
  `package_sales_service.create_sale`).
- `remaining` is decremented by 1 on each successful `apply_redemption` call and
  restored by `undo_redemption`.
- The eligibility query (`find_eligible_packages`) only returns sale items where
  `max_redemptions IS NULL OR remaining > 0`.

---

## PackageRedemptionAudit

**Table**: `package_redemption_audit`
**Purpose**: Append-only log of every redemption. Captures who redeemed and for whom (important for shared packages).

| Column | Type | Notes |
|---|---|---|
| `package_sale_id` | `FK → package_sales.id` | RESTRICT |
| `bill_item_id` | `FK → bill_items.id` (unique) | RESTRICT; 1:1 with the BillItem |
| `package_sale_item_id` | `FK → package_sale_items.id` | RESTRICT |
| `redeemed_for_customer_id` | `FK → customers.id` | RESTRICT; may differ from sale.customer_id (shared) |
| `performed_by_user_id` | `FK → users.id` | SET NULL |
| `redeemed_at` | `DateTime(tz=True)` | |
| `session_number` | `Integer` | NULL for unlimited |
| `notes` | `Text` | Optional |

**Known limitation**: payment lookup during undo uses `(bill_id, payment_method, amount)` triple (not unique if two equal-value redemptions hit the same bill). A future migration should add `payment_id` to this table.

---

## PackageExpiryExtension

**Table**: `package_expiry_extensions`
**Purpose**: Audit trail for every expiry extension.

| Column | Type | Notes |
|---|---|---|
| `package_sale_id` | `FK → package_sales.id` | RESTRICT |
| `previous_expires_at` | `DateTime(tz=True)` | Snapshot before extension |
| `new_expires_at` | `DateTime(tz=True)` | Must be > previous |
| `performed_by_user_id` | `FK → users.id` | SET NULL |
| `extended_at` | `DateTime(tz=True)` | |
| `reason` | `Text` | Required |

**Constraint**: `ck_package_extend_forward_in_time` enforces `new_expires_at > previous_expires_at`.

---

## BillItem additions

Two columns added to `bill_items` in `edc2fc235e3b_add_package_definition_id_to_bill_items`:

| Column | Type | Notes |
|---|---|---|
| `item_type` | `Enum` | `service` (default) / `product` / `package_sale_line` / `package_redemption` |
| `package_sale_id` | `FK → package_sales.id` | Set on package_redemption items |
| `package_sale_item_id` | `FK → package_sale_items.id` | Set on package_redemption items |
| `package_definition_id` | `FK → package_definitions.id` | Set on package_sale_line items (used at finalization to create PackageSale) |

---

## Bill additions

| Column | Type | Notes |
|---|---|---|
| `bill_type` | `Enum` | `normal` (default) / `credit_note` |
| `original_bill_id` | `FK → bills.id` | Set on credit notes; NULL on normal bills |

---

## Daily expiry job

A daily cron job (02:00 IST) bulk-marks `ACTIVE` sales with `expires_at < now()` as `EXPIRED`. Implemented in `app/jobs/scheduled.py` (`package_expiry_transitions_job`) and registered in `app/worker.py`.
