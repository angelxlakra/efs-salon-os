import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { ExpenseForm } from './expense-form';
import type { Expense } from '@/types/expense';

interface ExpenseDialogProps {
  isOpen: boolean;
  expense?: Expense | null;
  onClose: () => void;
  onSuccess: () => void;
}

export function ExpenseDialog({ isOpen, expense, onClose, onSuccess }: ExpenseDialogProps) {
  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>{expense ? 'Edit Expense' : 'Create New Expense'}</DialogTitle>
        </DialogHeader>

        <ExpenseForm 
          expense={expense} 
          onCancel={onClose} 
          onSuccess={onSuccess} 
        />
      </DialogContent>
    </Dialog>
  );
}
