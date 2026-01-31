import { useState, useEffect } from 'react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { CheckCircle, XCircle, Edit, Trash2 } from 'lucide-react';
import { expenseApi } from '@/lib/api/expenses';
import { ExpenseApprovalDialog } from './expense-approval-dialog';
import type { Expense, ExpenseFilters } from '@/types/expense';
import { ExpenseStatus } from '@/types/expense';
import { toast } from 'sonner';

interface ExpenseListProps {
  filters: ExpenseFilters;
  refreshTrigger: number;
  onExpenseUpdated: () => void;
  onEditExpense: (expense: Expense) => void;
}

export function ExpenseList({ filters, refreshTrigger, onExpenseUpdated, onEditExpense }: ExpenseListProps) {
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

  const getStatusBadge = (status: ExpenseStatus) => {
    const variants = {
      [ExpenseStatus.APPROVED]: 'bg-green-100 text-green-800',
      [ExpenseStatus.PENDING]: 'bg-yellow-100 text-yellow-800',
      [ExpenseStatus.REJECTED]: 'bg-red-100 text-red-800',
    };

    return (
      <Badge className={variants[status]}>
        {status.charAt(0).toUpperCase() + status.slice(1)}
      </Badge>
    );
  };

  if (loading) {
    return <Card className="p-8 text-center text-gray-500">Loading expenses...</Card>;
  }

  if (expenses.length === 0) {
    return (
      <Card className="p-8 text-center text-gray-500">
        No expenses found. Create your first expense to get started.
      </Card>
    );
  }

  return (
    <>
      <Card>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50 border-b">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Date</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Category</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Description</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Amount</th>
                <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase">Status</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {expenses.map((expense) => (
                <tr key={expense.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4 text-sm text-gray-900">{formatDate(expense.expense_date)}</td>
                  <td className="px-6 py-4 text-sm text-gray-600">
                    {expense.category.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase())}
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-900">
                    {expense.description}
                    {expense.vendor_name && (
                      <div className="text-xs text-gray-500 mt-1">Vendor: {expense.vendor_name}</div>
                    )}
                  </td>
                  <td className="px-6 py-4 text-sm text-right font-medium text-gray-900">
                    {formatCurrency(expense.amount)}
                  </td>
                  <td className="px-6 py-4 text-center">{getStatusBadge(expense.status)}</td>
                  <td className="px-6 py-4 text-right">
                    <div className="flex justify-end gap-2">
                      {expense.status === ExpenseStatus.PENDING && (
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => setApprovingExpense(expense)}
                        >
                          <CheckCircle className="h-4 w-4" />
                        </Button>
                      )}
                      {expense.status !== ExpenseStatus.APPROVED && (
                        <>
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => onEditExpense(expense)}
                          >
                            <Edit className="h-4 w-4" />
                          </Button>
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => handleDelete(expense.id)}
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        <div className="px-6 py-4 border-t flex items-center justify-between">
          <div className="text-sm text-gray-500">
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
