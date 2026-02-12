import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Checkbox } from '@/components/ui/checkbox';
import { expenseApi } from '@/lib/api/expenses';
import { ExpenseCategory, RecurrenceType, type Expense, type ExpenseCreate } from '@/types/expense';
import { toast } from 'sonner';
import { useAuthStore } from '@/stores/auth-store';

interface ExpenseFormProps {
  expense?: Expense | null;
  onCancel: () => void;
  onSuccess: () => void;
}

export function ExpenseForm({ expense, onCancel, onSuccess }: ExpenseFormProps) {
  const { user } = useAuthStore();
  const [loading, setLoading] = useState(false);
  const [formData, setFormData] = useState<Partial<ExpenseCreate>>({
    category: ExpenseCategory.OTHER,
    amount: 0,
    expense_date: new Date().toISOString().split('T')[0],
    description: '',
    is_recurring: false,
    requires_approval: false,
  });

  // Filter categories based on user role
  const availableCategories = Object.values(ExpenseCategory).filter((cat) => {
    // Receptionist cannot create rent or salary expenses
    if (user?.role === 'receptionist') {
      return cat !== ExpenseCategory.RENT && cat !== ExpenseCategory.SALARIES;
    }
    return true;
  });

  useEffect(() => {
    if (expense) {
      setFormData({
        category: expense.category,
        amount: expense.amount,
        expense_date: expense.expense_date,
        description: expense.description,
        vendor_name: expense.vendor_name,
        invoice_number: expense.invoice_number,
        notes: expense.notes,
        is_recurring: expense.is_recurring,
        recurrence_type: expense.recurrence_type,
        requires_approval: expense.requires_approval,
      });
    }
  }, [expense]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    try {
      if (expense) {
        await expenseApi.update(expense.id, formData);
        toast.success('Expense updated');
      } else {
        await expenseApi.create(formData as ExpenseCreate);
        toast.success('Expense created');
      }
      onSuccess();
    } catch (error) {
      console.error('Failed to save expense:', error);
      toast.error('Failed to save expense');
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="text-sm font-medium block mb-2">Category *</label>
          <Select
            value={formData.category}
            onValueChange={(value) => setFormData({ ...formData, category: value as ExpenseCategory })}
          >
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {availableCategories.map((cat) => (
                <SelectItem key={cat} value={cat}>
                  {cat.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase())}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div>
          <label className="text-sm font-medium block mb-2">Amount (₹) *</label>
          <Input
            type="number"
            step="0.01"
            min="0"
            value={formData.amount ? formData.amount / 100 : ''}
            onChange={(e) => setFormData({ ...formData, amount: Math.round(parseFloat(e.target.value || '0') * 100) })}
            required
          />
        </div>

        <div>
          <label className="text-sm font-medium block mb-2">Date *</label>
          <Input
            type="date"
            value={formData.expense_date}
            onChange={(e) => setFormData({ ...formData, expense_date: e.target.value })}
            required
          />
        </div>

        <div>
          <label className="text-sm font-medium block mb-2">Vendor Name</label>
          <Input
            value={formData.vendor_name || ''}
            onChange={(e) => setFormData({ ...formData, vendor_name: e.target.value })}
          />
        </div>

        <div className="md:col-span-2">
          <label className="text-sm font-medium block mb-2">Description *</label>
          <Input
            value={formData.description}
            onChange={(e) => setFormData({ ...formData, description: e.target.value })}
            required
          />
        </div>

        <div>
          <label className="text-sm font-medium block mb-2">Invoice Number</label>
          <Input
            value={formData.invoice_number || ''}
            onChange={(e) => setFormData({ ...formData, invoice_number: e.target.value })}
          />
        </div>

        <div className="md:col-span-2">
          <label className="text-sm font-medium block mb-2">Notes</label>
          <Input
            value={formData.notes || ''}
            onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
          />
        </div>

        <div className="md:col-span-2 space-y-4">
          <div className="flex items-center space-x-2">
            <Checkbox
              id="recurring"
              checked={formData.is_recurring}
              onCheckedChange={(checked) => setFormData({ ...formData, is_recurring: !!checked })}
            />
            <label htmlFor="recurring" className="text-sm font-medium cursor-pointer">
              Recurring Expense
            </label>
          </div>

          {formData.is_recurring && (
            <div>
              <label className="text-sm font-medium block mb-2">Recurrence Type *</label>
              <Select
                value={formData.recurrence_type}
                onValueChange={(value) => setFormData({ ...formData, recurrence_type: value as RecurrenceType })}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select frequency" />
                </SelectTrigger>
                <SelectContent>
                  {Object.values(RecurrenceType).map((type) => (
                    <SelectItem key={type} value={type}>
                      {type.charAt(0).toUpperCase() + type.slice(1)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          )}

          <div className="flex items-center space-x-2">
            <Checkbox
              id="approval"
              checked={formData.requires_approval}
              onCheckedChange={(checked) => setFormData({ ...formData, requires_approval: !!checked })}
            />
            <label htmlFor="approval" className="text-sm font-medium cursor-pointer">
              Requires Approval
            </label>
          </div>
        </div>
      </div>

      <div className="flex justify-end gap-2 pt-4">
        <Button type="button" variant="outline" onClick={onCancel} disabled={loading}>
          Cancel
        </Button>
        <Button type="submit" disabled={loading}>
          {loading ? 'Saving...' : expense ? 'Update Expense' : 'Create Expense'}
        </Button>
      </div>
    </form>
  );
}
