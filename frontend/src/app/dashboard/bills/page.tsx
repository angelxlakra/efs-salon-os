'use client';

import { useState, useEffect } from 'react';
import { Search, Filter, Download, Eye, Printer, RotateCcw, XCircle, Loader2, FileText, FileSpreadsheet } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { apiClient } from '@/lib/api-client';
import { toast } from 'sonner';
import { BillDetailsDialog } from '@/components/bills/bill-details-dialog';

interface Bill {
  id: string;
  invoice_number: string | null;
  customer_name: string | null;
  rounded_total: number; // in paise
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
  const [bills, setBills] = useState<Bill[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [total, setTotal] = useState(0);
  const [selectedBillId, setSelectedBillId] = useState<string | null>(null);
  const [showBillDetails, setShowBillDetails] = useState(false);

  useEffect(() => {
    fetchBills();
  }, [page, statusFilter]);

  const fetchBills = async () => {
    try {
      setIsLoading(true);
      const params: any = {
        page,
        limit: 20,
      };

      if (statusFilter !== 'all') {
        params.status = statusFilter;
      }

      if (searchQuery.trim()) {
        params.invoice_number = searchQuery.trim();
      }

      const { data } = await apiClient.get<BillsResponse>('/pos/bills', { params });

      setBills(data.bills || []);
      setTotal(data.pagination?.total || 0);
      setTotalPages(data.pagination?.pages || 1);
    } catch (error: any) {
      console.error('Error fetching bills:', error);
      toast.error(error.response?.data?.detail || 'Failed to load bills');
      setBills([]);
      setTotal(0);
      setTotalPages(1);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSearch = () => {
    setPage(1);
    fetchBills();
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

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'draft':
        return <Badge variant="secondary">Draft</Badge>;
      case 'posted':
        return <Badge className="bg-green-500">Paid</Badge>;
      case 'void':
        return <Badge variant="outline" className="text-gray-500">Voided</Badge>;
      case 'refunded':
        return <Badge variant="destructive">Refunded</Badge>;
      default:
        return <Badge variant="outline">{status}</Badge>;
    }
  };

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
    } catch (error: any) {
      console.error('Error printing receipt:', error);
      toast.error('Failed to print receipt');
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
      setShowBillDetails(false); // Close dialog if open
    } catch (error: any) {
      console.error('Error voiding bill:', error);
      toast.error(error.response?.data?.detail || 'Failed to void bill');
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
    } catch (error: any) {
      console.error('Error refunding bill:', error);
      toast.error(error.response?.data?.detail || 'Failed to refund bill');
    }
  };

  const handleExport = async (format: 'csv' | 'pdf') => {
    try {
      const params: any = {};

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
    } catch (error: any) {
      console.error('Error exporting bills:', error);
      toast.error(error.response?.data?.detail || 'Failed to export bills');
    }
  };

  if (isLoading && bills.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="h-8 w-8 animate-spin text-gray-400 mx-auto mb-2" />
          <p className="text-sm text-gray-500">Loading bills...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div>
        <h1 className="text-2xl md:text-3xl font-bold">Bills & Transactions</h1>
        <p className="text-sm text-muted-foreground mt-1">
          View and manage all sales transactions
        </p>
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="p-4">
          <div className="flex flex-col sm:flex-row gap-3">
            {/* Search */}
            <div className="flex-1 flex gap-2">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
                <Input
                  placeholder="Search by invoice number..."
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

            {/* Status Filter */}
            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger className="w-full sm:w-40">
                <SelectValue placeholder="Status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Status</SelectItem>
                <SelectItem value="draft">Draft</SelectItem>
                <SelectItem value="posted">Paid</SelectItem>
                <SelectItem value="void">Voided</SelectItem>
                <SelectItem value="refunded">Refunded</SelectItem>
              </SelectContent>
            </Select>

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
          {/* Mobile View */}
          <div className="block sm:hidden">
            {bills.length === 0 ? (
              <div className="p-8 text-center text-gray-500">
                No bills found
              </div>
            ) : (
              <div className="divide-y">
                {bills.map((bill) => (
                  <div key={bill.id} className="p-4 space-y-2">
                    <div className="flex justify-between items-start">
                      <div>
                        <p className="font-semibold">{bill.invoice_number}</p>
                        <p className="text-sm text-muted-foreground">
                          {bill.customer_name || 'Walk-in'}
                        </p>
                      </div>
                      {getStatusBadge(bill.status)}
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-sm text-muted-foreground">
                        {formatDate(bill.created_at)}
                      </span>
                      <span className="font-semibold text-lg">
                        {formatPrice(bill.rounded_total)}
                      </span>
                    </div>
                    <div className="flex gap-2">
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => handleViewBill(bill.id)}
                        className="flex-1"
                      >
                        <Eye className="h-3.5 w-3.5 mr-1.5" />
                        View
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => handleReprintReceipt(bill.id)}
                        className="flex-1"
                      >
                        <Printer className="h-3.5 w-3.5 mr-1.5" />
                        Print
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Desktop View */}
          <div className="hidden sm:block overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 border-b">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Invoice #
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Customer
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Date & Time
                  </th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">
                    Amount
                  </th>
                  <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">
                    Status
                  </th>
                  <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {bills.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="px-4 py-8 text-center text-gray-500">
                      No bills found
                    </td>
                  </tr>
                ) : (
                  bills.map((bill) => (
                    <tr key={bill.id} className="hover:bg-gray-50">
                      <td className="px-4 py-3 text-sm font-medium">
                        {bill.invoice_number}
                      </td>
                      <td className="px-4 py-3 text-sm">
                        <p className="font-medium">{bill.customer_name || 'Walk-in'}</p>
                      </td>
                      <td className="px-4 py-3 text-sm text-muted-foreground">
                        {formatDate(bill.created_at)}
                      </td>
                      <td className="px-4 py-3 text-sm font-semibold text-right">
                        {formatPrice(bill.rounded_total)}
                      </td>
                      <td className="px-4 py-3 text-center">
                        {getStatusBadge(bill.status)}
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
                            {bill.status === 'draft' && (
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
            <div className="flex items-center justify-between px-4 py-3 border-t">
              <div className="text-sm text-muted-foreground">
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

      {/* Bill Details Dialog */}
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
