'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Search, Filter, Download, Eye, Printer, RotateCcw, XCircle, Loader2, FileText, FileSpreadsheet, AlertTriangle } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { apiClient } from '@/lib/api-client';
import { toast } from 'sonner';
import { BillDetailsDialog } from '@/components/bills/bill-details-dialog';
import { titleCase } from '@/lib/utils';
import { useAuthStore } from '@/stores/auth-store';

interface Bill {
  id: string;
  invoice_number: string | null;
  customer_name: string | null;
  customer_phone: string | null;
  rounded_total: number; // in paise
  total_paid: number; // in paise
  write_off_amount: number; // in paise
  status: string;
  created_at: string;
  posted_at: string | null;
}

interface BillsResponse {
  bills: Bill[];
  pagination: {
    page: number;
    limit: number;
    total: number;
    pages: number;
  };
}

export default function BillsPage() {
  const { user } = useAuthStore();
  const isOwner = user?.role === 'owner';
  const [bills, setBills] = useState<Bill[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [total, setTotal] = useState(0);
  const router = useRouter();
  const [selectedBillId, setSelectedBillId] = useState<string | null>(null);
  const [showBillDetails, setShowBillDetails] = useState(false);
  const [searchDebounced, setSearchDebounced] = useState('');
  const [fromDate, setFromDate] = useState('');
  const [toDate, setToDate] = useState('');

  useEffect(() => {
    const timer = setTimeout(() => {
      setSearchDebounced(searchQuery);
      setPage(1); // reset to page 1 on new search
    }, 300);
    return () => clearTimeout(timer);
  }, [searchQuery]);

  useEffect(() => {
    fetchBills();
  }, [page, statusFilter, searchDebounced, fromDate, toDate]);

  const fetchBills = async () => {
    try {
      setIsLoading(true);
      const params: Record<string, string | number | boolean> = {
        page,
        limit: 20,
      };

      if (statusFilter === 'pending') {
        params.pending_only = true;
      } else if (statusFilter !== 'all') {
        params.status = statusFilter;
      }

      if (searchDebounced) {
        params.search = searchDebounced;
      }

      if (fromDate) params.from_date = fromDate;
      if (toDate) params.to_date = toDate;

      const { data } = await apiClient.get<BillsResponse>('/pos/bills', { params });

      setBills(data.bills || []);
      setTotal(data.pagination?.total || 0);
      setTotalPages(data.pagination?.pages || 1);
    } catch (error: unknown) {
      console.error('Error fetching bills:', error);
      const msg = error instanceof Error ? error.message : 'Failed to load bills';
      toast.error(msg);
      setBills([]);
      setTotal(0);
      setTotalPages(1);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSearch = () => {
    setPage(1);
    setSearchDebounced(searchQuery);
  };

  const formatPrice = (paise: number) => {
    return `₹${(paise / 100).toLocaleString('en-IN', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    })}`;
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString('en-IN', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const getStatusChip = (status: string): React.ReactNode => {
    const map: Record<string, { bg: string; text: string; label: string }> = {
      posted:   { bg: 'bg-green-950/40',  text: 'text-green-400',  label: 'Paid' },
      draft:    { bg: 'bg-amber-950/40',  text: 'text-amber-400',  label: 'Draft' },
      void:     { bg: 'bg-zinc-900/60',   text: 'text-text-muted', label: 'Voided' },
      refunded: { bg: 'bg-red-950/40',    text: 'text-red-400',    label: 'Refunded' },
    };
    const cfg = map[status] ?? { bg: 'bg-zinc-900/60', text: 'text-text-muted', label: status };
    return (
      <span className={`text-xs px-2 py-0.5 rounded-full ${cfg.bg} ${cfg.text}`}>
        {cfg.label}
      </span>
    );
  };

  const hasPendingBalance = (bill: Bill) =>
    bill.status === 'posted' &&
    bill.total_paid + (bill.write_off_amount ?? 0) < bill.rounded_total;

  const handleViewBill = (billId: string) => {
    setSelectedBillId(billId);
    setShowBillDetails(true);
  };

  const handleReprintReceipt = async (billId: string) => {
    try {
      const response = await apiClient.get(`/pos/bills/${billId}/receipt`, {
        responseType: 'blob',
      });

      const blob = new Blob([response.data], { type: 'application/pdf' });
      const url = window.URL.createObjectURL(blob);
      window.open(url, '_blank');

      toast.success('Receipt opened in new tab');
    } catch (error: unknown) {
      console.error('Error printing receipt:', error);
      const msg = error instanceof Error ? error.message : 'Failed to print receipt';
      toast.error(msg);
    }
  };

  const handleVoidBill = async (billId: string) => {
    const reason = prompt('Please enter the reason for voiding this bill:');

    if (!confirm('Are you sure you want to void this bill? This action cannot be undone.')) {
      return;
    }

    try {
      await apiClient.post(`/pos/bills/${billId}/void`, {
        reason: reason?.trim() || null,
      });
      toast.success('Bill voided successfully');
      fetchBills(); // Refresh the list
      setShowBillDetails(false);
    } catch (error: unknown) {
      console.error('Error voiding bill:', error);
      const msg = error instanceof Error ? error.message : 'Failed to void bill';
      toast.error(msg);
    }
  };

  const handleRefund = async (billId: string) => {
    const reason = prompt('Please enter the reason for refund:');
    if (!reason) {
      toast.info('Refund cancelled');
      return;
    }

    if (!confirm('Are you sure you want to refund this bill? This will reverse the payment.')) {
      return;
    }

    try {
      await apiClient.post(`/pos/bills/${billId}/refund`, {
        reason: reason.trim(),
      });
      toast.success('Bill refunded successfully');
      fetchBills(); // Refresh the list
    } catch (error: unknown) {
      console.error('Error refunding bill:', error);
      const msg = error instanceof Error ? error.message : 'Failed to refund bill';
      toast.error(msg);
    }
  };

  const handleExport = async (format: 'csv' | 'pdf') => {
    try {
      const params: Record<string, string | number> = {};

      if (statusFilter !== 'all') {
        params.status_filter = statusFilter;
      }

      if (searchQuery.trim()) {
        // Note: Export doesn't support invoice_number filter,
        // so we'll export all and user can filter in Excel
      }

      params.format = format;

      const response = await apiClient.get('/pos/bills/export', {
        params,
        responseType: 'blob',
      });

      // Create download link
      const blob = new Blob([response.data], {
        type: format === 'csv' ? 'text/csv' : 'application/pdf',
      });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `bills_export_${new Date().toISOString().split('T')[0]}.${format}`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);

      toast.success(`Bills exported as ${format.toUpperCase()}`);
    } catch (error: unknown) {
      console.error('Error exporting bills:', error);
      const msg = error instanceof Error ? error.message : 'Failed to export bills';
      toast.error(msg);
    }
  };

  if (isLoading && bills.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="h-8 w-8 animate-spin text-text-muted mx-auto mb-2" />
          <p className="text-sm text-text-secondary">Loading bills...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-4 md:p-6 pt-6 md:pt-8 space-y-4">
      {/* Header */}
      <div>
        <h1 className="text-xl font-semibold">Bills & Transactions</h1>
        <p className="text-sm text-text-secondary mt-1">
          View and manage all sales transactions
        </p>
      </div>

      {/* Quick Filters */}
      <div className="flex gap-2 overflow-x-auto pb-1 flex-nowrap">
        {[
          { label: 'All', value: 'all' },
          { label: 'Pending Payment', value: 'pending' },
          { label: 'Draft', value: 'draft' },
          { label: 'Paid', value: 'posted' },
          { label: 'Refunds', value: 'refunded' },
          { label: 'Voided', value: 'void' },
        ].map(({ label, value }) => (
          <Button
            key={value}
            variant={statusFilter === value ? 'default' : 'outline'}
            size="sm"
            className={`shrink-0${value === 'pending' && statusFilter !== 'pending' ? ' border-red-300 text-red-600 hover:bg-red-50' : ''}`}
            onClick={() => { setStatusFilter(value); setPage(1); }}
          >
            {label}
          </Button>
        ))}
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="p-4">
          <div className="flex flex-col sm:flex-row gap-3">
            {/* Search */}
            <div className="flex-1 flex gap-2">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-text-muted" />
                <Input
                  placeholder="Search by invoice #, customer name, or phone..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                  className="pl-10"
                />
              </div>
              <Button onClick={handleSearch} size="sm">
                Search
              </Button>
            </div>

            {/* Date Range */}
            <Input
              type="date"
              value={fromDate}
              onChange={(e) => { setFromDate(e.target.value); setPage(1); }}
              className="w-36"
              title="From date"
            />
            <Input
              type="date"
              value={toDate}
              onChange={(e) => { setToDate(e.target.value); setPage(1); }}
              className="w-36"
              title="To date"
            />

            {/* Export */}
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="outline" size="sm" className="sm:w-auto">
                  <Download className="h-4 w-4 mr-2" />
                  Export
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem onClick={() => handleExport('csv')}>
                  <FileSpreadsheet className="h-4 w-4 mr-2" />
                  Export as CSV
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => handleExport('pdf')}>
                  <FileText className="h-4 w-4 mr-2" />
                  Export as PDF
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </CardContent>
      </Card>

      {/* Bills Table */}
      <Card>
        <CardHeader className="p-4 pb-3">
          <CardTitle className="text-lg">
            {total} Transaction{total !== 1 ? 's' : ''}
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {/* Mobile cards */}
          <div className="md:hidden space-y-2 p-3">
            {bills.length === 0 ? (
              <div className="p-8 text-center text-text-secondary">
                No bills found
              </div>
            ) : (
              bills.map((bill) => (
                <div
                  key={bill.id}
                  className="rounded-xl bg-surface-card border border-border-subtle p-4 space-y-2"
                >
                  {/* Row 1: invoice number + time */}
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-xs text-text-muted">
                      {bill.invoice_number ?? '—'}
                    </span>
                    <span className="text-xs text-text-muted">
                      {new Date(bill.posted_at ?? bill.created_at).toLocaleTimeString('en-IN', {
                        hour: '2-digit',
                        minute: '2-digit',
                      })}
                    </span>
                  </div>
                  {/* Row 2: customer name + total */}
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-text-primary text-sm truncate max-w-[60%]">
                      {bill.customer_name ?? 'Walk-in'}
                    </span>
                    <span className="font-semibold text-accent text-sm">
                      {formatPrice(bill.rounded_total)}
                    </span>
                  </div>
                  {/* Pending balance indicator */}
                  {hasPendingBalance(bill) && (
                    <div className="flex items-center gap-1.5 text-xs font-semibold text-red-400">
                      <AlertTriangle className="h-3.5 w-3.5" />
                      Pending: {formatPrice(bill.rounded_total - bill.total_paid - (bill.write_off_amount ?? 0))}
                    </div>
                  )}
                  {/* Row 3: status badge + View button */}
                  <div className="flex items-center justify-between gap-2">
                    {getStatusChip(bill.status)}
                    <button
                      type="button"
                      className="text-xs text-text-secondary hover:text-text-primary transition-colors"
                      onClick={() => handleViewBill(bill.id)}
                    >
                      View
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>

          {/* Desktop table */}
          <div className="hidden md:block overflow-x-auto">
            <table className="w-full">
              <thead className="bg-surface-page border-b border-border-subtle">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-text-secondary uppercase">
                    Invoice #
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-text-secondary uppercase">
                    Customer
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-text-secondary uppercase">
                    Date & Time
                  </th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-text-secondary uppercase">
                    Amount
                  </th>
                  <th className="px-4 py-3 text-center text-xs font-medium text-text-secondary uppercase">
                    Status
                  </th>
                  <th className="px-4 py-3 text-center text-xs font-medium text-text-secondary uppercase">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border-subtle">
                {bills.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="px-4 py-8 text-center text-text-secondary">
                      No bills found
                    </td>
                  </tr>
                ) : (
                  bills.map((bill) => (
                    <tr key={bill.id} className={hasPendingBalance(bill) ? 'bg-red-950/20 border-l-4 border-red-500' : 'hover:bg-surface-row'}>
                      <td className="px-4 py-3 text-sm font-medium text-text-primary">
                        {bill.invoice_number}
                      </td>
                      <td className="px-4 py-3 text-sm">
                        <p className="font-medium text-text-primary">{titleCase(bill.customer_name) || 'Walk-in'}</p>
                        {hasPendingBalance(bill) && (
                          <p className="text-xs font-semibold text-red-400 flex items-center gap-1 mt-0.5">
                            <AlertTriangle className="h-3 w-3" />
                            Pending {formatPrice(bill.rounded_total - bill.total_paid - (bill.write_off_amount ?? 0))}
                          </p>
                        )}
                      </td>
                      <td className="px-4 py-3 text-sm text-text-secondary">
                        {formatDate(bill.created_at)}
                      </td>
                      <td className="px-4 py-3 text-sm font-semibold text-right text-text-primary">
                        {formatPrice(bill.rounded_total)}
                      </td>
                      <td className="px-4 py-3 text-center">
                        {getStatusChip(bill.status)}
                      </td>
                      <td className="px-4 py-3 text-center">
                        <DropdownMenu>
                          <DropdownMenuTrigger asChild>
                            <Button variant="ghost" size="sm">
                              Actions
                            </Button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="end">
                            <DropdownMenuItem onClick={() => handleViewBill(bill.id)}>
                              <Eye className="h-4 w-4 mr-2" />
                              View Details
                            </DropdownMenuItem>
                            <DropdownMenuItem onClick={() => handleReprintReceipt(bill.id)}>
                              <Printer className="h-4 w-4 mr-2" />
                              Reprint Receipt
                            </DropdownMenuItem>
                            {(bill.status === 'draft' || (bill.status === 'posted' && isOwner)) && (
                              <DropdownMenuItem
                                onClick={() => handleVoidBill(bill.id)}
                                className="text-destructive"
                              >
                                <XCircle className="h-4 w-4 mr-2" />
                                Void Bill
                              </DropdownMenuItem>
                            )}
                            {bill.status === 'posted' && (
                              <DropdownMenuItem onClick={() => handleRefund(bill.id)}>
                                <RotateCcw className="h-4 w-4 mr-2" />
                                Process Refund
                              </DropdownMenuItem>
                            )}
                          </DropdownMenuContent>
                        </DropdownMenu>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between px-4 py-3 border-t border-border-subtle">
              <div className="text-sm text-text-secondary">
                Page {page} of {totalPages}
              </div>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setPage(page - 1)}
                  disabled={page === 1}
                >
                  Previous
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setPage(page + 1)}
                  disabled={page === totalPages}
                >
                  Next
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      <BillDetailsDialog
        billId={selectedBillId}
        open={showBillDetails}
        onOpenChange={setShowBillDetails}
        onVoid={handleVoidBill}
        onRefund={handleRefund}
        onReprint={handleReprintReceipt}
      />
    </div>
  );
}
