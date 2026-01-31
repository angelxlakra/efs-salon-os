'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Package, Search } from 'lucide-react';
import { productApi } from '@/lib/api/products';
import type { RetailProduct } from '@/types/product';
import { useCartStore } from '@/stores/cart-store';
import { toast } from 'sonner';

interface ProductGridProps {
  onProductAdded?: () => void;
}

export function ProductGrid({ onProductAdded }: ProductGridProps) {
  const [products, setProducts] = useState<RetailProduct[]>([]);
  const [filteredProducts, setFilteredProducts] = useState<RetailProduct[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [categoryFilter, setCategoryFilter] = useState<string>('all');

  const addItem = useCartStore(state => state.addItem);

  useEffect(() => {
    loadProducts();
  }, []);

  useEffect(() => {
    filterProducts();
  }, [searchTerm, categoryFilter, products]);

  const loadProducts = async () => {
    setLoading(true);
    try {
      const data = await productApi.listRetailProducts({
        in_stock_only: false, // Show all sellable items, even out of stock
      });
      setProducts(data);
      setFilteredProducts(data);
    } catch (error) {
      console.error('Failed to load products:', error);
      toast.error('Failed to load products');
    } finally {
      setLoading(false);
    }
  };

  const filterProducts = () => {
    let filtered = products;

    // Filter by category
    if (categoryFilter !== 'all') {
      filtered = filtered.filter(p => p.category_id === categoryFilter);
    }

    // Filter by search term
    if (searchTerm) {
      const term = searchTerm.toLowerCase();
      filtered = filtered.filter(
        p =>
          p.name.toLowerCase().includes(term) ||
          p.sku_code.toLowerCase().includes(term) ||
          p.category_name?.toLowerCase().includes(term)
      );
    }

    setFilteredProducts(filtered);
  };

  const handleProductClick = (product: RetailProduct) => {
    if (product.current_stock <= 0) {
      toast.error('Product out of stock');
      return;
    }

    addItem({
      isProduct: true,
      skuId: product.id,
      productName: product.name,
      quantity: 1,
      unitPrice: product.retail_price,
      discount: 0,
      taxRate: 18, // GST rate
    });

    toast.success(`Added ${product.name} to cart`);
    onProductAdded?.();
  };

  const formatCurrency = (paise: number) => {
    return `₹${(paise / 100).toLocaleString('en-IN', { minimumFractionDigits: 2 })}`;
  };

  // Get unique categories
  const categories = Array.from(new Set(products.map(p => p.category_name).filter(Boolean)));

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-muted-foreground">Loading products...</div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Filters */}
      <div className="flex gap-4">
        <div className="flex-1 relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search products..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="pl-10"
          />
        </div>
        <Select value={categoryFilter} onValueChange={setCategoryFilter}>
          <SelectTrigger className="w-[200px]">
            <SelectValue placeholder="All Categories" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Categories</SelectItem>
            {categories.map((cat) => (
              <SelectItem key={cat} value={cat || 'uncategorized'}>
                {cat || 'Uncategorized'}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Product Grid */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
        {filteredProducts.map((product) => (
          <Card
            key={product.id}
            className={`cursor-pointer transition-all hover:shadow-md ${
              product.current_stock <= 0 ? 'opacity-50 cursor-not-allowed' : ''
            }`}
            onClick={() => handleProductClick(product)}
          >
            <CardContent className="p-4">
              <div className="flex flex-col h-full">
                <div className="flex items-start justify-between mb-2">
                  <Package className="h-5 w-5 text-blue-600" />
                  <span
                    className={`text-xs px-2 py-1 rounded ${
                      product.current_stock > 10
                        ? 'bg-green-100 text-green-700'
                        : product.current_stock > 0
                        ? 'bg-yellow-100 text-yellow-700'
                        : 'bg-red-100 text-red-700'
                    }`}
                  >
                    {product.current_stock > 0 ? `${product.current_stock} ${product.uom}` : 'Out of stock'}
                  </span>
                </div>

                <h3 className="font-medium text-sm mb-1 line-clamp-2">{product.name}</h3>

                <p className="text-xs text-muted-foreground mb-2">{product.sku_code}</p>

                {product.category_name && (
                  <p className="text-xs text-muted-foreground mb-2">{product.category_name}</p>
                )}

                <div className="mt-auto">
                  <div className="text-lg font-bold text-blue-600">
                    {formatCurrency(product.retail_price)}
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {filteredProducts.length === 0 && (
        <div className="text-center py-12 text-muted-foreground">
          <Package className="h-12 w-12 mx-auto mb-4 opacity-20" />
          <p>No products found</p>
        </div>
      )}
    </div>
  );
}
