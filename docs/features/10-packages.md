# 10 — Bundles & Session Packages

## What it is

The Packages feature lets salon owners pre-sell service bundles as a single discounted purchase. A customer buys a "Hair Spa 5-pack" today and redeems one session per visit over the next 6 months. The salon collects cash upfront; the customer gets a lower per-session price.

Three package structures are supported:

| Structure | When to use |
|---|---|
| **Counted bundle (personal)** | Fixed N sessions for one customer (e.g. "Facial × 10") |
| **Counted bundle (shared)** | Fixed N sessions redeemable by any registered customer (e.g. family pack) |
| **Unlimited (personal)** | Unlimited sessions within a validity window (e.g. "Hair wash — daily, 90 days") |

---

## User-facing flows

### 1. Admin — Create a package definition (Owner only)

1. Navigate to **Catalogue → Packages → New Package**.
2. Fill in the left column: name, entitlement type, sessions (if counted), validity days, cancellation fee %, auto-apply toggle.
3. Add included services in the right column. Set per-line prices; apply an optional package-level discount (% off / ₹ off / final amount).
4. Click **Save & draft** → review → **Publish**.

Published packages appear in the POS "Packages" tab and in the eligibility rail.

### 2. POS — Sell a package

1. Select a customer with a linked profile.
2. Tap the **Packages** tab in the POS service grid.
3. Tap the desired package card → it appears on the bill as a `package_sale_line` with the bundled price.
4. Finalize payment as normal. At finalization, the system creates a `PackageSale` record and sets `sessions_remaining = total_sessions`.

### 3. POS — Redeem a session

1. Customer arrives; select the customer.
2. The **Entitlements Rail** shows all active packages with sessions remaining and expiry.
3. Add the service (e.g. "Hair Spa") from the service grid. If exactly one eligible package with `auto_apply = true` exists, the system auto-applies the redemption — the bill line becomes gold-tinted with "Paid via package". If two or more eligible packages exist, the `MultiPackageSelector` prompts the cashier to choose which one.
4. Complete the bill. The payment canvas shows a "PACKAGE REDEMPTION" entry (internal accounting).
5. To **undo** a redemption (only on DRAFT bills): click the **↩ Undo** pill on the redemption line.

### 4. Owner — Refund a package

1. Navigate to **Packages → Sold Packages** or open the original sale bill.
2. Click **Refund** on the relevant package row.
3. Choose the refund method (cash / UPI / card / pending balance) and enter a reason.
4. Click **Issue Credit Note** → the system calculates the refundable amount after the cancellation fee and creates a credit note bill.

### 5. Owner — Extend expiry

1. Navigate to **Packages → Sold Packages**.
2. Click **Extend** on an active (or recently expired) package.
3. Set a new expiry date (must be after the current expiry) and enter a reason.

---

## Key non-obvious behaviors

### Snapshot pricing
When a package is sold, all per-line prices are snapshotted into `PackageSaleItem.snapshot_unit_price_paise`. Subsequent edits to the `PackageDefinition` do not affect already-sold packages. This means the customer's purchase price is locked at sale time.

### FIFO conflict resolution
When two packages both cover the same service, the system selects the one expiring soonest (FIFO). If `auto_apply` is on and only one eligible package exists, it is applied silently. If two or more exist, the cashier sees the `MultiPackageSelector` to pick one.

### Shared redemption
A `shared` package can be redeemed by any registered customer, not just the buyer. The audit log (`PackageRedemptionAudit`) records both the buyer and the recipient for each redemption. Staff role users do not see the buyer's name (PII redaction).

### Unlimited package refund math
For unlimited packages, the refund is pro-rated by time remaining. Formula:
```
refundable = total_purchase_price × (days_remaining / validity_days) × (1 − cancellation_fee_pct)
```

### Last-visit recognition aid
When a customer is selected in POS, the customer header shows `Last visit: <relative date>`. This lets the cashier recognise returning customers faster.

---

## Edge cases and troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| "Package not applied automatically" | Service ID on the bill item doesn't match any `PackageSaleItem.service_id` | Check that the service added to the bill is the exact same service in the package definition |
| Redemption rejected: "no sessions remaining" | `sessions_remaining` reached 0 | Package is exhausted; issue a new package or the customer pays full price |
| Redemption rejected: "Package expired" | `expires_at < now` | Owner can extend expiry via Sold Packages → Extend |
| Refund shows 0 amount | `cancellation_fee_pct = 100` or all sessions consumed | Intentional — no refundable value remains |
| "Undo" button missing on redemption line | Bill is already POSTED (not DRAFT) | Undo is only allowed on draft bills |
