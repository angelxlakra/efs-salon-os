'use client';

import { useState, useEffect } from 'react';
import { Plus, FileText, CheckCircle, DollarSign, Eye, Users } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { purchaseApi, PurchaseInvoiceListItem } from '@/lib/api/purchases';
import { toast } from 'sonner';
import { useRouter } from 'next/navigation';

export default function PurchaseInvoicesPage() {
  const router = useRouter();
  const [invoices, setInvoices] = useState<PurchaseInvoiceListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState<string>('all');

  useEffect(() => {
    loadInvoices();
  }, [statusFilter]);

  const loadInvoices = async () => {
    try {
      setLoading(true);
      const params: any = { size: 100 };
      if (statusFilter !== 'all') {
        params.status = statusFilter;
      }
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
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Purchase Invoices</h1>
          <p className="text-muted-foreground">Track and manage supplier invoices</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => router.push('/dashboard/purchases/suppliers')}>
            <Users className="mr-2 h-4 w-4" />
            Suppliers
          </Button>
          <Button onClick={() => router.push('/dashboard/purchases/invoices/new')}>
            <Plus className="mr-2 h-4 w-4" />
            New Invoice
          </Button>
        </div>
      </div>

      {/* Status Filter */}
      <div className="flex gap-2">
        <Button
          variant={statusFilter === 'all' ? 'default' : 'outline'}
          size="sm"
          onClick={() => setStatusFilter('all')}
        >
          All
        </Button>
        <Button
          variant={statusFilter === 'draft' ? 'default' : 'outline'}
          size="sm"
          onClick={() => setStatusFilter('draft')}
        >
          Draft
        </Button>
        <Button
          variant={statusFilter === 'received' ? 'default' : 'outline'}
          size="sm"
          onClick={() => setStatusFilter('received')}
        >
          Received
        </Button>
        <Button
          variant={statusFilter === 'partially_paid' ? 'default' : 'outline'}
          size="sm"
          onClick={() => setStatusFilter('partially_paid')}
        >
          Partially Paid
        </Button>
        <Button
          variant={statusFilter === 'paid' ? 'default' : 'outline'}
          size="sm"
          onClick={() => setStatusFilter('paid')}
        >
          Paid
        </Button>
      </div>

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
              <CardContent className="p-6">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-start gap-4">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-2">
                          <h3 className="text-lg font-semibold">{invoice.invoice_number}</h3>
                          {getStatusBadge(invoice.status)}
                        </div>
                        <p className="text-sm text-muted-foreground mb-1">
                          <span className="font-medium">{invoice.supplier_name}</span>
                        </p>
                        <p className="text-sm text-muted-foreground">
                          Invoice Date: {formatDate(invoice.invoice_date)}
                          {invoice.due_date && ` • Due: ${formatDate(invoice.due_date)}`}
                        </p>
                      </div>

                      <div className="text-right min-w-[200px]">
                        <div className="text-2xl font-bold">
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

                    <div className="flex items-center gap-2 mt-4">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => router.push(`/dashboard/purchases/invoices/${invoice.id}`)}
                      >
                        <Eye className="mr-2 h-4 w-4" />
                        View Details
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
                          <CheckCircle className="mr-2 h-4 w-4" />
                          Mark Received
                        </Button>
                      )}

                      {(invoice.status === 'received' || invoice.status === 'partially_paid') && invoice.balance_due > 0 && (
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => router.push(`/dashboard/purchases/payments/new?invoice_id=${invoice.id}`)}
                        >
                          <DollarSign className="mr-2 h-4 w-4" />
                          Record Payment
                        </Button>
                      )}
                    </div>
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
