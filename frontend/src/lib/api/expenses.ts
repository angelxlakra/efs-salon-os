import { apiClient } from '../api-client';
import type {
  Expense,
  ExpenseCreate,
  ExpenseUpdate,
  ExpenseListResponse,
  ExpenseSummary,
  ExpenseFilters,
} from '@/types/expense';

export const expenseApi = {
  /**
   * Create a new expense
   */
  async create(data: ExpenseCreate): Promise<Expense> {
    const response = await apiClient.post('/expenses', data);
    return response.data;
  },

  /**
   * List expenses with filters
   */
  async list(filters?: ExpenseFilters): Promise<ExpenseListResponse> {
    const response = await apiClient.get('/expenses', { params: filters });
    return response.data;
  },

  /**
   * Get expense summary
   */
  async getSummary(startDate?: string, endDate?: string): Promise<ExpenseSummary> {
    const response = await apiClient.get('/expenses/summary', {
      params: {
        start_date: startDate,
        end_date: endDate,
      },
    });
    return response.data;
  },

  /**
   * Get expense by ID
   */
  async getById(id: string): Promise<Expense> {
    const response = await apiClient.get(`/expenses/${id}`);
    return response.data;
  },

  /**
   * Update expense
   */
  async update(id: string, data: ExpenseUpdate): Promise<Expense> {
    const response = await apiClient.patch(`/expenses/${id}`, data);
    return response.data;
  },

  /**
   * Approve or reject expense
   */
  async approve(id: string, approved: boolean, notes?: string): Promise<Expense> {
    const response = await apiClient.post(`/expenses/${id}/approve`, {
      approved,
      notes,
    });
    return response.data;
  },

  /**
   * Delete expense
   */
  async delete(id: string): Promise<void> {
    await apiClient.delete(`/expenses/${id}`);
  },
};
