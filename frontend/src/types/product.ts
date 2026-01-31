// Retail product types

export interface RetailProduct {
  id: string;
  sku_code: string;
  name: string;
  description?: string;
  retail_price: number; // paise
  current_stock: number;
  uom: string;
  category_name: string;
  category_id: string;
}

export interface ProductCartItem {
  id: string;
  skuId: string;
  productName: string;
  quantity: number;
  unitPrice: number; // in paise (retail_price)
  discount: number; // in paise
  taxRate: number; // percentage (e.g., 18 for 18%)
  uom: string;
  availableStock: number;
  isProduct: true; // distinguish from service items
}
