'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Checkbox } from '@/components/ui/checkbox';
import { Package, Search, Edit, Plus, Minus, TrendingUp, CheckCircle, XCircle, RefreshCw, Camera, ArrowRightLeft } from 'lucide-react';
import { BarcodeScanner } from '@/components/barcode-scanner';
import { TransferDialog } from '@/components/inventory/transfer-dialog';
import { Dialog, DialogBody, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Label } from '@/components/ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { apiClient } from '@/lib/api-client';
import { toast } from 'sonner';
import { useAuthStore } from '@/stores/auth-store';

interface SKU {
  id: string;
  sku_code: string;
  name: string;
  barcode?: string;
  category_name?: string;
  current_stock: number;
  uom: string;
  avg_cost_per_unit: number;
  is_sellable: boolean;
  retail_price?: number;
  retail_markup_percent?: number;
  brand_name?: string;
  volume?: string;
}

interface ChangeRequest {
  id: string;
  sku_id: string;
  sku_code?: string;
  sku_name?: string;
  change_type: 'receive' | 'adjust' | 'consume';
  quantity: number;
  unit_cost?: number;
  supplier_invoice_number?: string;
  supplier_discount_percent?: number;
  supplier_discount_fixed?: number;
  reason_code: string;
  notes?: string;
  status: 'pending' | 'approved' | 'rejected';
  requested_by: string;
  requested_at: string;
  reviewed_by?: string;
  reviewed_at?: string;
  review_notes?: string;
}

export default function InventoryPage() {
  const { user } = useAuthStore();
  const [skus, setSkus] = useState<SKU[]>([]);
  const [filteredSkus, setFilteredSkus] = useState<SKU[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [editingSku, setEditingSku] = useState<SKU | null>(null);
  const [isDialogOpen, setIsDialogOpen] = useState(false);

  // Form state for edit dialog
  const [editBarcode, setEditBarcode] = useState('');
  const [isSellable, setIsSellable] = useState(false);
  const [retailPrice, setRetailPrice] = useState('');
  const [retailMarkup, setRetailMarkup] = useState('');

  // Stock adjustment state
  const [stockDialogOpen, setStockDialogOpen] = useState(false);
  const [adjustingSku, setAdjustingSku] = useState<SKU | null>(null);
  const [adjustmentType, setAdjustmentType] = useState<'receive' | 'adjust' | 'consume'>('receive');
  const [adjustmentQty, setAdjustmentQty] = useState('');
  const [unitCost, setUnitCost] = useState('');
  const [reasonCode, setReasonCode] = useState('');
  const [adjustmentNotes, setAdjustmentNotes] = useState('');

  // Supplier tracking (for receive type)
  const [supplierInvoiceNumber, setSupplierInvoiceNumber] = useState('');
  const [supplierDiscountPercent, setSupplierDiscountPercent] = useState('');
  const [supplierDiscountFixed, setSupplierDiscountFixed] = useState('');

  // Change requests state
  const [changeRequests, setChangeRequests] = useState<ChangeRequest[]>([]);
  const [loadingRequests, setLoadingRequests] = useState(false);

  // Sync from purchases state
  const [syncing, setSyncing] = useState(false);

  // Barcode scanner state
  const [showBarcodeScanner, setShowBarcodeScanner] = useState(false);

  // Transfer state
  const [transferDialogOpen, setTransferDialogOpen] = useState(false);
  const [transferingSku, setTransferingSku] = useState<SKU | null>(null);

  useEffect(() => {
    loadSkus();
    loadChangeRequests();
  }, []);

  useEffect(() => {
    filterSkus();
  }, [searchTerm, skus]);

  const loadSkus = async () => {
    setLoading(true);
    try {
      const response = await apiClient.get('/inventory/skus', {
        params: { size: 100 } // Get SKUs with pagination limit
      });
      setSkus(response.data.items || []);
      setFilteredSkus(response.data.items || []);
    } catch (error) {
      console.error('Failed to load SKUs:', error);
      toast.error('Failed to load inventory');
    } finally {
      setLoading(false);
    }
  };

  const filterSkus = () => {
    if (!searchTerm) {
      setFilteredSkus(skus);
      return;
    }

    const term = searchTerm.toLowerCase();
    const filtered = skus.filter(
      (sku) =>
        sku.name.toLowerCase().includes(term) ||
        sku.sku_code.toLowerCase().includes(term) ||
        sku.category_name?.toLowerCase().includes(term)
    );
    setFilteredSkus(filtered);
  };

  const handleEdit = (sku: SKU) => {
    setEditingSku(sku);
    setEditBarcode(sku.barcode || '');
    setIsSellable(sku.is_sellable);
    setRetailPrice(sku.retail_price ? (sku.retail_price / 100).toFixed(2) : '');
    setRetailMarkup(sku.retail_markup_percent?.toString() || '');
    setIsDialogOpen(true);
  };

  const handleSave = async () => {
    if (!editingSku) return;

    try {
      const updateData: Record<string, string | number | boolean | null> = {
        is_sellable: isSellable,
        barcode: editBarcode.trim() || null,
      };

      if (isSellable) {
        if (!retailPrice || parseFloat(retailPrice) <= 0) {
          toast.error('Please enter a valid retail price');
          return;
        }
        updateData.retail_price = Math.round(parseFloat(retailPrice) * 100);

        if (retailMarkup) {
          updateData.retail_markup_percent = parseFloat(retailMarkup);
        }
      }

      await apiClient.patch(`/inventory/skus/${editingSku.id}`, updateData);

      toast.success('SKU updated successfully');
      setIsDialogOpen(false);
      loadSkus(); // Reload data
    } catch (error: unknown) {
      console.error('Failed to update SKU:', error);
      const detail = error instanceof Error ? error.message : 'Failed to update SKU';
      toast.error(detail);
    }
  };

  const formatCurrency = (paise: number) => {
    return `₹${(paise / 100).toLocaleString('en-IN', { minimumFractionDigits: 2 })}`;
  };

  const calculateMarkup = () => {
    if (!editingSku || !retailPrice) return '';
    const retail = parseFloat(retailPrice) * 100; // Convert to paise
    const cost = editingSku.avg_cost_per_unit;
    if (cost === 0) return '0.00';
    const markup = ((retail - cost) / cost) * 100;
    return markup.toFixed(2);
  };

  const loadChangeRequests = async () => {
    setLoadingRequests(true);
    try {
      const response = await apiClient.get('/inventory/change-requests', {
        params: { status: 'pending' }
      });
      setChangeRequests(response.data || []);
    } catch (error) {
      console.error('Failed to load change requests:', error);
    } finally {
      setLoadingRequests(false);
    }
  };

  const handleAdjustStock = (sku: SKU) => {
    setAdjustingSku(sku);
    setAdjustmentType('receive');
    setAdjustmentQty('');
    setUnitCost('');
    setReasonCode('');
    setAdjustmentNotes('');
    // Reset supplier fields
    setSupplierInvoiceNumber('');
    setSupplierDiscountPercent('');
    setSupplierDiscountFixed('');
    setStockDialogOpen(true);
  };

  const handleCreateAdjustment = async () => {
    if (!adjustingSku) return;

    // Validation
    if (!adjustmentQty || parseFloat(adjustmentQty) <= 0) {
      toast.error('Please enter a valid quantity');
      return;
    }

    if (adjustmentType === 'receive' && (!unitCost || parseFloat(unitCost) <= 0)) {
      toast.error('Unit cost is required for receiving stock');
      return;
    }

    if (!reasonCode) {
      toast.error('Please select a reason');
      return;
    }

    try {
      const payload: Record<string, string | number | undefined> = {
        sku_id: adjustingSku.id,
        change_type: adjustmentType,
        quantity: parseFloat(adjustmentQty),
        reason_code: reasonCode,
        notes: adjustmentNotes || undefined,
      };

      if (adjustmentType === 'receive') {
        payload.unit_cost = Math.round(parseFloat(unitCost) * 100); // Convert to paise

        // Add supplier tracking fields if provided
        if (supplierInvoiceNumber) {
          payload.supplier_invoice_number = supplierInvoiceNumber;
        }
        if (supplierDiscountPercent && parseFloat(supplierDiscountPercent) > 0) {
          payload.supplier_discount_percent = parseFloat(supplierDiscountPercent);
        }
        if (supplierDiscountFixed && parseFloat(supplierDiscountFixed) > 0) {
          payload.supplier_discount_fixed = Math.round(parseFloat(supplierDiscountFixed) * 100); // Convert to paise
        }
      }

      await apiClient.post('/inventory/change-requests', payload);

      toast.success('Stock adjustment request created successfully');
      setStockDialogOpen(false);

      // Reset form fields
      setAdjustmentQty('');
      setUnitCost('');
      setReasonCode('');
      setAdjustmentNotes('');
      setSupplierInvoiceNumber('');
      setSupplierDiscountPercent('');
      setSupplierDiscountFixed('');

      loadChangeRequests();
    } catch (error: unknown) {
      console.error('Failed to create adjustment:', error);
      const detail = error instanceof Error ? error.message : 'Failed to create adjustment request';
      toast.error(detail);
    }
  };

  const handleApproveRequest = async (requestId: string) => {
    try {
      await apiClient.post(`/inventory/change-requests/${requestId}/approve`);
      toast.success('Change request approved');
      loadChangeRequests();
      loadSkus(); // Reload SKUs to reflect stock changes
    } catch (error: unknown) {
      console.error('Failed to approve request:', error);
      const detail = error instanceof Error ? error.message : 'Failed to approve request';
      toast.error(detail);
    }
  };

  const handleRejectRequest = async (requestId: string) => {
    try {
      await apiClient.post(`/inventory/change-requests/${requestId}/reject`);
      toast.success('Change request rejected');
      loadChangeRequests();
    } catch (error: unknown) {
      console.error('Failed to reject request:', error);
      const detail = error instanceof Error ? error.message : 'Failed to reject request';
      toast.error(detail);
    }
  };

  const handleTransfer = (sku: SKU) => {
    setTransferingSku(sku);
    setTransferDialogOpen(true);
  };

  const handleSyncFromPurchases = async () => {
    setSyncing(true);
    try {
      const response = await apiClient.post('/purchases/fix-missing-skus');
      const data = response.data;
      if (data.fixed > 0) {
        toast.success(`Synced ${data.fixed} items from purchases to inventory`);
        loadSkus();
      } else {
        toast.info('All purchase items are already synced to inventory');
      }
    } catch (error: unknown) {
      console.error('Failed to sync from purchases:', error);
      const detail = error instanceof Error ? error.message : 'Failed to sync from purchases';
      toast.error(detail);
    } finally {
      setSyncing(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-text-secondary">Loading inventory...</div>
      </div>
    );
  }

  const isOwner = user?.role === 'owner';

  return (
    <div className="p-4 md:p-6 space-y-4 md:space-y-6">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
        <div className="min-w-0">
          <h1 className="text-xl md:text-2xl font-bold">Inventory Management</h1>
          <p className="text-sm text-text-secondary">Manage SKUs, retail settings, and stock adjustments</p>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={handleSyncFromPurchases}
          disabled={syncing}
          className="shrink-0"
        >
          <RefreshCw className={`mr-2 h-4 w-4 ${syncing ? 'animate-spin' : ''}`} />
          {syncing ? 'Syncing...' : 'Sync from Purchases'}
        </Button>
      </div>

      <Tabs defaultValue="skus" className="space-y-4">
        <TabsList>
          <TabsTrigger value="skus">SKU List</TabsTrigger>
          <TabsTrigger value="adjustments">
            Stock Adjustments
            {changeRequests.length > 0 && (
              <Badge variant="destructive" className="ml-2">{changeRequests.length}</Badge>
            )}
          </TabsTrigger>
        </TabsList>

        <TabsContent value="skus" className="space-y-4">
          {/* Search */}
          <div className="flex gap-4">
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-text-secondary" />
              <Input
                placeholder="Search SKUs..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-10"
              />
            </div>
          </div>

      {/* SKU List - Mobile Cards */}
      <div className="md:hidden space-y-2">
        {filteredSkus.map((sku) => {
          const isLowStock = sku.current_stock <= (5);
          return (
            <div key={sku.id} className="bg-surface-card border border-border-subtle rounded-lg p-4 space-y-2">
              {/* Row 1: SKU code + category chip */}
              <div className="flex items-center justify-between gap-2">
                <span className="font-mono text-xs text-text-muted">{sku.sku_code}</span>
                {sku.category_name && (
                  <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-purple-500/40 text-purple-400">
                    {sku.category_name}
                  </span>
                )}
              </div>
              {/* Row 2: Product name + brand */}
              <div className="flex items-start justify-between gap-2">
                <div>
                  <div className="text-text-primary font-semibold text-sm">{sku.name}</div>
                  {sku.brand_name && (
                    <div className="text-text-secondary text-xs mt-0.5">{sku.brand_name}</div>
                  )}
                </div>
                <div className="flex gap-1 shrink-0">
                  <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => handleEdit(sku)}>
                    <Edit className="h-4 w-4" />
                  </Button>
                  <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => handleAdjustStock(sku)}>
                    <TrendingUp className="h-4 w-4" />
                  </Button>
                  <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => handleTransfer(sku)} title="Transfer to another store">
                    <ArrowRightLeft className="h-4 w-4" />
                  </Button>
                </div>
              </div>
              {/* Row 3: Stock quantity + sellable chip */}
              <div className="flex items-center gap-3 pt-1 border-t border-border-subtle">
                <span className={`text-sm font-medium ${isLowStock ? 'text-red-400' : 'text-text-primary'}`}>
                  {sku.current_stock} {sku.uom}
                </span>
                <span className="text-text-muted text-xs">{formatCurrency(sku.avg_cost_per_unit)} cost</span>
                {sku.retail_price && (
                  <span className="text-text-secondary text-xs">{formatCurrency(sku.retail_price)} retail</span>
                )}
                {sku.is_sellable && (
                  <span className="ml-auto inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-green-500/40 text-green-400">
                    POS
                  </span>
                )}
              </div>
            </div>
          );
        })}
        {filteredSkus.length === 0 && (
          <div className="text-center py-12 text-text-secondary">
            <Package className="h-12 w-12 mx-auto mb-4 opacity-20" />
            <p>No SKUs found</p>
          </div>
        )}
      </div>

      {/* SKU List - Desktop Table */}
      <Card className="hidden md:block">
        <CardHeader>
          <CardTitle>SKU List</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-border-subtle">
                  <th className="text-left py-3 px-4 text-text-secondary font-medium text-sm">SKU Code</th>
                  <th className="text-left py-3 px-4 text-text-secondary font-medium text-sm">Name</th>
                  <th className="text-left py-3 px-4 text-text-secondary font-medium text-sm">Category</th>
                  <th className="text-right py-3 px-4 text-text-secondary font-medium text-sm">Stock</th>
                  <th className="text-right py-3 px-4 text-text-secondary font-medium text-sm">Cost</th>
                  <th className="text-center py-3 px-4 text-text-secondary font-medium text-sm">Sellable</th>
                  <th className="text-right py-3 px-4 text-text-secondary font-medium text-sm">Retail Price</th>
                  <th className="text-center py-3 px-4 text-text-secondary font-medium text-sm">Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredSkus.map((sku) => {
                  const isLowStock = sku.current_stock <= 5;
                  return (
                    <tr key={sku.id} className="border-b border-border-subtle hover:bg-surface-row">
                      <td className="py-3 px-4 font-mono text-sm text-text-muted">{sku.sku_code}</td>
                      <td className="py-3 px-4 text-text-primary">{sku.name}</td>
                      <td className="py-3 px-4 text-sm text-text-secondary">
                        {sku.category_name || '-'}
                      </td>
                      <td className={`py-3 px-4 text-right font-medium ${isLowStock ? 'text-red-400' : 'text-text-primary'}`}>
                        {sku.current_stock} {sku.uom}
                      </td>
                      <td className="py-3 px-4 text-right text-text-primary">
                        {formatCurrency(sku.avg_cost_per_unit)}
                      </td>
                      <td className="py-3 px-4 text-center">
                        {sku.is_sellable ? (
                          <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-green-500/40 text-green-400">
                            Yes
                          </span>
                        ) : (
                          <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-surface-row text-text-muted">
                            No
                          </span>
                        )}
                      </td>
                      <td className="py-3 px-4 text-right text-text-primary">
                        {sku.retail_price ? formatCurrency(sku.retail_price) : '-'}
                      </td>
                      <td className="py-3 px-4">
                        <div className="flex gap-1 justify-center">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleEdit(sku)}
                            title="Edit SKU"
                          >
                            <Edit className="h-4 w-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleAdjustStock(sku)}
                            title="Adjust stock"
                          >
                            <TrendingUp className="h-4 w-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleTransfer(sku)}
                            title="Transfer to another store"
                          >
                            <ArrowRightLeft className="h-4 w-4" />
                          </Button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>

            {filteredSkus.length === 0 && (
              <div className="text-center py-12 text-text-secondary">
                <Package className="h-12 w-12 mx-auto mb-4 opacity-20" />
                <p>No SKUs found</p>
              </div>
            )}
          </div>
        </CardContent>
      </Card>
        </TabsContent>

        <TabsContent value="adjustments" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Pending Stock Adjustments</CardTitle>
            </CardHeader>
            <CardContent>
              {loadingRequests ? (
                <div className="text-center py-8 text-text-secondary">Loading...</div>
              ) : changeRequests.length === 0 ? (
                <div className="text-center py-12 text-text-secondary">
                  <CheckCircle className="h-12 w-12 mx-auto mb-4 opacity-20" />
                  <p>No pending change requests</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {changeRequests.map((request) => (
                    <div key={request.id} className="border rounded-lg p-3 md:p-4">
                      <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3">
                        <div className="flex-1 min-w-0">
                          <div className="flex flex-wrap items-center gap-1.5 mb-2">
                            <span className="font-semibold truncate">{request.sku_name}</span>
                            <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-surface-row text-text-muted">
                              {request.sku_code}
                            </span>
                            <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
                              request.change_type === 'receive' ? 'bg-blue-500/40 text-blue-400' :
                              request.change_type === 'consume' ? 'bg-red-500/40 text-red-400' :
                              'bg-slate-500/40 text-slate-400'
                            }`}>
                              {request.change_type.toUpperCase()}
                            </span>
                          </div>
                          <div className="text-sm space-y-1">
                            <div>
                              <span className="text-text-secondary">Quantity: </span>
                              <span className="font-medium">
                                {request.change_type === 'consume' ? '-' : '+'}{request.quantity}
                              </span>
                            </div>
                            {request.unit_cost && (
                              <div>
                                <span className="text-text-secondary">Unit Cost: </span>
                                <span className="font-medium">{formatCurrency(request.unit_cost)}</span>
                              </div>
                            )}
                            <div>
                              <span className="text-text-secondary">Reason: </span>
                              <span>{request.reason_code}</span>
                            </div>
                            {request.notes && (
                              <div>
                                <span className="text-text-secondary">Notes: </span>
                                <span className="text-sm">{request.notes}</span>
                              </div>
                            )}
                            <div className="text-xs text-text-secondary mt-2">
                              Requested at {new Date(request.requested_at).toLocaleString('en-IN')}
                            </div>
                          </div>
                        </div>
                        {isOwner && (
                          <div className="flex gap-2 shrink-0">
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => handleApproveRequest(request.id)}
                            >
                              <CheckCircle className="h-4 w-4 mr-1" />
                              Approve
                            </Button>
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => handleRejectRequest(request.id)}
                            >
                              <XCircle className="h-4 w-4 mr-1" />
                              Reject
                            </Button>
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Stock Adjustment Dialog */}
      <Dialog open={stockDialogOpen} onOpenChange={setStockDialogOpen}>
        <DialogContent size="lg">
          <DialogHeader>
            <DialogTitle>Adjust Stock</DialogTitle>
          </DialogHeader>

          {adjustingSku && (
            <DialogBody className="space-y-4">
              <div>
                <div className="text-sm font-medium mb-1">SKU: {adjustingSku.sku_code}</div>
                <div className="text-sm text-text-secondary">{adjustingSku.name}</div>
                <div className="text-sm text-text-secondary mt-1">
                  Current Stock: {adjustingSku.current_stock} {adjustingSku.uom}
                </div>
              </div>

              <div>
                <Label htmlFor="adjustment-type">Adjustment Type *</Label>
                <Select value={adjustmentType} onValueChange={(value) => setAdjustmentType(value as 'receive' | 'adjust' | 'consume')}>
                  <SelectTrigger id="adjustment-type">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="receive">Receive Stock (Purchase/Restock)</SelectItem>
                    <SelectItem value="adjust">Adjust (Correction)</SelectItem>
                    <SelectItem value="consume">Consume (Usage/Damage)</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div>
                <Label htmlFor="quantity">Quantity *</Label>
                <Input
                  id="quantity"
                  type="number"
                  step="0.01"
                  min="0"
                  value={adjustmentQty}
                  onChange={(e) => setAdjustmentQty(e.target.value)}
                  placeholder={`Enter quantity in ${adjustingSku.uom}`}
                />
              </div>

              {adjustmentType === 'receive' && (
                <>
                  <div>
                    <Label htmlFor="unit-cost">Unit Cost (₹) *</Label>
                    <Input
                      id="unit-cost"
                      type="number"
                      step="0.01"
                      min="0"
                      value={unitCost}
                      onChange={(e) => setUnitCost(e.target.value)}
                      placeholder="Cost per unit"
                    />
                    <p className="text-xs text-text-secondary mt-1">
                      Base cost before any discounts
                    </p>
                  </div>

                  <div>
                    <Label htmlFor="supplier-invoice">Supplier Invoice Number (Optional)</Label>
                    <Input
                      id="supplier-invoice"
                      type="text"
                      value={supplierInvoiceNumber}
                      onChange={(e) => setSupplierInvoiceNumber(e.target.value)}
                      placeholder="e.g., INV-2024-001"
                    />
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div>
                      <Label htmlFor="discount-percent">Supplier Discount (%)</Label>
                      <Input
                        id="discount-percent"
                        type="number"
                        step="0.01"
                        min="0"
                        max="100"
                        value={supplierDiscountPercent}
                        onChange={(e) => setSupplierDiscountPercent(e.target.value)}
                        placeholder="e.g., 15.5"
                      />
                      <p className="text-xs text-text-secondary mt-1">
                        Percentage discount from supplier
                      </p>
                    </div>

                    <div>
                      <Label htmlFor="discount-fixed">Fixed Discount (₹)</Label>
                      <Input
                        id="discount-fixed"
                        type="number"
                        step="0.01"
                        min="0"
                        value={supplierDiscountFixed}
                        onChange={(e) => setSupplierDiscountFixed(e.target.value)}
                        placeholder="e.g., 50"
                      />
                      <p className="text-xs text-text-secondary mt-1">
                        Fixed amount discount
                      </p>
                    </div>
                  </div>

                  {(supplierDiscountPercent || supplierDiscountFixed) && unitCost && (
                    <div className="bg-blue-500/10 border border-blue-500/30 rounded-lg p-3">
                      <p className="text-sm font-medium text-blue-400">Final Unit Cost</p>
                      <p className="text-lg font-bold text-blue-400">
                        ₹{(() => {
                          const base = parseFloat(unitCost) || 0;
                          const percentDiscount = (base * (parseFloat(supplierDiscountPercent) || 0)) / 100;
                          const fixedDiscount = parseFloat(supplierDiscountFixed) || 0;
                          const final = Math.max(0, base - percentDiscount - fixedDiscount);
                          return final.toFixed(2);
                        })()}
                      </p>
                      <p className="text-xs text-text-secondary mt-1">
                        This will be used for calculating weighted average cost
                      </p>
                    </div>
                  )}
                </>
              )}

              <div>
                <Label htmlFor="reason">Reason *</Label>
                <Select value={reasonCode} onValueChange={setReasonCode}>
                  <SelectTrigger id="reason">
                    <SelectValue placeholder="Select reason" />
                  </SelectTrigger>
                  <SelectContent>
                    {adjustmentType === 'receive' && (
                      <>
                        <SelectItem value="new_stock">New Stock Purchase</SelectItem>
                        <SelectItem value="restock">Restock</SelectItem>
                        <SelectItem value="return">Return from Supplier</SelectItem>
                      </>
                    )}
                    {adjustmentType === 'consume' && (
                      <>
                        <SelectItem value="service_usage">Service Usage</SelectItem>
                        <SelectItem value="damage">Damaged/Expired</SelectItem>
                        <SelectItem value="sample">Sample/Testing</SelectItem>
                      </>
                    )}
                    {adjustmentType === 'adjust' && (
                      <>
                        <SelectItem value="correction">Stock Correction</SelectItem>
                        <SelectItem value="count_adjustment">Physical Count Adjustment</SelectItem>
                        <SelectItem value="error_fix">Error Correction</SelectItem>
                      </>
                    )}
                  </SelectContent>
                </Select>
              </div>

              <div>
                <Label htmlFor="notes">Notes (Optional)</Label>
                <Textarea
                  id="notes"
                  value={adjustmentNotes}
                  onChange={(e) => setAdjustmentNotes(e.target.value)}
                  placeholder="Additional notes about this adjustment..."
                  rows={3}
                />
              </div>
            </DialogBody>
          )}

          <DialogFooter>
            <Button variant="outline" onClick={() => setStockDialogOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleCreateAdjustment}>
              Create Request
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Edit Dialog */}
      <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
        <DialogContent size="md">
          <DialogHeader>
            <DialogTitle>Edit SKU</DialogTitle>
          </DialogHeader>

          {editingSku && (
            <DialogBody className="space-y-4">
              <div>
                <div className="text-sm font-medium mb-1">SKU: {editingSku.sku_code}</div>
                <div className="text-sm text-text-secondary">{editingSku.name}</div>
                <div className="text-sm text-text-secondary mt-1">
                  Cost: {formatCurrency(editingSku.avg_cost_per_unit)}
                </div>
              </div>

              <div>
                <Label htmlFor="barcode">Barcode</Label>
                <div className="flex gap-2">
                  <Input
                    id="barcode"
                    value={editBarcode}
                    onChange={(e) => setEditBarcode(e.target.value)}
                    placeholder="Enter barcode"
                    className="flex-1"
                  />
                  <Button
                    type="button"
                    variant="outline"
                    size="icon"
                    onClick={() => setShowBarcodeScanner(true)}
                    title="Scan barcode with camera"
                  >
                    <Camera className="h-4 w-4" />
                  </Button>
                </div>
                <p className="text-xs text-text-secondary mt-1">
                  Type manually or scan with camera. Can be added or updated at any time.
                </p>
              </div>

              <div className="flex items-center space-x-2">
                <Checkbox
                  id="sellable"
                  checked={isSellable}
                  onCheckedChange={(checked) => setIsSellable(!!checked)}
                />
                <label htmlFor="sellable" className="text-sm font-medium cursor-pointer">
                  Mark as sellable in POS
                </label>
              </div>

              {isSellable && (
                <>
                  <div>
                    <Label htmlFor="retail_price">Retail Price (₹) *</Label>
                    <Input
                      id="retail_price"
                      type="number"
                      step="0.01"
                      min="0"
                      value={retailPrice}
                      onChange={(e) => setRetailPrice(e.target.value)}
                      placeholder="0.00"
                    />
                  </div>

                  <div>
                    <Label htmlFor="retail_markup">Markup %</Label>
                    <Input
                      id="retail_markup"
                      type="number"
                      step="0.01"
                      value={retailMarkup}
                      onChange={(e) => setRetailMarkup(e.target.value)}
                      placeholder="Auto-calculated"
                    />
                    {retailPrice && (
                      <div className="text-xs text-text-secondary mt-1">
                        Calculated markup: {calculateMarkup()}%
                      </div>
                    )}
                  </div>
                </>
              )}
            </DialogBody>
          )}

          <DialogFooter>
            <Button variant="outline" onClick={() => setIsDialogOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleSave}>Save Changes</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Barcode Scanner Modal */}
      {showBarcodeScanner && (
        <BarcodeScanner
          onScan={(barcode) => {
            setEditBarcode(barcode);
            setShowBarcodeScanner(false);
          }}
          onClose={() => setShowBarcodeScanner(false)}
          autoClose={true}
        />
      )}

      {/* Transfer Dialog */}
      {transferingSku && (
        <TransferDialog
          sku={transferingSku}
          open={transferDialogOpen}
          onOpenChange={setTransferDialogOpen}
          onSuccess={() => loadSkus()}
        />
      )}
    </div>
  );
}
