import { useState } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { CheckCircle, XCircle } from 'lucide-react';
import { expenseApi } from '@/lib/api/expenses';
import type { Expense } from '@/types/expense';
import { toast } from 'sonner';

interface ExpenseApprovalDialogProps {
  expense: Expense;
  onClose: () => void;
  onSuccess: () => void;
}

export function ExpenseApprovalDialog({ expense, onClose, onSuccess }: ExpenseApprovalDialogProps) {
  const [loading, setLoading] = useState(false);
  const [notes, setNotes] = useState('');

  const handleApprove = async (approved: boolean) => {
    setLoading(true);

    try {
      await expenseApi.approve(expense.id, approved, notes || undefined);
      toast.success(approved ? 'Expense approved' : 'Expense rejected');
      onSuccess();
    } catch (error) {
      console.error('Failed to process approval:', error);
      toast.error('Failed to process approval');
    } finally {
      setLoading(false);
    }
  };

  const formatCurrency = (paise: number) => {
    return `₹${(paise / 100).toLocaleString('en-IN', { minimumFractionDigits: 2 })}`;
  };

  return (
    <Dialog open={true} onOpenChange={onClose}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Approve/Reject Expense</DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          <div className="bg-gray-50 p-4 rounded-lg space-y-2">
            <div className="flex justify-between">
              <span className="text-sm text-gray-600">Category:</span>
              <span className="text-sm font-medium">
                {expense.category.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase())}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-sm text-gray-600">Amount:</span>
              <span className="text-sm font-bold">{formatCurrency(expense.amount)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-sm text-gray-600">Description:</span>
              <span className="text-sm">{expense.description}</span>
            </div>
          </div>

          <div>
            <label className="text-sm font-medium block mb-2">Notes (optional)</label>
            <Input
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Add notes for approval/rejection"
            />
          </div>

          <div className="flex gap-2">
            <Button
              className="flex-1"
              variant="outline"
              onClick={() => handleApprove(false)}
              disabled={loading}
            >
              <XCircle className="h-4 w-4 mr-2" />
              Reject
            </Button>
            <Button
              className="flex-1"
              onClick={() => handleApprove(true)}
              disabled={loading}
            >
              <CheckCircle className="h-4 w-4 mr-2" />
              Approve
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
