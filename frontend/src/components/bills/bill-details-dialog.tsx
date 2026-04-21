'use client';

import { useEffect, useState } from 'react';
import { Printer, User, UserPlus, FileText, Edit, Trash2, CreditCard, MessageCircle } from 'lucide-react';
import {
  Dialog,
  DialogBody,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { apiClient } from '@/lib/api-client';
import { toast } from 'sonner';
import { Loader2 } from 'lucide-react';
import { useSettingsStore } from '@/stores/settings-store';
import { sendReceiptToWhatsApp } from '@/lib/whatsapp-receipt';
import { StaffContributionResponse } from '@/types/multi-staff';
import { titleCase } from '@/lib/utils';
import { CustomerSearch } from '@/components/pos/customer-search';
import { useAuthStore } from '@/stores/auth-store';

interface BillItem {
  id: string;
  service_id: string;
  item_name: string;
  base_price: number; // paise
  quantity: number;
  line_total: number; // paise
  staff_id: string | null;
  staff_contributions?: StaffContributionResponse[]; // Multi-staff contributions
  notes: string | null;
}

interface Payment {
  id: string;
  bill_id: string;
  payment_method: 'cash' | 'upi' | 'card' | 'other';
  amount: number; // paise
  reference_number: string | null;
  notes: string | null;
  confirmed_at: string;
  confirmed_by: string;
}

interface BillDetails {
  id: string;
  invoice_number: string | null;
  customer_id: string | null;
  customer_name: string | null;
  customer_phone: string | null;
  status: string;
  subtotal: number; // paise
  discount_amount: number; // paise
  tax_amount: number; // paise
  cgst_amount: number; // paise
  sgst_amount: number; // paise
  total_amount: number; // paise
  rounded_total: number; // paise
  rounding_adjustment: number; // paise
  write_off_amount: number; // paise — total written off (0 if none)
  write_off_at: string | null;
  items: BillItem[];
  payments: Payment[];
  created_at: string;
  posted_at: string | null;
  created_by: string;
}

interface BillDetailsDialogProps {
  billId: string | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onVoid?: (billId: string) => void;
  onRefund?: (billId: string) => void;
  onReprint?: (billId: string) => void;
}

export function BillDetailsDialog({
  billId,
  open,
  onOpenChange,
  onVoid,
  onRefund,
  onReprint,
}: BillDetailsDialogProps) {
  const [bill, setBill] = useState<BillDetails | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [editingPayment, setEditingPayment] = useState<Payment | null>(null);
  const [isEditDialogOpen, setIsEditDialogOpen] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const { hasGST, fetchSettings, settings } = useSettingsStore();
  const { hasPermission, user } = useAuthStore();
  const [showAssignCustomer, setShowAssignCustomer] = useState(false);
  const [isAssigning, setIsAssigning] = useState(false);
  const canAssignCustomer = hasPermission('billing', 'update');
  const isOwner = user?.role === 'owner';
  const canDiscount = hasPermission('billing', 'discount');
  const canAddPayment = hasPermission('billing', 'create');

  // Edit discount state
  const [showEditDiscount, setShowEditDiscount] = useState(false);
  const [discountInput, setDiscountInput] = useState('');
  const [discountReason, setDiscountReason] = useState('');
  const [isSavingDiscount, setIsSavingDiscount] = useState(false);

  // Collect pending payment state (posted bills with pending balance)
  const [showCollectPayment, setShowCollectPayment] = useState(false);
  const [collectAmount, setCollectAmount] = useState('');
  const [collectMethod, setCollectMethod] = useState<'cash' | 'upi' | 'card' | 'other'>('cash');
  const [collectRef, setCollectRef] = useState('');
  const [isCollecting, setIsCollecting] = useState(false);

  // Write-off state
  const [showWriteOff, setShowWriteOff] = useState(false);
  const [writeOffAmount, setWriteOffAmount] = useState('');
  const [writeOffReason, setWriteOffReason] = useState('');
  const [isSavingWriteOff, setIsSavingWriteOff] = useState(false);

  // Add payment state
  const [showAddPayment, setShowAddPayment] = useState(false);
  const [addPaymentAmount, setAddPaymentAmount] = useState('');
  const [addPaymentMethod, setAddPaymentMethod] = useState<'cash' | 'upi' | 'card' | 'other'>('cash');
  const [addPaymentRef, setAddPaymentRef] = useState('');
  const [isAddingPayment, setIsAddingPayment] = useState(false);

  useEffect(() => {
    if (!settings) {
      fetchSettings();
    }
  }, []);

  useEffect(() => {
    if (open && billId) {
      fetchBillDetails();
    }
  }, [open, billId]);

  const fetchBillDetails = async () => {
    if (!billId) return;

    try {
      setIsLoading(true);
      const { data } = await apiClient.get<BillDetails>(`/pos/bills/${billId}`);
      setBill(data);
    } catch (error: any) {
      console.error('Error fetching bill details:', error);
      toast.error(error.response?.data?.detail || 'Failed to load bill details');
      onOpenChange(false);
    } finally {
      setIsLoading(false);
    }
  };

  const handleEditPayment = (payment: Payment) => {
    setEditingPayment(payment);
    setIsEditDialogOpen(true);
  };

  const handleDeletePayment = async (paymentId: string) => {
    if (!bill || !billId) return;

    if (!confirm('Are you sure you want to delete this payment?')) {
      return;
    }

    try {
      setIsSaving(true);
      await apiClient.delete(`/pos/bills/${billId}/payments/${paymentId}`);
      toast.success('Payment deleted successfully');
      await fetchBillDetails(); // Refresh bill details
    } catch (error: any) {
      console.error('Error deleting payment:', error);
      toast.error(error.response?.data?.detail || 'Failed to delete payment');
    } finally {
      setIsSaving(false);
    }
  };

  const handleSavePayment = async (updatedData: Partial<Payment>) => {
    if (!editingPayment || !bill || !billId) return;

    try {
      setIsSaving(true);
      const payload: any = {};

      if (updatedData.payment_method) payload.method = updatedData.payment_method;
      if (updatedData.amount !== undefined) payload.amount = updatedData.amount / 100; // Convert to rupees
      if (updatedData.reference_number !== undefined) payload.reference_number = updatedData.reference_number;
      if (updatedData.notes !== undefined) payload.notes = updatedData.notes;

      await apiClient.patch(`/pos/bills/${billId}/payments/${editingPayment.id}`, payload);
      toast.success('Payment updated successfully');
      setIsEditDialogOpen(false);
      setEditingPayment(null);
      await fetchBillDetails(); // Refresh bill details
    } catch (error: any) {
      console.error('Error updating payment:', error);
      toast.error(error.response?.data?.detail || 'Failed to update payment');
    } finally {
      setIsSaving(false);
    }
  };

  const handleAddPayment = async () => {
    if (!bill || !billId) return;
    const amount = parseFloat(addPaymentAmount || '0');
    if (isNaN(amount) || amount <= 0) {
      toast.error('Enter a valid payment amount');
      return;
    }
    try {
      setIsAddingPayment(true);
      await apiClient.post(`/pos/bills/${billId}/payments`, {
        method: addPaymentMethod,
        amount,
        reference_number: addPaymentRef.trim() || null,
      });
      toast.success('Payment added');
      setShowAddPayment(false);
      setAddPaymentAmount('');
      setAddPaymentRef('');
      setAddPaymentMethod('cash');
      await fetchBillDetails();
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to add payment');
    } finally {
      setIsAddingPayment(false);
    }
  };

  const handleSaveDiscount = async () => {
    if (!bill || !billId) return;
    const discountRupees = parseFloat(discountInput || '0');
    if (isNaN(discountRupees) || discountRupees < 0) {
      toast.error('Enter a valid discount amount');
      return;
    }
    const discountPaise = Math.round(discountRupees * 100);
    try {
      setIsSavingDiscount(true);
      await apiClient.patch(`/pos/bills/${billId}/discount`, {
        discount_amount: discountPaise,
        reason: discountReason.trim() || null,
      });
      toast.success('Discount updated');
      setShowEditDiscount(false);
      setDiscountInput('');
      setDiscountReason('');
      await fetchBillDetails();
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to update discount');
    } finally {
      setIsSavingDiscount(false);
    }
  };

  const handleCollectPayment = async () => {
    if (!bill || !billId) return;
    const amountRupees = parseFloat(collectAmount || '0');
    const amountPaise = Math.round(amountRupees * 100);
    const totalPaid = bill.payments?.reduce((s, p) => s + p.amount, 0) ?? 0;
    const pending = bill.rounded_total - totalPaid - (bill.write_off_amount ?? 0);
    if (amountPaise <= 0 || amountPaise > pending) {
      toast.error(`Amount must be between ₹0.01 and ${formatPrice(pending)}`);
      return;
    }
    try {
      setIsCollecting(true);
      await apiClient.post(`/pos/bills/${billId}/collect-pending`, {
        method: collectMethod,
        amount: amountRupees,
        reference_number: collectRef.trim() || null,
      });
      toast.success('Payment collected');
      setShowCollectPayment(false);
      setCollectAmount('');
      setCollectRef('');
      setCollectMethod('cash');
      await fetchBillDetails();
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to collect payment');
    } finally {
      setIsCollecting(false);
    }
  };

  const handleWriteOff = async () => {
    if (!bill || !billId) return;
    const amountRupees = parseFloat(writeOffAmount || '0');
    const amountPaise = Math.round(amountRupees * 100);
    const totalPaid = bill.payments?.reduce((s, p) => s + p.amount, 0) ?? 0;
    const pending = bill.rounded_total - totalPaid - (bill.write_off_amount ?? 0);
    if (amountPaise <= 0 || amountPaise > pending) {
      toast.error(`Write-off amount must be between ₹0.01 and ${formatPrice(pending)}`);
      return;
    }
    if (!writeOffReason.trim()) {
      toast.error('Reason is required');
      return;
    }
    try {
      setIsSavingWriteOff(true);
      await apiClient.patch(`/pos/bills/${billId}/write-off`, {
        write_off_amount: amountPaise,
        reason: writeOffReason.trim(),
      });
      toast.success('Pending balance written off');
      setShowWriteOff(false);
      setWriteOffAmount('');
      setWriteOffReason('');
      await fetchBillDetails();
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to write off balance');
    } finally {
      setIsSavingWriteOff(false);
    }
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

  const getPaymentMethodLabel = (method: string) => {
    switch (method) {
      case 'cash':
        return 'Cash';
      case 'upi':
        return 'UPI';
      case 'card':
        return 'Card';
      case 'other':
        return 'Other';
      default:
        return method;
    }
  };


  if (!open) return null;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent size="lg" className="lg:max-w-[768px]">
        <DialogHeader>
          <DialogTitle>Bill Details</DialogTitle>
        </DialogHeader>

        <DialogBody>
        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-8 w-8 animate-spin text-gray-400" />
          </div>
        ) : bill ? (
          <div className="space-y-6">
            {/* Header Info */}
            <div className="flex items-start justify-between">
              <div>
                <h3 className="text-2xl font-bold">{bill.invoice_number || 'Draft'}</h3>
                <p className="text-sm text-muted-foreground mt-1">
                  {formatDate(bill.created_at)}
                </p>
              </div>
              {getStatusBadge(bill.status)}
            </div>

            {/* Customer Info */}
            <div className="bg-gray-50 rounded-lg p-4">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <User className="h-4 w-4 text-gray-500" />
                  <span className="font-semibold text-sm">Customer</span>
                </div>
                {!bill.customer_phone && canAssignCustomer && !showAssignCustomer && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setShowAssignCustomer(true)}
                    disabled={isAssigning}
                  >
                    <UserPlus className="h-3 w-3 mr-1" />
                    Assign Customer
                  </Button>
                )}
              </div>
              <p className="text-base">{titleCase(bill.customer_name) || 'Walk-in Customer'}</p>
              {showAssignCustomer && (
                <div className="mt-3">
                  <CustomerSearch
                    value={{ id: null, name: null }}
                    onChange={async (id, name, phone) => {
                      if (!id || !billId) return;
                      setIsAssigning(true);
                      try {
                        await apiClient.patch(`/pos/bills/${billId}/customer`, {
                          customer_id: id,
                        });
                        toast.success(`Customer assigned: ${name}`);
                        setShowAssignCustomer(false);
                        await fetchBillDetails();
                      } catch (error: any) {
                        toast.error(error.response?.data?.detail || 'Failed to assign customer');
                      } finally {
                        setIsAssigning(false);
                      }
                    }}
                  />
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setShowAssignCustomer(false)}
                    className="mt-2"
                    disabled={isAssigning}
                  >
                    Cancel
                  </Button>
                </div>
              )}
            </div>

            {/* Services */}
            <div>
              <h4 className="font-semibold mb-3 flex items-center gap-2">
                <FileText className="h-4 w-4" />
                Services
              </h4>
              <div className="border rounded-lg overflow-hidden overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-gray-50 border-b">
                    <tr>
                      <th className="px-3 sm:px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                        Service
                      </th>
                      <th className="px-4 py-2 text-center text-xs font-medium text-gray-500 uppercase">
                        Qty
                      </th>
                      <th className="px-4 py-2 text-right text-xs font-medium text-gray-500 uppercase">
                        Price
                      </th>
                      <th className="px-4 py-2 text-right text-xs font-medium text-gray-500 uppercase">
                        Total
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y">
                    {(bill.items || []).map((item) => (
                      <tr key={item.id}>
                        <td className="px-4 py-3">
                          <p className="font-medium text-sm">{item.item_name}</p>
                          {item.notes && (
                            <p className="text-xs text-muted-foreground italic">
                              {item.notes}
                            </p>
                          )}
                          {/* Multi-staff contributions */}
                          {item.staff_contributions && item.staff_contributions.length > 0 && (
                            <div className="mt-2 space-y-1">
                              <p className="text-xs text-gray-600 font-medium">Staff Team:</p>
                              {item.staff_contributions.map((contrib, idx) => (
                                <div key={idx} className="flex items-center justify-between text-xs">
                                  <span className="text-gray-600">
                                    {contrib.role_in_service}
                                  </span>
                                  <span className="font-medium">
                                    {formatPrice(contrib.contribution_amount)}
                                  </span>
                                </div>
                              ))}
                            </div>
                          )}
                        </td>
                        <td className="px-4 py-3 text-center text-sm">
                          {item.quantity}
                        </td>
                        <td className="px-4 py-3 text-right text-sm">
                          {formatPrice(item.base_price)}
                        </td>
                        <td className="px-4 py-3 text-right text-sm font-medium">
                          {formatPrice(item.line_total)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Payments */}
            {bill.payments && bill.payments.length > 0 && (
              <div>
                <h4 className="font-semibold mb-3 flex items-center gap-2">
                  <CreditCard className="h-4 w-4" />
                  Payments
                </h4>
                <div className="border rounded-lg overflow-hidden">
                  <table className="w-full">
                    <thead className="bg-gray-50 border-b">
                      <tr>
                        <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                          Method
                        </th>
                        <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                          Reference
                        </th>
                        <th className="px-4 py-2 text-right text-xs font-medium text-gray-500 uppercase">
                          Amount
                        </th>
                        <th className="px-4 py-2 text-right text-xs font-medium text-gray-500 uppercase">
                          Actions
                        </th>
                      </tr>
                    </thead>
                    <tbody className="divide-y">
                      {bill.payments.map((payment) => (
                        <tr key={payment.id}>
                          <td className="px-4 py-3">
                            <p className="font-medium text-sm">
                              {getPaymentMethodLabel(payment.payment_method)}
                            </p>
                            {payment.notes && (
                              <p className="text-xs text-muted-foreground italic">
                                {payment.notes}
                              </p>
                            )}
                          </td>
                          <td className="px-4 py-3 text-sm text-muted-foreground">
                            {payment.reference_number || '-'}
                          </td>
                          <td className="px-4 py-3 text-right text-sm font-medium">
                            {formatPrice(payment.amount)}
                          </td>
                          <td className="px-4 py-3 text-right">
                            {bill.status !== 'refunded' && (
                              <div className="flex gap-1 justify-end">
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  onClick={() => handleEditPayment(payment)}
                                  disabled={isSaving}
                                >
                                  <Edit className="h-3 w-3" />
                                </Button>
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  onClick={() => handleDeletePayment(payment.id)}
                                  disabled={isSaving}
                                  className="text-red-600 hover:text-red-700 hover:bg-red-50"
                                >
                                  <Trash2 className="h-3 w-3" />
                                </Button>
                              </div>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* Pricing Summary */}
            <div className="bg-gray-50 rounded-lg p-4 space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">Subtotal</span>
                <span>{formatPrice(bill.subtotal)}</span>
              </div>
              {bill.discount_amount > 0 && (
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Discount</span>
                  <span className="text-red-600">-{formatPrice(bill.discount_amount)}</span>
                </div>
              )}
              {(bill.write_off_amount ?? 0) > 0 && (
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Write-off</span>
                  <span className="text-amber-600">-{formatPrice(bill.write_off_amount)}</span>
                </div>
              )}
              {hasGST() && (
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Tax (CGST + SGST)</span>
                  <span>{formatPrice(bill.tax_amount)}</span>
                </div>
              )}
              {bill.rounding_adjustment !== 0 && (
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Rounding</span>
                  <span>
                    {bill.rounding_adjustment > 0 ? '+' : ''}
                    {formatPrice(Math.abs(bill.rounding_adjustment))}
                  </span>
                </div>
              )}
              <Separator />
              <div className="flex justify-between text-lg font-bold">
                <span>Total</span>
                <span>{formatPrice(bill.rounded_total)}</span>
              </div>
            </div>

            {/* Status Info */}
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium">Created by</p>
                  <p className="text-xs text-muted-foreground">{bill.created_by}</p>
                </div>
                {bill.posted_at && (
                  <div className="text-right">
                    <p className="text-sm font-medium">Posted at</p>
                    <p className="text-xs text-muted-foreground">{formatDate(bill.posted_at)}</p>
                  </div>
                )}
              </div>
            </div>

            {/* Actions */}
            <div className="flex flex-wrap gap-2 pt-4 border-t">
              <Button
                variant="outline"
                onClick={() => {
                  if (onReprint && bill.id) onReprint(bill.id);
                }}
                className="flex-1 min-w-[120px]"
              >
                <Printer className="h-4 w-4 mr-2" />
                Reprint
              </Button>

              {bill.customer_phone && (
                <Button
                  variant="outline"
                  onClick={() => {
                    const sent = sendReceiptToWhatsApp(bill, settings?.salon_name);
                    if (!sent) {
                      toast.error('No phone number available for this customer');
                    }
                  }}
                  className="flex-1"
                >
                  <MessageCircle className="h-4 w-4 mr-2" />
                  Send to WhatsApp
                </Button>
              )}

              {bill.status === 'draft' && canAddPayment && (
                showAddPayment ? (
                  <div className="w-full space-y-2 border rounded-lg p-3 bg-gray-50">
                    <p className="text-sm font-medium">
                      Add Payment
                      {bill.rounded_total - (bill.payments?.reduce((s, p) => s + p.amount, 0) ?? 0) - (bill.write_off_amount ?? 0) > 0 && (
                        <span className="text-xs text-muted-foreground ml-2">
                          Remaining: {formatPrice(bill.rounded_total - (bill.payments?.reduce((s, p) => s + p.amount, 0) ?? 0) - (bill.write_off_amount ?? 0))}
                        </span>
                      )}
                    </p>
                    <select
                      className="w-full px-3 py-2 border rounded-md text-sm"
                      value={addPaymentMethod}
                      onChange={(e) => setAddPaymentMethod(e.target.value as any)}
                    >
                      <option value="cash">Cash</option>
                      <option value="upi">UPI</option>
                      <option value="card">Card</option>
                      <option value="other">Other</option>
                    </select>
                    <input
                      type="number"
                      min="0.01"
                      step="0.01"
                      placeholder="Amount in ₹"
                      className="w-full px-3 py-2 border rounded-md text-sm"
                      value={addPaymentAmount}
                      onChange={(e) => setAddPaymentAmount(e.target.value)}
                    />
                    {(addPaymentMethod === 'upi' || addPaymentMethod === 'card') && (
                      <input
                        type="text"
                        placeholder="Reference number (optional)"
                        className="w-full px-3 py-2 border rounded-md text-sm"
                        value={addPaymentRef}
                        onChange={(e) => setAddPaymentRef(e.target.value)}
                      />
                    )}
                    <div className="flex gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        className="flex-1"
                        onClick={() => { setShowAddPayment(false); setAddPaymentAmount(''); setAddPaymentRef(''); }}
                        disabled={isAddingPayment}
                      >
                        Cancel
                      </Button>
                      <Button
                        size="sm"
                        className="flex-1"
                        onClick={handleAddPayment}
                        disabled={isAddingPayment}
                      >
                        {isAddingPayment ? 'Adding…' : 'Confirm'}
                      </Button>
                    </div>
                  </div>
                ) : (
                  <Button
                    variant="outline"
                    onClick={() => {
                      const remaining = (bill.rounded_total - (bill.payments?.reduce((s, p) => s + p.amount, 0) ?? 0) - (bill.write_off_amount ?? 0)) / 100;
                      setAddPaymentAmount(remaining > 0 ? remaining.toFixed(2) : '');
                      setShowAddPayment(true);
                    }}
                    className="flex-1"
                  >
                    <CreditCard className="h-4 w-4 mr-2" />
                    Add Payment
                  </Button>
                )
              )}

              {bill.status === 'draft' && canDiscount && (
                showEditDiscount ? (
                  <div className="w-full space-y-2 border rounded-lg p-3 bg-gray-50">
                    <p className="text-sm font-medium">Edit Discount</p>
                    <input
                      type="number"
                      min="0"
                      step="1"
                      placeholder="Discount in ₹"
                      className="w-full px-3 py-2 border rounded-md text-sm"
                      value={discountInput}
                      onChange={(e) => setDiscountInput(e.target.value)}
                    />
                    <input
                      type="text"
                      placeholder="Reason (optional)"
                      className="w-full px-3 py-2 border rounded-md text-sm"
                      value={discountReason}
                      onChange={(e) => setDiscountReason(e.target.value)}
                    />
                    <div className="flex gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        className="flex-1"
                        onClick={() => { setShowEditDiscount(false); setDiscountInput(''); setDiscountReason(''); }}
                        disabled={isSavingDiscount}
                      >
                        Cancel
                      </Button>
                      <Button
                        size="sm"
                        className="flex-1"
                        onClick={handleSaveDiscount}
                        disabled={isSavingDiscount}
                      >
                        {isSavingDiscount ? 'Saving…' : 'Apply'}
                      </Button>
                    </div>
                  </div>
                ) : (
                  <Button
                    variant="outline"
                    onClick={() => {
                      setDiscountInput(((bill.discount_amount || 0) / 100).toString());
                      setShowEditDiscount(true);
                    }}
                    className="flex-1"
                  >
                    Edit Discount
                  </Button>
                )
              )}

              {bill.status === 'posted' && canAddPayment && (bill.rounded_total - (bill.payments?.reduce((s, p) => s + p.amount, 0) ?? 0) - (bill.write_off_amount ?? 0)) > 0 && (
                showCollectPayment ? (
                  <div className="w-full space-y-2 border rounded-lg p-3 bg-gray-50">
                    <p className="text-sm font-medium">
                      Collect Payment
                      <span className="text-xs text-muted-foreground ml-2">
                        Pending: {formatPrice(bill.rounded_total - (bill.payments?.reduce((s, p) => s + p.amount, 0) ?? 0) - (bill.write_off_amount ?? 0))}
                      </span>
                    </p>
                    <select
                      className="w-full px-3 py-2 border rounded-md text-sm"
                      value={collectMethod}
                      onChange={(e) => setCollectMethod(e.target.value as any)}
                    >
                      <option value="cash">Cash</option>
                      <option value="upi">UPI</option>
                      <option value="card">Card</option>
                      <option value="other">Other</option>
                    </select>
                    <input
                      type="number"
                      min="0.01"
                      step="0.01"
                      placeholder="Amount in ₹"
                      className="w-full px-3 py-2 border rounded-md text-sm"
                      value={collectAmount}
                      onChange={(e) => setCollectAmount(e.target.value)}
                    />
                    {(collectMethod === 'upi' || collectMethod === 'card') && (
                      <input
                        type="text"
                        placeholder="Reference number (optional)"
                        className="w-full px-3 py-2 border rounded-md text-sm"
                        value={collectRef}
                        onChange={(e) => setCollectRef(e.target.value)}
                      />
                    )}
                    <div className="flex gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        className="flex-1"
                        onClick={() => { setShowCollectPayment(false); setCollectAmount(''); setCollectRef(''); }}
                        disabled={isCollecting}
                      >
                        Cancel
                      </Button>
                      <Button
                        size="sm"
                        className="flex-1"
                        onClick={handleCollectPayment}
                        disabled={isCollecting}
                      >
                        {isCollecting ? 'Collecting…' : 'Confirm'}
                      </Button>
                    </div>
                  </div>
                ) : (
                  <Button
                    variant="outline"
                    onClick={() => {
                      const pending = bill.rounded_total - (bill.payments?.reduce((s, p) => s + p.amount, 0) ?? 0) - (bill.write_off_amount ?? 0);
                      setCollectAmount((pending / 100).toFixed(2));
                      setShowCollectPayment(true);
                    }}
                    className="flex-1"
                  >
                    <CreditCard className="h-4 w-4 mr-2" />
                    Collect Payment
                  </Button>
                )
              )}

              {bill.status === 'posted' && isOwner && (bill.rounded_total - (bill.payments?.reduce((s, p) => s + p.amount, 0) ?? 0) - (bill.write_off_amount ?? 0)) > 0 && (
                showWriteOff ? (
                  <div className="w-full space-y-2 border rounded-lg p-3 bg-amber-50 border-amber-200">
                    <p className="text-sm font-medium text-amber-900">
                      Write Off Pending Balance
                      <span className="text-xs text-amber-700 ml-2">
                        Pending: {formatPrice(bill.rounded_total - (bill.payments?.reduce((s, p) => s + p.amount, 0) ?? 0) - (bill.write_off_amount ?? 0))}
                      </span>
                    </p>
                    <input
                      type="number"
                      min="0.01"
                      step="0.01"
                      placeholder="Amount to write off (₹)"
                      className="w-full px-3 py-2 border rounded-md text-sm"
                      value={writeOffAmount}
                      onChange={(e) => setWriteOffAmount(e.target.value)}
                    />
                    <input
                      type="text"
                      placeholder="Reason (required)"
                      className="w-full px-3 py-2 border rounded-md text-sm"
                      value={writeOffReason}
                      onChange={(e) => setWriteOffReason(e.target.value)}
                    />
                    <div className="flex gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        className="flex-1"
                        onClick={() => { setShowWriteOff(false); setWriteOffAmount(''); setWriteOffReason(''); }}
                        disabled={isSavingWriteOff}
                      >
                        Cancel
                      </Button>
                      <Button
                        size="sm"
                        className="flex-1 bg-amber-600 hover:bg-amber-700 text-white"
                        onClick={handleWriteOff}
                        disabled={isSavingWriteOff}
                      >
                        {isSavingWriteOff ? 'Writing off…' : 'Confirm Write-Off'}
                      </Button>
                    </div>
                  </div>
                ) : (
                  <Button
                    variant="outline"
                    onClick={() => {
                      const pending = bill.rounded_total - (bill.payments?.reduce((s, p) => s + p.amount, 0) ?? 0) - (bill.write_off_amount ?? 0);
                      setWriteOffAmount((pending / 100).toFixed(2));
                      setShowWriteOff(true);
                    }}
                    className="flex-1 border-amber-300 text-amber-700 hover:bg-amber-50"
                  >
                    Write Off Pending
                  </Button>
                )
              )}

              {(bill.status === 'draft' || (bill.status === 'posted' && isOwner)) && onVoid && (
                <Button
                  variant="destructive"
                  onClick={() => {
                    if (bill.id) onVoid(bill.id);
                  }}
                  className="flex-1"
                >
                  Void Bill
                </Button>
              )}

              {bill.status === 'posted' && onRefund && (
                <Button
                  variant="destructive"
                  onClick={() => {
                    if (bill.id) onRefund(bill.id);
                    onOpenChange(false);
                  }}
                  className="flex-1"
                >
                  Process Refund
                </Button>
              )}
            </div>
          </div>
        ) : null}
        </DialogBody>
      </DialogContent>

      {/* Edit Payment Dialog */}
      <Dialog open={isEditDialogOpen} onOpenChange={setIsEditDialogOpen}>
        <DialogContent size="md">
          <DialogHeader>
            <DialogTitle>Edit Payment</DialogTitle>
          </DialogHeader>

          {editingPayment && (
            <DialogBody className="space-y-4">
              {/* Payment Method */}
              <div>
                <label className="text-sm font-medium mb-2 block">Payment Method</label>
                <select
                  className="w-full px-3 py-2 border rounded-md"
                  value={editingPayment.payment_method}
                  onChange={(e) =>
                    setEditingPayment({
                      ...editingPayment,
                      payment_method: e.target.value as any,
                    })
                  }
                >
                  <option value="cash">Cash</option>
                  <option value="upi">UPI</option>
                  <option value="card">Card</option>
                  <option value="other">Other</option>
                </select>
              </div>

              {/* Amount */}
              <div>
                <label className="text-sm font-medium mb-2 block">Amount (₹)</label>
                <input
                  type="number"
                  step="0.01"
                  min="0"
                  className="w-full px-3 py-2 border rounded-md"
                  value={editingPayment.amount / 100}
                  onChange={(e) =>
                    setEditingPayment({
                      ...editingPayment,
                      amount: Math.round(parseFloat(e.target.value || '0') * 100),
                    })
                  }
                />
              </div>

              {/* Reference Number */}
              <div>
                <label className="text-sm font-medium mb-2 block">
                  Reference Number (Optional)
                </label>
                <input
                  type="text"
                  className="w-full px-3 py-2 border rounded-md"
                  placeholder="e.g., UPI123456"
                  value={editingPayment.reference_number || ''}
                  onChange={(e) =>
                    setEditingPayment({
                      ...editingPayment,
                      reference_number: e.target.value,
                    })
                  }
                />
              </div>

              {/* Notes */}
              <div>
                <label className="text-sm font-medium mb-2 block">Notes (Optional)</label>
                <textarea
                  className="w-full px-3 py-2 border rounded-md"
                  rows={3}
                  placeholder="Additional notes..."
                  value={editingPayment.notes || ''}
                  onChange={(e) =>
                    setEditingPayment({
                      ...editingPayment,
                      notes: e.target.value,
                    })
                  }
                />
              </div>

              {/* Actions */}
              <div className="flex gap-2 pt-4">
                <Button
                  variant="outline"
                  onClick={() => {
                    setIsEditDialogOpen(false);
                    setEditingPayment(null);
                  }}
                  disabled={isSaving}
                  className="flex-1"
                >
                  Cancel
                </Button>
                <Button
                  onClick={() => handleSavePayment(editingPayment)}
                  disabled={isSaving}
                  className="flex-1"
                >
                  {isSaving ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      Saving...
                    </>
                  ) : (
                    'Save Changes'
                  )}
                </Button>
              </div>
            </DialogBody>
          )}
        </DialogContent>
      </Dialog>
    </Dialog>
  );
}
