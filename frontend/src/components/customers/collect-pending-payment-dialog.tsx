'use client';

import { useState } from 'react';
import { Loader2, Wallet, CreditCard, Banknote } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { apiClient } from '@/lib/api-client';
import { toast } from 'sonner';

interface CollectPendingPaymentDialogProps {
  open: boolean;
  onClose: () => void;
  customerId: string;
  customerName: string;
  pendingBalance: number; // in paise
  onSuccess?: () => void;
}

type PaymentMethod = 'cash' | 'card' | 'upi';

export function CollectPendingPaymentDialog({
  open,
  onClose,
  customerId,
  customerName,
  pendingBalance,
  onSuccess,
}: CollectPendingPaymentDialogProps) {
  const [paymentMethod, setPaymentMethod] = useState<PaymentMethod>('cash');
  const [amount, setAmount] = useState((pendingBalance / 100).toFixed(2));
  const [reference, setReference] = useState('');
  const [notes, setNotes] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const formatPrice = (paise: number) => {
    return `₹${(paise / 100).toLocaleString('en-IN', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    })}`;
  };

  const handleSubmit = async () => {
    const amountNum = parseFloat(amount);

    if (isNaN(amountNum) || amountNum <= 0) {
      toast.error('Please enter a valid amount');
      return;
    }

    if (amountNum > pendingBalance / 100) {
      toast.error('Amount exceeds pending balance');
      return;
    }

    try {
      setIsSubmitting(true);

      await apiClient.post('/pos/pending-payments/collect', {
        customer_id: customerId,
        amount: amountNum,
        payment_method: paymentMethod,
        reference_number: reference || undefined,
        notes: notes || undefined,
      });

      toast.success('Payment collected successfully!');
      onSuccess?.();
      handleClose();
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to collect payment');
      console.error('Collect payment error:', error);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleClose = () => {
    if (!isSubmitting) {
      setPaymentMethod('cash');
      setAmount((pendingBalance / 100).toFixed(2));
      setReference('');
      setNotes('');
      onClose();
    }
  };

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="max-h-[90vh] overflow-y-auto" style={{ maxWidth: 'min(32rem, calc(100vw - 2rem))' }}>
        <DialogHeader>
          <DialogTitle>Collect Pending Payment</DialogTitle>
          <DialogDescription>
            Collect pending balance from {customerName}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 sm:space-y-5 mt-4">
          {/* Pending Balance Info */}
          <div className="bg-red-50 rounded-lg p-3 sm:p-4 border border-red-200">
            <div className="flex justify-between items-center">
              <span className="text-sm font-medium text-red-900">Pending Balance</span>
              <span className="text-xl sm:text-2xl font-bold text-red-600">
                {formatPrice(pendingBalance)}
              </span>
            </div>
          </div>

          {/* Payment Method Selection */}
          <div className="space-y-2">
            <Label>Payment Method</Label>
            <RadioGroup
              value={paymentMethod}
              onValueChange={(value) => setPaymentMethod(value as PaymentMethod)}
              className="grid grid-cols-3 gap-2 sm:gap-3"
            >
              {[
                { id: 'cash', label: 'Cash', icon: Banknote, color: 'text-green-600' },
                { id: 'card', label: 'Card', icon: CreditCard, color: 'text-blue-600' },
                { id: 'upi', label: 'UPI', icon: Wallet, color: 'text-purple-600' },
              ].map((method) => (
                <div key={method.id}>
                  <RadioGroupItem value={method.id} id={`pending-${method.id}`} className="peer sr-only" />
                  <Label
                    htmlFor={`pending-${method.id}`}
                    className="flex flex-col items-center justify-center rounded-md border-2 border-muted bg-transparent p-2.5 sm:p-4 hover:bg-accent hover:text-accent-foreground peer-data-[state=checked]:border-primary peer-data-[state=checked]:bg-primary/5 cursor-pointer transition-all text-xs sm:text-sm"
                  >
                    <method.icon className={`mb-1 sm:mb-2 h-5 w-5 sm:h-6 sm:w-6 ${method.color}`} />
                    {method.label}
                  </Label>
                </div>
              ))}
            </RadioGroup>
          </div>

          {/* Amount */}
          <div>
            <Label htmlFor="amount">Amount to Collect</Label>
            <Input
              id="amount"
              type="number"
              step="0.01"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              className="mt-1"
              placeholder="Enter amount"
            />
            <p className="text-xs text-muted-foreground mt-1">
              Max: {formatPrice(pendingBalance)}
            </p>
          </div>

          {/* Reference (optional) */}
          {paymentMethod !== 'cash' && (
            <div>
              <Label htmlFor="reference">
                {paymentMethod === 'upi' ? 'UPI Reference' : 'Card Reference'} (Optional)
              </Label>
              <Input
                id="reference"
                value={reference}
                onChange={(e) => setReference(e.target.value)}
                className="mt-1"
                placeholder={paymentMethod === 'upi' ? 'UPI Ref Number' : 'Last 4 digits'}
              />
            </div>
          )}

          {/* Notes (optional) */}
          <div>
            <Label htmlFor="notes">Notes (Optional)</Label>
            <Input
              id="notes"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              className="mt-1"
              placeholder="e.g., Partial payment"
            />
          </div>

          {/* Action Buttons */}
          <div className="flex gap-2 sm:gap-3 pt-1">
            <Button
              variant="outline"
              onClick={handleClose}
              disabled={isSubmitting}
              className="flex-1"
            >
              Cancel
            </Button>
            <Button
              onClick={handleSubmit}
              disabled={isSubmitting}
              className="flex-1"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Collecting...
                </>
              ) : (
                `Collect ₹${amount}`
              )}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
