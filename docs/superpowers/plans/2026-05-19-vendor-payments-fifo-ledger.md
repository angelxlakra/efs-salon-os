# Vendor-Wise Payments — FIFO Allocation + Supplier Ledger Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enable vendor-level payments that are automatically applied to the oldest outstanding invoices (FIFO), and expose a per-supplier ledger showing the full invoice/payment history with a running balance.

**Architecture:** Two-part change — (1) backend FIFO allocation inside `record_supplier_payment` when no invoice is specified, updating each invoice's `paid_amount`/`balance_due`/`status` in chronological order; (2) a new `GET /purchases/suppliers/{id}/ledger` endpoint that merges invoices (debits) and payments (credits) into a chronological statement with a running balance. Frontend adds a supplier detail page surfacing this ledger, updates the payment form to support vendor-level payments, and makes the supplier list rows navigate to the detail page.

**Tech Stack:** FastAPI, SQLAlchemy 2.0, PostgreSQL 15, pytest (real PostgreSQL test DB via `salon_test_db`), Next.js 16, React 19, Tailwind CSS v4.

---

## Context — existing schema

- `supplier_payments.purchase_invoice_id` is already `Optional[str] = None` in the Pydantic schema — the field exists and can be null.
- Currently a payment with no invoice link is stored but **does not update any invoice**. That is the gap this plan fixes.
- `Supplier.total_outstanding` is a Python `@property` that sums `balance_due` across all related `PurchaseInvoice` rows.
- Backend test DB: real PostgreSQL at `postgresql+psycopg://salon_user:change_me_123@localhost:5432/salon_test_db`. Tests use `db_session` fixture (function-scoped, rolls back after each test). All fixtures live in `backend/tests/conftest.py`.
- Frontend API client: `frontend/src/lib/api/purchases.ts` — the `purchaseApi` object wraps all purchases endpoints.

---

## File structure

| Status | File | Responsibility |
|---|---|---|
| Modify | `backend/app/api/purchases.py:671-675` | FIFO allocation when `invoice` is None |
| Modify | `backend/app/schemas/purchase.py` | Add `LedgerEntry`, `SupplierLedgerResponse` schemas |
| Modify | `backend/app/api/purchases.py:100` | New `GET /suppliers/{supplier_id}/ledger` endpoint |
| Create | `backend/tests/test_purchases.py` | Tests for FIFO allocation + ledger |
| Modify | `frontend/src/lib/api/purchases.ts` | `LedgerEntry`, `SupplierLedger` types; `getSupplierLedger` API call |
| Create | `frontend/src/app/(shell)/dashboard/purchases/suppliers/[id]/page.tsx` | Supplier detail + ledger page |
| Modify | `frontend/src/app/(shell)/dashboard/purchases/payments/new/page.tsx` | `supplier_id` query param, FIFO hint, post-payment redirect |
| Modify | `frontend/src/app/(shell)/dashboard/purchases/suppliers/page.tsx` | Supplier name links to detail page |

---

## Task 1: Backend — FIFO allocation in `record_supplier_payment`

**Files:**
- Modify: `backend/app/api/purchases.py:671-675`
- Create: `backend/tests/test_purchases.py`

- [ ] **Step 1: Create the test file with failing tests**

Create `backend/tests/test_purchases.py`:

```python
import pytest
from datetime import date
from app.models.purchase import Supplier, PurchaseInvoice, SupplierPayment
from app.utils.ulid import generate_ulid


# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def supplier(db_session):
    s = Supplier(
        id=generate_ulid(),
        name="Test Supplier",
        is_active=True,
    )
    db_session.add(s)
    db_session.flush()
    return s


def make_invoice(db_session, supplier_id: str, total: int, invoice_date=None):
    """Create a RECEIVED invoice with the given total_amount (paise)."""
    inv = PurchaseInvoice(
        id=generate_ulid(),
        supplier_id=supplier_id,
        invoice_number=f"INV-{generate_ulid()[:6]}",
        invoice_date=invoice_date or date(2026, 1, 1),
        subtotal=total,
        invoice_discount_amount=0,
        round_off_amount=0,
        total_amount=total,
        paid_amount=0,
        balance_due=total,
        status="received",
        created_by=generate_ulid(),
    )
    db_session.add(inv)
    db_session.flush()
    return inv


# ── FIFO allocation tests ─────────────────────────────────────────────────────

def test_fifo_payment_fully_settles_oldest_invoice(db_session, supplier, test_user):
    """A general payment that exactly covers the oldest invoice marks it PAID."""
    inv1 = make_invoice(db_session, supplier.id, total=100_00, invoice_date=date(2026, 1, 1))
    inv2 = make_invoice(db_session, supplier.id, total=200_00, invoice_date=date(2026, 2, 1))

    from app.api.purchases import record_supplier_payment
    from app.schemas.purchase import SupplierPaymentCreate

    record_supplier_payment(
        payment_data=SupplierPaymentCreate(
            supplier_id=supplier.id,
            payment_date=date.today(),
            amount=100_00,
            payment_method="cash",
        ),
        current_user=test_user,
        db=db_session,
    )

    db_session.refresh(inv1)
    db_session.refresh(inv2)

    assert inv1.status == "paid"
    assert inv1.balance_due == 0
    assert inv2.status == "received"  # untouched
    assert inv2.balance_due == 200_00


def test_fifo_payment_spans_multiple_invoices(db_session, supplier, test_user):
    """A payment larger than the first invoice spills over into the second."""
    inv1 = make_invoice(db_session, supplier.id, total=100_00, invoice_date=date(2026, 1, 1))
    inv2 = make_invoice(db_session, supplier.id, total=200_00, invoice_date=date(2026, 2, 1))

    from app.api.purchases import record_supplier_payment
    from app.schemas.purchase import SupplierPaymentCreate

    record_supplier_payment(
        payment_data=SupplierPaymentCreate(
            supplier_id=supplier.id,
            payment_date=date.today(),
            amount=150_00,  # covers inv1 fully, ₹50 into inv2
            payment_method="cash",
        ),
        current_user=test_user,
        db=db_session,
    )

    db_session.refresh(inv1)
    db_session.refresh(inv2)

    assert inv1.status == "paid"
    assert inv1.balance_due == 0
    assert inv2.status == "partially_paid"
    assert inv2.balance_due == 150_00  # 200 - 50 = 150


def test_invoice_linked_payment_unchanged(db_session, supplier, test_user):
    """Existing behaviour: invoice-linked payment only touches that invoice."""
    inv1 = make_invoice(db_session, supplier.id, total=100_00, invoice_date=date(2026, 1, 1))
    inv2 = make_invoice(db_session, supplier.id, total=200_00, invoice_date=date(2026, 2, 1))

    from app.api.purchases import record_supplier_payment
    from app.schemas.purchase import SupplierPaymentCreate

    record_supplier_payment(
        payment_data=SupplierPaymentCreate(
            supplier_id=supplier.id,
            purchase_invoice_id=inv1.id,
            payment_date=date.today(),
            amount=50_00,
            payment_method="cash",
        ),
        current_user=test_user,
        db=db_session,
    )

    db_session.refresh(inv1)
    db_session.refresh(inv2)

    assert inv1.status == "partially_paid"
    assert inv1.balance_due == 50_00
    assert inv2.balance_due == 200_00  # untouched
```

- [ ] **Step 2: Run tests — verify they FAIL**

```bash
cd /Users/angelxlakra/dev/efs-salon/efs-salon-os/backend
uv run pytest tests/test_purchases.py::test_fifo_payment_fully_settles_oldest_invoice \
              tests/test_purchases.py::test_fifo_payment_spans_multiple_invoices -v 2>&1 | tail -20
```

Expected: FAIL — `inv1.status` remains `"received"` because FIFO is not implemented yet.

- [ ] **Step 3: Implement FIFO allocation**

Open `backend/app/api/purchases.py`. Find the block at line 671 (inside `record_supplier_payment`):

```python
    # Update invoice if payment is linked
    if invoice:
        invoice.paid_amount += payment_data.amount
        invoice.balance_due = invoice.total_amount - invoice.paid_amount
        invoice.update_status()
```

Replace it with:

```python
    # Update invoice(s) based on payment type
    if invoice:
        # Linked payment: update the specific invoice only
        invoice.paid_amount += payment_data.amount
        invoice.balance_due = invoice.total_amount - invoice.paid_amount
        invoice.update_status()
    else:
        # General vendor payment: apply FIFO to oldest unpaid invoices
        remaining = payment_data.amount
        unpaid_invoices = (
            db.query(PurchaseInvoice)
            .filter(
                PurchaseInvoice.supplier_id == payment_data.supplier_id,
                PurchaseInvoice.balance_due > 0,
            )
            .order_by(PurchaseInvoice.invoice_date.asc(), PurchaseInvoice.created_at.asc())
            .all()
        )
        for inv in unpaid_invoices:
            if remaining <= 0:
                break
            apply = min(remaining, inv.balance_due)
            inv.paid_amount += apply
            inv.balance_due = inv.total_amount - inv.paid_amount
            inv.update_status()
            remaining -= apply
```

- [ ] **Step 4: Run all 3 tests — verify they PASS**

```bash
cd /Users/angelxlakra/dev/efs-salon/efs-salon-os/backend
uv run pytest tests/test_purchases.py -v 2>&1 | tail -20
```

Expected: 3 PASS.

- [ ] **Step 5: Commit**

```bash
cd /Users/angelxlakra/dev/efs-salon/efs-salon-os
git add backend/app/api/purchases.py backend/tests/test_purchases.py
git commit -m "feat(purchases): FIFO allocation for general vendor payments"
```

---

## Task 2: Backend — Supplier ledger schemas + endpoint

**Files:**
- Modify: `backend/app/schemas/purchase.py` — append ledger schemas at end of file
- Modify: `backend/app/api/purchases.py` — new GET route after line 100; new imports

- [ ] **Step 1: Add ledger Pydantic schemas**

Open `backend/app/schemas/purchase.py`. At the very end of the file (after `SupplierPaymentListResponse`), append:

```python
class LedgerEntry(BaseModel):
    entry_type: str          # "invoice" or "payment"
    date: date
    description: str         # "Invoice #INV-001" or "Payment via Cash"
    reference_id: str        # invoice.id or payment.id
    debit: int               # paise — invoice total (positive)
    credit: int              # paise — payment amount (positive)
    running_balance: int     # paise — cumulative outstanding after this entry


class SupplierLedgerResponse(BaseModel):
    supplier_id: str
    supplier_name: str
    total_outstanding: int   # paise — current outstanding (sum of invoice balance_due)
    entries: list[LedgerEntry]
```

- [ ] **Step 2: Write a failing ledger test**

Append to `backend/tests/test_purchases.py`:

```python
# ── Ledger endpoint tests ─────────────────────────────────────────────────────

def test_supplier_ledger_running_balance(db_session, supplier, test_user):
    """Ledger entries sorted by date; running balance reflects debits then credits."""
    inv = make_invoice(db_session, supplier.id, total=300_00, invoice_date=date(2026, 3, 1))

    # Record a payment and manually apply it (simulating the allocation)
    payment = SupplierPayment(
        id=generate_ulid(),
        supplier_id=supplier.id,
        payment_date=date(2026, 3, 15),
        amount=100_00,
        payment_method="cash",
        recorded_by=test_user.id,
    )
    db_session.add(payment)
    inv.paid_amount = 100_00
    inv.balance_due = 200_00
    inv.status = "partially_paid"
    db_session.flush()

    from app.api.purchases import get_supplier_ledger

    result = get_supplier_ledger(
        supplier_id=supplier.id,
        current_user=test_user,
        db=db_session,
    )

    assert result.total_outstanding == 200_00
    assert len(result.entries) == 2

    invoice_entry = next(e for e in result.entries if e.entry_type == "invoice")
    assert invoice_entry.debit == 300_00
    assert invoice_entry.credit == 0
    assert invoice_entry.running_balance == 300_00

    payment_entry = next(e for e in result.entries if e.entry_type == "payment")
    assert payment_entry.credit == 100_00
    assert payment_entry.debit == 0
    assert payment_entry.running_balance == 200_00


def test_supplier_ledger_empty(db_session, supplier, test_user):
    """Ledger for a supplier with no transactions returns empty entries."""
    from app.api.purchases import get_supplier_ledger

    result = get_supplier_ledger(
        supplier_id=supplier.id,
        current_user=test_user,
        db=db_session,
    )

    assert result.total_outstanding == 0
    assert result.entries == []
```

- [ ] **Step 3: Run the failing tests**

```bash
cd /Users/angelxlakra/dev/efs-salon/efs-salon-os/backend
uv run pytest tests/test_purchases.py::test_supplier_ledger_running_balance \
              tests/test_purchases.py::test_supplier_ledger_empty -v 2>&1 | tail -20
```

Expected: FAIL — `get_supplier_ledger` does not exist.

- [ ] **Step 4: Update schema imports in purchases.py**

Open `backend/app/api/purchases.py`. Find the `from app.schemas.purchase import (...)` block near the top of the file. Add `LedgerEntry, SupplierLedgerResponse` to that import list.

- [ ] **Step 5: Implement the ledger endpoint**

In `backend/app/api/purchases.py`, after the existing `@router.get("/suppliers/{supplier_id}", ...)` endpoint (around line 100), add:

```python
@router.get("/suppliers/{supplier_id}/ledger", response_model=SupplierLedgerResponse)
def get_supplier_ledger(
    supplier_id: str,
    current_user: User = Depends(require_permission("purchases", "read")),
    db: Session = Depends(get_db),
) -> SupplierLedgerResponse:
    """
    Return a chronological statement of all invoices (debits) and payments (credits)
    for a supplier with a cumulative running balance.
    """
    supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")

    invoices = (
        db.query(PurchaseInvoice)
        .filter(PurchaseInvoice.supplier_id == supplier_id)
        .order_by(PurchaseInvoice.invoice_date.asc(), PurchaseInvoice.created_at.asc())
        .all()
    )
    payments = (
        db.query(SupplierPayment)
        .filter(SupplierPayment.supplier_id == supplier_id)
        .order_by(SupplierPayment.payment_date.asc(), SupplierPayment.created_at.asc())
        .all()
    )

    raw: list[dict] = []
    for inv in invoices:
        raw.append({
            "entry_type": "invoice",
            "date": inv.invoice_date,
            "description": f"Invoice #{inv.invoice_number}" if inv.invoice_number else "Invoice",
            "reference_id": inv.id,
            "debit": inv.total_amount,
            "credit": 0,
        })
    for pmt in payments:
        method_label = pmt.payment_method.replace("_", " ").title()
        raw.append({
            "entry_type": "payment",
            "date": pmt.payment_date,
            "description": f"Payment via {method_label}",
            "reference_id": pmt.id,
            "debit": 0,
            "credit": pmt.amount,
        })

    # Chronological: same date → invoices before payments
    raw.sort(key=lambda e: (e["date"], 0 if e["entry_type"] == "invoice" else 1))

    running = 0
    entries: list[LedgerEntry] = []
    for e in raw:
        running += e["debit"] - e["credit"]
        entries.append(LedgerEntry(
            entry_type=e["entry_type"],
            date=e["date"],
            description=e["description"],
            reference_id=e["reference_id"],
            debit=e["debit"],
            credit=e["credit"],
            running_balance=running,
        ))

    total_outstanding = sum(inv.balance_due for inv in invoices)

    return SupplierLedgerResponse(
        supplier_id=supplier.id,
        supplier_name=supplier.name,
        total_outstanding=total_outstanding,
        entries=entries,
    )
```

- [ ] **Step 6: Run all 5 tests — verify they PASS**

```bash
cd /Users/angelxlakra/dev/efs-salon/efs-salon-os/backend
uv run pytest tests/test_purchases.py -v 2>&1 | tail -20
```

Expected: 5 PASS.

- [ ] **Step 7: Commit**

```bash
cd /Users/angelxlakra/dev/efs-salon/efs-salon-os
git add backend/app/api/purchases.py backend/app/schemas/purchase.py backend/tests/test_purchases.py
git commit -m "feat(purchases): supplier ledger endpoint — chronological invoice+payment statement"
```

---

## Task 3: Frontend API — Ledger types + API call

**Files:**
- Modify: `frontend/src/lib/api/purchases.ts`

- [ ] **Step 1: Add ledger TypeScript interfaces**

Open `frontend/src/lib/api/purchases.ts`. After the `SupplierPaymentListResponse` interface (around line 209), add:

```typescript
export interface LedgerEntry {
  entry_type: 'invoice' | 'payment';
  date: string;            // ISO date "YYYY-MM-DD"
  description: string;     // "Invoice #INV-001" or "Payment via Cash"
  reference_id: string;    // invoice.id or payment.id
  debit: number;           // paise
  credit: number;          // paise
  running_balance: number; // paise — outstanding after this entry
}

export interface SupplierLedger {
  supplier_id: string;
  supplier_name: string;
  total_outstanding: number; // paise
  entries: LedgerEntry[];
}
```

- [ ] **Step 2: Add getSupplierLedger to purchaseApi**

Inside the `purchaseApi` object, after the `updateSupplier` function, add:

```typescript
  getSupplierLedger: async (supplierId: string): Promise<SupplierLedger> => {
    const response = await apiClient.get(`/purchases/suppliers/${supplierId}/ledger`);
    return response.data;
  },
```

- [ ] **Step 3: TypeScript check**

```bash
cd frontend && npx tsc --noEmit 2>&1 | grep "purchases" | head -10
```

Expected: no output.

- [ ] **Step 4: Commit**

```bash
cd /Users/angelxlakra/dev/efs-salon/efs-salon-os
git add frontend/src/lib/api/purchases.ts
git commit -m "feat(purchases): SupplierLedger types and getSupplierLedger API call"
```

---

## Task 4: Frontend — Supplier detail + ledger page

**Files:**
- Create: `frontend/src/app/(shell)/dashboard/purchases/suppliers/[id]/page.tsx`

- [ ] **Step 1: Create the page**

Create `frontend/src/app/(shell)/dashboard/purchases/suppliers/[id]/page.tsx`:

```tsx
'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { ArrowLeft, TrendingDown, TrendingUp } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { purchaseApi, Supplier, SupplierLedger } from '@/lib/api/purchases';
import { toast } from 'sonner';

function formatCurrency(paise: number): string {
  return `₹${(paise / 100).toLocaleString('en-IN', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}

function formatDate(iso: string): string {
  return new Date(iso + 'T00:00:00').toLocaleDateString('en-IN', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  });
}

export default function SupplierDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const supplierId = params.id;

  const [supplier, setSupplier] = useState<Supplier | null>(null);
  const [ledger, setLedger] = useState<SupplierLedger | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const [supplierData, ledgerData] = await Promise.all([
          purchaseApi.getSupplier(supplierId),
          purchaseApi.getSupplierLedger(supplierId),
        ]);
        setSupplier(supplierData);
        setLedger(ledgerData);
      } catch {
        toast.error('Failed to load supplier details');
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [supplierId]);

  if (loading) {
    return (
      <div className="p-4 md:p-6 space-y-4" aria-busy="true">
        <div className="flex items-center gap-3">
          <Skeleton shape="kpi" />
        </div>
        <Skeleton shape="card" />
        <Skeleton shape="card" />
      </div>
    );
  }

  if (!supplier || !ledger) return null;

  return (
    <div className="p-4 md:p-6 space-y-6">
      {/* Header */}
      <div className="flex items-start gap-3">
        <Button variant="ghost" size="icon" onClick={() => router.back()}>
          <ArrowLeft className="h-5 w-5" />
        </Button>
        <div className="flex-1 min-w-0">
          <h1 className="text-xl font-semibold text-text-primary">{supplier.name}</h1>
          {supplier.phone && (
            <p className="text-sm text-text-muted">{supplier.phone}</p>
          )}
          {supplier.contact_person && (
            <p className="text-sm text-text-muted">{supplier.contact_person}</p>
          )}
        </div>
        <Button
          onClick={() =>
            router.push(`/dashboard/purchases/payments/new?supplier_id=${supplierId}`)
          }
        >
          Record Payment
        </Button>
      </div>

      {/* Outstanding balance card */}
      <div className="rounded-xl border border-border-default bg-surface-card p-5 flex items-center justify-between">
        <div>
          <p className="text-sm text-text-muted mb-1">Outstanding Balance</p>
          <p
            className={`text-3xl font-bold ${
              ledger.total_outstanding > 0 ? 'text-warning-fg' : 'text-success-fg'
            }`}
          >
            {formatCurrency(ledger.total_outstanding)}
          </p>
        </div>
        {ledger.total_outstanding > 0 ? (
          <TrendingDown className="h-8 w-8 text-warning-fg" />
        ) : (
          <TrendingUp className="h-8 w-8 text-success-fg" />
        )}
      </div>

      {/* Ledger table */}
      <div className="rounded-xl border border-border-default bg-surface-card overflow-hidden">
        <div className="px-4 py-3 border-b border-border-subtle">
          <h2 className="text-sm font-semibold text-text-primary">Account Ledger</h2>
        </div>

        {ledger.entries.length === 0 ? (
          <div className="p-8 text-center text-sm text-text-muted">
            No transactions yet
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border-subtle bg-surface-row">
                  <th className="px-4 py-2 text-left text-xs font-medium text-text-muted whitespace-nowrap">
                    Date
                  </th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-text-muted">
                    Description
                  </th>
                  <th className="px-4 py-2 text-right text-xs font-medium text-text-muted whitespace-nowrap">
                    Invoice (Dr)
                  </th>
                  <th className="px-4 py-2 text-right text-xs font-medium text-text-muted whitespace-nowrap">
                    Payment (Cr)
                  </th>
                  <th className="px-4 py-2 text-right text-xs font-medium text-text-muted whitespace-nowrap">
                    Balance
                  </th>
                </tr>
              </thead>
              <tbody>
                {ledger.entries.map((entry, i) => (
                  <tr
                    key={entry.reference_id}
                    className={`border-b border-border-subtle last:border-0 ${
                      i % 2 !== 0 ? 'bg-surface-row' : ''
                    }`}
                  >
                    <td className="px-4 py-3 text-text-muted tabular-nums whitespace-nowrap">
                      {formatDate(entry.date)}
                    </td>
                    <td className="px-4 py-3 text-text-primary">{entry.description}</td>
                    <td className="px-4 py-3 text-right tabular-nums text-danger-fg">
                      {entry.debit > 0 ? formatCurrency(entry.debit) : '—'}
                    </td>
                    <td className="px-4 py-3 text-right tabular-nums text-success-fg">
                      {entry.credit > 0 ? formatCurrency(entry.credit) : '—'}
                    </td>
                    <td
                      className={`px-4 py-3 text-right tabular-nums font-medium ${
                        entry.running_balance > 0 ? 'text-warning-fg' : 'text-success-fg'
                      }`}
                    >
                      {formatCurrency(entry.running_balance)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: TypeScript check**

```bash
cd frontend && npx tsc --noEmit 2>&1 | grep "suppliers" | head -10
```

Expected: no output.

- [ ] **Step 3: Commit**

```bash
cd /Users/angelxlakra/dev/efs-salon/efs-salon-os
git add "frontend/src/app/(shell)/dashboard/purchases/suppliers/[id]/page.tsx"
git commit -m "feat(purchases): supplier detail + account ledger page"
```

---

## Task 5: Frontend — Payment form `supplier_id` param + supplier list links

**Files:**
- Modify: `frontend/src/app/(shell)/dashboard/purchases/payments/new/page.tsx`
- Modify: `frontend/src/app/(shell)/dashboard/purchases/suppliers/page.tsx`

### Part A — Payment form

The existing form already reads `invoice_id` from `useSearchParams`. Extend it for `supplier_id`.

- [ ] **Step 1: Read the full payments/new/page.tsx**

Read `frontend/src/app/(shell)/dashboard/purchases/payments/new/page.tsx` to confirm exact line numbers. The file is ~391 lines and the key areas are:
- Line 19: `const invoiceIdParam = searchParams.get('invoice_id');`
- Line 28: `const [supplierId, setSupplierId] = useState<string>('');`
- Line 172: `disabled={!!invoiceIdParam}` on the supplier `<Select>`
- Lines 119-122: post-submit navigation

- [ ] **Step 2: Add `supplier_id` param and pre-fill supplier**

In `RecordPaymentPageInner`, after line 19:
```tsx
const invoiceIdParam = searchParams.get('invoice_id');
```

Add:
```tsx
const supplierIdParam = searchParams.get('supplier_id');
```

Change line 28 from:
```tsx
const [supplierId, setSupplierId] = useState<string>('');
```

To:
```tsx
const [supplierId, setSupplierId] = useState<string>(supplierIdParam || '');
```

- [ ] **Step 3: Add FIFO hint when no invoice is linked**

Find the invoice info block (around line 193):
```tsx
{invoiceIdParam && invoice && (
  <div className="p-4 bg-muted rounded-lg space-y-2">
    ...
  </div>
)}
```

Immediately after that closing `)}`, add:
```tsx
{!invoiceIdParam && supplierId && (
  <div className="p-3 bg-surface-row rounded-lg border border-border-subtle">
    <p className="text-xs text-text-secondary">
      This payment will be automatically applied to the oldest outstanding invoices for this supplier.
    </p>
  </div>
)}
```

- [ ] **Step 4: Disable supplier select when `supplier_id` param is set**

Find:
```tsx
disabled={!!invoiceIdParam}
```

Replace with:
```tsx
disabled={!!invoiceIdParam || !!supplierIdParam}
```

Find the helper text:
```tsx
{invoiceIdParam && (
  <p className="text-xs text-muted-foreground">
    Supplier is pre-selected based on the invoice
  </p>
)}
```

Add sibling after it:
```tsx
{supplierIdParam && !invoiceIdParam && (
  <p className="text-xs text-text-muted">
    Supplier is pre-selected
  </p>
)}
```

- [ ] **Step 5: Redirect to supplier detail after payment**

Find (around line 119):
```tsx
      // Navigate back to invoice if it was an invoice payment
      if (invoiceId) {
        router.push(`/dashboard/purchases/invoices/${invoiceId}`);
      } else {
        router.push('/dashboard/purchases/invoices');
      }
```

Replace with:
```tsx
      if (invoiceId) {
        router.push(`/dashboard/purchases/invoices/${invoiceId}`);
      } else if (supplierIdParam) {
        router.push(`/dashboard/purchases/suppliers/${supplierIdParam}`);
      } else {
        router.push('/dashboard/purchases/invoices');
      }
```

### Part B — Supplier list links

- [ ] **Step 6: Read the suppliers list page**

Read `frontend/src/app/(shell)/dashboard/purchases/suppliers/page.tsx` fully to find where `supplier.name` is displayed (it will be in a table cell or a card). Note the exact JSX structure.

- [ ] **Step 7: Wrap supplier name with a Next.js Link**

Add the `Link` import to the top of the file if it isn't already imported:
```tsx
import Link from 'next/link';
```

Find wherever `supplier.name` (or `s.name`) is rendered in the supplier row. Wrap it:

```tsx
// Before (whatever renders the name):
<span className="font-medium">{supplier.name}</span>

// After:
<Link
  href={`/dashboard/purchases/suppliers/${supplier.id}`}
  className="font-medium text-text-primary hover:text-accent-default hover:underline"
>
  {supplier.name}
</Link>
```

Adapt to the actual JSX found in the file — this may be inside a `<td>`, a `<div>`, or a card component. The goal is: clicking the supplier name navigates to `/dashboard/purchases/suppliers/{id}`.

- [ ] **Step 8: TypeScript check**

```bash
cd frontend && npx tsc --noEmit 2>&1 | grep -E "payments/new|suppliers/page" | head -10
```

Expected: no output.

- [ ] **Step 9: Commit**

```bash
cd /Users/angelxlakra/dev/efs-salon/efs-salon-os
git add "frontend/src/app/(shell)/dashboard/purchases/payments/new/page.tsx" \
        "frontend/src/app/(shell)/dashboard/purchases/suppliers/page.tsx"
git commit -m "feat(purchases): payment form supplier-id param + supplier list links to detail page"
```

---

## Self-review checklist

**Spec coverage:**
- ✅ General vendor payment (no invoice) auto-allocates FIFO to oldest invoices — updates `paid_amount`, `balance_due`, `status` on each
- ✅ Existing invoice-linked payment behaviour is unchanged
- ✅ `GET /purchases/suppliers/{id}/ledger` returns chronological entries with running balance
- ✅ Frontend supplier detail page shows outstanding balance + full chronological ledger
- ✅ "Record Payment" button from supplier detail pre-fills `supplier_id` and redirects back on success
- ✅ FIFO hint shown when vendor-only payment (no invoice linked)
- ✅ Supplier list rows link to `/dashboard/purchases/suppliers/{id}`
- ✅ 5 backend tests cover: single-invoice settlement, multi-invoice spill, invoice-linked unchanged, ledger balance, ledger empty

**No placeholders:** All steps show exact code to write. ✅

**Type consistency:**
- `LedgerEntry.reference_id` (TypeScript) ↔ `LedgerEntry.reference_id` (Python) ✅
- `entry_type: 'invoice' | 'payment'` (TS) ↔ `entry_type: str` set to `"invoice"` or `"payment"` (Python) ✅
- `SupplierLedger.total_outstanding` (TS) ↔ `SupplierLedgerResponse.total_outstanding` (Python) ✅
- All paise (integer) on both sides ✅
