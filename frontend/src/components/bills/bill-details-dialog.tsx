'use client';

import { useEffect, useState } from 'react';
import { Printer, User, FileText } from 'lucide-react';
import {
  Dialog,
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

interface BillItem {
  id: string;
  service_id: string;
  item_name: string;
  base_price: number; // paise
  quantity: number;
  line_total: number; // paise
  staff_id: string | null;
  notes: string | null;
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
  items: BillItem[];
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
  const { hasGST, fetchSettings, settings } = useSettingsStore();

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


  if (!open) return null;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[600px] lg:max-w-[800px] max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Bill Details</DialogTitle>
        </DialogHeader>

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
              <div className="flex items-center gap-2 mb-2">
                <User className="h-4 w-4 text-gray-500" />
                <span className="font-semibold text-sm">Customer</span>
              </div>
              <p className="text-base">{bill.customer_name || 'Walk-in Customer'}</p>
            </div>

            {/* Services */}
            <div>
              <h4 className="font-semibold mb-3 flex items-center gap-2">
                <FileText className="h-4 w-4" />
                Services
              </h4>
              <div className="border rounded-lg overflow-hidden">
                <table className="w-full">
                  <thead className="bg-gray-50 border-b">
                    <tr>
                      <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
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
            <div className="flex gap-2 pt-4 border-t">
              <Button
                variant="outline"
                onClick={() => {
                  if (onReprint && bill.id) onReprint(bill.id);
                }}
                className="flex-1"
              >
                <Printer className="h-4 w-4 mr-2" />
                Reprint Receipt
              </Button>

              {bill.status === 'draft' && onVoid && (
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
      </DialogContent>
    </Dialog>
  );
}
