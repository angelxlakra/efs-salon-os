'use client';

import { useState, useEffect, useCallback } from 'react';
import { Plus, FileText, CheckCircle, DollarSign, Eye, Users, Search, Calendar } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { purchaseApi, PurchaseInvoiceListItem } from '@/lib/api/purchases';
import { toast } from 'sonner';
import { useRouter } from 'next/navigation';

export default function PurchaseInvoicesPage() {
  const router = useRouter();
  const [invoices, setInvoices] = useState<PurchaseInvoiceListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [searchDebounced, setSearchDebounced] = useState('');

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
      const params: any = { size: 50 };
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

  const formatCurrency = (amount: number) => {
    return `₹${(amount / 100).toFixed(2)}`;
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-IN', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
    });
  };

  const getStatusBadge = (status: string) => {
    const variants: Record<string, 'default' | 'secondary' | 'destructive' | 'outline'> = {
      draft: 'secondary',
      received: 'default',
      partially_paid: 'secondary',
      paid: 'default',
    };

    return (
      <Badge variant={variants[status] || 'secondary'}>
        {status.replace('_', ' ').toUpperCase()}
      </Badge>
    );
  };

  const filteredInvoices = invoices;

  return (
    <div className="space-y-4 md:space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl md:text-3xl font-bold">Purchase Invoices</h1>
          <p className="text-muted-foreground text-sm">Track and manage supplier invoices</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" className="sm:size-auto" onClick={() => router.push('/dashboard/purchases/suppliers')}>
            <Users className="mr-1.5 h-4 w-4" />
            <span className="hidden sm:inline">Suppliers</span>
            <span className="sm:hidden">Suppliers</span>
          </Button>
          <Button size="sm" className="sm:size-auto" onClick={() => router.push('/dashboard/purchases/invoices/new')}>
            <Plus className="mr-1.5 h-4 w-4" />
            <span className="hidden sm:inline">New Invoice</span>
            <span className="sm:hidden">New</span>
          </Button>
        </div>
      </div>

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
          <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
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
        <p className="text-sm text-muted-foreground">
          Showing {invoices.length} invoice{invoices.length !== 1 ? 's' : ''}
          {searchDebounced && ` matching "${searchDebounced}"`}
        </p>
      )}

      {/* Invoices List */}
      {loading ? (
        <div className="text-center py-12">Loading invoices...</div>
      ) : filteredInvoices.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center">
            <FileText className="mx-auto h-12 w-12 text-muted-foreground mb-4" />
            <p className="text-muted-foreground">
              No purchase invoices found
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {filteredInvoices.map((invoice) => (
            <Card key={invoice.id} className="hover:shadow-md transition-shadow">
              <CardContent className="p-4 md:p-6">
                <div className="space-y-3">
                  <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-2">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1 flex-wrap">
                        <h3 className="text-base sm:text-lg font-semibold">{invoice.invoice_number}</h3>
                        {getStatusBadge(invoice.status)}
                      </div>
                      <p className="text-sm text-muted-foreground">
                        <span className="font-medium">{invoice.supplier_name}</span>
                      </p>
                      <p className="text-xs sm:text-sm text-muted-foreground">
                        {formatDate(invoice.invoice_date)}
                        {invoice.due_date && ` • Due: ${formatDate(invoice.due_date)}`}
                      </p>
                    </div>

                    <div className="text-left sm:text-right shrink-0">
                      <div className="text-xl sm:text-2xl font-bold">
                        {formatCurrency(invoice.total_amount)}
                      </div>
                      <div className="text-sm text-muted-foreground">
                        Paid: {formatCurrency(invoice.paid_amount)}
                      </div>
                      {invoice.balance_due > 0 && (
                        <div className="text-sm font-medium text-orange-600">
                          Due: {formatCurrency(invoice.balance_due)}
                        </div>
                      )}
                    </div>
                  </div>

                  <div className="flex flex-wrap items-center gap-2">
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
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
