'use client';

import { useEffect, useState } from 'react';
import { Loader2, ChevronDown, ChevronRight } from 'lucide-react';
import {
  Dialog,
  DialogBody,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { apiClient } from '@/lib/api-client';
import { toast } from 'sonner';

interface BillItemSummary {
  item_name: string;
  base_price: number;  // paise
  quantity: number;
  line_total: number;  // paise
  staff_name: string | null;
  has_multi_staff: boolean;
}

interface BillSummary {
  id: string;
  invoice_number: string | null;
  posted_at: string | null;
  rounded_total: number;  // paise
  payment_methods: string[];
  items: BillItemSummary[];
}

interface CustomerBillsResponse {
  items: BillSummary[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

interface Props {
  open: boolean;
  onClose: () => void;
  customerId: string;
  customerName: string;
}

export function CustomerHistoryDialog({ open, onClose, customerId, customerName }: Props) {
  const [data, setData] = useState<CustomerBillsResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [page, setPage] = useState(1);
  const [expandedBills, setExpandedBills] = useState<Set<string>>(new Set());

  // Reset and fetch on open / customer change
  useEffect(() => {
    if (!open) return;
    setPage(1);
    setExpandedBills(new Set());
    fetchBills(1);
  }, [open, customerId]); // eslint-disable-line react-hooks/exhaustive-deps

  // Fetch on page change (skip page 1 — handled above)
  useEffect(() => {
    if (!open || page === 1) return;
    fetchBills(page);
  }, [page]); // eslint-disable-line react-hooks/exhaustive-deps

  const fetchBills = async (p: number) => {
    try {
      setIsLoading(true);
      const { data: res } = await apiClient.get(
        `/customers/${customerId}/bills?page=${p}&size=10`
      );
      setData(res);
    } catch {
      toast.error('Failed to load visit history');
    } finally {
      setIsLoading(false);
    }
  };

  const toggleBill = (billId: string) => {
    setExpandedBills((prev) => {
      const next = new Set(prev);
      if (next.has(billId)) next.delete(billId);
      else next.add(billId);
      return next;
    });
  };

  const formatPrice = (paise: number) => `₹${(paise / 100).toFixed(2)}`;

  const formatDate = (dt: string | null) => {
    if (!dt) return '—';
    return new Date(dt).toLocaleDateString('en-IN', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  };

  const formatPaymentMethods = (methods: string[]) =>
    methods.map((m) => m.charAt(0).toUpperCase() + m.slice(1)).join(' + ');

  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
      <DialogContent size="md">
        <DialogHeader>
          <DialogTitle>Visit History — {customerName}</DialogTitle>
          {data && (
            <p className="text-sm text-gray-500">{data.total} visit{data.total !== 1 ? 's' : ''} on record</p>
          )}
        </DialogHeader>

        <DialogBody className="max-h-[60vh] overflow-y-auto pr-1">
          {isLoading && !data ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
            </div>
          ) : data?.items.length === 0 ? (
            <p className="text-sm text-gray-500 py-8 text-center">
              No visits found for this customer.
            </p>
          ) : (
            <div className="space-y-2">
              {data?.items.map((bill) => {
                const expanded = expandedBills.has(bill.id);
                return (
                  <div key={bill.id} className="border rounded-lg overflow-hidden">
                    {/* Bill header row — clickable to expand */}
                    <button
                      className="w-full flex items-center justify-between px-4 py-3 hover:bg-gray-50 transition-colors text-left"
                      onClick={() => toggleBill(bill.id)}
                    >
                      <div className="flex items-center gap-2">
                        {expanded ? (
                          <ChevronDown className="h-4 w-4 text-gray-400 shrink-0" />
                        ) : (
                          <ChevronRight className="h-4 w-4 text-gray-400 shrink-0" />
                        )}
                        <div>
                          <span className="font-medium text-sm text-gray-900">
                            {formatDate(bill.posted_at)}
                          </span>
                          {bill.invoice_number && (
                            <span className="text-xs text-gray-400 ml-2">
                              {bill.invoice_number}
                            </span>
                          )}
                        </div>
                      </div>
                      <div className="flex items-center gap-2 ml-2 shrink-0">
                        {bill.payment_methods.length > 0 && (
                          <Badge variant="outline" className="text-xs font-normal hidden sm:inline-flex">
                            {formatPaymentMethods(bill.payment_methods)}
                          </Badge>
                        )}
                        <span className="font-semibold text-sm">
                          {formatPrice(bill.rounded_total)}
                        </span>
                      </div>
                    </button>

                    {/* Expanded items list */}
                    {expanded && (
                      <div className="border-t divide-y bg-gray-50">
                        {bill.items.map((item, idx) => (
                          <div
                            key={idx}
                            className="px-4 py-2 flex items-center justify-between text-sm"
                          >
                            <div>
                              <span className="text-gray-900">{item.item_name}</span>
                              {item.quantity > 1 && (
                                <span className="text-gray-400 ml-1">×{item.quantity}</span>
                              )}
                              {item.staff_name && (
                                <span className="block text-xs text-gray-400 mt-0.5">
                                  by {item.staff_name}
                                </span>
                              )}
                            </div>
                            <span className="text-gray-700 ml-4 shrink-0">
                              {formatPrice(item.line_total)}
                            </span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                );
              })}

              {/* Pagination */}
              {data && data.pages > 1 && (
                <div className="flex items-center justify-between pt-2">
                  <span className="text-xs text-gray-500">{data.total} visits total</span>
                  <div className="flex items-center gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setPage((p) => p - 1)}
                      disabled={page === 1 || isLoading}
                    >
                      Previous
                    </Button>
                    <span className="text-xs text-gray-500 px-1">
                      {page} / {data.pages}
                    </span>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setPage((p) => p + 1)}
                      disabled={page === data.pages || isLoading}
                    >
                      Next
                    </Button>
                  </div>
                </div>
              )}
            </div>
          )}
        </DialogBody>
      </DialogContent>
    </Dialog>
  );
}
