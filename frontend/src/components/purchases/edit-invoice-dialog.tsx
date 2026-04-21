'use client';

import { useState, useEffect } from 'react';
import { Trash2, Plus, Calculator, ChevronUp, ChevronDown, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Switch } from '@/components/ui/switch';
import { Dialog, DialogBody, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Card, CardContent } from '@/components/ui/card';
import { purchaseApi, PurchaseInvoice, PurchaseItemCreate } from '@/lib/api/purchases';
import { toast } from 'sonner';

interface ItemFormState {
  sku_id?: string;
  product_name: string;
  barcode?: string;
  uom: string;
  quantity: number;
  unit_cost: number;
  discount_amount: number;
  cgst_amount: number;
  sgst_amount: number;
  rate_incl_tax?: number;
  tax_rate_percent: number;
  discount_percent?: number;
  discount_mode: 'percent' | 'flat';
}

function getItemCalc(item: ItemFormState) {
  const rateInclTax = item.rate_incl_tax || 0;
  const taxRatePercent = item.tax_rate_percent || 18;
  const taxMult = 1 + taxRatePercent / 100;
  const qty = item.quantity || 0;
  const baseRatePerUnit = rateInclTax / taxMult;

  let taxablePerUnit: number;
  let lineDiscountAmount: number;

  if (item.discount_mode === 'percent') {
    const discRate = (item.discount_percent || 0) / 100;
    taxablePerUnit = baseRatePerUnit * (1 - discRate);
    lineDiscountAmount = Math.round(baseRatePerUnit * discRate * qty);
  } else {
    const baseLineTotal = baseRatePerUnit * qty;
    lineDiscountAmount = item.discount_amount || 0;
    taxablePerUnit = qty > 0 ? (baseLineTotal - lineDiscountAmount) / qty : 0;
  }

  const taxableLine = Math.round(taxablePerUnit * qty);
  const halfTaxRate = taxRatePercent / 2 / 100;
  const cgst = Math.round(taxableLine * halfTaxRate);
  const sgst = Math.round(taxableLine * halfTaxRate);
  const unitCostAllIn = Math.round(taxablePerUnit * taxMult);
  const lineTotal = taxableLine + cgst + sgst;

  return { taxableLine, cgst, sgst, unitCostAllIn, lineDiscountAmount, lineTotal };
}

function prepareItemForApi(item: ItemFormState, autoCalc: boolean): PurchaseItemCreate {
  if (autoCalc) {
    const calc = getItemCalc(item);
    return {
      sku_id: item.sku_id,
      product_name: item.product_name,
      barcode: item.barcode,
      uom: item.uom,
      quantity: item.quantity,
      unit_cost: Math.max(calc.unitCostAllIn, 1),
      discount_amount: 0,
      rate_incl_tax: item.rate_incl_tax,
      tax_rate_percent: item.tax_rate_percent,
      discount_percent: item.discount_mode === 'percent' ? (item.discount_percent || 0) : undefined,
      cgst_amount: calc.cgst,
      sgst_amount: calc.sgst,
    };
  }
  return {
    sku_id: item.sku_id,
    product_name: item.product_name,
    barcode: item.barcode,
    uom: item.uom,
    quantity: item.quantity,
    unit_cost: item.unit_cost,
    discount_amount: item.discount_amount || 0,
    rate_incl_tax: item.rate_incl_tax,
    tax_rate_percent: item.tax_rate_percent,
    discount_percent: item.discount_percent,
    cgst_amount: item.cgst_amount || 0,
    sgst_amount: item.sgst_amount || 0,
  };
}

const defaultItem = (): ItemFormState => ({
  product_name: '',
  uom: 'piece',
  quantity: 1,
  unit_cost: 0,
  discount_amount: 0,
  cgst_amount: 0,
  sgst_amount: 0,
  rate_incl_tax: undefined,
  tax_rate_percent: 18,
  discount_percent: undefined,
  discount_mode: 'percent',
});

interface EditInvoiceDialogProps {
  invoice: PurchaseInvoice;
  open: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export default function EditInvoiceDialog({ invoice, open, onClose, onSuccess }: EditInvoiceDialogProps) {
  const [items, setItems] = useState<ItemFormState[]>([]);
  const [invoiceDiscount, setInvoiceDiscount] = useState(0);
  const [roundOff, setRoundOff] = useState(0);
  const [notes, setNotes] = useState('');
  const [saving, setSaving] = useState(false);
  // Default to manual mode when editing existing data (new invoices may not have rate_incl_tax)
  const [autoCalc, setAutoCalc] = useState(false);

  useEffect(() => {
    if (open && invoice) {
      setItems(
        invoice.items.map((item) => ({
          sku_id: item.sku_id,
          product_name: item.product_name,
          barcode: item.barcode,
          uom: item.uom,
          quantity: item.quantity,
          unit_cost: item.unit_cost,
          discount_amount: item.discount_amount || 0,
          cgst_amount: item.cgst_amount || 0,
          sgst_amount: item.sgst_amount || 0,
          rate_incl_tax: item.rate_incl_tax,
          tax_rate_percent: item.tax_rate_percent || 18,
          discount_percent: item.discount_percent,
          // Use percent mode if discount_percent is stored, else flat
          discount_mode: item.discount_percent != null ? 'percent' : 'flat',
        }))
      );
      setInvoiceDiscount(invoice.invoice_discount_amount || 0);
      setRoundOff(invoice.round_off_amount || 0);
      setNotes(invoice.notes || '');
      // Switch to auto-calc if all existing items have rate_incl_tax set
      const allHaveRate = invoice.items.length > 0 && invoice.items.every(i => i.rate_incl_tax);
      setAutoCalc(allHaveRate);
    }
  }, [open, invoice]);

  const handleAddItem = () => setItems([...items, defaultItem()]);

  const handleRemoveItem = (index: number) => {
    if (items.length === 1) { toast.error('At least one item is required'); return; }
    setItems(items.filter((_, i) => i !== index));
  };

  const handleItemChange = (index: number, field: keyof ItemFormState, value: any) => {
    const newItems = [...items];
    (newItems[index] as any)[field] = value;
    setItems(newItems);
  };

  const getLineTotal = (item: ItemFormState): number => {
    if (autoCalc) return getItemCalc(item).lineTotal;
    return Math.max(0, item.quantity * item.unit_cost - (item.discount_amount || 0));
  };

  const calculateSubtotal = () => items.reduce((sum, item) => sum + getLineTotal(item), 0);
  const calculateTotal = () => calculateSubtotal() - invoiceDiscount + roundOff;

  const applyRoundDown = () => {
    const preRound = calculateSubtotal() - invoiceDiscount;
    setRoundOff(Math.floor(preRound / 100) * 100 - preRound);
  };

  const applyRoundUp = () => {
    const preRound = calculateSubtotal() - invoiceDiscount;
    setRoundOff(Math.ceil(preRound / 100) * 100 - preRound);
  };

  const getAutoCalcSummary = () => {
    let totalTaxable = 0, totalCgst = 0, totalSgst = 0;
    items.forEach(item => {
      const calc = getItemCalc(item);
      totalTaxable += calc.taxableLine;
      totalCgst += calc.cgst;
      totalSgst += calc.sgst;
    });
    return { totalTaxable, totalCgst, totalSgst };
  };

  const formatCurrency = (amount: number) => `₹${(amount / 100).toFixed(2)}`;

  const handleSave = async () => {
    const filledItems = items.filter((item) => item.product_name.trim());
    if (filledItems.length === 0) { toast.error('Please add at least one item'); return; }

    for (const item of filledItems) {
      if (!item.uom) { toast.error(`Item "${item.product_name}": Unit of measure is required`); return; }
      if (item.quantity <= 0) { toast.error(`Item "${item.product_name}": Quantity must be greater than 0`); return; }

      if (autoCalc) {
        if (!item.rate_incl_tax || item.rate_incl_tax <= 0) {
          toast.error(`Item "${item.product_name}": Rate (incl. tax) must be greater than 0`);
          return;
        }
        const calc = getItemCalc(item);
        if (calc.unitCostAllIn <= 0) {
          toast.error(`Item "${item.product_name}": Calculated unit cost is invalid — check discount`);
          return;
        }
      } else {
        if (item.unit_cost <= 0) { toast.error(`Item "${item.product_name}": Unit cost must be greater than 0`); return; }
        if ((item.discount_amount || 0) > item.quantity * item.unit_cost) {
          toast.error(`Item "${item.product_name}": Discount cannot exceed item subtotal`);
          return;
        }
      }
    }

    const subtotal = calculateSubtotal();
    if (invoiceDiscount > subtotal) { toast.error('Invoice discount cannot exceed subtotal'); return; }

    try {
      setSaving(true);
      await purchaseApi.editPurchaseInvoiceWithDiscounts(invoice.id, {
        items: filledItems.map(item => prepareItemForApi(item, autoCalc)),
        invoice_discount_amount: invoiceDiscount,
        round_off_amount: roundOff,
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

  const uomOptions = (
    <>
      <SelectItem value="piece">Piece</SelectItem>
      <SelectItem value="ml">ML</SelectItem>
      <SelectItem value="gm">Gram</SelectItem>
      <SelectItem value="kg">KG</SelectItem>
      <SelectItem value="liter">Liter</SelectItem>
      <SelectItem value="box">Box</SelectItem>
      <SelectItem value="bottle">Bottle</SelectItem>
    </>
  );

  const { totalTaxable, totalCgst, totalSgst } = autoCalc ? getAutoCalcSummary() : { totalTaxable: 0, totalCgst: 0, totalSgst: 0 };

  return (
    <Dialog open={open} onOpenChange={(isOpen) => !isOpen && onClose()}>
      <DialogContent size="xl">
        <DialogHeader>
          <DialogTitle>Edit Invoice: {invoice.invoice_number}</DialogTitle>
        </DialogHeader>

        <DialogBody className="space-y-4">
          {/* Items */}
          <div className="space-y-3">
            <div className="flex items-center justify-between flex-wrap gap-2">
              <Label className="text-base font-semibold">Line Items</Label>
              <div className="flex items-center gap-3">
                <div className="flex items-center gap-2 border rounded-md px-3 py-1.5 bg-muted/50">
                  <Calculator className="h-3.5 w-3.5 text-muted-foreground" />
                  <Label htmlFor="editAutoCalc" className="text-xs font-medium cursor-pointer">Auto-calculate</Label>
                  <Switch id="editAutoCalc" checked={autoCalc} onCheckedChange={setAutoCalc} />
                </div>
                <Button onClick={handleAddItem} size="sm" variant="outline">
                  <Plus className="mr-2 h-4 w-4" />Add Item
                </Button>
              </div>
            </div>

            {items.map((item, index) => (
              <Card key={index}>
                <CardContent className="pt-4">
                  <div className="grid gap-3">
                    {/* Product Name + Barcode */}
                    <div className="grid gap-3 md:grid-cols-2">
                      <div className="space-y-2">
                        <Label className="text-xs">Product Name *</Label>
                        <Input value={item.product_name} onChange={(e) => handleItemChange(index, 'product_name', e.target.value)} placeholder="Product name" />
                      </div>
                      <div className="space-y-2">
                        <Label className="text-xs">Barcode</Label>
                        <Input value={item.barcode || ''} onChange={(e) => handleItemChange(index, 'barcode', e.target.value)} placeholder="Product barcode" />
                      </div>
                    </div>

                    {/* Auto-calc mode */}
                    {autoCalc ? (
                      <>
                        <div className="grid gap-3 grid-cols-2 sm:grid-cols-3 lg:grid-cols-6">
                          <div className="space-y-2">
                            <Label className="text-xs">Unit</Label>
                            <Select value={item.uom} onValueChange={(v) => handleItemChange(index, 'uom', v)}>
                              <SelectTrigger className="h-9"><SelectValue /></SelectTrigger>
                              <SelectContent>{uomOptions}</SelectContent>
                            </Select>
                          </div>
                          <div className="space-y-2">
                            <Label className="text-xs">Qty *</Label>
                            <Input
                              type="number" step="1" min="1"
                              value={item.quantity === 0 ? '' : item.quantity}
                              onChange={(e) => handleItemChange(index, 'quantity', e.target.value === '' ? 0 : parseFloat(e.target.value) || 0)}
                              onBlur={() => { if (item.quantity === 0) handleItemChange(index, 'quantity', 1); }}
                              className="h-9"
                            />
                          </div>
                          <div className="space-y-2 sm:col-span-1 lg:col-span-2">
                            <Label className="text-xs">Rate (incl. tax ₹) *</Label>
                            <Input
                              type="number" step="0.01" min="0"
                              value={!item.rate_incl_tax ? '' : item.rate_incl_tax / 100}
                              onChange={(e) => handleItemChange(index, 'rate_incl_tax', e.target.value === '' ? undefined : Math.round(parseFloat(e.target.value) * 100) || undefined)}
                              placeholder="MRP"
                              className="h-9"
                            />
                          </div>
                          <div className="space-y-2">
                            <Label className="text-xs">GST %</Label>
                            <Select value={String(item.tax_rate_percent)} onValueChange={(v) => handleItemChange(index, 'tax_rate_percent', parseInt(v))}>
                              <SelectTrigger className="h-9"><SelectValue /></SelectTrigger>
                              <SelectContent>
                                <SelectItem value="0">0%</SelectItem>
                                <SelectItem value="5">5%</SelectItem>
                                <SelectItem value="12">12%</SelectItem>
                                <SelectItem value="18">18%</SelectItem>
                                <SelectItem value="28">28%</SelectItem>
                              </SelectContent>
                            </Select>
                          </div>
                          <div className="space-y-2">
                            <Label className="text-xs">Discount ({item.discount_mode === 'percent' ? '%' : '₹'})</Label>
                            <div className="flex gap-1">
                              <Button
                                type="button" variant="outline" size="sm"
                                className="h-9 w-9 px-0 shrink-0 font-mono text-xs"
                                onClick={() => handleItemChange(index, 'discount_mode', item.discount_mode === 'percent' ? 'flat' : 'percent')}
                                title="Toggle discount type"
                              >
                                {item.discount_mode === 'percent' ? '%' : '₹'}
                              </Button>
                              {item.discount_mode === 'percent' ? (
                                <Input
                                  type="number" step="0.01" min="0" max="100"
                                  value={item.discount_percent === undefined ? '' : item.discount_percent}
                                  onChange={(e) => handleItemChange(index, 'discount_percent', e.target.value === '' ? undefined : parseFloat(e.target.value) || 0)}
                                  placeholder="0"
                                  className="h-9"
                                />
                              ) : (
                                <Input
                                  type="number" step="0.01" min="0"
                                  value={(item.discount_amount || 0) === 0 ? '' : (item.discount_amount || 0) / 100}
                                  onChange={(e) => handleItemChange(index, 'discount_amount', e.target.value === '' ? 0 : Math.round(parseFloat(e.target.value) * 100) || 0)}
                                  placeholder="0.00"
                                  className="h-9"
                                />
                              )}
                            </div>
                          </div>
                        </div>

                        {/* Computed breakdown */}
                        {(item.rate_incl_tax || 0) > 0 && (() => {
                          const calc = getItemCalc(item);
                          const baseRate = Math.round((item.rate_incl_tax || 0) / (1 + item.tax_rate_percent / 100));
                          return (
                            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 rounded-md bg-muted/40 border px-3 py-2">
                              <div>
                                <p className="text-xs text-muted-foreground">Base Rate/unit</p>
                                <p className="text-sm font-medium">{formatCurrency(baseRate)}</p>
                              </div>
                              <div>
                                <p className="text-xs text-muted-foreground">Taxable (line)</p>
                                <p className="text-sm font-medium">{formatCurrency(calc.taxableLine)}</p>
                              </div>
                              <div>
                                <p className="text-xs text-muted-foreground">CGST + SGST</p>
                                <p className="text-sm font-medium">{formatCurrency(calc.cgst + calc.sgst)}</p>
                              </div>
                              <div>
                                <p className="text-xs text-muted-foreground">Line Total</p>
                                <p className="text-sm font-semibold text-primary">{formatCurrency(calc.lineTotal)}</p>
                              </div>
                            </div>
                          );
                        })()}
                      </>
                    ) : (
                      /* Manual mode */
                      <>
                        <div className="grid gap-3 grid-cols-1 sm:grid-cols-2 md:grid-cols-5">
                          <div className="space-y-2">
                            <Label className="text-xs">Unit</Label>
                            <Select value={item.uom} onValueChange={(v) => handleItemChange(index, 'uom', v)}>
                              <SelectTrigger className="h-9"><SelectValue /></SelectTrigger>
                              <SelectContent>{uomOptions}</SelectContent>
                            </Select>
                          </div>
                          <div className="space-y-2">
                            <Label className="text-xs">Qty *</Label>
                            <Input
                              type="number" step="1" min="1"
                              value={item.quantity === 0 ? '' : item.quantity}
                              onChange={(e) => handleItemChange(index, 'quantity', e.target.value === '' ? 0 : parseFloat(e.target.value) || 0)}
                              className="h-9"
                            />
                          </div>
                          <div className="space-y-2">
                            <Label className="text-xs">Cost/unit (₹) *</Label>
                            <Input
                              type="number" step="0.01" min="0"
                              value={item.unit_cost === 0 ? '' : item.unit_cost / 100}
                              onChange={(e) => handleItemChange(index, 'unit_cost', e.target.value === '' ? 0 : Math.round(parseFloat(e.target.value) * 100) || 0)}
                              className="h-9"
                            />
                          </div>
                          <div className="space-y-2">
                            <Label className="text-xs">Discount (₹)</Label>
                            <Input
                              type="number" step="0.01" min="0"
                              value={(item.discount_amount || 0) === 0 ? '' : (item.discount_amount || 0) / 100}
                              onChange={(e) => handleItemChange(index, 'discount_amount', e.target.value === '' ? 0 : Math.round(parseFloat(e.target.value) * 100) || 0)}
                              className="h-9"
                            />
                          </div>
                          <div className="space-y-2">
                            <Label className="text-xs">Total</Label>
                            <div className="flex items-center h-9 px-3 border rounded-md bg-muted text-sm font-semibold">
                              {formatCurrency(Math.max(0, item.quantity * item.unit_cost - (item.discount_amount || 0)))}
                            </div>
                          </div>
                        </div>
                        {/* CGST / SGST reference */}
                        <div className="grid gap-3 grid-cols-2 sm:grid-cols-4">
                          <div className="space-y-2">
                            <Label className="text-xs text-muted-foreground">CGST (₹)</Label>
                            <Input
                              type="number" step="0.01" min="0"
                              value={(item.cgst_amount || 0) === 0 ? '' : (item.cgst_amount || 0) / 100}
                              onChange={(e) => handleItemChange(index, 'cgst_amount', e.target.value === '' ? 0 : Math.round(parseFloat(e.target.value) * 100) || 0)}
                              placeholder="0.00" className="h-9"
                            />
                          </div>
                          <div className="space-y-2">
                            <Label className="text-xs text-muted-foreground">SGST (₹)</Label>
                            <Input
                              type="number" step="0.01" min="0"
                              value={(item.sgst_amount || 0) === 0 ? '' : (item.sgst_amount || 0) / 100}
                              onChange={(e) => handleItemChange(index, 'sgst_amount', e.target.value === '' ? 0 : Math.round(parseFloat(e.target.value) * 100) || 0)}
                              placeholder="0.00" className="h-9"
                            />
                          </div>
                          <div className="space-y-2">
                            <Label className="text-xs text-muted-foreground">GST %</Label>
                            <Select value={String(item.tax_rate_percent)} onValueChange={(v) => handleItemChange(index, 'tax_rate_percent', parseInt(v))}>
                              <SelectTrigger className="h-9"><SelectValue /></SelectTrigger>
                              <SelectContent>
                                <SelectItem value="0">0%</SelectItem>
                                <SelectItem value="5">5%</SelectItem>
                                <SelectItem value="12">12%</SelectItem>
                                <SelectItem value="18">18%</SelectItem>
                                <SelectItem value="28">28%</SelectItem>
                              </SelectContent>
                            </Select>
                          </div>
                        </div>
                      </>
                    )}

                    {items.length > 1 && (
                      <div className="flex justify-end">
                        <Button variant="ghost" size="sm" onClick={() => handleRemoveItem(index)} className="text-red-600 hover:text-red-700 hover:bg-red-50">
                          <Trash2 className="mr-2 h-4 w-4" />Remove
                        </Button>
                      </div>
                    )}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>

          {/* Invoice Discount + Round Off + Notes */}
          <Card className="border-2 border-primary/20 bg-primary/5">
            <CardContent className="pt-4 space-y-4">
              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <Label className="text-sm font-semibold">Invoice Discount (₹)</Label>
                  <Input
                    type="number" step="0.01" min="0"
                    value={invoiceDiscount === 0 ? '' : invoiceDiscount / 100}
                    onChange={(e) => setInvoiceDiscount(e.target.value === '' ? 0 : Math.round(parseFloat(e.target.value) * 100) || 0)}
                    placeholder="0.00"
                  />
                  <p className="text-xs text-muted-foreground">Additional discount on the entire invoice</p>
                </div>
                <div className="space-y-2">
                  <Label className="text-sm font-semibold">Notes</Label>
                  <Textarea value={notes} onChange={(e) => setNotes(e.target.value)} placeholder="Additional notes" rows={3} />
                </div>
              </div>
              <div className="space-y-2">
                <Label className="text-sm font-semibold">Round Off (₹)</Label>
                <div className="flex items-center gap-2 flex-wrap">
                  <Button type="button" variant="outline" size="sm" onClick={applyRoundDown} title="Round total down to nearest rupee">
                    <ChevronDown className="h-3.5 w-3.5 mr-1" />Round Down
                  </Button>
                  <Button type="button" variant="outline" size="sm" onClick={applyRoundUp} title="Round total up to nearest rupee">
                    <ChevronUp className="h-3.5 w-3.5 mr-1" />Round Up
                  </Button>
                  <Input
                    type="number" step="0.01"
                    value={roundOff === 0 ? '' : roundOff / 100}
                    onChange={(e) => setRoundOff(e.target.value === '' ? 0 : Math.round(parseFloat(e.target.value) * 100) || 0)}
                    placeholder="0.00"
                    className="w-28"
                  />
                  {roundOff !== 0 && (
                    <Button type="button" variant="ghost" size="sm" onClick={() => setRoundOff(0)}>
                      <X className="h-3.5 w-3.5" />
                    </Button>
                  )}
                </div>
                <p className="text-xs text-muted-foreground">Negative = round down (−), positive = round up (+)</p>
              </div>
            </CardContent>
          </Card>

          {/* Summary */}
          <Card>
            <CardContent className="pt-4">
              <div className="space-y-2">
                {autoCalc && totalTaxable > 0 && (
                  <>
                    <div className="flex justify-between text-sm">
                      <span className="text-muted-foreground">Taxable Value</span>
                      <span>{formatCurrency(totalTaxable)}</span>
                    </div>
                    <div className="flex justify-between text-sm text-blue-600">
                      <span>CGST</span>
                      <span>{formatCurrency(totalCgst)}</span>
                    </div>
                    <div className="flex justify-between text-sm text-blue-600">
                      <span>SGST</span>
                      <span>{formatCurrency(totalSgst)}</span>
                    </div>
                  </>
                )}
                <div className="flex justify-between text-sm pt-1 border-t">
                  <span className="text-muted-foreground">Subtotal</span>
                  <span className="font-semibold">{formatCurrency(calculateSubtotal())}</span>
                </div>
                {invoiceDiscount > 0 && (
                  <div className="flex justify-between text-sm text-green-600">
                    <span>Invoice Discount</span>
                    <span className="font-semibold">-{formatCurrency(invoiceDiscount)}</span>
                  </div>
                )}
                {roundOff !== 0 && (
                  <div className={`flex justify-between text-sm ${roundOff < 0 ? 'text-orange-600' : 'text-green-600'}`}>
                    <span>Round Off</span>
                    <span className="font-semibold">
                      {roundOff > 0 ? '+' : ''}{formatCurrency(roundOff)}
                    </span>
                  </div>
                )}
                <div className="flex justify-between text-lg font-bold pt-2 border-t">
                  <span>Total Amount</span>
                  <span>{formatCurrency(calculateTotal())}</span>
                </div>
              </div>
            </CardContent>
          </Card>
        </DialogBody>

        <DialogFooter>
          <Button variant="outline" onClick={onClose} disabled={saving}>Cancel</Button>
          <Button onClick={handleSave} disabled={saving}>{saving ? 'Saving...' : 'Save Changes'}</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
