'use client';

import { useState } from 'react';
import { CreditCard, Wallet, Banknote, Loader2, CheckCircle2, Printer } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { useCartStore } from '@/stores/cart-store';
import { apiClient } from '@/lib/api-client';
import { toast } from 'sonner';
import { useRouter } from 'next/navigation';

interface PaymentModalProps {
  isOpen: boolean;
  onClose: () => void;
}

type PaymentMethod = 'cash' | 'card' | 'upi';
type PaymentStatus = 'idle' | 'processing' | 'success' | 'error';

export function PaymentModal({ isOpen, onClose }: PaymentModalProps) {
  const router = useRouter();
  const {
    items,
    customerName,
    customerId,
    customerPhone,
    discount,
    sessionId,
    getTotal,
    clearCart,
  } = useCartStore();

  const [paymentMethod, setPaymentMethod] = useState<PaymentMethod>('cash');
  const [amountToPay, setAmountToPay] = useState('');
  const [upiReference, setUpiReference] = useState('');
  const [cardReference, setCardReference] = useState('');
  const [status, setStatus] = useState<PaymentStatus>('idle');
  const [billId, setBillId] = useState<string | null>(null);
  const [successData, setSuccessData] = useState<{ total: number; change: number } | null>(null);
  
  // Track payments and remaining amount
  const [payments, setPayments] = useState<any[]>([]);
  const total = getTotal(); // Total bill amount in paise
  const totalPaid = payments.reduce((sum, p) => sum + (p.amount * 100), 0);
  const remainingPaise = Math.max(0, total - totalPaid);
  
  // Initialize amountToPay with remaining amount when it changes or when modal opens
  const remainingRupees = remainingPaise / 100;

  // Set initial amount to pay
  useState(() => {
    setAmountToPay(remainingRupees.toString());
  });

  // Calculate change for cash payment
  const changeAmount = paymentMethod === 'cash' && amountToPay
    ? Math.max(0, parseFloat(amountToPay) - remainingRupees)
    : 0;

  const formatPrice = (paise: number) => {
    return `₹${(paise / 100).toLocaleString('en-IN', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    })}`;
  };

  const handlePayment = async () => {
    // Validation
    const amount = parseFloat(amountToPay);
    if (isNaN(amount) || amount <= 0) {
      toast.error('Please enter a valid amount');
      return;
    }

    if (amount > remainingRupees + 0.1 && paymentMethod !== 'cash') { // Allow small float error or overpayment only for cash
        toast.error('Amount exceeds remaining balance');
        return;
    }



    try {
      setStatus('processing');
      let currentBillId = billId;

      // 1. Create bill if it doesn't exist
      if (!currentBillId) {
        const billPayload = {
          items: items.map(item => {
            // For services
            if (!item.isProduct) {
              return {
                service_id: item.serviceId,
                quantity: item.quantity,
                unit_price: item.unitPrice,
                discount: item.discount,
                staff_id: item.staffId,
              };
            }
            // For products
            return {
              sku_id: item.skuId,
              quantity: item.quantity,
              unit_price: item.unitPrice,
              discount: item.discount,
            };
          }),
          customer_name: customerName || 'Walk-in Customer',
          customer_phone: customerPhone,
          customer_id: customerId,
          discount_amount: discount,
          session_id: sessionId,
        };

        const { data: billData } = await apiClient.post('/pos/bills', billPayload);
        currentBillId = billData.id;
        setBillId(currentBillId);
      }

      // 2. Process payment
      // For cash, we only record what is needed to cover the bill, or the full amount if it's less
      // Actually, backend might complain if we overpay. 
      // User might enter 500 for a 450 bill. We should send 450 to backend, and show 50 change.
      // BUT if it is a split payment, maybe they are just paying a chunk.
      
      let paymentAmount = amount;
      if (paymentMethod === 'cash' && amount > remainingRupees) {
          paymentAmount = remainingRupees; // Cap payment at remaining amount for backend
      }

      const paymentPayload = {
        method: paymentMethod,
        amount: paymentAmount, // Send in Rupees (backend expects float/int rupees)
        reference: paymentMethod === 'upi' ? upiReference :
                   paymentMethod === 'card' ? cardReference :
                   undefined,
      };

      const { data: paymentResponse } = await apiClient.post(`/pos/bills/${currentBillId}/payments`, paymentPayload);

      // 3. Update state
      const newPayment = {
          method: paymentMethod,
          amount: paymentPayload.amount,
          reference: paymentPayload.reference
      };
      
      const newPaymentsList = [...payments, newPayment];
      setPayments(newPaymentsList);
      
      // Check if bill is fully paid
      if (paymentResponse.bill_status === 'posted') {
        setSuccessData({ total, change: changeAmount });
        setStatus('success');
        toast.success('Payment completed successfully!');
        
        setTimeout(() => {
            clearCart();
            // onClose(); // Keep open to allow printing receipt
            // resetForm(); // Do not reset immediately, let user close explicitly
        }, 2000);
      } else {
          // Partial payment success
          setStatus('idle');
          toast.success('Partial payment added');
          
          // clear inputs
          setAmountToPay((remainingRupees - paymentAmount).toFixed(2));
          setUpiReference('');
          setCardReference('');
      }

    } catch (error: any) {
      setStatus('error');
      toast.error(error.response?.data?.detail || 'Payment failed');
      console.error('Payment error:', error);
      // Reset status to idle so they can try again if it was a recoverable error
      setTimeout(() => setStatus('idle'), 2000); 
    }
  };

  const handlePrintReceipt = async () => {
    if (!billId) return;
    try {
      const response = await apiClient.get(`/pos/bills/${billId}/receipt`, {
        responseType: 'blob',
      });
      const url = window.URL.createObjectURL(new Blob([response.data], { type: 'application/pdf' }));
      window.open(url, '_blank');
    } catch (error) {
      console.error('Failed to download receipt', error);
      toast.error('Failed to download receipt');
    }
  };

  const resetForm = () => {
    setPaymentMethod('cash');
    setAmountToPay('');
    setUpiReference('');
    setCardReference('');
    setBillId(null);
    setPayments([]);
    setStatus('idle');
    setSuccessData(null);
  };

  const handleClose = () => {
    if (status === 'processing') return;
    // warning if partial payment made?
    if (payments.length > 0 && status !== 'success') {
        if(!confirm("Transaction is incomplete. Are you sure you want to close?")) return;
    }
    
    onClose();
    if (status === 'success') {
      resetForm();
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-3xl">
        <DialogHeader>
          <DialogTitle>
            {status === 'success' ? 'Payment Successful' : 'Process Payment'}
          </DialogTitle>
        </DialogHeader>

        {status === 'success' ? (
          <div className="flex flex-col items-center py-8">
            <div className="rounded-full bg-green-100 p-3 mb-4">
              <CheckCircle2 className="h-12 w-12 text-green-600" />
            </div>
            <h3 className="text-xl font-semibold text-gray-900 mb-2">
              Payment Received!
            </h3>
            <p className="text-3xl font-bold text-gray-900 mb-4">
              {formatPrice(successData?.total ?? total)}
            </p>
            {paymentMethod === 'cash' && (successData?.change ?? changeAmount) > 0 && (
              <p className="text-gray-600 mb-6">
                Change: <span className="font-semibold">₹{(successData?.change ?? changeAmount).toFixed(2)}</span>
              </p>
            )}
            <Button onClick={handlePrintReceipt} variant="outline" className="w-full">
              <Printer className="h-4 w-4 mr-2" />
              Print Receipt
            </Button>
          </div>
        ) : (
          <div className="space-y-6">
            {/* Amount Information */}
            <div className="bg-gray-50 rounded-lg p-4">
              <div className="flex justify-between items-end mb-2">
                 <span className="text-sm text-gray-600">Total Amount</span>
                 <span className="text-lg font-bold text-gray-900">{formatPrice(total)}</span>
              </div>
              
              {payments.length > 0 && (
                  <div className="space-y-1 mb-2 pt-2 border-t border-gray-200">
                      {payments.map((p, i) => (
                          <div key={i} className="flex justify-between text-sm">
                              <span className="text-gray-500 capitalize">{p.method}</span>
                              <span className="text-green-600 font-medium">-{formatPrice(p.amount * 100)}</span>
                          </div>
                      ))}
                  </div>
              )}
              
              <div className="flex justify-between items-end pt-2 border-t border-gray-200">
                 <span className="text-base font-medium text-gray-900">Remaining</span>
                 <span className="text-2xl font-bold text-primary">{formatPrice(remainingPaise)}</span>
              </div>
            </div>

            {/* Payment Method Selection */}
            <div className="space-y-3">
              <Label>Payment Method</Label>
              <RadioGroup
                value={paymentMethod}
                onValueChange={(value) => setPaymentMethod(value as PaymentMethod)}
                className="grid grid-cols-3 gap-3"
              >
                {[
                  { id: 'cash', label: 'Cash', icon: Banknote, color: 'text-green-600' },
                  { id: 'card', label: 'Card', icon: CreditCard, color: 'text-blue-600' },
                  { id: 'upi', label: 'UPI', icon: Wallet, color: 'text-purple-600' },
                ].map((method) => (
                    <div key={method.id}>
                        <RadioGroupItem value={method.id} id={method.id} className="peer sr-only" />
                        <Label
                            htmlFor={method.id}
                            className="flex flex-col items-center justify-center rounded-md border-2 border-muted bg-transparent p-4 hover:bg-accent hover:text-accent-foreground peer-data-[state=checked]:border-primary peer-data-[state=checked]:bg-primary/5 cursor-pointer transition-all"
                        >
                            <method.icon className={`mb-2 h-6 w-6 ${method.color}`} />
                            {method.label}
                        </Label>
                    </div>
                ))}
              </RadioGroup>
            </div>

            {/* Payment Details */}
            <div className="grid gap-4">
               <div>
                 <Label htmlFor="amount-to-pay">Amount to Pay</Label>
                 <Input
                   id="amount-to-pay"
                   type="number"
                   step="0.01"
                   value={amountToPay}
                   onChange={(e) => setAmountToPay(e.target.value)}
                   className="mt-1.5"
                   placeholder="Enter amount"
                 />
                 {paymentMethod === 'cash' && changeAmount > 0 && (
                   <p className="text-sm text-muted-foreground mt-1.5">
                     Change to return: <span className="font-semibold text-green-600">₹{changeAmount.toFixed(2)}</span>
                   </p>
                 )}
               </div>

                {paymentMethod === 'upi' && (
                  <div>
                    <Label htmlFor="upi-reference">UPI Reference / ID (Optional)</Label>
                    <Input
                      id="upi-reference"
                      value={upiReference}
                      onChange={(e) => setUpiReference(e.target.value)}
                      className="mt-1.5"
                      placeholder="e.g. UPI Ref Number"
                    />
                  </div>
                )}

                {paymentMethod === 'card' && (
                  <div>
                    <Label htmlFor="card-reference">Last 4 Digits / Ref (Optional)</Label>
                    <Input
                      id="card-reference"
                      value={cardReference}
                      onChange={(e) => setCardReference(e.target.value)}
                      className="mt-1.5"
                      placeholder="e.g. 1234"
                    />
                  </div>
                )}
            </div>

            {/* Action Buttons */}
            <div className="flex gap-3 pt-2">
              <Button
                variant="outline"
                onClick={handleClose}
                disabled={status === 'processing'}
                className="flex-1"
              >
                Cancel
              </Button>
              <Button
                onClick={handlePayment}
                disabled={status === 'processing' || remainingPaise <= 0}
                className="flex-1"
              >
                {status === 'processing' ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Processing...
                  </>
                ) : (
                  remainingRupees > parseFloat(amountToPay || '0')
                    ? `Pay ₹${amountToPay} (${paymentMethod.toUpperCase()})`
                    : 'Complete Payment'
                )}
              </Button>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
