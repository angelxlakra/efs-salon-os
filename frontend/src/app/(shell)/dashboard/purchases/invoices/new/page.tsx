'use client';

import { useState, useEffect, useCallback } from 'react';
import { ArrowLeft, Plus, Trash2, Search, Camera, Calculator, ChevronUp, ChevronDown, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Switch } from '@/components/ui/switch';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Dialog, DialogBody, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { BarcodeScanner } from '@/components/barcode-scanner';
import { purchaseApi, PurchaseItemCreate, SupplierListItem } from '@/lib/api/purchases';
import { toast } from 'sonner';
import { useRouter } from 'next/navigation';

// Extended item state including UI-only discount_mode field
interface ItemFormState {
  sku_id?: string;
  product_name: string;
  barcode?: string;
  uom: string;
  quantity: number;
  // Manual mode fields
  unit_cost: number;       // all-in per unit in paise
  discount_amount: number; // flat line discount in paise
  cgst_amount: number;     // line CGST in paise (manual)
  sgst_amount: number;     // line SGST in paise (manual)
  // Auto-calc fields
  rate_incl_tax?: number;  // MRP per unit in paise
  tax_rate_percent: number;
  discount_percent?: number;
  discount_mode: 'percent' | 'flat'; // frontend-only
}

function getItemCalc(item: ItemFormState) {
  const rateInclTax = item.rate_incl_tax || 0;
  const taxRatePercent = item.tax_rate_percent || 18;
  const taxMult = 1 + taxRatePercent / 100;
  const qty = item.quantity || 0;

  // Base rate per unit (excl. GST), in paise (floating point)
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

export default function NewPurchaseInvoicePage() {
  const router = useRouter();
  const [suppliers, setSuppliers] = useState<SupplierListItem[]>([]);
  const [supplierId, setSupplierId] = useState('');
  const [invoiceNumber, setInvoiceNumber] = useState('');
  const [invoiceDate, setInvoiceDate] = useState(new Date().toISOString().split('T')[0]);
  const [dueDate, setDueDate] = useState('');
  const [notes, setNotes] = useState('');
  const [invoiceDiscount, setInvoiceDiscount] = useState(0);
  const [roundOff, setRoundOff] = useState(0);
  const [autoCalc, setAutoCalc] = useState(true);
  const [items, setItems] = useState<ItemFormState[]>([defaultItem()]);

  const [barcodeSearch, setBarcodeSearch] = useState('');
  const [searchingBarcode, setSearchingBarcode] = useState(false);
  const [showScanner, setShowScanner] = useState(false);
  const [scannerDisabled, setScannerDisabled] = useState(false);
  const [unmappedBarcode, setUnmappedBarcode] = useState<string | null>(null);
  const [quickAddForm, setQuickAddForm] = useState({
    product_name: '',
    uom: 'piece',
    quantity: 1,
    unit_cost: 0,
  });

  useEffect(() => {
    loadSuppliers();
  }, []);

  const loadSuppliers = async () => {
    try {
      const response = await purchaseApi.listSuppliers({ size: 100, active_only: true });
      setSuppliers(response.items || []);
    } catch (error) {
      console.error('Error loading suppliers:', error);
      toast.error('Failed to load suppliers');
    }
  };

  const handleBarcodeSearch = useCallback(async (barcode?: string) => {
    const searchBarcode = barcode || barcodeSearch;
    if (!searchBarcode.trim() || searchingBarcode) {
      if (!searchBarcode.trim()) toast.error('Please enter a barcode');
      return;
    }
    if (unmappedBarcode === searchBarcode) return;

    const existingItemIndex = items.findIndex(item =>
      item.barcode && item.barcode.trim() === searchBarcode.trim()
    );
    if (existingItemIndex !== -1) {
      const newItems = [...items];
      newItems[existingItemIndex].quantity += 1;
      setItems(newItems);
      toast.success(`Increased quantity of ${newItems[existingItemIndex].product_name}`);
      setBarcodeSearch('');
      return;
    }

    try {
      setSearchingBarcode(true);
      const result = await purchaseApi.searchByBarcode(searchBarcode);

      if (result.found) {
        const existingIndex = items.findIndex(item =>
          (item.barcode && item.barcode === result.barcode) ||
          (item.sku_id && item.sku_id === result.sku_id)
        );
        if (existingIndex !== -1) {
          const newItems = [...items];
          newItems[existingIndex].quantity += 1;
          setItems(newItems);
          toast.success(`Increased quantity of ${result.product_name}`);
        } else {
          const newItem: ItemFormState = {
            ...defaultItem(),
            sku_id: result.sku_id,
            product_name: result.product_name || '',
            barcode: result.barcode,
            uom: result.uom || 'piece',
            quantity: 1,
            // pre-fill unit_cost from last known cost (manual mode reference)
            unit_cost: result.avg_cost_per_unit || 0,
          };
          setItems(prev => [...prev, newItem]);
          toast.success(`Added ${result.product_name}`);
        }
        setBarcodeSearch('');
      } else {
        setScannerDisabled(true);
        setUnmappedBarcode(searchBarcode);
        setQuickAddForm({ product_name: '', uom: 'piece', quantity: 1, unit_cost: 0 });
        setBarcodeSearch('');
      }
    } catch (error) {
      console.error('Error searching barcode:', error);
      toast.error('Failed to search barcode');
    } finally {
      setSearchingBarcode(false);
    }
  }, [barcodeSearch, searchingBarcode, unmappedBarcode, items]);

  const handleQuickAdd = useCallback(() => {
    if (!quickAddForm.product_name.trim()) {
      toast.error('Product name is required');
      return;
    }
    if (quickAddForm.unit_cost <= 0) {
      toast.error('Unit cost must be greater than 0');
      return;
    }
    const newItem: ItemFormState = {
      ...defaultItem(),
      product_name: quickAddForm.product_name,
      barcode: unmappedBarcode || undefined,
      uom: quickAddForm.uom,
      quantity: quickAddForm.quantity,
      unit_cost: quickAddForm.unit_cost,
    };
    setItems(prev => [...prev, newItem]);
    setUnmappedBarcode(null);
    setScannerDisabled(false);
    setQuickAddForm({ product_name: '', uom: 'piece', quantity: 1, unit_cost: 0 });
    toast.success('Product added to invoice');
  }, [quickAddForm, unmappedBarcode]);

  const handleCameraScan = useCallback((barcode: string) => {
    handleBarcodeSearch(barcode);
  }, [handleBarcodeSearch]);

  const handleAddItem = () => setItems([...items, defaultItem()]);

  const handleRemoveItem = (index: number) => {
    const filledItems = items.filter(item => item.product_name.trim());
    if (filledItems.length === 1 && items[index].product_name.trim()) {
      toast.error('At least one item is required');
      return;
    }
    const newItems = items.filter((_, i) => i !== index);
    setItems(newItems.length === 0 ? [defaultItem()] : newItems);
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

  const calculateSubtotal = () =>
    items
      .filter(item => item.product_name.trim())
      .reduce((sum, item) => sum + getLineTotal(item), 0);

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
    items.filter(item => item.product_name.trim()).forEach(item => {
      const calc = getItemCalc(item);
      totalTaxable += calc.taxableLine;
      totalCgst += calc.cgst;
      totalSgst += calc.sgst;
    });
    return { totalTaxable, totalCgst, totalSgst };
  };

  const formatCurrency = (amount: number) => `₹${(amount / 100).toFixed(2)}`;

  const handleSubmit = async () => {
    if (!supplierId) { toast.error('Please select a supplier'); return; }
    if (!invoiceNumber.trim()) { toast.error('Please enter invoice number'); return; }
    if (!invoiceDate) { toast.error('Please enter invoice date'); return; }

    const filledItems = items.filter(item => item.product_name.trim());
    if (filledItems.length === 0) {
      toast.error('Please add at least one item to the invoice');
      return;
    }

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
    if (invoiceDiscount > subtotal) {
      toast.error('Invoice discount cannot exceed subtotal');
      return;
    }

    try {
      await purchaseApi.createPurchaseInvoice({
        supplier_id: supplierId,
        invoice_number: invoiceNumber.trim(),
        invoice_date: invoiceDate,
        due_date: dueDate || undefined,
        notes: notes.trim() || undefined,
        items: filledItems.map(item => prepareItemForApi(item, autoCalc)),
        invoice_discount_amount: invoiceDiscount,
        round_off_amount: roundOff,
      });
      toast.success('Purchase invoice created successfully');
      router.push('/dashboard/purchases/invoices');
    } catch (error: any) {
      console.error('Error creating invoice:', error);
      toast.error(error.response?.data?.detail || 'Failed to create purchase invoice');
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
    <div className="p-4 md:p-6 space-y-4">
      {/* Header */}
      <div className="flex items-center gap-3 md:gap-4">
        <Button variant="ghost" size="icon" onClick={() => router.back()}>
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <div className="min-w-0 flex-1">
          <h1 className="text-xl font-semibold truncate">New Purchase Invoice</h1>
          <p className="text-sm md:text-base text-text-muted truncate">Create a new supplier invoice</p>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Main Form */}
        <div className="lg:col-span-2 space-y-6">
          {/* Invoice Details */}
          <Card>
            <CardHeader><CardTitle>Invoice Details</CardTitle></CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="supplier">Supplier *</Label>
                  <Select value={supplierId} onValueChange={setSupplierId}>
                    <SelectTrigger><SelectValue placeholder="Select supplier" /></SelectTrigger>
                    <SelectContent>
                      {suppliers.map((supplier) => (
                        <SelectItem key={supplier.id} value={supplier.id}>{supplier.name}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="invoiceNumber">Invoice Number *</Label>
                  <Input id="invoiceNumber" value={invoiceNumber} onChange={(e) => setInvoiceNumber(e.target.value)} placeholder="INV-001" />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="invoiceDate">Invoice Date *</Label>
                  <Input id="invoiceDate" type="date" value={invoiceDate} onChange={(e) => setInvoiceDate(e.target.value)} />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="dueDate">Due Date</Label>
                  <Input id="dueDate" type="date" value={dueDate} onChange={(e) => setDueDate(e.target.value)} />
                </div>
              </div>
              <div className="space-y-2">
                <Label htmlFor="notes">Notes</Label>
                <Textarea id="notes" value={notes} onChange={(e) => setNotes(e.target.value)} placeholder="Additional notes about this invoice" rows={3} />
              </div>
            </CardContent>
          </Card>

          {/* Barcode Search */}
          <Card>
            <CardHeader><CardTitle>Quick Add by Barcode</CardTitle></CardHeader>
            <CardContent>
              <div className="flex flex-col sm:flex-row gap-2">
                <Input
                  placeholder="Enter barcode and press Enter"
                  value={barcodeSearch}
                  onChange={(e) => setBarcodeSearch(e.target.value)}
                  onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); handleBarcodeSearch(); } }}
                  className="flex-1"
                />
                <div className="flex gap-2">
                  <Button onClick={() => handleBarcodeSearch()} disabled={searchingBarcode} variant="secondary" className="flex-1 sm:flex-none">
                    <Search className="mr-2 h-4 w-4" />Search
                  </Button>
                  <Button onClick={() => setShowScanner(true)} variant="default" className="flex-1 sm:flex-none">
                    <Camera className="mr-2 h-4 w-4" />Scan
                  </Button>
                </div>
              </div>
              <p className="text-xs text-text-muted mt-2">Type barcode manually or use camera to scan</p>
            </CardContent>
          </Card>

          {/* Line Items */}
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between flex-wrap gap-2">
                <CardTitle>Line Items</CardTitle>
                <div className="flex items-center gap-3">
                  {/* Auto-calc toggle */}
                  <div className="flex items-center gap-2 border rounded-md px-3 py-1.5 bg-muted/50">
                    <Calculator className="h-3.5 w-3.5 text-text-muted" />
                    <Label htmlFor="autoCalc" className="text-xs font-medium cursor-pointer">
                      Auto-calculate
                    </Label>
                    <Switch id="autoCalc" checked={autoCalc} onCheckedChange={setAutoCalc} />
                  </div>
                  <Button onClick={handleAddItem} size="sm">
                    <Plus className="mr-2 h-4 w-4" />Add Item
                  </Button>
                </div>
              </div>
              {autoCalc && (
                <p className="text-xs text-text-muted mt-1">
                  Enter MRP (rate incl. tax), GST %, and discount — totals are calculated automatically.
                </p>
              )}
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {items.map((item, index) => (
                  <Card key={index}>
                    <CardContent className="pt-6">
                      <div className="grid gap-4">
                        {/* Row 1: Product Name + Barcode */}
                        <div className="grid gap-4 md:grid-cols-2">
                          <div className="space-y-2">
                            <Label>Product Name *</Label>
                            <Input value={item.product_name} onChange={(e) => handleItemChange(index, 'product_name', e.target.value)} placeholder="Product name" />
                          </div>
                          <div className="space-y-2">
                            <Label>Barcode</Label>
                            <Input value={item.barcode || ''} onChange={(e) => handleItemChange(index, 'barcode', e.target.value)} placeholder="Product barcode" />
                          </div>
                        </div>

                        {/* Auto-calc mode rows */}
                        {autoCalc ? (
                          <>
                            {/* Row 2: Unit + Qty + Rate incl. tax + GST % + Discount */}
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
                                <Select
                                  value={String(item.tax_rate_percent)}
                                  onValueChange={(v) => handleItemChange(index, 'tax_rate_percent', parseInt(v))}
                                >
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
                                <Label className="text-xs">
                                  Discount ({item.discount_mode === 'percent' ? '%' : '₹'})
                                </Label>
                                <div className="flex gap-1">
                                  <Button
                                    type="button"
                                    variant="outline"
                                    size="sm"
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

                            {/* Row 3: Computed breakdown (only when rate is set) */}
                            {(item.rate_incl_tax || 0) > 0 && (() => {
                              const calc = getItemCalc(item);
                              const baseRate = Math.round((item.rate_incl_tax || 0) / (1 + item.tax_rate_percent / 100));
                              return (
                                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 rounded-md bg-muted/40 border px-3 py-2">
                                  <div>
                                    <p className="text-xs text-text-muted">Base Rate/unit</p>
                                    <p className="text-sm font-medium">{formatCurrency(baseRate)}</p>
                                  </div>
                                  <div>
                                    <p className="text-xs text-text-muted">Taxable (line)</p>
                                    <p className="text-sm font-medium">{formatCurrency(calc.taxableLine)}</p>
                                  </div>
                                  <div>
                                    <p className="text-xs text-text-muted">CGST + SGST</p>
                                    <p className="text-sm font-medium">{formatCurrency(calc.cgst + calc.sgst)}</p>
                                  </div>
                                  <div>
                                    <p className="text-xs text-text-muted">Line Total</p>
                                    <p className="text-sm font-semibold text-primary">{formatCurrency(calc.lineTotal)}</p>
                                  </div>
                                </div>
                              );
                            })()}
                          </>
                        ) : (
                          /* Manual mode rows */
                          <>
                            <div className="grid gap-4 grid-cols-1 sm:grid-cols-2 md:grid-cols-5">
                              <div className="space-y-2">
                                <Label className="text-xs sm:text-sm">Unit</Label>
                                <Select value={item.uom} onValueChange={(v) => handleItemChange(index, 'uom', v)}>
                                  <SelectTrigger className="h-9 sm:h-10"><SelectValue /></SelectTrigger>
                                  <SelectContent>{uomOptions}</SelectContent>
                                </Select>
                              </div>
                              <div className="space-y-2">
                                <Label className="text-xs sm:text-sm">Qty *</Label>
                                <Input
                                  type="number" step="1" min="1"
                                  value={item.quantity === 0 ? '' : item.quantity}
                                  onChange={(e) => handleItemChange(index, 'quantity', e.target.value === '' ? 0 : parseFloat(e.target.value) || 0)}
                                  onBlur={() => { if (item.quantity === 0) handleItemChange(index, 'quantity', 1); }}
                                  className="h-9 sm:h-10"
                                />
                              </div>
                              <div className="space-y-2">
                                <Label className="text-xs sm:text-sm">Cost/unit (₹) *</Label>
                                <Input
                                  type="number" step="0.01" min="0"
                                  value={item.unit_cost === 0 ? '' : item.unit_cost / 100}
                                  onChange={(e) => handleItemChange(index, 'unit_cost', e.target.value === '' ? 0 : Math.round(parseFloat(e.target.value) * 100) || 0)}
                                  className="h-9 sm:h-10"
                                />
                              </div>
                              <div className="space-y-2">
                                <Label className="text-xs sm:text-sm">Discount (₹)</Label>
                                <Input
                                  type="number" step="0.01" min="0"
                                  value={(item.discount_amount || 0) === 0 ? '' : (item.discount_amount || 0) / 100}
                                  onChange={(e) => handleItemChange(index, 'discount_amount', e.target.value === '' ? 0 : Math.round(parseFloat(e.target.value) * 100) || 0)}
                                  className="h-9 sm:h-10"
                                />
                              </div>
                              <div className="space-y-2">
                                <Label className="text-xs sm:text-sm">Total</Label>
                                <div className="flex items-center h-9 sm:h-10 px-2 sm:px-3 border rounded-md bg-muted text-sm font-semibold">
                                  {formatCurrency(Math.max(0, item.quantity * item.unit_cost - (item.discount_amount || 0)))}
                                </div>
                              </div>
                            </div>
                            {/* CGST / SGST reference fields */}
                            <div className="grid gap-4 grid-cols-2 sm:grid-cols-4">
                              <div className="space-y-2">
                                <Label className="text-xs text-text-muted">CGST (₹)</Label>
                                <Input
                                  type="number" step="0.01" min="0"
                                  value={(item.cgst_amount || 0) === 0 ? '' : (item.cgst_amount || 0) / 100}
                                  onChange={(e) => handleItemChange(index, 'cgst_amount', e.target.value === '' ? 0 : Math.round(parseFloat(e.target.value) * 100) || 0)}
                                  placeholder="0.00"
                                  className="h-9"
                                />
                              </div>
                              <div className="space-y-2">
                                <Label className="text-xs text-text-muted">SGST (₹)</Label>
                                <Input
                                  type="number" step="0.01" min="0"
                                  value={(item.sgst_amount || 0) === 0 ? '' : (item.sgst_amount || 0) / 100}
                                  onChange={(e) => handleItemChange(index, 'sgst_amount', e.target.value === '' ? 0 : Math.round(parseFloat(e.target.value) * 100) || 0)}
                                  placeholder="0.00"
                                  className="h-9"
                                />
                              </div>
                              <div className="space-y-2">
                                <Label className="text-xs text-text-muted">GST %</Label>
                                <Select
                                  value={String(item.tax_rate_percent)}
                                  onValueChange={(v) => handleItemChange(index, 'tax_rate_percent', parseInt(v))}
                                >
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
                            <Button variant="destructive" size="sm" onClick={() => handleRemoveItem(index)}>
                              <Trash2 className="mr-2 h-4 w-4" />Remove Item
                            </Button>
                          </div>
                        )}
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Invoice Discount + Round Off */}
          <Card className="border-2 border-primary/20 bg-primary/5">
            <CardHeader><CardTitle>Invoice Adjustments</CardTitle></CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="invoiceDiscount">Additional Discount (₹)</Label>
                <Input
                  id="invoiceDiscount" type="number" step="0.01" min="0"
                  value={invoiceDiscount === 0 ? '' : invoiceDiscount / 100}
                  onChange={(e) => setInvoiceDiscount(e.target.value === '' ? 0 : Math.round(parseFloat(e.target.value) * 100) || 0)}
                  placeholder="0.00"
                />
                <p className="text-xs text-text-muted">
                  Applied to the entire invoice after item discounts
                </p>
              </div>

              <div className="space-y-2">
                <Label>Round Off (₹)</Label>
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
                <p className="text-xs text-text-muted">
                  Negative = round down (−), positive = round up (+)
                </p>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Summary Sidebar */}
        <div>
          <Card className="sticky top-6">
            <CardHeader><CardTitle>Invoice Summary</CardTitle></CardHeader>
            <CardContent className="space-y-4">
              {/* Items List */}
              {items.some(item => item.product_name.trim()) && (
                <div className="space-y-2">
                  <p className="text-sm font-medium text-text-muted">Items Added:</p>
                  <div className="space-y-2 max-h-60 overflow-y-auto">
                    {items.filter(item => item.product_name.trim()).map((item, index) => (
                      <div key={index} className="p-2 bg-muted rounded-md text-sm">
                        <div className="font-medium truncate" title={item.product_name}>{item.product_name}</div>
                        <div className="flex justify-between text-xs text-text-muted mt-1">
                          <span>{item.quantity} {item.uom}</span>
                          <span>{formatCurrency(getLineTotal(item))}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <div className="space-y-2 pt-2 border-t">
                <div className="flex justify-between text-sm">
                  <span className="text-text-muted">Total Items:</span>
                  <span className="font-medium">{items.filter(item => item.product_name.trim()).length}</span>
                </div>

                {/* Auto-calc GST breakdown */}
                {autoCalc && totalTaxable > 0 && (
                  <>
                    <div className="flex justify-between text-sm pt-1">
                      <span className="text-text-muted">Taxable Value:</span>
                      <span>{formatCurrency(totalTaxable)}</span>
                    </div>
                    <div className="flex justify-between text-sm text-accent">
                      <span>CGST:</span>
                      <span>{formatCurrency(totalCgst)}</span>
                    </div>
                    <div className="flex justify-between text-sm text-accent">
                      <span>SGST:</span>
                      <span>{formatCurrency(totalSgst)}</span>
                    </div>
                  </>
                )}

                <div className="flex justify-between text-sm pt-1 border-t">
                  <span className="text-text-muted">Subtotal:</span>
                  <span className="font-semibold">{formatCurrency(calculateSubtotal())}</span>
                </div>
                {invoiceDiscount > 0 && (
                  <div className="flex justify-between text-sm text-warning-fg">
                    <span>Invoice Discount:</span>
                    <span className="font-semibold">-{formatCurrency(invoiceDiscount)}</span>
                  </div>
                )}
                {roundOff !== 0 && (
                  <div className={`flex justify-between text-sm ${roundOff < 0 ? 'text-warning-fg' : 'text-success-fg'}`}>
                    <span>Round Off:</span>
                    <span className="font-semibold">
                      {roundOff > 0 ? '+' : ''}{formatCurrency(roundOff)}
                    </span>
                  </div>
                )}
                <div className="flex justify-between text-lg font-bold pt-2 border-t">
                  <span>Total:</span>
                  <span>{formatCurrency(calculateTotal())}</span>
                </div>
              </div>

              <div className="space-y-2 pt-4">
                <Button className="w-full" onClick={handleSubmit}>Create Invoice</Button>
                <Button variant="outline" className="w-full" onClick={() => router.back()}>Cancel</Button>
              </div>

              <div className="text-xs text-text-muted pt-4 border-t">
                <p>Note: Invoice will be created in DRAFT status. Mark as received to update inventory.</p>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Quick Add Dialog for Unmapped Barcode */}
      {unmappedBarcode && (
        <Dialog open={true} onOpenChange={(open) => {
          if (!open) {
            setUnmappedBarcode(null);
            setScannerDisabled(false);
            setQuickAddForm({ product_name: '', uom: 'piece', quantity: 1, unit_cost: 0 });
          }
        }}>
          <DialogContent>
            <DialogHeader><DialogTitle>Add Product Details</DialogTitle></DialogHeader>
            <DialogBody className="space-y-4">
              <div className="p-3 bg-muted rounded-lg">
                <p className="text-sm text-text-muted">Barcode not found in system</p>
                <p className="font-mono font-semibold">{unmappedBarcode}</p>
              </div>
              <div className="space-y-2">
                <Label htmlFor="quickProduct">Product Name *</Label>
                <Input id="quickProduct" value={quickAddForm.product_name} onChange={(e) => setQuickAddForm({ ...quickAddForm, product_name: e.target.value })} placeholder="Enter product name" autoFocus />
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="quickUom" className="text-sm">Unit</Label>
                  <Select value={quickAddForm.uom} onValueChange={(v) => setQuickAddForm({ ...quickAddForm, uom: v })}>
                    <SelectTrigger id="quickUom"><SelectValue /></SelectTrigger>
                    <SelectContent>{uomOptions}</SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="quickQty" className="text-sm">Quantity</Label>
                  <Input
                    id="quickQty" type="number" step="1" min="1"
                    value={quickAddForm.quantity === 0 ? '' : quickAddForm.quantity}
                    onChange={(e) => setQuickAddForm({ ...quickAddForm, quantity: e.target.value === '' ? 0 : parseFloat(e.target.value) || 0 })}
                    onBlur={() => { if (quickAddForm.quantity === 0) setQuickAddForm({ ...quickAddForm, quantity: 1 }); }}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="quickCost">Cost (₹)</Label>
                  <Input
                    id="quickCost" type="number" step="0.01" min="0"
                    value={quickAddForm.unit_cost === 0 ? '' : quickAddForm.unit_cost / 100}
                    onChange={(e) => setQuickAddForm({ ...quickAddForm, unit_cost: e.target.value === '' ? 0 : Math.round(parseFloat(e.target.value) * 100) || 0 })}
                  />
                </div>
              </div>
            </DialogBody>
            <DialogFooter>
              <Button variant="outline" onClick={() => {
                setUnmappedBarcode(null);
                setScannerDisabled(false);
                setQuickAddForm({ product_name: '', uom: 'piece', quantity: 1, unit_cost: 0 });
              }}>Cancel</Button>
              <Button onClick={handleQuickAdd}>Add to Invoice</Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      )}

      {/* Barcode Scanner Modal */}
      {showScanner && (
        <BarcodeScanner
          onScan={handleCameraScan}
          onClose={() => { setShowScanner(false); setScannerDisabled(false); }}
          disabled={scannerDisabled}
        />
      )}
    </div>
  );
}
