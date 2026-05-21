'use client';

import { useState, useEffect, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ArrowRightLeft } from 'lucide-react';
import { apiClient } from '@/lib/api-client';
import { toast } from 'sonner';

interface Transfer {
  id: string;
  direction: 'IN' | 'OUT';
  other_store_name: string;
  product_name: string;
  product_sku?: string;
  quantity: number;
  unit_cost_paise: number;
  total_cost_paise: number;
  status: string;
  initiated_at: string;
  applied_at?: string | null;
  cancelled_at?: string | null;
  notes?: string | null;
}

interface TransferListResponse {
  transfers: Transfer[];
  total: number;
  page: number;
  size: number;
}

type DirectionFilter = 'ALL' | 'IN' | 'OUT';

const formatCurrency = (paise: number) =>
  `₹${(paise / 100).toLocaleString('en-IN', { minimumFractionDigits: 2 })}`;

const statusVariant: Record<string, 'default' | 'destructive' | 'secondary' | 'outline'> = {
  PENDING: 'default',
  APPLIED: 'secondary',
  FAILED: 'destructive',
  CANCELLED: 'outline',
};

const statusLabel: Record<string, string> = {
  PENDING: 'Pending',
  APPLIED: 'Applied',
  FAILED: 'Failed',
  CANCELLED: 'Cancelled',
};

export default function TransfersPage() {
  const [transfers, setTransfers] = useState<Transfer[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<DirectionFilter>('ALL');
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const SIZE = 20;

  const loadTransfers = useCallback(async () => {
    setLoading(true);
    try {
      const params: Record<string, string | number> = { page, size: SIZE };
      if (filter !== 'ALL') params.direction = filter;
      const response = await apiClient.get<TransferListResponse>('/inventory/transfers', { params });
      setTransfers(response.data.transfers);
      setTotal(response.data.total);
    } catch {
      toast.error('Failed to load transfers');
    } finally {
      setLoading(false);
    }
  }, [page, filter]);

  useEffect(() => {
    loadTransfers();
  }, [loadTransfers]);

  const handleCancel = async (id: string) => {
    try {
      await apiClient.patch(`/inventory/transfers/${id}/cancel`);
      toast.success('Transfer cancelled');
      loadTransfers();
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to cancel transfer');
    }
  };

  const handleFilterChange = (f: DirectionFilter) => {
    setFilter(f);
    setPage(1);
  };

  const totalPages = Math.ceil(total / SIZE);

  return (
    <div className="p-4 md:p-6 pt-6 md:pt-8 space-y-4">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
        <div>
          <h1 className="text-xl font-semibold">Inventory Transfers</h1>
          <p className="text-sm text-muted-foreground">Cross-store stock movements</p>
        </div>
      </div>

      {/* Direction filter */}
      <div className="flex gap-2">
        {(['ALL', 'IN', 'OUT'] as DirectionFilter[]).map((f) => (
          <Button
            key={f}
            variant={filter === f ? 'default' : 'outline'}
            size="sm"
            onClick={() => handleFilterChange(f)}
          >
            {f === 'IN' ? '← Incoming' : f === 'OUT' ? '→ Outgoing' : 'All'}
          </Button>
        ))}
      </div>

      {loading ? (
        <div className="text-center py-12 text-muted-foreground">Loading transfers...</div>
      ) : transfers.length === 0 ? (
        <div className="text-center py-12 text-muted-foreground">
          <ArrowRightLeft className="h-12 w-12 mx-auto mb-4 opacity-20" />
          <p>No transfers found</p>
        </div>
      ) : (
        <>
          {/* Mobile cards */}
          <div className="md:hidden space-y-3">
            {transfers.map((t) => (
              <Card key={t.id}>
                <CardContent className="p-4 space-y-2">
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0 flex-1">
                      <div className="font-medium truncate">{t.product_name}</div>
                      {t.product_sku && (
                        <div className="text-xs font-mono text-muted-foreground">{t.product_sku}</div>
                      )}
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      <Badge variant={t.direction === 'IN' ? 'default' : 'outline'}>
                        {t.direction === 'IN' ? '← IN' : '→ OUT'}
                      </Badge>
                      <Badge variant={statusVariant[t.status] ?? 'outline'}>
                        {statusLabel[t.status] ?? t.status}
                      </Badge>
                    </div>
                  </div>
                  <div className="text-sm text-muted-foreground">{t.other_store_name}</div>
                  <div className="grid grid-cols-2 gap-2 text-sm pt-1 border-t">
                    <div>
                      <span className="text-muted-foreground text-xs">Qty: </span>
                      <span>{t.quantity}</span>
                    </div>
                    <div>
                      <span className="text-muted-foreground text-xs">Cost: </span>
                      <span>{formatCurrency(t.total_cost_paise)}</span>
                    </div>
                  </div>
                  <div className="text-xs text-muted-foreground">
                    {new Date(t.initiated_at).toLocaleString('en-IN')}
                  </div>
                  {t.status === 'PENDING' && t.direction === 'OUT' && (
                    <Button
                      variant="outline"
                      size="sm"
                      className="w-full"
                      onClick={() => handleCancel(t.id)}
                    >
                      Cancel Transfer
                    </Button>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>

          {/* Desktop table */}
          <Card className="hidden md:block">
            <CardHeader>
              <CardTitle>Transfer History</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b">
                      <th className="text-left py-3 px-4">Date</th>
                      <th className="text-center py-3 px-4">Direction</th>
                      <th className="text-left py-3 px-4">Product</th>
                      <th className="text-left py-3 px-4">Store</th>
                      <th className="text-right py-3 px-4">Qty</th>
                      <th className="text-right py-3 px-4">Cost</th>
                      <th className="text-center py-3 px-4">Status</th>
                      <th className="text-center py-3 px-4">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {transfers.map((t) => (
                      <tr key={t.id} className="border-b hover:bg-surface-row-hover">
                        <td className="py-3 px-4 text-sm text-muted-foreground">
                          {new Date(t.initiated_at).toLocaleDateString('en-IN')}
                        </td>
                        <td className="py-3 px-4 text-center">
                          <Badge
                            variant={t.direction === 'IN' ? 'default' : 'outline'}
                            className={
                              t.direction === 'IN'
                                ? 'bg-green-100 text-green-800 border-green-200'
                                : 'bg-orange-100 text-orange-800 border-orange-200'
                            }
                          >
                            {t.direction}
                          </Badge>
                        </td>
                        <td className="py-3 px-4">
                          <div>{t.product_name}</div>
                          {t.product_sku && (
                            <div className="text-xs font-mono text-muted-foreground">{t.product_sku}</div>
                          )}
                        </td>
                        <td className="py-3 px-4 text-sm">{t.other_store_name}</td>
                        <td className="py-3 px-4 text-right">{t.quantity}</td>
                        <td className="py-3 px-4 text-right">{formatCurrency(t.total_cost_paise)}</td>
                        <td className="py-3 px-4 text-center">
                          <Badge variant={statusVariant[t.status] ?? 'outline'}>
                            {statusLabel[t.status] ?? t.status}
                          </Badge>
                        </td>
                        <td className="py-3 px-4 text-center">
                          {t.status === 'PENDING' && t.direction === 'OUT' && (
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleCancel(t.id)}
                            >
                              Cancel
                            </Button>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Pagination */}
              {totalPages > 1 && (
                <div className="flex justify-between items-center mt-4 pt-4 border-t text-sm">
                  <span className="text-muted-foreground">
                    {total} transfer{total !== 1 ? 's' : ''}
                  </span>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={page <= 1}
                      onClick={() => setPage((p) => p - 1)}
                    >
                      Previous
                    </Button>
                    <span className="flex items-center px-2">
                      {page} / {totalPages}
                    </span>
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={page >= totalPages}
                      onClick={() => setPage((p) => p + 1)}
                    >
                      Next
                    </Button>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
