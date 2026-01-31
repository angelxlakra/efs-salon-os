# Frontend Implementation Guide: Remaining Tasks

## Status Summary

### ✅ Completed
1. **API Client Functions** - All API services created
2. **Type Definitions** - Expense, Product, Reports types created
3. **Expense Management Page** - Fully implemented with all components

### 🔨 Partially Complete - Need Finishing Touches

4. **POS Retail Products** - Types created, needs cart store update and UI components
5. **P&L Report Page** - Types and API ready, needs page component
6. **Inventory Retail Settings** - Needs form field additions
7. **Navigation Menu** - Needs menu items added

---

## Remaining Implementation Tasks

### Task 2: Add Retail Products to POS

#### Step 1: Update Cart Store
**File:** `frontend/src/stores/cart-store.ts`

Add product support by making CartItem flexible:

```typescript
// Update CartItem interface
export interface CartItem {
  id: string;
  // Service fields (optional)
  serviceId?: string;
  serviceName?: string;
  staffId?: string | null;
  staffName?: string | null;
  duration?: number;

  // Product fields (optional)
  skuId?: string;
  productName?: string;
  uom?: string;
  availableStock?: number;

  // Common fields
  itemName: string; // Display name
  quantity: number;
  unitPrice: number; // in paise
  discount: number; // in paise
  taxRate: number; // percentage
  isProduct: boolean; // true for products, false for services
  isBooked: boolean;
}

// Add product-specific action
addProduct: (product: {
  skuId: string;
  productName: string;
  quantity: number;
  unitPrice: number;
  uom: string;
  availableStock: number;
}) => void;
```

Implementation:
```typescript
addProduct: (product) => {
  const newItem: CartItem = {
    id: `cart-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
    skuId: product.skuId,
    productName: product.productName,
    itemName: product.productName,
    quantity: product.quantity,
    unitPrice: product.unitPrice,
    discount: 0,
    taxRate: 18,
    uom: product.uom,
    availableStock: product.availableStock,
    isProduct: true,
    isBooked: false,
  };
  set({ items: [...get().items, newItem] });
},
```

#### Step 2: Create Product Grid Component
**File:** `frontend/src/components/pos/product-grid.tsx`

```typescript
'use client';

import { useState, useEffect } from 'react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Plus, Package } from 'lucide-react';
import { productApi } from '@/lib/api/products';
import { useCartStore } from '@/stores/cart-store';
import type { RetailProduct } from '@/types/product';
import { toast } from 'sonner';

export function ProductGrid() {
  const [products, setProducts] = useState<RetailProduct[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(true);
  const addProduct = useCartStore((state) => state.addProduct);

  useEffect(() => {
    loadProducts();
  }, []);

  const loadProducts = async () => {
    try {
      const data = await productApi.listRetailProducts({ in_stock_only: true });
      setProducts(data);
    } catch (error) {
      console.error('Failed to load products:', error);
      toast.error('Failed to load products');
    } finally {
      setLoading(false);
    }
  };

  const filteredProducts = products.filter(
    (p) =>
      p.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      p.sku_code.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const handleAddToCart = (product: RetailProduct) => {
    if (product.current_stock < 1) {
      toast.error('Product out of stock');
      return;
    }

    addProduct({
      skuId: product.id,
      productName: product.name,
      quantity: 1,
      unitPrice: product.retail_price,
      uom: product.uom,
      availableStock: product.current_stock,
    });

    toast.success(`Added ${product.name} to cart`);
  };

  return (
    <div className="space-y-4">
      <Input
        placeholder="Search products..."
        value={searchQuery}
        onChange={(e) => setSearchQuery(e.target.value)}
      />

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {filteredProducts.map((product) => (
          <Card key={product.id} className="p-4 hover:shadow-md transition-shadow">
            <div className="flex items-start justify-between mb-2">
              <div className="flex-1">
                <h3 className="font-medium text-gray-900">{product.name}</h3>
                <p className="text-xs text-gray-500 mt-1">{product.sku_code}</p>
              </div>
              <Package className="h-5 w-5 text-gray-400" />
            </div>

            <div className="space-y-2">
              <div className="flex justify-between items-center">
                <span className="text-lg font-bold text-gray-900">
                  ₹{(product.retail_price / 100).toFixed(2)}
                </span>
                <Badge variant={product.current_stock > 10 ? 'default' : 'destructive'}>
                  {product.current_stock} {product.uom}
                </Badge>
              </div>

              <Button
                className="w-full"
                size="sm"
                onClick={() => handleAddToCart(product)}
                disabled={product.current_stock < 1}
              >
                <Plus className="h-4 w-4 mr-2" />
                Add to Cart
              </Button>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}
```

#### Step 3: Update POS Page with Tabs
**File:** `frontend/src/app/dashboard/pos/page.tsx`

Add tabs for Services and Products:

```typescript
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ProductGrid } from '@/components/pos/product-grid';

// Inside component:
<Tabs defaultValue="services" className="flex-1">
  <TabsList className="mb-4">
    <TabsTrigger value="services">Services</TabsTrigger>
    <TabsTrigger value="products">Products</TabsTrigger>
  </TabsList>

  <TabsContent value="services">
    <ServiceGrid searchInputRef={serviceSearchRef} />
  </TabsContent>

  <TabsContent value="products">
    <ProductGrid />
  </TabsContent>
</Tabs>
```

#### Step 4: Update CartSidebar to Handle Products
**File:** `frontend/src/components/pos/cart-sidebar.tsx`

Update to display both services and products:

```typescript
// In the cart item rendering:
{item.isProduct ? (
  <div className="flex items-center gap-2">
    <Package className="h-4 w-4 text-gray-400" />
    <span className="font-medium">{item.productName}</span>
    <Badge variant="outline" className="ml-auto">
      {item.uom}
    </Badge>
  </div>
) : (
  <div className="flex items-center gap-2">
    <Scissors className="h-4 w-4 text-gray-400" />
    <span className="font-medium">{item.serviceName}</span>
  </div>
)}
```

#### Step 5: Update Payment Modal to Submit Products
**File:** `frontend/src/components/pos/payment-modal.tsx`

Update bill submission to include products:

```typescript
const billItems = items.map((item) =>
  item.isProduct
    ? {
        sku_id: item.skuId,
        quantity: item.quantity,
        notes: item.notes,
      }
    : {
        service_id: item.serviceId,
        quantity: item.quantity,
        staff_id: item.staffId,
        notes: item.notes,
      }
);
```

---

### Task 3: Create P&L Report Page

**File:** `frontend/src/app/dashboard/reports/profit-loss/page.tsx`

```typescript
'use client';

import { useState } from 'react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { reportApi } from '@/lib/api/reports';
import type { ProfitLossReport } from '@/types/reports';
import { toast } from 'sonner';
import { TrendingUp, TrendingDown, DollarSign } from 'lucide-react';

export default function ProfitLossPage() {
  const [report, setReport] = useState<ProfitLossReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');

  const loadReport = async () => {
    if (!startDate || !endDate) {
      toast.error('Please select both start and end dates');
      return;
    }

    setLoading(true);
    try {
      const data = await reportApi.getProfitLoss({ start_date: startDate, end_date: endDate });
      setReport(data);
    } catch (error) {
      console.error('Failed to load P&L report:', error);
      toast.error('Failed to load report');
    } finally {
      setLoading(false);
    }
  };

  const formatCurrency = (paise: number) => {
    return `₹${(paise / 100).toLocaleString('en-IN', { minimumFractionDigits: 2 })}`;
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Profit & Loss Statement</h1>
        <p className="text-sm text-gray-500 mt-1">
          Comprehensive financial performance report
        </p>
      </div>

      {/* Date Range Selector */}
      <Card className="p-4">
        <div className="flex gap-4 items-end">
          <div className="flex-1">
            <label className="text-sm font-medium block mb-2">Start Date</label>
            <Input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} />
          </div>
          <div className="flex-1">
            <label className="text-sm font-medium block mb-2">End Date</label>
            <Input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} />
          </div>
          <Button onClick={loadReport} disabled={loading}>
            {loading ? 'Loading...' : 'Generate Report'}
          </Button>
        </div>
      </Card>

      {report && (
        <>
          {/* Revenue Section */}
          <Card className="p-6">
            <h2 className="text-lg font-bold mb-4">Revenue</h2>
            <div className="space-y-2">
              <div className="flex justify-between">
                <span className="text-gray-600">Gross Revenue</span>
                <span className="font-medium">{formatCurrency(report.revenue.gross_revenue)}</span>
              </div>
              <div className="flex justify-between text-red-600">
                <span>Less: Discounts</span>
                <span>({formatCurrency(report.revenue.discount_amount)})</span>
              </div>
              <div className="flex justify-between text-red-600">
                <span>Less: Refunds</span>
                <span>({formatCurrency(report.revenue.refund_amount)})</span>
              </div>
              <div className="flex justify-between pt-2 border-t font-bold">
                <span>Net Revenue</span>
                <span>{formatCurrency(report.revenue.net_revenue)}</span>
              </div>
            </div>
          </Card>

          {/* COGS Section */}
          <Card className="p-6">
            <h2 className="text-lg font-bold mb-4">Cost of Goods Sold</h2>
            <div className="space-y-2">
              <div className="flex justify-between">
                <span className="text-gray-600">Service Materials</span>
                <span>{formatCurrency(report.cogs.service_cogs)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Retail Products</span>
                <span>{formatCurrency(report.cogs.product_cogs)}</span>
              </div>
              <div className="flex justify-between pt-2 border-t font-bold">
                <span>Total COGS</span>
                <span>{formatCurrency(report.cogs.total_cogs)}</span>
              </div>
            </div>
          </Card>

          {/* Operating Expenses Section */}
          <Card className="p-6">
            <h2 className="text-lg font-bold mb-4">Operating Expenses</h2>
            <div className="space-y-2">
              {Object.entries(report.operating_expenses.by_category).map(([category, amount]) => (
                <div key={category} className="flex justify-between">
                  <span className="text-gray-600">
                    {category.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase())}
                  </span>
                  <span>{formatCurrency(amount)}</span>
                </div>
              ))}
              <div className="flex justify-between pt-2 border-t font-bold">
                <span>Total Expenses</span>
                <span>{formatCurrency(report.operating_expenses.total_expenses)}</span>
              </div>
            </div>
          </Card>

          {/* Profitability Section */}
          <Card className="p-6 bg-gradient-to-br from-blue-50 to-indigo-50">
            <h2 className="text-lg font-bold mb-4">Profitability</h2>
            <div className="space-y-3">
              <div className="flex justify-between items-center">
                <span className="text-gray-700">Gross Profit</span>
                <div className="text-right">
                  <div className="font-bold text-lg">
                    {formatCurrency(report.profitability.gross_profit)}
                  </div>
                  <div className="text-sm text-gray-600">
                    {report.profitability.gross_margin_percent.toFixed(2)}% margin
                  </div>
                </div>
              </div>
              <div className="flex justify-between items-center pt-3 border-t-2">
                <span className="font-bold text-lg">Net Profit</span>
                <div className="text-right">
                  <div className="font-bold text-2xl text-blue-600">
                    {formatCurrency(report.profitability.net_profit)}
                  </div>
                  <div className="text-sm text-gray-600">
                    {report.profitability.net_margin_percent.toFixed(2)}% margin
                  </div>
                </div>
              </div>
            </div>
          </Card>

          {/* Summary Stats */}
          <div className="grid grid-cols-2 gap-4">
            <Card className="p-4">
              <div className="text-sm text-gray-600">Total Bills</div>
              <div className="text-2xl font-bold mt-1">{report.total_bills}</div>
            </Card>
            <Card className="p-4">
              <div className="text-sm text-gray-600">Tips Collected</div>
              <div className="text-2xl font-bold mt-1">{formatCurrency(report.tips_collected)}</div>
            </Card>
          </div>
        </>
      )}
    </div>
  );
}
```

---

### Task 4: Add Retail Settings to Inventory

**File:** `frontend/src/components/inventory/sku-form.tsx` (or similar)

Add to the SKU form fields:

```typescript
{/* Retail Sales Section */}
<div className="col-span-2 border-t pt-4">
  <h3 className="font-medium mb-4">Retail Sales</h3>

  <div className="space-y-4">
    <div className="flex items-center space-x-2">
      <Checkbox
        id="is_sellable"
        checked={formData.is_sellable}
        onCheckedChange={(checked) => setFormData({ ...formData, is_sellable: !!checked })}
      />
      <label htmlFor="is_sellable" className="text-sm font-medium cursor-pointer">
        Available for retail sale
      </label>
    </div>

    {formData.is_sellable && (
      <div className="grid grid-cols-2 gap-4 pl-6">
        <div>
          <label className="text-sm font-medium block mb-2">Retail Price (₹)</label>
          <Input
            type="number"
            step="0.01"
            min="0"
            value={formData.retail_price ? formData.retail_price / 100 : ''}
            onChange={(e) => setFormData({
              ...formData,
              retail_price: Math.round(parseFloat(e.target.value || '0') * 100)
            })}
            placeholder="0.00"
          />
        </div>

        <div>
          <label className="text-sm font-medium block mb-2">Markup %</label>
          <Input
            type="number"
            step="0.1"
            min="0"
            value={formData.retail_markup_percent || ''}
            onChange={(e) => setFormData({
              ...formData,
              retail_markup_percent: parseFloat(e.target.value || '0')
            })}
            placeholder="0.0"
          />
          <p className="text-xs text-gray-500 mt-1">
            Calculated from cost: ₹{formData.avg_cost_per_unit ? (formData.avg_cost_per_unit / 100).toFixed(2) : '0.00'}
          </p>
        </div>
      </div>
    )}
  </div>
</div>
```

---

### Task 6: Update Navigation Menu

**File:** `frontend/src/components/dashboard/sidebar.tsx` (or navigation component)

Add menu items:

```typescript
const menuItems = [
  // ... existing items
  {
    label: 'Expenses',
    href: '/dashboard/expenses',
    icon: DollarSign,
    roles: ['owner'],
  },
  {
    label: 'Reports',
    icon: TrendingUp,
    roles: ['owner', 'receptionist'],
    children: [
      {
        label: 'Dashboard',
        href: '/dashboard/reports',
      },
      {
        label: 'Profit & Loss',
        href: '/dashboard/reports/profit-loss',
      },
    ],
  },
  // ... rest of items
];
```

---

## Testing Checklist

### Expense Management
- [ ] Create expense with all fields
- [ ] Create recurring expense
- [ ] Filter expenses by date, category, status
- [ ] Edit pending expense
- [ ] Approve expense
- [ ] Reject expense with notes
- [ ] Delete pending expense
- [ ] View expense summary cards

### Retail Products in POS
- [ ] View retail products in POS
- [ ] Search products
- [ ] Add product to cart
- [ ] Check stock validation
- [ ] Mix services and products in cart
- [ ] Complete checkout with products
- [ ] Verify stock reduction after bill posting

### P&L Report
- [ ] Select date range
- [ ] Generate report
- [ ] View all sections (revenue, COGS, expenses, profitability)
- [ ] Verify calculations
- [ ] Check margin percentages

### Inventory Retail Settings
- [ ] Mark SKU as sellable
- [ ] Set retail price
- [ ] Set markup percentage
- [ ] View in retail products catalog

---

## Notes

1. **Toast Notifications**: Install `sonner` if not already: `npm install sonner`
2. **Icons**: Using lucide-react icons
3. **Currency Format**: All amounts in paise, divide by 100 for display
4. **Date Format**: Use 'en-IN' locale for Indian formatting
5. **Permissions**: Expenses are owner-only, P&L is owner/receptionist

---

## File Structure Summary

```
frontend/src/
├── app/dashboard/
│   ├── expenses/
│   │   └── page.tsx ✅
│   ├── reports/
│   │   └── profit-loss/
│   │       └── page.tsx 📝
│   └── pos/
│       └── page.tsx 🔧 (needs tabs update)
├── components/
│   ├── expenses/
│   │   ├── expense-list.tsx ✅
│   │   ├── expense-dialog.tsx ✅
│   │   ├── expense-approval-dialog.tsx ✅
│   │   ├── expense-filters-bar.tsx ✅
│   │   └── expense-summary-cards.tsx ✅
│   ├── pos/
│   │   ├── product-grid.tsx 📝
│   │   ├── cart-sidebar.tsx 🔧
│   │   └── payment-modal.tsx 🔧
│   └── inventory/
│       └── sku-form.tsx 🔧
├── lib/api/
│   ├── expenses.ts ✅
│   ├── products.ts ✅
│   └── reports.ts ✅
├── types/
│   ├── expense.ts ✅
│   ├── product.ts ✅
│   └── reports.ts ✅
└── stores/
    └── cart-store.ts 🔧

✅ = Complete
📝 = Needs creation
🔧 = Needs modification
```
