'use client';

import { useState, useEffect } from 'react';
import { Plus, ArrowLeft } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { ExpenseList } from '@/components/expenses/expense-list';
import { ExpenseForm } from '@/components/expenses/expense-form';
import { ExpenseSummaryCards } from '@/components/expenses/expense-summary-cards';
import { ExpenseFiltersBar } from '@/components/expenses/expense-filters-bar';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { expenseApi } from '@/lib/api/expenses';
import type { Expense, ExpenseSummary, ExpenseFilters } from '@/types/expense';
import { toast } from 'sonner';

export default function ExpensesPage() {
  const [view, setView] = useState<'list' | 'form'>('list');
  const [editingExpense, setEditingExpense] = useState<Expense | null>(null);
  const [summary, setSummary] = useState<ExpenseSummary | null>(null);
  const [filters, setFilters] = useState<ExpenseFilters>({
    page: 1,
    size: 20,
  });
  const [refreshTrigger, setRefreshTrigger] = useState(0);

  // Load summary
  useEffect(() => {
    const loadSummary = async () => {
      try {
        const data = await expenseApi.getSummary(filters.start_date, filters.end_date);
        setSummary(data);
      } catch (error) {
        console.error('Failed to load expense summary:', error);
      }
    };

    loadSummary();
  }, [filters.start_date, filters.end_date, refreshTrigger]);

  const handleExpenseSuccess = () => {
    setView('list');
    setEditingExpense(null);
    setRefreshTrigger((prev) => prev + 1);
  };

  const handleEditExpense = (expense: Expense) => {
    setEditingExpense(expense);
    setView('form');
  };

  const handleCreateExpense = () => {
    setEditingExpense(null);
    setView('form');
  };

  if (view === 'form') {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={() => setView('list')}>
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">
              {editingExpense ? 'Edit Expense' : 'New Expense'}
            </h1>
            <p className="text-sm text-gray-500 mt-1">
              {editingExpense ? `Updating expense from ${editingExpense.expense_date}` : 'Record a new business expense'}
            </p>
          </div>
        </div>

        <div className="max-w-3xl">
          <Card>
            <CardHeader>
              <CardTitle>Expense Details</CardTitle>
            </CardHeader>
            <CardContent>
              <ExpenseForm 
                expense={editingExpense}
                onCancel={() => setView('list')} 
                onSuccess={handleExpenseSuccess} 
              />
            </CardContent>
          </Card>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Expenses</h1>
          <p className="text-sm text-gray-500 mt-1">
            Track and manage business expenses
          </p>
        </div>
        <Button onClick={handleCreateExpense}>
          <Plus className="h-4 w-4 mr-2" />
          New Expense
        </Button>
      </div>

      {/* Summary Cards */}
      {summary && <ExpenseSummaryCards summary={summary} />}

      {/* Filters */}
      <ExpenseFiltersBar filters={filters} onFiltersChange={setFilters} />

      {/* Expense List */}
      <ExpenseList
        filters={filters}
        refreshTrigger={refreshTrigger}
        onExpenseUpdated={() => setRefreshTrigger((prev) => prev + 1)}
        onEditExpense={handleEditExpense}
      />
    </div>
  );
}
