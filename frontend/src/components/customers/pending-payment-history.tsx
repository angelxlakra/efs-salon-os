'use client';

import { useState, useEffect } from 'react';
import { Loader2, ArrowDownCircle } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Badge } from '@/components/ui/badge';
import { apiClient } from '@/lib/api-client';
import { toast } from 'sonner';

interface PendingPaymentCollection {
  id: string;
  customer_id: string;
  amount: number; // in paise
  payment_method: string;
  reference_number: string | null;
  notes: string | null;
  bill_id: string | null;
  collected_by: string;
  collected_at: string;
  previous_balance: number; // in paise
  new_balance: number; // in paise
}

interface PendingPaymentHistoryProps {
  open: boolean;
  onClose: () => void;
  customerId: string;
  customerName: string;
}

export function PendingPaymentHistory({
  open,
  onClose,
  customerId,
  customerName,
}: PendingPaymentHistoryProps) {
  const [collections, setCollections] = useState<PendingPaymentCollection[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    if (open && customerId) {
      fetchHistory();
    }
  }, [open, customerId]);

  const fetchHistory = async () => {
    try {
      setIsLoading(true);
      const { data } = await apiClient.get(`/pos/pending-payments/customer/${customerId}`);
      setCollections(data || []);
    } catch (error: any) {
      toast.error('Failed to load payment history');
      console.error(error);
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
    return new Date(dateString).toLocaleDateString('en-IN', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const getPaymentMethodColor = (method: string) => {
    switch (method) {
      case 'cash':
        return 'bg-green-100 text-green-800';
      case 'upi':
        return 'bg-purple-100 text-purple-800';
      case 'card':
        return 'bg-blue-100 text-blue-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-h-[80vh] overflow-y-auto" style={{ maxWidth: 'min(42rem, calc(100vw - 2rem))' }}>
        <DialogHeader>
          <DialogTitle>Pending Payment Collection History</DialogTitle>
          <p className="text-sm text-muted-foreground">{customerName}</p>
        </DialogHeader>

        <div className="space-y-4 max-h-[500px] overflow-y-auto">
          {isLoading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
            </div>
          ) : collections.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              <ArrowDownCircle className="h-12 w-12 mx-auto mb-2 text-gray-300" />
              <p>No payment collection history</p>
            </div>
          ) : (
            <div className="space-y-3">
              {collections.map((collection) => (
                <div
                  key={collection.id}
                  className="border rounded-lg p-4 hover:bg-gray-50 transition-colors"
                >
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="font-semibold text-green-600">
                          {formatPrice(collection.amount)}
                        </span>
                        <Badge
                          variant="secondary"
                          className={getPaymentMethodColor(collection.payment_method)}
                        >
                          {collection.payment_method.toUpperCase()}
                        </Badge>
                      </div>
                      <p className="text-sm text-gray-600">
                        {formatDate(collection.collected_at)}
                      </p>
                    </div>
                    <div className="text-right">
                      <div className="text-xs text-gray-500">Balance</div>
                      <div className="text-sm">
                        <span className="text-red-600">{formatPrice(collection.previous_balance)}</span>
                        {' → '}
                        <span className={collection.new_balance > 0 ? 'text-red-600' : 'text-green-600'}>
                          {formatPrice(collection.new_balance)}
                        </span>
                      </div>
                    </div>
                  </div>

                  {collection.bill_id && (
                    <div className="text-xs text-gray-500 mb-1">
                      Via overpayment on bill
                    </div>
                  )}

                  {collection.reference_number && (
                    <div className="text-xs text-gray-500 mb-1">
                      Ref: {collection.reference_number}
                    </div>
                  )}

                  {collection.notes && (
                    <div className="text-sm text-gray-600 mt-2 p-2 bg-gray-50 rounded">
                      {collection.notes}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
