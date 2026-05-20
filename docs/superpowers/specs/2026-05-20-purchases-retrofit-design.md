# Purchases Module — V2 Retrofit + Outstanding Balances UX

**Date:** 2026-05-20
**Status:** Approved

---

## Goal

Retrofit the four existing purchases pages with V2 semantic design tokens, upgrade loading/empty-state patterns, fix a date timezone bug, and add a prominent "Outstanding Balances" section to the invoice list page so staff can see and pay vendor balances without navigating through the supplier detail page.

---

## Architecture

No new backend endpoints. All data comes from two existing API calls (`listSuppliers` + `listPurchaseInvoices`) fired in parallel on page load. The outstanding balance section is derived entirely client-side.

**Files changed:**

| File | Change type |
|---|---|
| `frontend/src/app/(shell)/dashboard/purchases/invoices/page.tsx` | Outstanding section + token fixes + Skeleton + EmptyState |
| `frontend/src/app/(shell)/dashboard/purchases/invoices/[id]/page.tsx` | Token fixes only |
| `frontend/src/app/(shell)/dashboard/purchases/invoices/new/page.tsx` | Token fixes only |
| `frontend/src/app/(shell)/dashboard/purchases/suppliers/page.tsx` | Token fixes + `formatDate` timezone fix |

---

## Feature 1: Outstanding Balances Section (`invoices/page.tsx`)

### Placement
Above the status filter chips, below the page header. Hidden entirely when no supplier has `total_outstanding > 0`.

### Page load data fetch
```
Promise.all([
  purchaseApi.listSuppliers({ active_only: true, size: 100 }),
  purchaseApi.listPurchaseInvoices({ size: 50, ...filters }),
])
```
Both calls fire simultaneously. Outstanding suppliers are derived client-side from the supplier list response.

### Each supplier row contains
- **Supplier name** — links to `/dashboard/purchases/suppliers/{id}`
- **Oldest unpaid invoice date** — minimum `invoice_date` across invoices where `supplier_id` matches AND `balance_due > 0` AND `status !== 'draft'`. Computed from the already-fetched invoice list. Displayed as "Since 12 Mar 2026".
- **Outstanding amount** — `total_outstanding` in `text-warning-fg`
- **Pay button** — navigates to `/dashboard/purchases/payments/new?supplier_id={id}`

### Layout
- **Desktop:** horizontal row — name | since date | amount | Pay button
- **Mobile:** stacked card — supplier name top row, amount + Pay button bottom row
- Section header: "Outstanding Balances" + count badge in `text-warning-fg`
- Row surface: `bg-surface-card border border-border-default rounded-xl`

### Loading state
3 × `<Skeleton shape="row" />` with `aria-busy="true"` on wrapper, shown while either API call is in flight.

### Empty (no outstanding)
Section renders `null` — no empty state message.

---

## Feature 2: Token Fixes (all four pages)

### Semantic token map

| Raw class (current) | Semantic token (replacement) | Meaning |
|---|---|---|
| `text-green-600`, `text-green-400` | `text-success-fg` | Paid amounts, credit entries |
| `text-amber-400`, `text-orange-600` | `text-warning-fg` | Balance due, outstanding |
| `text-red-600` | `text-danger-fg` | Overpayment warning |
| `text-blue-600`, `text-blue-400` | `text-accent` | Tax lines, informational amounts |
| `text-muted-foreground` | `text-text-muted` | Muted labels (suppliers page) |

### Status badge token map (`invoices/page.tsx` `getStatusChip`)

| Status | Before | After |
|---|---|---|
| `draft` | `bg-slate-500/40 text-slate-400` | `bg-surface-row text-text-muted border border-border-subtle` |
| `received` | `bg-blue-500/40 text-blue-400` | `bg-accent/10 text-accent border border-accent/20` |
| `partially_paid` | `bg-amber-500/40 text-amber-400` | `bg-warning-bg-soft text-warning-fg border border-warning-border` |
| `paid` | `bg-green-500/40 text-green-400` | `bg-success-bg-soft text-success-fg border border-success-border` |

---

## Feature 3: Pattern Upgrades (`invoices/page.tsx`)

### Loading state
Replace `<div className="text-center py-12">Loading invoices...</div>` with 5 × `<Skeleton shape="row" />` inside an `aria-busy="true"` wrapper.

### Empty state
Replace the plain `<Card>` empty state with the `<EmptyState>` component:
```tsx
<EmptyState
  title="No purchase invoices"
  body="Create your first invoice to start tracking supplier purchases."
  headingLevel={3}
/>
```
When a search/filter is active: `title="No matching invoices"`, `body="Try a different status filter or date range."`

---

## Feature 4: `formatDate` Timezone Fix

**Problem:** `new Date("2026-01-15")` parses as UTC midnight, which rolls back to Jan 14 in IST (UTC+5:30).

**Fix:** Append `'T00:00:00'` before constructing the Date object:
```ts
new Date(dateString + 'T00:00:00').toLocaleDateString('en-IN', { ... })
```

**Apply to:** `invoices/page.tsx` and `suppliers/page.tsx`. (Already fixed in `suppliers/[id]/page.tsx` from the previous session.)

---

## Feature 5: `formatCurrency` Consistency (`invoices/page.tsx`)

Replace `toFixed(2)` with `toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })` to match the formatting used in all other purchases pages.

---

## What is NOT changing

- No structural/layout changes to `invoices/[id]/page.tsx` or `invoices/new/page.tsx` — token fixes only
- No new backend endpoints
- No changes to routing or navigation structure beyond the existing links
- The suppliers page form (add/edit supplier) is not touched
