'use client';

import { useState, useEffect } from 'react';
import { Dialog, DialogBody, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { apiClient } from '@/lib/api-client';
import { toast } from 'sonner';

interface SKU {
  id: string;
  name: string;
  sku_code: string;
  current_stock: number;
  avg_cost_per_unit: number;
}

interface AvailableStore {
  id: string;
  name: string;
}

interface TransferDialogProps {
  sku: SKU;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess: () => void;
}

export function TransferDialog({ sku, open, onOpenChange, onSuccess }: TransferDialogProps) {
  const [stores, setStores] = useState<AvailableStore[]>([]);
  const [loadingStores, setLoadingStores] = useState(false);
  const [destinationStoreId, setDestinationStoreId] = useState('');
  const [quantity, setQuantity] = useState('');
  const [notes, setNotes] = useState('');
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (open) {
      loadStores();
      setDestinationStoreId('');
      setQuantity('');
      setNotes('');
    }
  }, [open]);

  const loadStores = async () => {
    setLoadingStores(true);
    try {
      const response = await apiClient.get('/inventory/transfers/available-stores');
      setStores(response.data || []);
    } catch {
      toast.error('Failed to load destination stores');
      setStores([]);
    } finally {
      setLoadingStores(false);
    }
  };

  const unitCostRupees = (sku.avg_cost_per_unit / 100).toFixed(2);
  const qty = parseInt(quantity) || 0;
  const estimatedTotal = qty * sku.avg_cost_per_unit;

  const handleSubmit = async () => {
    if (!destinationStoreId) {
      toast.error('Please select a destination store');
      return;
    }
    if (!quantity || qty <= 0) {
      toast.error('Please enter a valid quantity');
      return;
    }
    if (qty > sku.current_stock) {
      toast.error(`Quantity cannot exceed current stock (${sku.current_stock})`);
      return;
    }

    const selectedStore = stores.find((s) => s.id === destinationStoreId);
    if (!selectedStore) return;

    setSubmitting(true);
    try {
      await apiClient.post('/inventory/transfers', {
        sku_id: sku.id,
        destination_store_id: destinationStoreId,
        destination_store_name: selectedStore.name,
        quantity: qty,
        notes: notes.trim() || undefined,
      });
      toast.success('Transfer initiated successfully');
      onOpenChange(false);
      onSuccess();
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to initiate transfer');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent size="md">
        <DialogHeader>
          <DialogTitle>Transfer Stock to Another Store</DialogTitle>
        </DialogHeader>

        <DialogBody className="space-y-4">
          <div>
            <div className="text-sm font-medium">{sku.name}</div>
            <div className="text-xs font-mono text-muted-foreground">{sku.sku_code}</div>
            <div className="text-sm text-muted-foreground mt-1">
              Available stock: <span className="font-medium">{sku.current_stock}</span>
            </div>
          </div>

          <div>
            <Label htmlFor="destination-store">Destination Store *</Label>
            <Select
              value={destinationStoreId}
              onValueChange={setDestinationStoreId}
              disabled={loadingStores}
            >
              <SelectTrigger id="destination-store">
                <SelectValue placeholder={loadingStores ? 'Loading...' : 'Select store'} />
              </SelectTrigger>
              <SelectContent>
                {stores.map((store) => (
                  <SelectItem key={store.id} value={store.id}>
                    {store.name}
                  </SelectItem>
                ))}
                {stores.length === 0 && !loadingStores && (
                  <SelectItem value="_none" disabled>
                    No stores configured
                  </SelectItem>
                )}
              </SelectContent>
            </Select>
          </div>

          <div>
            <Label htmlFor="transfer-quantity">Quantity * (max {sku.current_stock})</Label>
            <Input
              id="transfer-quantity"
              type="number"
              min="1"
              max={sku.current_stock}
              step="1"
              value={quantity}
              onChange={(e) => setQuantity(e.target.value)}
              placeholder="Enter quantity"
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label>Unit Cost (read-only)</Label>
              <Input value={`₹${unitCostRupees}`} readOnly className="bg-muted" />
            </div>
            <div>
              <Label>Estimated Total</Label>
              <Input
                value={qty > 0 ? `₹${(estimatedTotal / 100).toFixed(2)}` : '—'}
                readOnly
                className="bg-muted"
              />
            </div>
          </div>

          <div>
            <Label htmlFor="transfer-notes">Notes (optional)</Label>
            <Textarea
              id="transfer-notes"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Reason for transfer..."
              rows={2}
            />
          </div>
        </DialogBody>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={submitting}>
            Cancel
          </Button>
          <Button onClick={handleSubmit} disabled={submitting}>
            {submitting ? 'Initiating...' : 'Initiate Transfer'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
