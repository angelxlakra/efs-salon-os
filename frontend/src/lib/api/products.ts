import { apiClient } from '../api-client';
import type { RetailProduct } from '@/types/product';

export const productApi = {
  /**
   * Get all retail products (sellable SKUs)
   */
  async listRetailProducts(params?: {
    category_id?: string;
    in_stock_only?: boolean;
  }): Promise<RetailProduct[]> {
    const response = await apiClient.get('/catalog/retail-products', { params });
    return response.data;
  },
};
