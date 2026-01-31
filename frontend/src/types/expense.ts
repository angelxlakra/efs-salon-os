// Expense types matching backend schema

export enum ExpenseCategory {
  RENT = 'rent',
  SALARIES = 'salaries',
  UTILITIES = 'utilities',
  SUPPLIES = 'supplies',
  MARKETING = 'marketing',
  MAINTENANCE = 'maintenance',
  INSURANCE = 'insurance',
  TAXES_FEES = 'taxes_fees',
  PROFESSIONAL_SERVICES = 'professional_services',
  OTHER = 'other',
}

export enum RecurrenceType {
  DAILY = 'daily',
  WEEKLY = 'weekly',
  MONTHLY = 'monthly',
  QUARTERLY = 'quarterly',
  YEARLY = 'yearly',
}

export enum ExpenseStatus {
  PENDING = 'pending',
  APPROVED = 'approved',
  REJECTED = 'rejected',
}

export interface ExpenseCreate {
  category: ExpenseCategory;
  amount: number; // paise
  expense_date: string; // YYYY-MM-DD
  description: string;
  vendor_name?: string;
  invoice_number?: string;
  notes?: string;
  is_recurring: boolean;
  recurrence_type?: RecurrenceType;
  staff_id?: string;
  requires_approval: boolean;
}

export interface ExpenseUpdate {
  amount?: number;
  expense_date?: string;
  description?: string;
  vendor_name?: string;
  invoice_number?: string;
  notes?: string;
  staff_id?: string;
}

export interface Expense {
  id: string;
  category: ExpenseCategory;
  amount: number;
  expense_date: string;
  description: string;
  vendor_name?: string;
  invoice_number?: string;
  notes?: string;
  is_recurring: boolean;
  recurrence_type?: RecurrenceType;
  parent_expense_id?: string;
  staff_id?: string;
  status: ExpenseStatus;
  requires_approval: boolean;
  recorded_by: string;
  recorded_at: string;
  approved_by?: string;
  approved_at?: string;
  rejected_by?: string;
  rejected_at?: string;
  rejection_reason?: string;
  created_at: string;
  updated_at: string;
}

export interface ExpenseListResponse {
  items: Expense[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

export interface ExpenseSummary {
  total_amount: number;
  by_category: Record<string, number>;
  approved_count: number;
  pending_count: number;
  rejected_count: number;
}

export interface ExpenseFilters {
  start_date?: string;
  end_date?: string;
  category?: ExpenseCategory;
  status?: ExpenseStatus;
  staff_id?: string;
  is_recurring?: boolean;
  page?: number;
  size?: number;
}
