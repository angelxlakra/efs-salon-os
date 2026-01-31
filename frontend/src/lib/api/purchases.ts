/**
 * Purchase Management API Client
 *
 * Handles API calls for suppliers, purchase invoices, and payments.
 */

import { apiClient } from '../api-client';

// ============ Types ============

export interface Supplier {
  id: string;
  name: string;
  contact_person?: string;
  phone?: string;
  email?: string;
  address?: string;
  gstin?: string;
  payment_terms?: string;
  notes?: string;
  is_active: boolean;
  total_outstanding: number;
  total_purchases: number;
  created_at: string;
  updated_at: string;
}

export interface SupplierListItem {
  id: string;
  name: string;
  contact_person?: string;
  phone?: string;
  total_outstanding: number;
  total_purchases: number;
  is_active: boolean;
}

export interface SupplierListResponse {
  items: SupplierListItem[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

export interface SupplierCreate {
  name: string;
  contact_person?: string;
  phone?: string;
  email?: string;
  address?: string;
  gstin?: string;
  payment_terms?: string;
  notes?: string;
}

export interface SupplierUpdate {
  name?: string;
  contact_person?: string;
  phone?: string;
  email?: string;
  address?: string;
  gstin?: string;
  payment_terms?: string;
  notes?: string;
  is_active?: boolean;
}

export interface PurchaseItem {
  id: string;
  purchase_invoice_id: string;
  sku_id?: string;
  product_name: string;
  barcode?: string;
  uom: string;
  quantity: number;
  unit_cost: number;
  total_cost: number;
  created_at: string;
}

export interface PurchaseItemCreate {
  sku_id?: string;
  product_name: string;
  barcode?: string;
  uom: string;
  quantity: number;
  unit_cost: number;
}

export interface PurchaseInvoice {
  id: string;
  supplier_id: string;
  supplier_name?: string;
  invoice_number: string;
  invoice_date: string;
  due_date?: string;
  total_amount: number;
  paid_amount: number;
  balance_due: number;
  status: 'draft' | 'received' | 'partially_paid' | 'paid';
  received_at?: string;
  received_by?: string;
  notes?: string;
  invoice_file_url?: string;
  created_by: string;
  created_at: string;
  updated_at: string;
  items: PurchaseItem[];
}

export interface PurchaseInvoiceListItem {
  id: string;
  supplier_id: string;
  supplier_name: string;
  invoice_number: string;
  invoice_date: string;
  due_date?: string;
  total_amount: number;
  paid_amount: number;
  balance_due: number;
  status: 'draft' | 'received' | 'partially_paid' | 'paid';
  created_at: string;
}

export interface PurchaseInvoiceListResponse {
  items: PurchaseInvoiceListItem[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

export interface PurchaseInvoiceCreate {
  supplier_id: string;
  invoice_number: string;
  invoice_date: string;
  due_date?: string;
  notes?: string;
  invoice_file_url?: string;
  items: PurchaseItemCreate[];
}

export interface PurchaseInvoiceUpdate {
  invoice_number?: string;
  invoice_date?: string;
  due_date?: string;
  notes?: string;
  invoice_file_url?: string;
  items?: PurchaseItemCreate[];
}

export interface SupplierPayment {
  id: string;
  supplier_id: string;
  supplier_name?: string;
  purchase_invoice_id?: string;
  invoice_number?: string;
  payment_date: string;
  amount: number;
  payment_method: string;
  reference_number?: string;
  notes?: string;
  recorded_by: string;
  recorded_at: string;
  created_at: string;
}

export interface SupplierPaymentCreate {
  supplier_id: string;
  purchase_invoice_id?: string;
  payment_date: string;
  amount: number;
  payment_method: string;
  reference_number?: string;
  notes?: string;
}

export interface SupplierPaymentListResponse {
  items: SupplierPayment[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

export interface BarcodeSearchRequest {
  barcode: string;
}

export interface BarcodeSearchResponse {
  found: boolean;
  sku_id?: string;
  product_name?: string;
  barcode?: string;
  avg_cost_per_unit?: number;
  uom?: string;
  current_stock?: number;
}

// ============ API Functions ============

/**
 * Supplier Management
 */

export const purchaseApi = {
  // Suppliers
  createSupplier: async (data: SupplierCreate): Promise<Supplier> => {
    const response = await apiClient.post('/purchases/suppliers', data);
    return response.data;
  },

  listSuppliers: async (params?: {
    page?: number;
    size?: number;
    search?: string;
    active_only?: boolean;
  }): Promise<SupplierListResponse> => {
    const response = await apiClient.get('/purchases/suppliers', { params });
    return response.data;
  },

  getSupplier: async (id: string): Promise<Supplier> => {
    const response = await apiClient.get(`/purchases/suppliers/${id}`);
    return response.data;
  },

  updateSupplier: async (id: string, data: SupplierUpdate): Promise<Supplier> => {
    const response = await apiClient.patch(`/purchases/suppliers/${id}`, data);
    return response.data;
  },

  // Purchase Invoices
  createPurchaseInvoice: async (data: PurchaseInvoiceCreate): Promise<PurchaseInvoice> => {
    const response = await apiClient.post('/purchases/invoices', data);
    return response.data;
  },

  listPurchaseInvoices: async (params?: {
    page?: number;
    size?: number;
    supplier_id?: string;
    status?: string;
    start_date?: string;
    end_date?: string;
  }): Promise<PurchaseInvoiceListResponse> => {
    const response = await apiClient.get('/purchases/invoices', { params });
    return response.data;
  },

  getPurchaseInvoice: async (id: string): Promise<PurchaseInvoice> => {
    const response = await apiClient.get(`/purchases/invoices/${id}`);
    return response.data;
  },

  updatePurchaseInvoice: async (id: string, data: PurchaseInvoiceUpdate): Promise<PurchaseInvoice> => {
    const response = await apiClient.patch(`/purchases/invoices/${id}`, data);
    return response.data;
  },

  markGoodsReceived: async (id: string, received_at?: string): Promise<PurchaseInvoice> => {
    const response = await apiClient.post(`/purchases/invoices/${id}/receive`, {
      received_at: received_at || new Date().toISOString(),
    });
    return response.data;
  },

  // Supplier Payments
  recordPayment: async (data: SupplierPaymentCreate): Promise<SupplierPayment> => {
    const response = await apiClient.post('/purchases/payments', data);
    return response.data;
  },

  listPayments: async (params?: {
    page?: number;
    size?: number;
    supplier_id?: string;
    invoice_id?: string;
    start_date?: string;
    end_date?: string;
  }): Promise<SupplierPaymentListResponse> => {
    const response = await apiClient.get('/purchases/payments', { params });
    return response.data;
  },

  // Barcode Lookup
  searchByBarcode: async (barcode: string): Promise<BarcodeSearchResponse> => {
    const response = await apiClient.post('/purchases/barcode-search', { barcode });
    return response.data;
  },
};
