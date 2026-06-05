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
| `created_by_user_id` | `FK → users.id` | |

**Constraints**: `ck_package_def_entitlement_sessions` enforces counted↔total_sessions pairing.

---

## PackageDefinitionItem

**Table**: `package_definition_items`
**Purpose**: One row per service line in a package definition.

| Column | Type | Notes |
|---|---|---|
| `package_definition_id` | `FK → package_definitions.id` | CASCADE delete |
| `service_id` | `FK → services.id` | RESTRICT |
| `quantity` | `Integer` | ≥ 1 |
| `unit_price_paise` | `Integer` | ≥ 0; snapshotted to PackageSaleItem at sale |
| `locked` | `Boolean` | Locked lines are skipped during package-level discount distribution |
| `display_order` | `Integer` | |

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

**Index**: `(service_id, package_sale_id)` — covering index for eligibility sub-query.

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
