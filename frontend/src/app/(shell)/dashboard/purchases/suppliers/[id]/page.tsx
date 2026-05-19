'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { ArrowLeft, TrendingDown, TrendingUp } from 'lucide-react';
import Link from 'next/link';
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
  const [error, setError] = useState(false);

  async function load() {
    setLoading(true);
    setError(false);
    try {
      const [supplierData, ledgerData] = await Promise.all([
        purchaseApi.getSupplier(supplierId),
        purchaseApi.getSupplierLedger(supplierId),
      ]);
      setSupplier(supplierData);
      setLedger(ledgerData);
    } catch {
      setError(true);
      toast.error('Failed to load supplier details');
    } finally {
      setLoading(false);
    }
  }

  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => {
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

  if (error) {
    return (
      <div className="p-4 md:p-6 flex flex-col items-center gap-4 text-center">
        <p className="text-sm text-text-muted">Failed to load supplier details.</p>
        <div className="flex gap-3">
          <Button variant="ghost" onClick={() => router.back()}>Go Back</Button>
          <Button onClick={load}>Retry</Button>
        </div>
      </div>
    );
  }
  if (!supplier || !ledger) return null;

  return (
    <div className="p-4 md:p-6 space-y-6">
      {/* Header */}
      <div className="flex items-start gap-3">
        <Button variant="ghost" size="icon" aria-label="Back" onClick={() => router.back()}>
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
        <Button asChild>
          <Link href={`/dashboard/purchases/payments/new?supplier_id=${supplierId}`}>
            Record Payment
          </Link>
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
                    key={`${entry.entry_type}-${entry.reference_id}`}
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
