'use client';

import { useEffect, useState } from 'react';
import { Loader2, Users } from 'lucide-react';
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

interface ServiceHistoryItem {
  bill_id: string;
  invoice_number: string | null;
  posted_at: string;
  customer_name: string;
  staff_name: string | null;
  has_multi_staff: boolean;
  price_paid: number;  // paise
}

interface ServiceHistoryResponse {
  service_id: string;
  service_name: string;
  items: ServiceHistoryItem[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

interface Props {
  open: boolean;
  onClose: () => void;
  serviceId: string;
  serviceName: string;
}

export function ServiceHistoryDialog({ open, onClose, serviceId, serviceName }: Props) {
  const [data, setData] = useState<ServiceHistoryResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [page, setPage] = useState(1);

  // Reset and fetch on open / service change
  useEffect(() => {
    if (!open) return;
    setPage(1);
    fetchHistory(1);
  }, [open, serviceId]); // eslint-disable-line react-hooks/exhaustive-deps

  // Fetch on page change (skip page 1 — handled above)
  useEffect(() => {
    if (!open || page === 1) return;
    fetchHistory(page);
  }, [page]); // eslint-disable-line react-hooks/exhaustive-deps

  const fetchHistory = async (p: number) => {
    try {
      setIsLoading(true);
      const { data: res } = await apiClient.get(
        `/catalog/services/${serviceId}/history?page=${p}&size=20`
      );
      setData(res);
    } catch {
      toast.error('Failed to load service history');
    } finally {
      setIsLoading(false);
    }
  };

  const formatPrice = (paise: number) => `₹${(paise / 100).toFixed(2)}`;

  const formatDate = (dt: string) =>
    new Date(dt).toLocaleDateString('en-IN', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });

  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
      <DialogContent size="lg">
        <DialogHeader>
          <DialogTitle>Service History — {serviceName}</DialogTitle>
          {data && (
            <p className="text-sm text-text-muted">
              Performed {data.total} time{data.total !== 1 ? 's' : ''}
            </p>
          )}
        </DialogHeader>

        <DialogBody className="max-h-[60vh] overflow-y-auto">
          {isLoading && !data ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-6 w-6 animate-spin text-text-disabled" />
            </div>
          ) : data?.items.length === 0 ? (
            <p className="text-sm text-text-muted py-8 text-center">
              This service hasn't been performed yet.
            </p>
          ) : (
            <>
              <table className="w-full text-sm">
                <thead className="sticky top-0 bg-white border-b">
                  <tr>
                    <th className="px-3 py-2 text-left text-xs font-medium text-text-muted uppercase tracking-wider">
                      Date
                    </th>
                    <th className="px-3 py-2 text-left text-xs font-medium text-text-muted uppercase tracking-wider">
                      Customer
                    </th>
                    <th className="px-3 py-2 text-left text-xs font-medium text-text-muted uppercase tracking-wider">
                      Staff
                    </th>
                    <th className="px-3 py-2 text-right text-xs font-medium text-text-muted uppercase tracking-wider">
                      Price
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {data?.items.map((item, idx) => (
                    <tr key={`${item.bill_id}-${idx}`} className="hover:bg-surface-page">
                      <td className="px-3 py-2 whitespace-nowrap">
                        <span className="text-text-secondary">{formatDate(item.posted_at)}</span>
                        {item.invoice_number && (
                          <span className="block text-xs text-text-disabled">
                            {item.invoice_number}
                          </span>
                        )}
                      </td>
                      <td className="px-3 py-2 text-text-primary">{item.customer_name}</td>
                      <td className="px-3 py-2">
                        {item.has_multi_staff ? (
                          <Badge variant="secondary" className="text-xs">
                            <Users className="h-3 w-3 mr-1" />
                            Multiple
                          </Badge>
                        ) : item.staff_name ? (
                          <span className="text-text-secondary">{item.staff_name}</span>
                        ) : (
                          <span className="text-text-disabled">—</span>
                        )}
                      </td>
                      <td className="px-3 py-2 text-right font-medium text-text-primary">
                        {formatPrice(item.price_paid)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>

              {/* Pagination */}
              {data && data.pages > 1 && (
                <div className="flex items-center justify-between px-3 py-3 border-t mt-2">
                  <span className="text-xs text-text-muted">{data.total} records</span>
                  <div className="flex items-center gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setPage((p) => p - 1)}
                      disabled={page === 1 || isLoading}
                    >
                      Previous
                    </Button>
                    <span className="text-xs text-text-muted px-1">
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
            </>
          )}
        </DialogBody>
      </DialogContent>
    </Dialog>
  );
}
