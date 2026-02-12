'use client';

import { useState, useEffect } from 'react';
import { Trash2, Plus } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Card, CardContent } from '@/components/ui/card';
import { purchaseApi, PurchaseInvoice, PurchaseItemCreate } from '@/lib/api/purchases';
import { toast } from 'sonner';

interface EditInvoiceDialogProps {
  invoice: PurchaseInvoice;
  open: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export default function EditInvoiceDialog({ invoice, open, onClose, onSuccess }: EditInvoiceDialogProps) {
  const [items, setItems] = useState<PurchaseItemCreate[]>([]);
  const [invoiceDiscount, setInvoiceDiscount] = useState(0);
  const [notes, setNotes] = useState('');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (open && invoice) {
      // Initialize form with current invoice data
      setItems(
        invoice.items.map((item) => ({
          sku_id: item.sku_id,
          product_name: item.product_name,
          barcode: item.barcode,
          uom: item.uom,
          quantity: item.quantity,
          unit_cost: item.unit_cost,
          discount_amount: item.discount_amount || 0,
        }))
      );
      setInvoiceDiscount(invoice.invoice_discount_amount || 0);
      setNotes(invoice.notes || '');
    }
  }, [open, invoice]);

  const handleAddItem = () => {
    setItems([...items, { product_name: '', uom: 'piece', quantity: 1, unit_cost: 0, discount_amount: 0 }]);
  };

  const handleRemoveItem = (index: number) => {
    if (items.length === 1) {
      toast.error('At least one item is required');
      return;
    }
    setItems(items.filter((_, i) => i !== index));
  };

  const handleItemChange = (index: number, field: keyof PurchaseItemCreate, value: any) => {
    const newItems = [...items];
    (newItems[index] as any)[field] = value;
    setItems(newItems);
  };

  const calculateItemTotal = (item: PurchaseItemCreate) => {
    const baseCost = item.quantity * item.unit_cost;
    return baseCost - (item.discount_amount || 0);
  };

  const calculateSubtotal = () => {
    return items.reduce((sum, item) => sum + calculateItemTotal(item), 0);
  };

  const calculateTotal = () => {
    return calculateSubtotal() - invoiceDiscount;
  };

  const formatCurrency = (amount: number) => {
    return `₹${(amount / 100).toFixed(2)}`;
  };

  const handleSave = async () => {
    // Validation
    const filledItems = items.filter((item) => item.product_name.trim());
    if (filledItems.length === 0) {
      toast.error('Please add at least one item');
      return;
    }

    for (const item of filledItems) {
      if (!item.uom) {
        toast.error(`Item "${item.product_name}": Unit of measure is required`);
        return;
      }
      if (item.quantity <= 0) {
        toast.error(`Item "${item.product_name}": Quantity must be greater than 0`);
        return;
      }
      if (item.unit_cost <= 0) {
        toast.error(`Item "${item.product_name}": Unit cost must be greater than 0`);
        return;
      }
      const itemSubtotal = item.quantity * item.unit_cost;
      if ((item.discount_amount || 0) > itemSubtotal) {
        toast.error(`Item "${item.product_name}": Discount cannot exceed item subtotal`);
        return;
      }
    }

    const subtotal = calculateSubtotal();
    if (invoiceDiscount > subtotal) {
      toast.error('Invoice discount cannot exceed subtotal');
      return;
    }

    try {
      setSaving(true);
      await purchaseApi.editPurchaseInvoiceWithDiscounts(invoice.id, {
        items: filledItems,
        invoice_discount_amount: invoiceDiscount,
        notes: notes.trim() || undefined,
      });
      toast.success('Invoice updated successfully');
      onSuccess();
    } catch (error: any) {
      console.error('Error updating invoice:', error);
      toast.error(error.response?.data?.detail || 'Failed to update invoice');
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={(isOpen) => !isOpen && onClose()}>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Edit Invoice: {invoice.invoice_number}</DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          {/* Items */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <Label className="text-base font-semibold">Line Items</Label>
              <Button onClick={handleAddItem} size="sm" variant="outline">
                <Plus className="mr-2 h-4 w-4" />
                Add Item
              </Button>
            </div>

            {items.map((item, index) => (
              <Card key={index}>
                <CardContent className="pt-4">
                  <div className="grid gap-3">
                    <div className="grid gap-3 md:grid-cols-2">
                      <div className="space-y-2">
                        <Label className="text-xs">Product Name *</Label>
                        <Input
                          value={item.product_name}
                          onChange={(e) => handleItemChange(index, 'product_name', e.target.value)}
                          placeholder="Product name"
                        />
                      </div>
                      <div className="space-y-2">
                        <Label className="text-xs">Barcode</Label>
                        <Input
                          value={item.barcode || ''}
                          onChange={(e) => handleItemChange(index, 'barcode', e.target.value)}
                          placeholder="Product barcode"
                        />
                      </div>
                    </div>

                    <div className="grid gap-3 grid-cols-2 sm:grid-cols-5">
                      <div className="space-y-2">
                        <Label className="text-xs">Unit</Label>
                        <Select
                          value={item.uom}
                          onValueChange={(value) => handleItemChange(index, 'uom', value)}
                        >
                          <SelectTrigger className="h-9">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="piece">Piece</SelectItem>
                            <SelectItem value="ml">ML</SelectItem>
                            <SelectItem value="gm">Gram</SelectItem>
                            <SelectItem value="kg">KG</SelectItem>
                            <SelectItem value="liter">Liter</SelectItem>
                            <SelectItem value="box">Box</SelectItem>
                            <SelectItem value="bottle">Bottle</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>

                      <div className="space-y-2">
                        <Label className="text-xs">Qty *</Label>
                        <Input
                          type="number"
                          step="1"
                          min="1"
                          value={item.quantity === 0 ? '' : item.quantity}
                          onChange={(e) => {
                            const val = e.target.value;
                            handleItemChange(index, 'quantity', val === '' ? 0 : parseFloat(val) || 0);
                          }}
                          className="h-9"
                        />
                      </div>

                      <div className="space-y-2">
                        <Label className="text-xs">Cost (₹) *</Label>
                        <Input
                          type="number"
                          step="1"
                          min="0"
                          value={item.unit_cost === 0 ? '' : item.unit_cost / 100}
                          onChange={(e) => {
                            const val = e.target.value;
                            handleItemChange(index, 'unit_cost', val === '' ? 0 : Math.round(parseFloat(val) * 100) || 0);
                          }}
                          className="h-9"
                        />
                      </div>

                      <div className="space-y-2">
                        <Label className="text-xs">Discount (₹)</Label>
                        <Input
                          type="number"
                          step="1"
                          min="0"
                          value={(item.discount_amount || 0) === 0 ? '' : (item.discount_amount || 0) / 100}
                          onChange={(e) => {
                            const val = e.target.value;
                            handleItemChange(index, 'discount_amount', val === '' ? 0 : Math.round(parseFloat(val) * 100) || 0);
                          }}
                          className="h-9"
                        />
                      </div>

                      <div className="space-y-2">
                        <Label className="text-xs">Total</Label>
                        <div className="flex items-center h-9 px-3 border rounded-md bg-muted text-sm font-semibold">
                          {formatCurrency(calculateItemTotal(item))}
                        </div>
                      </div>
                    </div>

                    {items.length > 1 && (
                      <div className="flex justify-end">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleRemoveItem(index)}
                          className="text-red-600 hover:text-red-700 hover:bg-red-50"
                        >
                          <Trash2 className="mr-2 h-4 w-4" />
                          Remove
                        </Button>
                      </div>
                    )}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>

          {/* Invoice Discount */}
          <Card className="border-2 border-primary/20 bg-primary/5">
            <CardContent className="pt-4">
              <div className="grid gap-4">
                <div className="grid gap-3 md:grid-cols-2">
                  <div className="space-y-2">
                    <Label className="text-sm font-semibold">Invoice Discount (₹)</Label>
                    <Input
                      type="number"
                      step="1"
                      min="0"
                      value={invoiceDiscount === 0 ? '' : invoiceDiscount / 100}
                      onChange={(e) => {
                        const val = e.target.value;
                        setInvoiceDiscount(val === '' ? 0 : Math.round(parseFloat(val) * 100) || 0);
                      }}
                      placeholder="0.00"
                    />
                    <p className="text-xs text-muted-foreground">Additional discount on the entire invoice</p>
                  </div>

                  <div className="space-y-2">
                    <Label className="text-sm font-semibold">Notes</Label>
                    <Textarea
                      value={notes}
                      onChange={(e) => setNotes(e.target.value)}
                      placeholder="Additional notes"
                      rows={3}
                    />
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Summary */}
          <Card>
            <CardContent className="pt-4">
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Subtotal</span>
                  <span className="font-semibold">{formatCurrency(calculateSubtotal())}</span>
                </div>
                {invoiceDiscount > 0 && (
                  <div className="flex justify-between text-sm text-green-600">
                    <span>Invoice Discount</span>
                    <span className="font-semibold">-{formatCurrency(invoiceDiscount)}</span>
                  </div>
                )}
                <div className="flex justify-between text-lg font-bold pt-2 border-t">
                  <span>Total Amount</span>
                  <span>{formatCurrency(calculateTotal())}</span>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={onClose} disabled={saving}>
            Cancel
          </Button>
          <Button onClick={handleSave} disabled={saving}>
            {saving ? 'Saving...' : 'Save Changes'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
