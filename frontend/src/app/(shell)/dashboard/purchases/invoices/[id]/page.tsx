'use client';

import { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { ArrowLeft, DollarSign, CheckCircle, Package, FileText, Calendar, User, Phone, Mail, MapPin, CreditCard, Edit } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { purchaseApi, PurchaseInvoice, SupplierPayment } from '@/lib/api/purchases';
import { toast } from 'sonner';
import EditInvoiceDialog from '@/components/purchases/edit-invoice-dialog';

export default function InvoiceDetailPage() {
  const params = useParams();
  const router = useRouter();
  const invoiceId = params.id as string;

  const [invoice, setInvoice] = useState<PurchaseInvoice | null>(null);
  const [payments, setPayments] = useState<SupplierPayment[]>([]);
  const [loading, setLoading] = useState(true);
  const [showEditDialog, setShowEditDialog] = useState(false);

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
            <p className="text-text-muted">Invoice not found</p>
            <Button variant="outline" className="mt-4" onClick={() => router.back()}>
              Go Back
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="p-4 space-y-4">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="icon" onClick={() => router.back()}>
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <div className="min-w-0">
            <h1 className="text-xl font-semibold truncate">{invoice.invoice_number}</h1>
            <p className="text-sm text-text-muted">Purchase Invoice Details</p>
          </div>
        </div>

        <div className="flex flex-wrap gap-2">
          {invoice.status !== 'paid' && (
            <Button variant="outline" size="sm" onClick={() => setShowEditDialog(true)}>
              <Edit className="mr-1.5 h-4 w-4" />
              Edit
            </Button>
          )}

          {invoice.status === 'draft' && (
            <Button size="sm" onClick={handleMarkReceived}>
              <CheckCircle className="mr-1.5 h-4 w-4" />
              Received
            </Button>
          )}

          {(invoice.status === 'received' || invoice.status === 'partially_paid') && invoice.balance_due > 0 && (
            <Button size="sm" onClick={() => router.push(`/dashboard/purchases/payments/new?invoice_id=${invoice.id}`)}>
              <DollarSign className="mr-1.5 h-4 w-4" />
              Pay
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
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <p className="text-sm text-text-muted mb-1">Invoice Number</p>
                  <p className="font-semibold">{invoice.invoice_number}</p>
                </div>
                <div>
                  <p className="text-sm text-text-muted mb-1">Invoice Date</p>
                  <p className="font-semibold">{formatDate(invoice.invoice_date)}</p>
                </div>
                {invoice.due_date && (
                  <div>
                    <p className="text-sm text-text-muted mb-1">Due Date</p>
                    <p className="font-semibold">{formatDate(invoice.due_date)}</p>
                  </div>
                )}
                {invoice.received_at && (
                  <div>
                    <p className="text-sm text-text-muted mb-1">Received At</p>
                    <p className="font-semibold">{formatDateTime(invoice.received_at)}</p>
                  </div>
                )}
              </div>

              {invoice.notes && (
                <div>
                  <p className="text-sm text-text-muted mb-1">Notes</p>
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
                {/* Desktop table header */}
                <div className="hidden md:grid grid-cols-12 gap-2 text-sm font-medium text-text-muted pb-2 border-b">
                  <div className="col-span-5">Product</div>
                  <div className="col-span-2 text-center">UOM</div>
                  <div className="col-span-2 text-right">Quantity</div>
                  <div className="col-span-3 text-right">Amount</div>
                </div>

                {invoice.items.map((item) => (
                  <div key={item.id}>
                    {/* Mobile card */}
                    <div className="md:hidden py-3 border-b space-y-1">
                      <div className="flex justify-between items-start">
                        <div className="min-w-0 flex-1">
                          <p className="font-medium text-sm">{item.product_name}</p>
                          {item.barcode && (
                            <p className="text-xs text-text-muted">Barcode: {item.barcode}</p>
                          )}
                        </div>
                        <p className="font-semibold text-sm ml-2">{formatCurrency(item.total_cost)}</p>
                      </div>
                      <div className="flex gap-3 text-xs text-text-muted">
                        <span>{item.quantity} {item.uom}</span>
                        <span>@ {formatCurrency(item.unit_cost)}</span>
                        {item.discount_amount > 0 && (
                          <span className="text-warning-fg">-{formatCurrency(item.discount_amount)}</span>
                        )}
                      </div>
                    </div>
                    {/* Desktop row */}
                    <div className="hidden md:grid grid-cols-12 gap-2 text-sm py-2 border-b">
                      <div className="col-span-5">
                        <p className="font-medium">{item.product_name}</p>
                        {item.barcode && (
                          <p className="text-xs text-text-muted">Barcode: {item.barcode}</p>
                        )}
                      </div>
                      <div className="col-span-2 text-center">{item.uom}</div>
                      <div className="col-span-2 text-right">{item.quantity}</div>
                      <div className="col-span-3 text-right space-y-1">
                        <div className="text-xs text-text-muted">
                          @ {formatCurrency(item.unit_cost)}
                        </div>
                        {item.discount_amount > 0 && (
                          <div className="text-xs text-warning-fg">
                            Discount: -{formatCurrency(item.discount_amount)}
                          </div>
                        )}
                        <div className="font-semibold">{formatCurrency(item.total_cost)}</div>
                      </div>
                    </div>
                  </div>
                ))}

                <div className="pt-4 space-y-2">
                  <div className="flex justify-between text-sm">
                    <span className="text-text-muted">Subtotal</span>
                    <span className="font-semibold">{formatCurrency(invoice.subtotal)}</span>
                  </div>
                  {invoice.invoice_discount_amount > 0 && (
                    <div className="flex justify-between text-sm text-warning-fg">
                      <span>Invoice Discount</span>
                      <span className="font-semibold">-{formatCurrency(invoice.invoice_discount_amount)}</span>
                    </div>
                  )}
                  <Separator />
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
                        <p className="text-sm text-text-muted">
                          {formatDate(payment.payment_date)}
                          {payment.reference_number && ` • Ref: ${payment.reference_number}`}
                        </p>
                        {payment.notes && (
                          <p className="text-sm text-text-muted mt-1">{payment.notes}</p>
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
                  <span className="text-text-muted">Total Amount</span>
                  <span className="font-semibold">{formatCurrency(invoice.total_amount)}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-text-muted">Paid Amount</span>
                  <span className="font-semibold text-success-fg">{formatCurrency(invoice.paid_amount)}</span>
                </div>
                <Separator />
                <div className="flex justify-between">
                  <span className="font-semibold">Balance Due</span>
                  <span className={`font-bold text-lg ${invoice.balance_due > 0 ? 'text-warning-fg' : 'text-success-fg'}`}>
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

      {/* Edit Invoice Dialog */}
      {invoice && showEditDialog && (
        <EditInvoiceDialog
          invoice={invoice}
          open={showEditDialog}
          onClose={() => setShowEditDialog(false)}
          onSuccess={() => {
            setShowEditDialog(false);
            loadInvoiceDetails();
          }}
        />
      )}
    </div>
  );
}
