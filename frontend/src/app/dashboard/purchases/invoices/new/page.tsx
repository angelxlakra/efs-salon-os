'use client';

import { useState, useEffect, useCallback, useMemo } from 'react';
import { ArrowLeft, Plus, Trash2, Search, Camera } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { BarcodeScanner } from '@/components/barcode-scanner';
import { purchaseApi, PurchaseItemCreate, SupplierListItem } from '@/lib/api/purchases';
import { toast } from 'sonner';
import { useRouter } from 'next/navigation';

export default function NewPurchaseInvoicePage() {
  const router = useRouter();
  const [suppliers, setSuppliers] = useState<SupplierListItem[]>([]);
  const [supplierId, setSupplierId] = useState('');
  const [invoiceNumber, setInvoiceNumber] = useState('');
  const [invoiceDate, setInvoiceDate] = useState(new Date().toISOString().split('T')[0]);
  const [dueDate, setDueDate] = useState('');
  const [notes, setNotes] = useState('');
  const [invoiceDiscount, setInvoiceDiscount] = useState(0);
  const [items, setItems] = useState<PurchaseItemCreate[]>([
    { product_name: '', uom: 'piece', quantity: 1, unit_cost: 0, discount_amount: 0 },
  ]);

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

    // If we're already showing the details for this barcode, don't search again
    if (unmappedBarcode === searchBarcode) {
      return;
    }

    // First, check if this barcode already exists in the current items list
    const existingItemIndex = items.findIndex(item =>
      item.barcode && item.barcode.trim() === searchBarcode.trim()
    );

    if (existingItemIndex !== -1) {
      // Increment quantity of existing item in current list
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
        // Check if item with this barcode or sku_id already exists in current items
        const existingIndex = items.findIndex(item =>
          (item.barcode && item.barcode === result.barcode) ||
          (item.sku_id && item.sku_id === result.sku_id)
        );

        if (existingIndex !== -1) {
          // Increment quantity of existing item
          const newItems = [...items];
          newItems[existingIndex].quantity += 1;
          setItems(newItems);
          toast.success(`Increased quantity of ${result.product_name}`);
        } else {
          // Add new item with pre-filled data
          const newItem: PurchaseItemCreate = {
            sku_id: result.sku_id,
            product_name: result.product_name || '',
            barcode: result.barcode,
            uom: result.uom || 'piece',
            quantity: 1,
            unit_cost: result.avg_cost_per_unit || 0,
            discount_amount: 0,
          };
          setItems(prev => [...prev, newItem]);
          toast.success(`Added ${result.product_name}`);
        }
        setBarcodeSearch('');
      } else {
        // Disable scanner but keep it open
        setScannerDisabled(true);

        // Show quick add dialog for unmapped barcode
        setUnmappedBarcode(searchBarcode);
        setQuickAddForm({
          product_name: '',
          uom: 'piece',
          quantity: 1,
          unit_cost: 0,
        });
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

    const newItem: PurchaseItemCreate = {
      product_name: quickAddForm.product_name,
      barcode: unmappedBarcode || undefined,
      uom: quickAddForm.uom,
      quantity: quickAddForm.quantity,
      unit_cost: quickAddForm.unit_cost,
      discount_amount: 0,
    };

    setItems(prev => [...prev, newItem]);
    setUnmappedBarcode(null);
    setScannerDisabled(false); // Re-enable scanner
    setQuickAddForm({
      product_name: '',
      uom: 'piece',
      quantity: 1,
      unit_cost: 0,
    });
    toast.success('Product added to invoice');
  }, [quickAddForm, unmappedBarcode]);

  const handleCameraScan = useCallback((barcode: string) => {
    handleBarcodeSearch(barcode);
  }, [handleBarcodeSearch]);

  const handleAddItem = () => {
    setItems([...items, { product_name: '', uom: 'piece', quantity: 1, unit_cost: 0, discount_amount: 0 }]);
  };

  const handleRemoveItem = (index: number) => {
    const filledItems = items.filter(item => item.product_name.trim());

    // Only prevent removal if this is the last filled item
    if (filledItems.length === 1 && items[index].product_name.trim()) {
      toast.error('At least one item is required');
      return;
    }

    const newItems = items.filter((_, i) => i !== index);

    // Ensure at least one empty item for manual entry
    if (newItems.length === 0) {
      setItems([{ product_name: '', uom: 'piece', quantity: 1, unit_cost: 0, discount_amount: 0 }]);
    } else {
      setItems(newItems);
    }
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
    return items
      .filter(item => item.product_name.trim())
      .reduce((sum, item) => sum + calculateItemTotal(item), 0);
  };

  const calculateTotal = () => {
    return calculateSubtotal() - invoiceDiscount;
  };

  const formatCurrency = (amount: number) => {
    return `₹${(amount / 100).toFixed(2)}`;
  };

  const handleSubmit = async () => {
    // Validation
    if (!supplierId) {
      toast.error('Please select a supplier');
      return;
    }
    if (!invoiceNumber.trim()) {
      toast.error('Please enter invoice number');
      return;
    }
    if (!invoiceDate) {
      toast.error('Please enter invoice date');
      return;
    }

    // Filter out empty items (items without product names)
    const filledItems = items.filter(item => item.product_name.trim());

    // Check if there are any items at all
    if (filledItems.length === 0) {
      toast.error('Please add at least one item to the invoice');
      return;
    }

    // Validate filled items only
    for (let i = 0; i < filledItems.length; i++) {
      const item = filledItems[i];
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

    // Validate invoice discount
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
        items: filledItems, // Only submit filled items
        invoice_discount_amount: invoiceDiscount,
      });

      toast.success('Purchase invoice created successfully');
      router.push('/dashboard/purchases/invoices');
    } catch (error: any) {
      console.error('Error creating invoice:', error);
      toast.error(error.response?.data?.detail || 'Failed to create purchase invoice');
    }
  };

  return (
    <div className="p-4 md:p-6 space-y-4 md:space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3 md:gap-4">
        <Button variant="ghost" size="icon" onClick={() => router.back()}>
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <div className="min-w-0 flex-1">
          <h1 className="text-2xl md:text-3xl font-bold truncate">New Purchase Invoice</h1>
          <p className="text-sm md:text-base text-muted-foreground truncate">Create a new supplier invoice</p>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Main Form */}
        <div className="lg:col-span-2 space-y-6">
          {/* Invoice Details */}
          <Card>
            <CardHeader>
              <CardTitle>Invoice Details</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="supplier">Supplier *</Label>
                  <Select value={supplierId} onValueChange={setSupplierId}>
                    <SelectTrigger>
                      <SelectValue placeholder="Select supplier" />
                    </SelectTrigger>
                    <SelectContent>
                      {suppliers.map((supplier) => (
                        <SelectItem key={supplier.id} value={supplier.id}>
                          {supplier.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="invoiceNumber">Invoice Number *</Label>
                  <Input
                    id="invoiceNumber"
                    value={invoiceNumber}
                    onChange={(e) => setInvoiceNumber(e.target.value)}
                    placeholder="INV-001"
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="invoiceDate">Invoice Date *</Label>
                  <Input
                    id="invoiceDate"
                    type="date"
                    value={invoiceDate}
                    onChange={(e) => setInvoiceDate(e.target.value)}
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="dueDate">Due Date</Label>
                  <Input
                    id="dueDate"
                    type="date"
                    value={dueDate}
                    onChange={(e) => setDueDate(e.target.value)}
                  />
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="notes">Notes</Label>
                <Textarea
                  id="notes"
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  placeholder="Additional notes about this invoice"
                  rows={3}
                />
              </div>
            </CardContent>
          </Card>

          {/* Barcode Search */}
          <Card>
            <CardHeader>
              <CardTitle>Quick Add by Barcode</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex flex-col sm:flex-row gap-2">
                <Input
                  placeholder="Enter barcode and press Enter"
                  value={barcodeSearch}
                  onChange={(e) => setBarcodeSearch(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      e.preventDefault();
                      handleBarcodeSearch();
                    }
                  }}
                  className="flex-1"
                />
                <div className="flex gap-2">
                  <Button onClick={() => handleBarcodeSearch()} disabled={searchingBarcode} variant="secondary" className="flex-1 sm:flex-none">
                    <Search className="mr-2 h-4 w-4" />
                    <span className="hidden sm:inline">Search</span>
                    <span className="sm:hidden">Search</span>
                  </Button>
                  <Button onClick={() => setShowScanner(true)} variant="default" className="flex-1 sm:flex-none">
                    <Camera className="mr-2 h-4 w-4" />
                    <span className="hidden sm:inline">Scan</span>
                    <span className="sm:hidden">Scan</span>
                  </Button>
                </div>
              </div>
              <p className="text-xs text-muted-foreground mt-2">
                Type barcode manually or use camera to scan
              </p>
            </CardContent>
          </Card>

          {/* Line Items */}
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>Line Items</CardTitle>
                <Button onClick={handleAddItem} size="sm">
                  <Plus className="mr-2 h-4 w-4" />
                  Add Item
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {items.map((item, index) => (
                  <Card key={index}>
                    <CardContent className="pt-6">
                      <div className="grid gap-4">
                        <div className="grid gap-4 md:grid-cols-2">
                          <div className="space-y-2">
                            <Label>Product Name *</Label>
                            <Input
                              value={item.product_name}
                              onChange={(e) => handleItemChange(index, 'product_name', e.target.value)}
                              placeholder="Product name"
                            />
                          </div>
                          <div className="space-y-2">
                            <Label>Barcode</Label>
                            <Input
                              value={item.barcode || ''}
                              onChange={(e) => handleItemChange(index, 'barcode', e.target.value)}
                              placeholder="Product barcode"
                            />
                          </div>
                        </div>

                        <div className="grid gap-4 grid-cols-2 sm:grid-cols-5">
                          <div className="space-y-2">
                            <Label className="text-xs sm:text-sm">Unit</Label>
                            <Select
                              value={item.uom}
                              onValueChange={(value) => handleItemChange(index, 'uom', value)}
                            >
                              <SelectTrigger className="h-9 sm:h-10">
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
                            <Label className="text-xs sm:text-sm">Qty *</Label>
                            <Input
                              type="number"
                              step="1"
                              min="1"
                              value={item.quantity === 0 ? '' : item.quantity}
                              onChange={(e) => {
                                const val = e.target.value;
                                handleItemChange(index, 'quantity', val === '' ? 0 : parseFloat(val) || 0);
                              }}
                              onBlur={(e) => {
                                // Set to 1 if empty when losing focus
                                if (item.quantity === 0) {
                                  handleItemChange(index, 'quantity', 1);
                                }
                              }}
                              className="h-9 sm:h-10"
                            />
                          </div>

                          <div className="space-y-2">
                            <Label className="text-xs sm:text-sm">Cost (₹) *</Label>
                            <Input
                              type="number"
                              step="1"
                              min="0"
                              value={item.unit_cost === 0 ? '' : item.unit_cost / 100}
                              onChange={(e) => {
                                const val = e.target.value;
                                handleItemChange(index, 'unit_cost', val === '' ? 0 : Math.round(parseFloat(val) * 100) || 0);
                              }}
                              className="h-9 sm:h-10"
                            />
                          </div>

                          <div className="space-y-2">
                            <Label className="text-xs sm:text-sm">Discount (₹)</Label>
                            <Input
                              type="number"
                              step="1"
                              min="0"
                              value={(item.discount_amount || 0) === 0 ? '' : (item.discount_amount || 0) / 100}
                              onChange={(e) => {
                                const val = e.target.value;
                                handleItemChange(index, 'discount_amount', val === '' ? 0 : Math.round(parseFloat(val) * 100) || 0);
                              }}
                              className="h-9 sm:h-10"
                            />
                          </div>

                          <div className="space-y-2">
                            <Label className="text-xs sm:text-sm">Total</Label>
                            <div className="flex items-center h-9 sm:h-10 px-2 sm:px-3 border rounded-md bg-muted text-sm font-semibold">
                              {formatCurrency(calculateItemTotal(item))}
                            </div>
                          </div>
                        </div>

                        {items.length > 1 && (
                          <div className="flex justify-end">
                            <Button
                              variant="destructive"
                              size="sm"
                              onClick={() => handleRemoveItem(index)}
                            >
                              <Trash2 className="mr-2 h-4 w-4" />
                              Remove Item
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

          {/* Invoice Discount */}
          <Card className="border-2 border-primary/20 bg-primary/5">
            <CardHeader>
              <CardTitle>Invoice Discount</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                <Label htmlFor="invoiceDiscount">Additional Discount (₹)</Label>
                <Input
                  id="invoiceDiscount"
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
                <p className="text-xs text-muted-foreground">
                  Additional discount applied to the entire invoice (after item discounts)
                </p>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Summary Sidebar */}
        <div>
          <Card className="sticky top-6">
            <CardHeader>
              <CardTitle>Invoice Summary</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Items List */}
              {items.length > 0 && items.some(item => item.product_name.trim()) && (
                <div className="space-y-2">
                  <p className="text-sm font-medium text-muted-foreground">Items Added:</p>
                  <div className="space-y-2 max-h-60 overflow-y-auto">
                    {items.filter(item => item.product_name.trim()).map((item, index) => (
                      <div key={index} className="p-2 bg-muted rounded-md text-sm">
                        <div className="font-medium truncate" title={item.product_name}>
                          {item.product_name}
                        </div>
                        <div className="flex justify-between text-xs text-muted-foreground mt-1">
                          <span>{item.quantity} {item.uom}</span>
                          <span>{formatCurrency(item.quantity * item.unit_cost)}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <div className="space-y-2 pt-2 border-t">
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Total Items:</span>
                  <span className="font-medium">{items.filter(item => item.product_name.trim()).length}</span>
                </div>
                <div className="flex justify-between text-sm pt-2 border-t">
                  <span className="text-muted-foreground">Subtotal:</span>
                  <span className="font-semibold">{formatCurrency(calculateSubtotal())}</span>
                </div>
                {invoiceDiscount > 0 && (
                  <div className="flex justify-between text-sm text-green-600">
                    <span>Invoice Discount:</span>
                    <span className="font-semibold">-{formatCurrency(invoiceDiscount)}</span>
                  </div>
                )}
                <div className="flex justify-between text-lg font-bold pt-2 border-t">
                  <span>Total:</span>
                  <span>{formatCurrency(calculateTotal())}</span>
                </div>
              </div>

              <div className="space-y-2 pt-4">
                <Button className="w-full" onClick={handleSubmit}>
                  Create Invoice
                </Button>
                <Button
                  variant="outline"
                  className="w-full"
                  onClick={() => router.back()}
                >
                  Cancel
                </Button>
              </div>

              <div className="text-xs text-muted-foreground pt-4 border-t">
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
            setScannerDisabled(false); // Re-enable scanner
            setQuickAddForm({
              product_name: '',
              uom: 'piece',
              quantity: 1,
              unit_cost: 0,
            });
          }
        }}>
          <DialogContent>
          <DialogHeader>
            <DialogTitle>Add Product Details</DialogTitle>
          </DialogHeader>

          <div className="space-y-4">
            <div className="p-3 bg-muted rounded-lg">
              <p className="text-sm text-muted-foreground">Barcode not found in system</p>
              <p className="font-mono font-semibold">{unmappedBarcode}</p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="quickProduct">Product Name *</Label>
              <Input
                id="quickProduct"
                value={quickAddForm.product_name}
                onChange={(e) => setQuickAddForm({ ...quickAddForm, product_name: e.target.value })}
                placeholder="Enter product name"
                autoFocus
              />
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div className="space-y-2">
                <Label htmlFor="quickUom" className="text-sm">Unit</Label>
                <Select
                  value={quickAddForm.uom}
                  onValueChange={(value) => setQuickAddForm({ ...quickAddForm, uom: value })}
                >
                  <SelectTrigger id="quickUom">
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
                <Label htmlFor="quickQty" className="text-sm">Quantity</Label>
                <Input
                  id="quickQty"
                  type="number"
                  step="1"
                  min="1"
                  value={quickAddForm.quantity === 0 ? '' : quickAddForm.quantity}
                  onChange={(e) => {
                    const val = e.target.value;
                    setQuickAddForm({ ...quickAddForm, quantity: val === '' ? 0 : parseFloat(val) || 0 });
                  }}
                  onBlur={(e) => {
                    // Set to 1 if empty when losing focus
                    if (quickAddForm.quantity === 0) {
                      setQuickAddForm({ ...quickAddForm, quantity: 1 });
                    }
                  }}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="quickCost">Cost (₹)</Label>
                <Input
                  id="quickCost"
                  type="number"
                  step="1"
                  min="0"
                  value={quickAddForm.unit_cost === 0 ? '' : quickAddForm.unit_cost / 100}
                  onChange={(e) => {
                    const val = e.target.value;
                    setQuickAddForm({ ...quickAddForm, unit_cost: val === '' ? 0 : Math.round(parseFloat(val) * 100) || 0 });
                  }}
                />
              </div>
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => {
              setUnmappedBarcode(null);
              setScannerDisabled(false); // Re-enable scanner
              setQuickAddForm({
                product_name: '',
                uom: 'piece',
                quantity: 1,
                unit_cost: 0,
              });
            }}>
              Cancel
            </Button>
            <Button onClick={handleQuickAdd}>
              Add to Invoice
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
      )}

      {/* Barcode Scanner Modal */}
      {showScanner && (
        <BarcodeScanner
          onScan={handleCameraScan}
          onClose={() => {
            setShowScanner(false);
            setScannerDisabled(false); // Reset disabled state when closing
          }}
          disabled={scannerDisabled}
        />
      )}
    </div>
  );
}
