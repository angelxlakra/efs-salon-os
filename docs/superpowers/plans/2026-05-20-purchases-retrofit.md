# Purchases Module V2 Retrofit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Retrofit four purchases pages with V2 semantic design tokens, upgrade loading/empty-state patterns, fix the `formatDate` UTC timezone bug, and add a prominent Outstanding Balances section to the invoice list page.

**Architecture:** Frontend-only. No new backend endpoints. `invoices/page.tsx` upgrades to `Promise.all([listSuppliers, listPurchaseInvoices])` on every load; outstanding suppliers are derived client-side from the supplier response. The Outstanding section renders above the status filter chips and is hidden entirely when every supplier has `total_outstanding === 0`.

**Tech Stack:** Next.js (App Router), React 19, TypeScript, Tailwind, `Skeleton` (`@/components/ui/skeleton`, shapes: `row|card|kpi|text`), `EmptyState` (`@/components/ui/empty-state`, props: `title body headingLevel`).

---

## File Map

| File | Task | Change type |
|---|---|---|
| `frontend/src/app/(shell)/dashboard/purchases/invoices/page.tsx` | T1 | Outstanding section + Promise.all + token fixes + Skeleton + EmptyState + formatDate + formatCurrency |
| `frontend/src/app/(shell)/dashboard/purchases/invoices/[id]/page.tsx` | T2 | Token fixes only |
| `frontend/src/app/(shell)/dashboard/purchases/invoices/new/page.tsx` | T3 | Token fixes only |
| `frontend/src/app/(shell)/dashboard/purchases/suppliers/page.tsx` | T4 | Token fixes only |

### Semantic token reference

| Raw class (current) | Semantic token (replacement) |
|---|---|
| `text-muted-foreground` | `text-text-muted` |
| `text-green-600`, `text-green-400` | `text-success-fg` (paid amounts, settled balances) |
| `text-amber-400`, `text-orange-600` | `text-warning-fg` (balance due, outstanding, discounts) |
| `text-red-600` | `text-danger-fg` |
| `text-blue-600`, `text-blue-400` | `text-accent` (tax lines) |

---

## Task 1: `invoices/page.tsx` — Outstanding Section + All Fixes

**Files:**
- Modify: `frontend/src/app/(shell)/dashboard/purchases/invoices/page.tsx`

- [ ] **Step 1: Confirm TypeScript baseline compiles**

```bash
cd /path/to/repo/frontend && npx tsc --noEmit 2>&1 | head -20
```

Expected: zero errors (or only pre-existing errors unrelated to this file).

- [ ] **Step 2: Replace the import block**

Replace lines 1–11 (the entire import block):

```tsx
// OLD
import { useState, useEffect, useCallback } from 'react';
import { Plus, FileText, CheckCircle, DollarSign, Eye, Users, Search, Calendar } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { purchaseApi, PurchaseInvoiceListItem } from '@/lib/api/purchases';
import { toast } from 'sonner';
import { useRouter } from 'next/navigation';
```

```tsx
// NEW
import { useState, useEffect } from 'react';
import { Plus, CheckCircle, DollarSign, Eye, Users, Search } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Skeleton } from '@/components/ui/skeleton';
import { EmptyState } from '@/components/ui/empty-state';
import { purchaseApi, PurchaseInvoiceListItem, SupplierListItem } from '@/lib/api/purchases';
import { toast } from 'sonner';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
```

- [ ] **Step 3: Add `suppliers` state + update `loadInvoices` to `Promise.all`**

After `const [searchDebounced, setSearchDebounced] = useState('');` (line 21) add:

```tsx
const [suppliers, setSuppliers] = useState<SupplierListItem[]>([]);
```

Replace the `loadInvoices` function body (lines 32–48):

```tsx
// OLD
const loadInvoices = async () => {
  try {
    setLoading(true);
    const params: Record<string, string | number> = { size: 50 };
    if (statusFilter !== 'all') params.status = statusFilter;
    if (searchDebounced) params.search = searchDebounced;
    if (startDate) params.start_date = startDate;
    if (endDate) params.end_date = endDate;
    const response = await purchaseApi.listPurchaseInvoices(params);
    setInvoices(response.items || []);
  } catch (error) {
    console.error('Error loading invoices:', error);
    toast.error('Failed to load purchase invoices');
  } finally {
    setLoading(false);
  }
};
```

```tsx
// NEW
const loadInvoices = async () => {
  try {
    setLoading(true);
    const params: Record<string, string | number> = { size: 50 };
    if (statusFilter !== 'all') params.status = statusFilter;
    if (searchDebounced) params.search = searchDebounced;
    if (startDate) params.start_date = startDate;
    if (endDate) params.end_date = endDate;
    const [supplierResponse, invoiceResponse] = await Promise.all([
      purchaseApi.listSuppliers({ active_only: true, size: 100 }),
      purchaseApi.listPurchaseInvoices(params),
    ]);
    setSuppliers(supplierResponse.items || []);
    setInvoices(invoiceResponse.items || []);
  } catch (error) {
    console.error('Error loading data:', error);
    toast.error('Failed to load purchase data');
  } finally {
    setLoading(false);
  }
};
```

- [ ] **Step 4: Fix `formatCurrency`, `formatDate`, and `getStatusChip`**

Replace `formatCurrency` (lines 50–52):

```tsx
// OLD
const formatCurrency = (amount: number) => {
  return `₹${(amount / 100).toFixed(2)}`;
};
```

```tsx
// NEW
const formatCurrency = (amount: number) => {
  return `₹${(amount / 100).toLocaleString('en-IN', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
};
```

Replace `formatDate` (lines 54–60):

```tsx
// OLD
const formatDate = (dateString: string) => {
  return new Date(dateString).toLocaleDateString('en-IN', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  });
};
```

```tsx
// NEW
const formatDate = (dateString: string) => {
  return new Date(dateString + 'T00:00:00').toLocaleDateString('en-IN', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  });
};
```

Replace `getStatusChip` (lines 62–74):

```tsx
// OLD
const getStatusChip = (status: string) => {
  const styles: Record<string, string> = {
    draft: 'bg-slate-500/40 text-slate-400',
    received: 'bg-blue-500/40 text-blue-400',
    partially_paid: 'bg-amber-500/40 text-amber-400',
    paid: 'bg-green-500/40 text-green-400',
  };
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${styles[status] ?? 'bg-slate-500/40 text-slate-400'}`}>
      {status.replace('_', ' ').toUpperCase()}
    </span>
  );
};
```

```tsx
// NEW
const getStatusChip = (status: string) => {
  const styles: Record<string, string> = {
    draft:           'bg-surface-row text-text-muted border border-border-subtle',
    received:        'bg-accent/10 text-accent border border-accent/20',
    partially_paid:  'bg-warning-bg-soft text-warning-fg border border-warning-border',
    paid:            'bg-success-bg-soft text-success-fg border border-success-border',
  };
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${styles[status] ?? 'bg-surface-row text-text-muted border border-border-subtle'}`}>
      {status.replace('_', ' ').toUpperCase()}
    </span>
  );
};
```

After `const filteredInvoices = invoices;` (line 76) add the derived constant:

```tsx
const outstandingSuppliers = suppliers.filter((s) => s.total_outstanding > 0);
```

- [ ] **Step 5: Add Outstanding Balances section + fix loading and empty states**

The JSX inside `return (...)` needs three targeted changes. Apply them in this order.

**5a. Insert Outstanding Balances section after the Header `</div>` and before the Status Filter comment.**

Find this JSX block (just before `{/* Status Filter */}`):

```tsx
      </div>

      {/* Status Filter */}
```

Replace with:

```tsx
      </div>

      {/* Outstanding Balances */}
      {loading ? (
        <div aria-busy="true" className="space-y-2">
          <Skeleton shape="row" />
          <Skeleton shape="row" />
          <Skeleton shape="row" />
        </div>
      ) : outstandingSuppliers.length > 0 ? (
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <h2 className="text-sm font-semibold text-text-primary">Outstanding Balances</h2>
            <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-warning-bg-soft text-warning-fg border border-warning-border">
              {outstandingSuppliers.length}
            </span>
          </div>
          {outstandingSuppliers.map((supplier) => {
            const oldestDate = invoices
              .filter(
                (inv) =>
                  inv.supplier_id === supplier.id &&
                  inv.balance_due > 0 &&
                  inv.status !== 'draft',
              )
              .map((inv) => inv.invoice_date)
              .sort()[0];
            return (
              <div
                key={supplier.id}
                className="bg-surface-card border border-border-default rounded-xl px-4 py-3 flex flex-col sm:flex-row sm:items-center gap-3"
              >
                <Link
                  href={`/dashboard/purchases/suppliers/${supplier.id}`}
                  className="text-sm font-semibold text-text-primary hover:text-accent hover:underline flex-1 min-w-0 truncate"
                >
                  {supplier.name}
                </Link>
                {oldestDate && (
                  <span className="hidden sm:inline text-xs text-text-muted shrink-0">
                    Since {formatDate(oldestDate)}
                  </span>
                )}
                <span className="text-sm font-bold text-warning-fg shrink-0">
                  {formatCurrency(supplier.total_outstanding)}
                </span>
                <Button
                  size="sm"
                  variant="outline"
                  className="shrink-0"
                  onClick={() =>
                    router.push(
                      `/dashboard/purchases/payments/new?supplier_id=${supplier.id}`,
                    )
                  }
                >
                  Pay
                </Button>
              </div>
            );
          })}
        </div>
      ) : null}

      {/* Status Filter */}
```

**5b. Replace the loading state (currently plain text, line 182).**

Find:

```tsx
      {loading ? (
        <div className="text-center py-12">Loading invoices...</div>
```

Replace with:

```tsx
      {loading ? (
        <div aria-busy="true" className="space-y-3">
          <Skeleton shape="row" />
          <Skeleton shape="row" />
          <Skeleton shape="row" />
          <Skeleton shape="row" />
          <Skeleton shape="row" />
        </div>
```

**5c. Replace the empty state (plain Card) and fix the balance due token.**

Find the empty state block:

```tsx
      ) : filteredInvoices.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center">
            <FileText className="mx-auto h-12 w-12 text-text-muted mb-4" />
            <p className="text-text-secondary">
              No purchase invoices found
            </p>
          </CardContent>
        </Card>
```

Replace with:

```tsx
      ) : filteredInvoices.length === 0 ? (
        <EmptyState
          title={
            searchDebounced || statusFilter !== 'all' || startDate || endDate
              ? 'No matching invoices'
              : 'No purchase invoices'
          }
          body={
            searchDebounced || statusFilter !== 'all' || startDate || endDate
              ? 'Try a different status filter or date range.'
              : 'Create your first invoice to start tracking supplier purchases.'
          }
          headingLevel={3}
        />
```

Find the balance due line in the desktop card (inside the `hidden md:block` section):

```tsx
                        {invoice.balance_due > 0 && (
                          <div className="text-sm font-medium text-amber-400">
                            Due: {formatCurrency(invoice.balance_due)}
                          </div>
                        )}
```

Replace with:

```tsx
                        {invoice.balance_due > 0 && (
                          <div className="text-sm font-medium text-warning-fg">
                            Due: {formatCurrency(invoice.balance_due)}
                          </div>
                        )}
```

- [ ] **Step 6: TypeScript check**

```bash
cd frontend && npx tsc --noEmit 2>&1
```

Expected: zero errors. If `SupplierListItem` import is flagged, confirm it is exported from `@/lib/api/purchases` (it is — line 28 of purchases.ts).

- [ ] **Step 7: Commit**

```bash
git add frontend/src/app/\(shell\)/dashboard/purchases/invoices/page.tsx
git commit -m "feat: add Outstanding Balances section + V2 tokens to invoices list page"
```

---

## Task 2: `invoices/[id]/page.tsx` — Token Fixes

**Files:**
- Modify: `frontend/src/app/(shell)/dashboard/purchases/invoices/[id]/page.tsx`

- [ ] **Step 1: Replace all `text-muted-foreground` → `text-text-muted`**

This file has 13 occurrences spanning label text, barcode hints, payment notes, and sidebar labels. Use `replace_all`:

```
old_string: "text-muted-foreground"
new_string: "text-text-muted"
replace_all: true
```

Affected lines (for verification): 113, 134, 175, 179, 184, 190, 196, 199, 216, 231, 236, 249, 255, 271, 308, 312, 349, 351.

- [ ] **Step 2: Fix item discount color (discount is a deduction — `text-warning-fg`)**

Mobile card (line 240):

```tsx
// OLD
                          <span className="text-green-600">-{formatCurrency(item.discount_amount)}</span>
```

```tsx
// NEW
                          <span className="text-warning-fg">-{formatCurrency(item.discount_amount)}</span>
```

Desktop row (line 259):

```tsx
// OLD
                          <div className="text-xs text-green-600">
                            Discount: -{formatCurrency(item.discount_amount)}
                          </div>
```

```tsx
// NEW
                          <div className="text-xs text-warning-fg">
                            Discount: -{formatCurrency(item.discount_amount)}
                          </div>
```

- [ ] **Step 3: Fix invoice discount color (line 275)**

```tsx
// OLD
                  {invoice.invoice_discount_amount > 0 && (
                    <div className="flex justify-between text-sm text-green-600">
```

```tsx
// NEW
                  {invoice.invoice_discount_amount > 0 && (
                    <div className="flex justify-between text-sm text-warning-fg">
```

- [ ] **Step 4: Fix paid amount and balance due in the Payment Summary sidebar**

Paid amount (line 354) — paid amount is a positive, use `text-success-fg`:

```tsx
// OLD
                  <span className="font-semibold text-green-600">{formatCurrency(invoice.paid_amount)}</span>
```

```tsx
// NEW
                  <span className="font-semibold text-success-fg">{formatCurrency(invoice.paid_amount)}</span>
```

Balance due (line 359) — outstanding is `text-warning-fg`, settled is `text-success-fg`:

```tsx
// OLD
                  <span className={`font-bold text-lg ${invoice.balance_due > 0 ? 'text-orange-600' : 'text-green-600'}`}>
```

```tsx
// NEW
                  <span className={`font-bold text-lg ${invoice.balance_due > 0 ? 'text-warning-fg' : 'text-success-fg'}`}>
```

- [ ] **Step 5: TypeScript check**

```bash
cd frontend && npx tsc --noEmit 2>&1
```

Expected: zero errors.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/app/\(shell\)/dashboard/purchases/invoices/\[id\]/page.tsx
git commit -m "fix: apply V2 semantic tokens to invoice detail page"
```

---

## Task 3: `invoices/new/page.tsx` — Token Fixes

**Files:**
- Modify: `frontend/src/app/(shell)/dashboard/purchases/invoices/new/page.tsx`

- [ ] **Step 1: Replace all `text-muted-foreground` → `text-text-muted`**

This 906-line file has 20 occurrences. Use `replace_all`:

```
old_string: "text-muted-foreground"
new_string: "text-text-muted"
replace_all: true
```

Affected lines (for verification): 382, 446, 458, 470, 584, 588, 592, 596, 652, 662, 672, 718, 745, 761, 766, 778, 786, 801, 829, 850.

- [ ] **Step 2: Fix CGST and SGST color (two separate lines)**

CGST (line 789):

```tsx
// OLD
                    <div className="flex justify-between text-sm text-blue-600">
                      <span>CGST:</span>
```

```tsx
// NEW
                    <div className="flex justify-between text-sm text-accent">
                      <span>CGST:</span>
```

SGST (line 793):

```tsx
// OLD
                    <div className="flex justify-between text-sm text-blue-600">
                      <span>SGST:</span>
```

```tsx
// NEW
                    <div className="flex justify-between text-sm text-accent">
                      <span>SGST:</span>
```

Note: both lines have the same old string but different surrounding context (`<span>CGST:` vs `<span>SGST:`). Use the surrounding lines as context when editing to uniquely identify each target.

- [ ] **Step 3: Fix invoice discount color (line 805)**

Invoice discount is a deduction — `text-warning-fg`:

```tsx
// OLD
                  <div className="flex justify-between text-sm text-green-600">
                    <span>Invoice Discount:</span>
```

```tsx
// NEW
                  <div className="flex justify-between text-sm text-warning-fg">
                    <span>Invoice Discount:</span>
```

- [ ] **Step 4: Fix round-off conditional color (line 811)**

```tsx
// OLD
                  <div className={`flex justify-between text-sm ${roundOff < 0 ? 'text-orange-600' : 'text-green-600'}`}>
```

```tsx
// NEW
                  <div className={`flex justify-between text-sm ${roundOff < 0 ? 'text-warning-fg' : 'text-success-fg'}`}>
```

- [ ] **Step 5: TypeScript check**

```bash
cd frontend && npx tsc --noEmit 2>&1
```

Expected: zero errors.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/app/\(shell\)/dashboard/purchases/invoices/new/page.tsx
git commit -m "fix: apply V2 semantic tokens to new invoice form"
```

---

## Task 4: `suppliers/page.tsx` — Token Fixes

**Files:**
- Modify: `frontend/src/app/(shell)/dashboard/purchases/suppliers/page.tsx`

> **Note on `formatDate`:** The spec lists a `formatDate` timezone fix for this file, but the current suppliers page does not display any date field (the list items only show `name`, `phone`, `total_purchases`, `total_outstanding`, `is_active`). No `formatDate` function exists in the file, so there is nothing to fix. Skip the `formatDate` step.

- [ ] **Step 1: Replace all `text-muted-foreground` → `text-text-muted`**

This file has 9 occurrences. Use `replace_all`:

```
old_string: "text-muted-foreground"
new_string: "text-text-muted"
replace_all: true
```

Affected lines (for verification): 155, 284, 300, 315, 316, 337, 352, 358, 362.

- [ ] **Step 2: TypeScript check**

```bash
cd frontend && npx tsc --noEmit 2>&1
```

Expected: zero errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/app/\(shell\)/dashboard/purchases/suppliers/page.tsx
git commit -m "fix: apply V2 semantic tokens to suppliers list page"
```

---

## Self-Review Against Spec

### Spec coverage

| Spec requirement | Covered by |
|---|---|
| Outstanding Balances section above status filter, hidden when none | T1 Step 5a |
| Promise.all([listSuppliers, listPurchaseInvoices]) | T1 Step 3 |
| Supplier row: name → link, oldest date, amount in warning-fg, Pay button | T1 Step 5a |
| Desktop horizontal / mobile stacked layout | T1 Step 5a (flex-col sm:flex-row) |
| Section header with count badge in warning-fg | T1 Step 5a |
| Row surface: bg-surface-card border-border-default rounded-xl | T1 Step 5a |
| Loading: 3×Skeleton row + aria-busy (outstanding section) | T1 Step 5a |
| Loading: 5×Skeleton row (invoice list) | T1 Step 5b |
| Empty: null when no outstanding | T1 Step 5a (`: null`) |
| EmptyState component for invoice list | T1 Step 5c |
| EmptyState filter-aware text | T1 Step 5c |
| getStatusChip semantic tokens (all 4 statuses) | T1 Step 4 |
| balance_due text-warning-fg | T1 Step 5c |
| formatDate T00:00:00 fix for invoices/page.tsx | T1 Step 4 |
| formatCurrency toLocaleString for invoices/page.tsx | T1 Step 4 |
| text-muted-foreground → text-text-muted (invoices/[id]) | T2 Step 1 |
| Item/invoice discounts text-warning-fg (invoices/[id]) | T2 Steps 2–3 |
| Paid amount text-success-fg (invoices/[id]) | T2 Step 4 |
| Balance due text-warning-fg / text-success-fg (invoices/[id]) | T2 Step 4 |
| CGST/SGST text-accent (invoices/new) | T3 Step 2 |
| Invoice discount text-warning-fg (invoices/new) | T3 Step 3 |
| Round-off conditional tokens (invoices/new) | T3 Step 4 |
| text-muted-foreground → text-text-muted (suppliers) | T4 Step 1 |

### Confirmed not changing (per spec)

- No new backend endpoints
- No structural/layout changes to `invoices/[id]/page.tsx` or `invoices/new/page.tsx`
- Suppliers page form (add/edit supplier) untouched
- Suppliers page loading/empty states unchanged (pattern upgrades are invoices/page.tsx only)
- No routing or navigation structure changes beyond existing links
