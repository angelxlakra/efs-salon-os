'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Checkbox } from '@/components/ui/checkbox';
import { Package, Search, Edit, Plus, Minus, TrendingUp, CheckCircle, XCircle } from 'lucide-react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Label } from '@/components/ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { apiClient } from '@/lib/api-client';
import { toast } from 'sonner';
import { useAuth } from '@/lib/auth-context';

interface SKU {
  id: string;
  sku_code: string;
  name: string;
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
  const { user } = useAuth();
  const [skus, setSkus] = useState<SKU[]>([]);
  const [filteredSkus, setFilteredSkus] = useState<SKU[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [editingSku, setEditingSku] = useState<SKU | null>(null);
  const [isDialogOpen, setIsDialogOpen] = useState(false);

  // Form state for retail settings
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

  // Change requests state
  const [changeRequests, setChangeRequests] = useState<ChangeRequest[]>([]);
  const [loadingRequests, setLoadingRequests] = useState(false);

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
        params: { size: 1000 } // Get all SKUs
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
    setIsSellable(sku.is_sellable);
    setRetailPrice(sku.retail_price ? (sku.retail_price / 100).toFixed(2) : '');
    setRetailMarkup(sku.retail_markup_percent?.toString() || '');
    setIsDialogOpen(true);
  };

  const handleSave = async () => {
    if (!editingSku) return;

    try {
      const updateData: any = {
        is_sellable: isSellable,
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
    } catch (error: any) {
      console.error('Failed to update SKU:', error);
      toast.error(error.response?.data?.detail || 'Failed to update SKU');
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
      const payload: any = {
        sku_id: adjustingSku.id,
        change_type: adjustmentType,
        quantity: parseFloat(adjustmentQty),
        reason_code: reasonCode,
        notes: adjustmentNotes || undefined,
      };

      if (adjustmentType === 'receive') {
        payload.unit_cost = Math.round(parseFloat(unitCost) * 100); // Convert to paise
      }

      await apiClient.post('/inventory/change-requests', payload);

      toast.success('Stock adjustment request created successfully');
      setStockDialogOpen(false);
      loadChangeRequests();
    } catch (error: any) {
      console.error('Failed to create adjustment:', error);
      toast.error(error.response?.data?.detail || 'Failed to create adjustment request');
    }
  };

  const handleApproveRequest = async (requestId: string) => {
    try {
      await apiClient.post(`/inventory/change-requests/${requestId}/approve`);
      toast.success('Change request approved');
      loadChangeRequests();
      loadSkus(); // Reload SKUs to reflect stock changes
    } catch (error: any) {
      console.error('Failed to approve request:', error);
      toast.error(error.response?.data?.detail || 'Failed to approve request');
    }
  };

  const handleRejectRequest = async (requestId: string) => {
    try {
      await apiClient.post(`/inventory/change-requests/${requestId}/reject`);
      toast.success('Change request rejected');
      loadChangeRequests();
    } catch (error: any) {
      console.error('Failed to reject request:', error);
      toast.error(error.response?.data?.detail || 'Failed to reject request');
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-muted-foreground">Loading inventory...</div>
      </div>
    );
  }

  const isOwner = user?.role?.name === 'owner';

  return (
    <div className="p-6 space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold">Inventory Management</h1>
          <p className="text-muted-foreground">Manage SKUs, retail settings, and stock adjustments</p>
        </div>
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
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search SKUs..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-10"
              />
            </div>
          </div>

      {/* SKU List */}
      <Card>
        <CardHeader>
          <CardTitle>SKU List</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b">
                  <th className="text-left py-3 px-4">SKU Code</th>
                  <th className="text-left py-3 px-4">Name</th>
                  <th className="text-left py-3 px-4">Category</th>
                  <th className="text-right py-3 px-4">Stock</th>
                  <th className="text-right py-3 px-4">Cost</th>
                  <th className="text-center py-3 px-4">Sellable</th>
                  <th className="text-right py-3 px-4">Retail Price</th>
                  <th className="text-center py-3 px-4">Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredSkus.map((sku) => (
                  <tr key={sku.id} className="border-b hover:bg-gray-50">
                    <td className="py-3 px-4 font-mono text-sm">{sku.sku_code}</td>
                    <td className="py-3 px-4">{sku.name}</td>
                    <td className="py-3 px-4 text-sm text-muted-foreground">
                      {sku.category_name || '-'}
                    </td>
                    <td className="py-3 px-4 text-right">
                      {sku.current_stock} {sku.uom}
                    </td>
                    <td className="py-3 px-4 text-right">
                      {formatCurrency(sku.avg_cost_per_unit)}
                    </td>
                    <td className="py-3 px-4 text-center">
                      {sku.is_sellable ? (
                        <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800">
                          Yes
                        </span>
                      ) : (
                        <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
                          No
                        </span>
                      )}
                    </td>
                    <td className="py-3 px-4 text-right">
                      {sku.retail_price ? formatCurrency(sku.retail_price) : '-'}
                    </td>
                    <td className="py-3 px-4">
                      <div className="flex gap-1 justify-center">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleEdit(sku)}
                          title="Edit retail settings"
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
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            {filteredSkus.length === 0 && (
              <div className="text-center py-12 text-muted-foreground">
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
                <div className="text-center py-8 text-muted-foreground">Loading...</div>
              ) : changeRequests.length === 0 ? (
                <div className="text-center py-12 text-muted-foreground">
                  <CheckCircle className="h-12 w-12 mx-auto mb-4 opacity-20" />
                  <p>No pending change requests</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {changeRequests.map((request) => (
                    <div key={request.id} className="border rounded-lg p-4">
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-2">
                            <span className="font-semibold">{request.sku_name}</span>
                            <Badge variant="outline">{request.sku_code}</Badge>
                            <Badge variant={
                              request.change_type === 'receive' ? 'default' :
                              request.change_type === 'consume' ? 'destructive' : 'secondary'
                            }>
                              {request.change_type.toUpperCase()}
                            </Badge>
                          </div>
                          <div className="text-sm space-y-1">
                            <div>
                              <span className="text-muted-foreground">Quantity: </span>
                              <span className="font-medium">
                                {request.change_type === 'consume' ? '-' : '+'}{request.quantity}
                              </span>
                            </div>
                            {request.unit_cost && (
                              <div>
                                <span className="text-muted-foreground">Unit Cost: </span>
                                <span className="font-medium">{formatCurrency(request.unit_cost)}</span>
                              </div>
                            )}
                            <div>
                              <span className="text-muted-foreground">Reason: </span>
                              <span>{request.reason_code}</span>
                            </div>
                            {request.notes && (
                              <div>
                                <span className="text-muted-foreground">Notes: </span>
                                <span className="text-sm">{request.notes}</span>
                              </div>
                            )}
                            <div className="text-xs text-muted-foreground mt-2">
                              Requested at {new Date(request.requested_at).toLocaleString('en-IN')}
                            </div>
                          </div>
                        </div>
                        {isOwner && (
                          <div className="flex gap-2 ml-4">
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
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Adjust Stock</DialogTitle>
          </DialogHeader>

          {adjustingSku && (
            <div className="space-y-4">
              <div>
                <div className="text-sm font-medium mb-1">SKU: {adjustingSku.sku_code}</div>
                <div className="text-sm text-muted-foreground">{adjustingSku.name}</div>
                <div className="text-sm text-muted-foreground mt-1">
                  Current Stock: {adjustingSku.current_stock} {adjustingSku.uom}
                </div>
              </div>

              <div>
                <Label htmlFor="adjustment-type">Adjustment Type *</Label>
                <Select value={adjustmentType} onValueChange={(value: any) => setAdjustmentType(value)}>
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
                  <p className="text-xs text-muted-foreground mt-1">
                    Used for calculating weighted average cost
                  </p>
                </div>
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
            </div>
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
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Edit Retail Settings</DialogTitle>
          </DialogHeader>

          {editingSku && (
            <div className="space-y-4">
              <div>
                <div className="text-sm font-medium mb-1">SKU: {editingSku.sku_code}</div>
                <div className="text-sm text-muted-foreground">{editingSku.name}</div>
                <div className="text-sm text-muted-foreground mt-1">
                  Cost: {formatCurrency(editingSku.avg_cost_per_unit)}
                </div>
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
                      <div className="text-xs text-muted-foreground mt-1">
                        Calculated markup: {calculateMarkup()}%
                      </div>
                    )}
                  </div>
                </>
              )}
            </div>
          )}

          <DialogFooter>
            <Button variant="outline" onClick={() => setIsDialogOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleSave}>Save Changes</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
