'use client';

import { useState, useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { ArrowLeft, DollarSign, Save } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { purchaseApi, SupplierListItem, PurchaseInvoice } from '@/lib/api/purchases';
import { toast } from 'sonner';

export default function RecordPaymentPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const invoiceIdParam = searchParams.get('invoice_id');

  const [suppliers, setSuppliers] = useState<SupplierListItem[]>([]);
  const [invoice, setInvoice] = useState<PurchaseInvoice | null>(null);
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  // Form state
  const [supplierId, setSupplierId] = useState<string>('');
  const [invoiceId, setInvoiceId] = useState<string>(invoiceIdParam || '');
  const [paymentDate, setPaymentDate] = useState<string>(new Date().toISOString().split('T')[0]);
  const [amount, setAmount] = useState<string>('');
  const [paymentMethod, setPaymentMethod] = useState<string>('cash');
  const [referenceNumber, setReferenceNumber] = useState<string>('');
  const [notes, setNotes] = useState<string>('');

  useEffect(() => {
    loadSuppliers();
    if (invoiceIdParam) {
      loadInvoice(invoiceIdParam);
    }
  }, [invoiceIdParam]);

  const loadSuppliers = async () => {
    try {
      const response = await purchaseApi.listSuppliers({ active_only: true, size: 1000 });
      setSuppliers(response.items || []);
    } catch (error) {
      console.error('Error loading suppliers:', error);
      toast.error('Failed to load suppliers');
    }
  };

  const loadInvoice = async (id: string) => {
    try {
      setLoading(true);
      const data = await purchaseApi.getPurchaseInvoice(id);
      setInvoice(data);
      setSupplierId(data.supplier_id);
      setInvoiceId(id);

      // Set amount to balance due by default
      if (data.balance_due > 0) {
        setAmount((data.balance_due / 100).toFixed(2));
      }
    } catch (error) {
      console.error('Error loading invoice:', error);
      toast.error('Failed to load invoice details');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    // Validation
    if (!supplierId) {
      toast.error('Please select a supplier');
      return;
    }

    if (!paymentDate) {
      toast.error('Please select payment date');
      return;
    }

    const amountValue = parseFloat(amount);
    if (!amount || isNaN(amountValue) || amountValue <= 0) {
      toast.error('Please enter a valid payment amount');
      return;
    }

    if (!paymentMethod) {
      toast.error('Please select payment method');
      return;
    }

    // Check if amount exceeds balance due for invoice payments
    if (invoice && amountValue > invoice.balance_due / 100) {
      toast.error(`Payment amount cannot exceed balance due of ₹${(invoice.balance_due / 100).toFixed(2)}`);
      return;
    }

    try {
      setSubmitting(true);

      await purchaseApi.recordPayment({
        supplier_id: supplierId,
        purchase_invoice_id: invoiceId || undefined,
        payment_date: paymentDate,
        amount: Math.round(amountValue * 100), // Convert to paise
        payment_method: paymentMethod,
        reference_number: referenceNumber || undefined,
        notes: notes || undefined,
      });

      toast.success('Payment recorded successfully');

      // Navigate back to invoice if it was an invoice payment
      if (invoiceId) {
        router.push(`/dashboard/purchases/invoices/${invoiceId}`);
      } else {
        router.push('/dashboard/purchases/invoices');
      }
    } catch (error: any) {
      console.error('Error recording payment:', error);
      toast.error(error.response?.data?.detail || 'Failed to record payment');
    } finally {
      setSubmitting(false);
    }
  };

  const formatCurrency = (amount: number) => {
    return `₹${(amount / 100).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  };

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" onClick={() => router.back()}>
          <ArrowLeft className="h-5 w-5" />
        </Button>
        <div>
          <h1 className="text-3xl font-bold">Record Payment</h1>
          <p className="text-muted-foreground">Record a payment to supplier</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Form */}
        <div className="lg:col-span-2">
          <Card>
            <CardHeader>
              <CardTitle>Payment Details</CardTitle>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleSubmit} className="space-y-6">
                {/* Supplier */}
                <div className="space-y-2">
                  <Label htmlFor="supplier">Supplier *</Label>
                  <Select
                    value={supplierId}
                    onValueChange={(value) => {
                      setSupplierId(value);
                      // Clear invoice if supplier changes
                      if (value !== supplierId) {
                        setInvoiceId('');
                        setInvoice(null);
                        setAmount('');
                      }
                    }}
                    disabled={!!invoiceIdParam}
                  >
                    <SelectTrigger id="supplier">
                      <SelectValue placeholder="Select supplier" />
                    </SelectTrigger>
                    <SelectContent>
                      {suppliers.map((supplier) => (
                        <SelectItem key={supplier.id} value={supplier.id}>
                          {supplier.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  {invoiceIdParam && (
                    <p className="text-xs text-muted-foreground">
                      Supplier is pre-selected based on the invoice
                    </p>
                  )}
                </div>

                {/* Invoice (Optional) */}
                {invoiceIdParam && invoice && (
                  <div className="p-4 bg-muted rounded-lg space-y-2">
                    <p className="text-sm font-medium">Invoice: {invoice.invoice_number}</p>
                    <div className="grid grid-cols-3 gap-4 text-sm">
                      <div>
                        <p className="text-muted-foreground">Total Amount</p>
                        <p className="font-semibold">{formatCurrency(invoice.total_amount)}</p>
                      </div>
                      <div>
                        <p className="text-muted-foreground">Paid Amount</p>
                        <p className="font-semibold text-green-600">{formatCurrency(invoice.paid_amount)}</p>
                      </div>
                      <div>
                        <p className="text-muted-foreground">Balance Due</p>
                        <p className="font-semibold text-orange-600">{formatCurrency(invoice.balance_due)}</p>
                      </div>
                    </div>
                  </div>
                )}

                {/* Payment Date */}
                <div className="space-y-2">
                  <Label htmlFor="payment-date">Payment Date *</Label>
                  <Input
                    id="payment-date"
                    type="date"
                    value={paymentDate}
                    onChange={(e) => setPaymentDate(e.target.value)}
                    max={new Date().toISOString().split('T')[0]}
                    required
                  />
                </div>

                {/* Amount */}
                <div className="space-y-2">
                  <Label htmlFor="amount">Amount (₹) *</Label>
                  <Input
                    id="amount"
                    type="number"
                    step="0.01"
                    min="0.01"
                    value={amount}
                    onChange={(e) => setAmount(e.target.value)}
                    placeholder="0.00"
                    required
                  />
                  {invoice && parseFloat(amount) > 0 && (
                    <p className="text-xs text-muted-foreground">
                      {parseFloat(amount) <= invoice.balance_due / 100 ? (
                        <span className="text-green-600">
                          ✓ Amount is within balance due
                        </span>
                      ) : (
                        <span className="text-red-600">
                          ⚠ Amount exceeds balance due of {formatCurrency(invoice.balance_due)}
                        </span>
                      )}
                    </p>
                  )}
                </div>

                {/* Payment Method */}
                <div className="space-y-2">
                  <Label htmlFor="payment-method">Payment Method *</Label>
                  <Select value={paymentMethod} onValueChange={setPaymentMethod}>
                    <SelectTrigger id="payment-method">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="cash">Cash</SelectItem>
                      <SelectItem value="bank_transfer">Bank Transfer</SelectItem>
                      <SelectItem value="cheque">Cheque</SelectItem>
                      <SelectItem value="upi">UPI</SelectItem>
                      <SelectItem value="card">Card</SelectItem>
                      <SelectItem value="other">Other</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                {/* Reference Number */}
                <div className="space-y-2">
                  <Label htmlFor="reference">Reference Number (Optional)</Label>
                  <Input
                    id="reference"
                    type="text"
                    value={referenceNumber}
                    onChange={(e) => setReferenceNumber(e.target.value)}
                    placeholder="Transaction ID, Cheque Number, etc."
                  />
                </div>

                {/* Notes */}
                <div className="space-y-2">
                  <Label htmlFor="notes">Notes (Optional)</Label>
                  <Textarea
                    id="notes"
                    value={notes}
                    onChange={(e) => setNotes(e.target.value)}
                    placeholder="Additional notes about this payment..."
                    rows={3}
                  />
                </div>

                {/* Actions */}
                <div className="flex gap-2 justify-end pt-4">
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => router.back()}
                    disabled={submitting}
                  >
                    Cancel
                  </Button>
                  <Button type="submit" disabled={submitting || loading}>
                    {submitting ? (
                      <>Saving...</>
                    ) : (
                      <>
                        <Save className="mr-2 h-4 w-4" />
                        Record Payment
                      </>
                    )}
                  </Button>
                </div>
              </form>
            </CardContent>
          </Card>
        </div>

        {/* Sidebar - Summary */}
        <div>
          <Card>
            <CardHeader>
              <CardTitle>Payment Summary</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Supplier</span>
                  <span className="font-medium">
                    {suppliers.find(s => s.id === supplierId)?.name || '-'}
                  </span>
                </div>

                {invoice && (
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">Invoice</span>
                    <span className="font-medium">{invoice.invoice_number}</span>
                  </div>
                )}

                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Payment Date</span>
                  <span className="font-medium">
                    {paymentDate ? new Date(paymentDate).toLocaleDateString('en-IN') : '-'}
                  </span>
                </div>

                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Method</span>
                  <span className="font-medium capitalize">
                    {paymentMethod.replace('_', ' ')}
                  </span>
                </div>

                <div className="pt-2 border-t">
                  <div className="flex justify-between">
                    <span className="font-semibold">Amount</span>
                    <span className="font-bold text-lg">
                      ₹{parseFloat(amount || '0').toFixed(2)}
                    </span>
                  </div>
                </div>
              </div>

              <div className="pt-4 border-t">
                <p className="text-xs text-muted-foreground">
                  <DollarSign className="h-3 w-3 inline mr-1" />
                  This payment will be recorded against the supplier account
                  {invoice && ' and linked to the selected invoice'}.
                </p>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
