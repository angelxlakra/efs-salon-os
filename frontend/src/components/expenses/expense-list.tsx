import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { CheckCircle, Edit, Trash2 } from 'lucide-react';
import { expenseApi } from '@/lib/api/expenses';
import { ExpenseApprovalDialog } from './expense-approval-dialog';
import type { Expense, ExpenseFilters } from '@/types/expense';
import { ExpenseStatus } from '@/types/expense';
import { toast } from 'sonner';
import { useAuthStore } from '@/stores/auth-store';

interface ExpenseListProps {
  filters: ExpenseFilters;
  refreshTrigger: number;
  onExpenseUpdated: () => void;
  onEditExpense: (expense: Expense) => void;
}

export function ExpenseList({ filters, refreshTrigger, onExpenseUpdated, onEditExpense }: ExpenseListProps) {
  const { user } = useAuthStore();
  const isOwner = user?.role === 'owner';
  const [expenses, setExpenses] = useState<Expense[]>([]);
  const [loading, setLoading] = useState(true);
  const [total, setTotal] = useState(0);
  const [approvingExpense, setApprovingExpense] = useState<Expense | null>(null);

  useEffect(() => {
    const loadExpenses = async () => {
      setLoading(true);
      try {
        const data = await expenseApi.list(filters);
        setExpenses(data.items);
        setTotal(data.total);
      } catch (error) {
        console.error('Failed to load expenses:', error);
        toast.error('Failed to load expenses');
      } finally {
        setLoading(false);
      }
    };

    loadExpenses();
  }, [filters, refreshTrigger]);

  const handleDelete = async (id: string) => {
    if (!confirm('Are you sure you want to delete this expense?')) return;

    try {
      await expenseApi.delete(id);
      toast.success('Expense deleted');
      onExpenseUpdated();
    } catch (error) {
      console.error('Failed to delete expense:', error);
      toast.error('Failed to delete expense');
    }
  };

  const formatCurrency = (paise: number) => {
    return `₹${(paise / 100).toLocaleString('en-IN', { minimumFractionDigits: 2 })}`;
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-IN', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  };

  const formatCategory = (category: string) =>
    category.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase());

  const getStatusChip = (status: ExpenseStatus) => {
    const styles: Record<ExpenseStatus, string> = {
      [ExpenseStatus.APPROVED]: 'bg-green-500/40 text-green-400',
      [ExpenseStatus.PENDING]: 'bg-amber-500/40 text-amber-400',
      [ExpenseStatus.REJECTED]: 'bg-red-500/40 text-red-400',
    };
    return (
      <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${styles[status]}`}>
        {status.charAt(0).toUpperCase() + status.slice(1)}
      </span>
    );
  };

  if (loading) {
    return <Card className="p-8 text-center text-text-secondary">Loading expenses...</Card>;
  }

  if (expenses.length === 0) {
    return (
      <Card className="p-8 text-center text-text-secondary">
        No expenses found. Create your first expense to get started.
      </Card>
    );
  }

  return (
    <>
      {/* Mobile Cards */}
      <div className="md:hidden space-y-2">
        {expenses.map((expense) => (
          <div key={expense.id} className="bg-surface-card border border-border-subtle rounded-lg p-4 space-y-2">
            {/* Row 1: date + category chip */}
            <div className="flex items-center justify-between gap-2">
              <span className="text-xs text-text-secondary">{formatDate(expense.expense_date)}</span>
              <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-purple-500/40 text-purple-400">
                {formatCategory(expense.category)}
              </span>
            </div>
            {/* Row 2: description + amount */}
            <div className="flex items-start justify-between gap-2">
              <span className="text-text-primary font-semibold text-sm">{expense.description}</span>
              <span className="text-accent font-bold text-sm shrink-0">{formatCurrency(expense.amount)}</span>
            </div>
            {/* Row 3: payment method / vendor + status */}
            <div className="flex items-center justify-between gap-2 pt-1 border-t border-border-subtle">
              <span className="text-text-secondary text-xs">
                {expense.vendor_name ? `Vendor: ${expense.vendor_name}` : ' '}
              </span>
              <div className="flex items-center gap-1">
                {getStatusChip(expense.status)}
                {expense.status === ExpenseStatus.PENDING && (
                  <Button size="sm" variant="ghost" className="h-7 w-7 p-0" onClick={() => setApprovingExpense(expense)}>
                    <CheckCircle className="h-4 w-4" />
                  </Button>
                )}
                {expense.status !== ExpenseStatus.APPROVED && (
                  <>
                    <Button size="sm" variant="ghost" className="h-7 w-7 p-0" onClick={() => onEditExpense(expense)}>
                      <Edit className="h-4 w-4" />
                    </Button>
                    <Button size="sm" variant="ghost" className="h-7 w-7 p-0" onClick={() => handleDelete(expense.id)}>
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </>
                )}
              </div>
            </div>
          </div>
        ))}
        <div className="text-xs text-text-muted text-center py-2">
          Showing {expenses.length} of {total} expenses
        </div>
      </div>

      {/* Desktop Table */}
      <Card className="hidden md:block">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-surface-page border-b border-border-subtle">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-text-secondary uppercase">Date</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-text-secondary uppercase">Category</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-text-secondary uppercase">Description</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-text-secondary uppercase">Amount</th>
                <th className="px-6 py-3 text-center text-xs font-medium text-text-secondary uppercase">Status</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-text-secondary uppercase">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border-subtle">
              {expenses.map((expense) => (
                <tr key={expense.id} className="hover:bg-surface-row">
                  <td className="px-6 py-4 text-sm text-text-primary">{formatDate(expense.expense_date)}</td>
                  <td className="px-6 py-4 text-sm text-text-secondary">
                    {formatCategory(expense.category)}
                  </td>
                  <td className="px-6 py-4 text-sm text-text-primary">
                    {expense.description}
                    {expense.vendor_name && (
                      <div className="text-xs text-text-muted mt-1">Vendor: {expense.vendor_name}</div>
                    )}
                  </td>
                  <td className="px-6 py-4 text-sm text-right font-medium text-accent">
                    {formatCurrency(expense.amount)}
                  </td>
                  <td className="px-6 py-4 text-center">{getStatusChip(expense.status)}</td>
                  <td className="px-6 py-4 text-right">
                    <div className="flex justify-end gap-2">
                      {expense.status === ExpenseStatus.PENDING && isOwner && (
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => setApprovingExpense(expense)}
                        >
                          <CheckCircle className="h-4 w-4" />
                        </Button>
                      )}
                      {(isOwner || expense.status !== ExpenseStatus.APPROVED) && (
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => onEditExpense(expense)}
                        >
                          <Edit className="h-4 w-4" />
                        </Button>
                      )}
                      {isOwner && (
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => handleDelete(expense.id)}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        <div className="px-6 py-4 border-t border-border-subtle flex items-center justify-between">
          <div className="text-sm text-text-secondary">
            Showing {expenses.length} of {total} expenses
          </div>
        </div>
      </Card>

      {/* Approval Dialog */}
      {approvingExpense && (
        <ExpenseApprovalDialog
          expense={approvingExpense}
          onClose={() => setApprovingExpense(null)}
          onSuccess={() => {
            setApprovingExpense(null);
            onExpenseUpdated();
          }}
        />
      )}
    </>
  );
}
