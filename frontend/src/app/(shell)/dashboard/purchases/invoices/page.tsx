'use client';

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

export default function PurchaseInvoicesPage() {
  const router = useRouter();
  const [invoices, setInvoices] = useState<PurchaseInvoiceListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [searchDebounced, setSearchDebounced] = useState('');
  const [suppliers, setSuppliers] = useState<SupplierListItem[]>([]);

  useEffect(() => {
    const timer = setTimeout(() => setSearchDebounced(searchQuery), 300);
    return () => clearTimeout(timer);
  }, [searchQuery]);

  useEffect(() => {
    loadInvoices();
  }, [statusFilter, searchDebounced, startDate, endDate]);

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
      setSuppliers([]);
      setInvoices([]);
    } finally {
      setLoading(false);
    }
  };

  const formatCurrency = (amount: number) => {
    return `₹${(amount / 100).toLocaleString('en-IN', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    })}`;
  };

  const formatDate = (dateString: string) => {
    // Append local-time sentinel only when the string is a bare date (no T separator).
    // Prevents double-appending if the API returns a full datetime string.
    const normalised = dateString.includes('T') ? dateString : dateString + 'T00:00:00';
    return new Date(normalised).toLocaleDateString('en-IN', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
    });
  };

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

  const filteredInvoices = invoices;
  const outstandingSuppliers = suppliers.filter((s) => s.total_outstanding > 0);

  return (
    <div className="p-4 md:p-6 pt-6 md:pt-8 space-y-4">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold">Purchase Invoices</h1>
          <p className="text-text-secondary text-sm">Track and manage supplier invoices</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => router.push('/dashboard/purchases/suppliers')}>
            <Users className="mr-1.5 h-4 w-4" />
            Suppliers
          </Button>
          <Button onClick={() => router.push('/dashboard/purchases/invoices/new')}>
            <Plus className="mr-1.5 h-4 w-4" />
            New Invoice
          </Button>
        </div>
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
            // NOTE: derived from the current paginated invoice list (max size: 50,
            // filtered by active status/search/date). May be absent if the supplier's
            // oldest unpaid invoice falls outside the current page.
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
                  aria-label={`Pay ${supplier.name}`}
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
      <div className="flex gap-2 overflow-x-auto pb-1 flex-nowrap" aria-label="Filter by status">
        <Button
          variant={statusFilter === 'all' ? 'default' : 'outline'}
          size="sm"
          className="shrink-0"
          onClick={() => setStatusFilter('all')}
        >
          All
        </Button>
        <Button
          variant={statusFilter === 'draft' ? 'default' : 'outline'}
          size="sm"
          className="shrink-0"
          onClick={() => setStatusFilter('draft')}
        >
          Draft
        </Button>
        <Button
          variant={statusFilter === 'received' ? 'default' : 'outline'}
          size="sm"
          className="shrink-0"
          onClick={() => setStatusFilter('received')}
        >
          Received
        </Button>
        <Button
          variant={statusFilter === 'partially_paid' ? 'default' : 'outline'}
          size="sm"
          className="shrink-0"
          onClick={() => setStatusFilter('partially_paid')}
        >
          Partial
        </Button>
        <Button
          variant={statusFilter === 'paid' ? 'default' : 'outline'}
          size="sm"
          className="shrink-0"
          onClick={() => setStatusFilter('paid')}
        >
          Paid
        </Button>
      </div>

      {/* Search and Date Filters */}
      <div className="flex flex-col sm:flex-row gap-2">
        <div className="relative flex-1">
          <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-text-muted" />
          <Input
            placeholder="Search by invoice # or supplier..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-8"
          />
        </div>
        <div className="flex gap-2">
          <Input
            type="date"
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
            className="w-36"
            placeholder="From"
          />
          <Input
            type="date"
            value={endDate}
            onChange={(e) => setEndDate(e.target.value)}
            className="w-36"
            placeholder="To"
          />
        </div>
      </div>

      {invoices.length > 0 && (
        <p className="text-sm text-text-secondary">
          Showing {invoices.length} invoice{invoices.length !== 1 ? 's' : ''}
          {searchDebounced && ` matching "${searchDebounced}"`}
        </p>
      )}

      {/* Invoices List */}
      {loading ? (
        <div aria-busy="true" className="space-y-3">
          <Skeleton shape="row" />
          <Skeleton shape="row" />
          <Skeleton shape="row" />
          <Skeleton shape="row" />
          <Skeleton shape="row" />
        </div>
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
      ) : (
        <>
          {/* Mobile Cards */}
          <div className="md:hidden space-y-2">
            {filteredInvoices.map((invoice) => (
              <div key={invoice.id} className="bg-surface-card border border-border-subtle rounded-lg p-4 space-y-2">
                {/* Row 1: invoice ref + date */}
                <div className="flex items-center justify-between gap-2">
                  <span className="font-mono text-xs text-text-muted">{invoice.invoice_number}</span>
                  <span className="text-xs text-text-secondary">{formatDate(invoice.invoice_date)}</span>
                </div>
                {/* Row 2: supplier name + status chip */}
                <div className="flex items-center justify-between gap-2">
                  <span className="text-text-primary font-semibold text-sm">{invoice.supplier_name}</span>
                  {getStatusChip(invoice.status)}
                </div>
                {/* Row 3: total amount + view button */}
                <div className="flex items-center justify-between gap-2 pt-1 border-t border-border-subtle">
                  <span className="text-accent font-bold">{formatCurrency(invoice.total_amount)}</span>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => router.push(`/dashboard/purchases/invoices/${invoice.id}`)}
                  >
                    <Eye className="mr-1 h-4 w-4" />
                    View
                  </Button>
                </div>
              </div>
            ))}
          </div>

          {/* Desktop Cards */}
          <div className="hidden md:block space-y-3">
            {filteredInvoices.map((invoice) => (
              <div key={invoice.id} className="bg-surface-card border border-border-subtle rounded-lg p-6 hover:bg-surface-row transition-colors">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-start gap-4">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-2">
                          <h3 className="text-lg font-semibold text-text-primary">{invoice.invoice_number}</h3>
                          {getStatusChip(invoice.status)}
                        </div>
                        <p className="text-sm text-text-primary font-medium mb-1">{invoice.supplier_name}</p>
                        <p className="text-sm text-text-secondary">
                          Invoice Date: {formatDate(invoice.invoice_date)}
                          {invoice.due_date && ` • Due: ${formatDate(invoice.due_date)}`}
                        </p>
                      </div>

                      <div className="text-right min-w-[200px]">
                        <div className="text-2xl font-bold text-accent">
                          {formatCurrency(invoice.total_amount)}
                        </div>
                        <div className="text-sm text-text-secondary">
                          Paid: {formatCurrency(invoice.paid_amount)}
                        </div>
                        {invoice.balance_due > 0 && (
                          <div className="text-sm font-medium text-warning-fg">
                            Due: {formatCurrency(invoice.balance_due)}
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                </div>

                <div className="flex flex-wrap items-center gap-2 mt-4">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => router.push(`/dashboard/purchases/invoices/${invoice.id}`)}
                  >
                    <Eye className="mr-1.5 h-4 w-4" />
                    View
                  </Button>

                  {invoice.status === 'draft' && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={async () => {
                        try {
                          await purchaseApi.markGoodsReceived(invoice.id);
                          toast.success('Goods marked as received');
                          loadInvoices();
                        } catch (error) {
                          console.error('Error marking goods received:', error);
                          toast.error('Failed to mark goods as received');
                        }
                      }}
                    >
                      <CheckCircle className="mr-1.5 h-4 w-4" />
                      Received
                    </Button>
                  )}

                  {(invoice.status === 'received' || invoice.status === 'partially_paid') && invoice.balance_due > 0 && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => router.push(`/dashboard/purchases/payments/new?invoice_id=${invoice.id}`)}
                    >
                      <DollarSign className="mr-1.5 h-4 w-4" />
                      Pay
                    </Button>
                  )}
                </div>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
