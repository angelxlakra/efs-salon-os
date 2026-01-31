'use client';

import { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { ArrowLeft, DollarSign, CheckCircle, Package, FileText, Calendar, User, Phone, Mail, MapPin, CreditCard } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { purchaseApi, PurchaseInvoice, SupplierPayment } from '@/lib/api/purchases';
import { toast } from 'sonner';

export default function InvoiceDetailPage() {
  const params = useParams();
  const router = useRouter();
  const invoiceId = params.id as string;

  const [invoice, setInvoice] = useState<PurchaseInvoice | null>(null);
  const [payments, setPayments] = useState<SupplierPayment[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (invoiceId) {
      loadInvoiceDetails();
      loadPayments();
    }
  }, [invoiceId]);

  const loadInvoiceDetails = async () => {
    try {
      setLoading(true);
      const data = await purchaseApi.getPurchaseInvoice(invoiceId);
      setInvoice(data);
    } catch (error) {
      console.error('Error loading invoice:', error);
      toast.error('Failed to load invoice details');
    } finally {
      setLoading(false);
    }
  };

  const loadPayments = async () => {
    try {
      const response = await purchaseApi.listPayments({ invoice_id: invoiceId });
      setPayments(response.items || []);
    } catch (error) {
      console.error('Error loading payments:', error);
    }
  };

  const handleMarkReceived = async () => {
    if (!invoice) return;

    try {
      await purchaseApi.markGoodsReceived(invoice.id);
      toast.success('Goods marked as received');
      loadInvoiceDetails();
    } catch (error) {
      console.error('Error marking goods received:', error);
      toast.error('Failed to mark goods as received');
    }
  };

  const formatCurrency = (amount: number) => {
    return `₹${(amount / 100).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-IN', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
    });
  };

  const formatDateTime = (dateString: string) => {
    return new Date(dateString).toLocaleString('en-IN', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const getStatusBadge = (status: string) => {
    const config: Record<string, { label: string; variant: 'default' | 'secondary' | 'destructive' | 'outline' }> = {
      draft: { label: 'DRAFT', variant: 'secondary' },
      received: { label: 'RECEIVED', variant: 'default' },
      partially_paid: { label: 'PARTIALLY PAID', variant: 'secondary' },
      paid: { label: 'PAID', variant: 'default' },
    };

    const { label, variant } = config[status] || { label: status.toUpperCase(), variant: 'secondary' as const };
    return <Badge variant={variant}>{label}</Badge>;
  };

  if (loading) {
    return (
      <div className="p-6">
        <div className="text-center py-12">Loading invoice details...</div>
      </div>
    );
  }

  if (!invoice) {
    return (
      <div className="p-6">
        <Card>
          <CardContent className="py-12 text-center">
            <p className="text-muted-foreground">Invoice not found</p>
            <Button variant="outline" className="mt-4" onClick={() => router.back()}>
              Go Back
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={() => router.back()}>
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <div>
            <h1 className="text-3xl font-bold">{invoice.invoice_number}</h1>
            <p className="text-muted-foreground">Purchase Invoice Details</p>
          </div>
        </div>

        <div className="flex gap-2">
          {invoice.status === 'draft' && (
            <Button onClick={handleMarkReceived}>
              <CheckCircle className="mr-2 h-4 w-4" />
              Mark Received
            </Button>
          )}

          {(invoice.status === 'received' || invoice.status === 'partially_paid') && invoice.balance_due > 0 && (
            <Button onClick={() => router.push(`/dashboard/purchases/payments/new?invoice_id=${invoice.id}`)}>
              <DollarSign className="mr-2 h-4 w-4" />
              Record Payment
            </Button>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main Content */}
        <div className="lg:col-span-2 space-y-6">
          {/* Invoice Info */}
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>Invoice Information</CardTitle>
                {getStatusBadge(invoice.status)}
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-sm text-muted-foreground mb-1">Invoice Number</p>
                  <p className="font-semibold">{invoice.invoice_number}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground mb-1">Invoice Date</p>
                  <p className="font-semibold">{formatDate(invoice.invoice_date)}</p>
                </div>
                {invoice.due_date && (
                  <div>
                    <p className="text-sm text-muted-foreground mb-1">Due Date</p>
                    <p className="font-semibold">{formatDate(invoice.due_date)}</p>
                  </div>
                )}
                {invoice.received_at && (
                  <div>
                    <p className="text-sm text-muted-foreground mb-1">Received At</p>
                    <p className="font-semibold">{formatDateTime(invoice.received_at)}</p>
                  </div>
                )}
              </div>

              {invoice.notes && (
                <div>
                  <p className="text-sm text-muted-foreground mb-1">Notes</p>
                  <p className="text-sm">{invoice.notes}</p>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Items */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Package className="h-5 w-5" />
                Items ({invoice.items.length})
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                <div className="grid grid-cols-12 gap-2 text-sm font-medium text-muted-foreground pb-2 border-b">
                  <div className="col-span-5">Product</div>
                  <div className="col-span-2 text-center">UOM</div>
                  <div className="col-span-2 text-right">Quantity</div>
                  <div className="col-span-3 text-right">Amount</div>
                </div>

                {invoice.items.map((item) => (
                  <div key={item.id} className="grid grid-cols-12 gap-2 text-sm py-2 border-b">
                    <div className="col-span-5">
                      <p className="font-medium">{item.product_name}</p>
                      {item.barcode && (
                        <p className="text-xs text-muted-foreground">Barcode: {item.barcode}</p>
                      )}
                    </div>
                    <div className="col-span-2 text-center">{item.uom}</div>
                    <div className="col-span-2 text-right">{item.quantity}</div>
                    <div className="col-span-3 text-right space-y-1">
                      <div className="text-xs text-muted-foreground">
                        @ {formatCurrency(item.unit_cost)}
                      </div>
                      <div className="font-semibold">{formatCurrency(item.total_cost)}</div>
                    </div>
                  </div>
                ))}

                <div className="pt-4 space-y-2">
                  <div className="flex justify-between text-lg font-bold">
                    <span>Total Amount</span>
                    <span>{formatCurrency(invoice.total_amount)}</span>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Payment History */}
          {payments.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <CreditCard className="h-5 w-5" />
                  Payment History
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {payments.map((payment) => (
                    <div key={payment.id} className="flex items-center justify-between p-3 border rounded-lg">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          <p className="font-semibold">{formatCurrency(payment.amount)}</p>
                          <Badge variant="outline">{payment.payment_method}</Badge>
                        </div>
                        <p className="text-sm text-muted-foreground">
                          {formatDate(payment.payment_date)}
                          {payment.reference_number && ` • Ref: ${payment.reference_number}`}
                        </p>
                        {payment.notes && (
                          <p className="text-sm text-muted-foreground mt-1">{payment.notes}</p>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Supplier Info */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <User className="h-5 w-5" />
                Supplier
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div>
                <p className="font-semibold text-lg">{invoice.supplier_name}</p>
              </div>
            </CardContent>
          </Card>

          {/* Payment Summary */}
          <Card>
            <CardHeader>
              <CardTitle>Payment Summary</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Total Amount</span>
                  <span className="font-semibold">{formatCurrency(invoice.total_amount)}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Paid Amount</span>
                  <span className="font-semibold text-green-600">{formatCurrency(invoice.paid_amount)}</span>
                </div>
                <Separator />
                <div className="flex justify-between">
                  <span className="font-semibold">Balance Due</span>
                  <span className={`font-bold text-lg ${invoice.balance_due > 0 ? 'text-orange-600' : 'text-green-600'}`}>
                    {formatCurrency(invoice.balance_due)}
                  </span>
                </div>
              </div>

              {invoice.balance_due > 0 && (
                <Button
                  className="w-full"
                  onClick={() => router.push(`/dashboard/purchases/payments/new?invoice_id=${invoice.id}`)}
                >
                  <DollarSign className="mr-2 h-4 w-4" />
                  Record Payment
                </Button>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
