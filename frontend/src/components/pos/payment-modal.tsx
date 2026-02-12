'use client';

import { useState, useEffect } from 'react';
import { CreditCard, Wallet, Banknote, Loader2, CheckCircle2, Printer, MessageCircle } from 'lucide-react';
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
import { Alert, AlertDescription } from '@/components/ui/alert';
import { useCartStore } from '@/stores/cart-store';
import { apiClient } from '@/lib/api-client';
import { toast } from 'sonner';
import { useRouter } from 'next/navigation';
import { sendReceiptToWhatsApp } from '@/lib/whatsapp-receipt';
import { useSettingsStore } from '@/stores/settings-store';

interface PaymentModalProps {
  isOpen: boolean;
  onClose: () => void;
}

type PaymentMethod = 'cash' | 'card' | 'upi';
type PaymentStatus = 'idle' | 'processing' | 'success' | 'error';

export function PaymentModal({ isOpen, onClose }: PaymentModalProps) {
  const router = useRouter();
  const { settings } = useSettingsStore();
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
  const [successData, setSuccessData] = useState<{ total: number; paid: number; change: number; phone?: string } | null>(null);
  const [incompleteServices, setIncompleteServices] = useState<string[]>([]);
  const [isCheckingServices, setIsCheckingServices] = useState(false);
  const [customerPendingBalance, setCustomerPendingBalance] = useState<number>(0);
  const [completionNotes, setCompletionNotes] = useState('');
  const [showCollectPending, setShowCollectPending] = useState(false);

  // Track payments and remaining amount
  const [payments, setPayments] = useState<any[]>([]);
  const total = getTotal(); // Total bill amount in paise
  const totalPaid = payments.reduce((sum, p) => sum + (p.amount * 100), 0);
  const remainingPaise = Math.max(0, total - totalPaid);
  
  // Initialize amountToPay with remaining amount when it changes or when modal opens
  const remainingRupees = remainingPaise / 100;

  // Set initial amount to pay when modal opens
  useEffect(() => {
    if (isOpen && payments.length === 0) {
      const totalPaise = getTotal();
      setAmountToPay((totalPaise / 100).toString());
    }
  }, [isOpen]);

  // Check for incomplete services and fetch customer pending balance when modal opens
  useEffect(() => {
    const checkIncompleteServices = async () => {
      if (!isOpen || !sessionId) {
        setIncompleteServices([]);
        return;
      }

      setIsCheckingServices(true);
      try {
        // Fetch all walk-ins for this session
        const { data } = await apiClient.get('/appointments/walkins/active');
        const session = data.sessions?.find((s: any) => s.session_id === sessionId);

        if (session) {
          // Find services that are not completed
          const incomplete = session.walkins
            .filter((w: any) => w.status !== 'completed')
            .map((w: any) => w.service.name);

          setIncompleteServices(incomplete);
        }
      } catch (error) {
        console.error('Error checking services:', error);
      } finally {
        setIsCheckingServices(false);
      }
    };

    const fetchCustomerPendingBalance = async () => {
      if (!isOpen || !customerId) {
        setCustomerPendingBalance(0);
        return;
      }

      try {
        const { data } = await apiClient.get(`/customers/${customerId}`);
        setCustomerPendingBalance(data.pending_balance || 0);
      } catch (error) {
        console.error('Error fetching customer:', error);
      }
    };

    checkIncompleteServices();
    fetchCustomerPendingBalance();
  }, [isOpen, sessionId, customerId]);

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
    // Check for incomplete services
    if (incompleteServices.length > 0) {
      toast.error('Please complete all services before checkout');
      return;
    }

    // Validation - allow zero for free services
    const amount = parseFloat(amountToPay);
    if (isNaN(amount) || amount < 0) {
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
        const billPayload: any = {
          items: items.map(item => {
            // For services
            if (!item.isProduct) {
              const serviceItem: any = {
                service_id: item.serviceId,
                quantity: item.quantity,
                unit_price: item.unitPrice,
                discount: item.discount,
              };

              // Multi-staff service with contributions
              if (item.isMultiStaff && item.staffContributions && item.staffContributions.length > 0) {
                serviceItem.staff_contributions = item.staffContributions;
              } else {
                // Single-staff service
                serviceItem.staff_id = item.staffId;
              }

              return serviceItem;
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
          discount_amount: discount,
          session_id: sessionId,
        };

        // Only include customer_phone and customer_id if they exist
        if (customerPhone) {
          billPayload.customer_phone = customerPhone;
        }
        if (customerId) {
          billPayload.customer_id = customerId;
        }

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
        const actualPaid = totalPaid + (paymentAmount * 100);
        setSuccessData({ total, paid: actualPaid, change: changeAmount, phone: customerPhone || undefined });
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

  const handleCompleteBill = async () => {
    // Check for incomplete services
    if (incompleteServices.length > 0) {
      toast.error('Please complete all services before checkout');
      return;
    }

    try {
      setStatus('processing');
      let currentBillId = billId;

      // 1. Create bill if it doesn't exist
      if (!currentBillId) {
        const billPayload: any = {
          items: items.map(item => {
            // For services
            if (!item.isProduct) {
              const serviceItem: any = {
                service_id: item.serviceId,
                quantity: item.quantity,
                unit_price: item.unitPrice,
                discount: item.discount,
              };

              // Multi-staff service with contributions
              if (item.isMultiStaff && item.staffContributions && item.staffContributions.length > 0) {
                serviceItem.staff_contributions = item.staffContributions;
              } else {
                // Single-staff service
                serviceItem.staff_id = item.staffId;
              }

              return serviceItem;
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
          discount_amount: discount,
          session_id: sessionId,
        };

        // Only include customer_phone and customer_id if they exist
        if (customerPhone) {
          billPayload.customer_phone = customerPhone;
        }
        if (customerId) {
          billPayload.customer_id = customerId;
        }

        const { data: billData } = await apiClient.post('/pos/bills', billPayload);
        currentBillId = billData.id;
        setBillId(currentBillId);
      }

      // 2. Complete the bill with pending balance
      await apiClient.post(`/pos/bills/${currentBillId}/complete`, {
        notes: completionNotes || undefined,
      });

      setSuccessData({ total, paid: totalPaid, change: 0, phone: customerPhone || undefined });
      setStatus('success');
      toast.success('Bill completed successfully! Receipt can now be printed.');

      setTimeout(() => {
        clearCart();
      }, 2000);

    } catch (error: any) {
      setStatus('error');
      toast.error(error.response?.data?.detail || 'Failed to complete bill');
      console.error('Complete bill error:', error);
      setTimeout(() => setStatus('idle'), 2000);
    }
  };

  const handleCollectPending = async () => {
    if (!customerId || customerPendingBalance <= 0) return;

    try {
      setStatus('processing');

      const amount = parseFloat(amountToPay);
      if (isNaN(amount) || amount <= 0 || amount > customerPendingBalance / 100) {
        toast.error('Invalid amount for pending balance collection');
        setStatus('idle');
        return;
      }

      await apiClient.post('/pos/pending-payments/collect', {
        customer_id: customerId,
        amount: amount,
        payment_method: paymentMethod,
        reference_number: paymentMethod === 'upi' ? upiReference :
                         paymentMethod === 'card' ? cardReference :
                         undefined,
        notes: 'Collected from POS',
      });

      toast.success('Pending payment collected successfully!');

      // Refresh pending balance
      const { data } = await apiClient.get(`/customers/${customerId}`);
      setCustomerPendingBalance(data.pending_balance || 0);

      // Reset form
      setAmountToPay('');
      setUpiReference('');
      setCardReference('');
      setStatus('idle');

    } catch (error: any) {
      setStatus('error');
      toast.error(error.response?.data?.detail || 'Failed to collect payment');
      console.error('Collect pending error:', error);
      setTimeout(() => setStatus('idle'), 2000);
    }
  };

  const [isSendingWhatsApp, setIsSendingWhatsApp] = useState(false);

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

  const handleSendWhatsApp = async () => {
    const phone = successData?.phone || customerPhone;
    if (!billId || !phone) return;
    try {
      setIsSendingWhatsApp(true);
      const { data: billData } = await apiClient.get(`/pos/bills/${billId}`);
      const sent = sendReceiptToWhatsApp(billData, settings?.salon_name);
      if (!sent) {
        toast.error('No phone number available for this customer');
      }
    } catch (error) {
      console.error('Failed to send WhatsApp receipt', error);
      toast.error('Failed to prepare WhatsApp receipt');
    } finally {
      setIsSendingWhatsApp(false);
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
      <DialogContent className="max-h-[90vh] overflow-y-auto" style={{ maxWidth: 'min(32rem, calc(100vw - 2rem))' }}>
        <DialogHeader>
          <DialogTitle>
            {status === 'success' ? 'Payment Successful' : 'Process Payment'}
          </DialogTitle>
        </DialogHeader>

        {status === 'success' ? (
          <div className="flex flex-col items-center py-4 sm:py-8 mt-4">
            <div className="rounded-full bg-green-100 p-3 mb-3">
              <CheckCircle2 className="h-10 w-10 sm:h-12 sm:w-12 text-green-600" />
            </div>
            <h3 className="text-lg sm:text-xl font-semibold text-gray-900 mb-1">
              Payment Received!
            </h3>
            <p className="text-2xl sm:text-3xl font-bold text-gray-900 mb-3">
              {formatPrice(successData?.paid ?? total)}
            </p>
            {successData && successData.paid < successData.total && (
              <p className="text-sm text-orange-600 mb-1">
                Pending: {formatPrice(successData.total - successData.paid)}
              </p>
            )}
            {paymentMethod === 'cash' && (successData?.change ?? changeAmount) > 0 && (
              <p className="text-gray-600 mb-4">
                Change: <span className="font-semibold">₹{(successData?.change ?? changeAmount).toFixed(2)}</span>
              </p>
            )}
            <div className="w-full space-y-2">
              <Button onClick={handlePrintReceipt} variant="outline" className="w-full">
                <Printer className="h-4 w-4 mr-2" />
                Print Receipt
              </Button>
              {successData?.phone && (
                <Button
                  onClick={handleSendWhatsApp}
                  variant="outline"
                  className="w-full"
                  disabled={isSendingWhatsApp}
                >
                  {isSendingWhatsApp ? (
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  ) : (
                    <MessageCircle className="h-4 w-4 mr-2" />
                  )}
                  Send to WhatsApp
                </Button>
              )}
            </div>
          </div>
        ) : (
          <div className="space-y-3 sm:space-y-5 mt-4">
            {/* Incomplete Services Warning */}
            {incompleteServices.length > 0 && (
              <Alert variant="destructive">
                <AlertDescription>
                  <strong>Cannot checkout:</strong> The following services are not completed yet:
                  <ul className="mt-2 ml-4 list-disc">
                    {incompleteServices.map((service, index) => (
                      <li key={index}>{service}</li>
                    ))}
                  </ul>
                  Please mark all services as completed before processing payment.
                </AlertDescription>
              </Alert>
            )}

            {/* Customer Pending Balance Alert */}
            {customerPendingBalance > 0 && (
              <Alert>
                <AlertDescription className="flex items-center justify-between gap-2">
                  <div className="text-sm">
                    <strong>Pending balance:</strong> {formatPrice(customerPendingBalance)}
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setShowCollectPending(!showCollectPending)}
                    className="shrink-0"
                  >
                    {showCollectPending ? 'Hide' : 'Collect Now'}
                  </Button>
                </AlertDescription>
              </Alert>
            )}

            {/* Collect Pending Balance Section */}
            {showCollectPending && customerPendingBalance > 0 && (
              <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3 space-y-3">
                <h3 className="font-semibold text-sm text-yellow-900">Collect Pending Balance</h3>

                <div className="grid gap-3">
                  <div>
                    <Label htmlFor="pending-amount">Amount to Collect</Label>
                    <Input
                      id="pending-amount"
                      type="number"
                      step="0.01"
                      value={amountToPay}
                      onChange={(e) => setAmountToPay(e.target.value)}
                      className="mt-1"
                      placeholder="Enter amount"
                    />
                    <p className="text-xs text-muted-foreground mt-1">
                      Max: {formatPrice(customerPendingBalance)}
                    </p>
                  </div>

                  {paymentMethod === 'upi' && (
                    <div>
                      <Label htmlFor="upi-ref-pending">UPI Reference (Optional)</Label>
                      <Input
                        id="upi-ref-pending"
                        value={upiReference}
                        onChange={(e) => setUpiReference(e.target.value)}
                        className="mt-1"
                        placeholder="e.g. UPI Ref Number"
                      />
                    </div>
                  )}

                  {paymentMethod === 'card' && (
                    <div>
                      <Label htmlFor="card-ref-pending">Card Reference (Optional)</Label>
                      <Input
                        id="card-ref-pending"
                        value={cardReference}
                        onChange={(e) => setCardReference(e.target.value)}
                        className="mt-1"
                        placeholder="e.g. 1234"
                      />
                    </div>
                  )}

                  <Button
                    onClick={handleCollectPending}
                    disabled={status === 'processing'}
                    className="w-full"
                  >
                    {status === 'processing' ? (
                      <>
                        <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                        Collecting...
                      </>
                    ) : (
                      `Collect ₹${amountToPay || '0'} from Pending`
                    )}
                  </Button>
                </div>
              </div>
            )}

            {/* Amount Information */}
            <div className="bg-gray-50 rounded-lg p-3">
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
                 <span className="text-xl sm:text-2xl font-bold text-primary">{formatPrice(remainingPaise)}</span>
              </div>
            </div>

            {/* Payment Method Selection - only show if bill has amount */}
            {total > 0 && (
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
                          <RadioGroupItem value={method.id} id={method.id} className="peer sr-only" />
                          <Label
                              htmlFor={method.id}
                              className="flex flex-col items-center justify-center rounded-md border-2 border-muted bg-transparent p-2.5 sm:p-4 hover:bg-accent hover:text-accent-foreground peer-data-[state=checked]:border-primary peer-data-[state=checked]:bg-primary/5 cursor-pointer transition-all text-xs sm:text-sm"
                          >
                              <method.icon className={`mb-1 sm:mb-2 h-5 w-5 sm:h-6 sm:w-6 ${method.color}`} />
                              {method.label}
                          </Label>
                      </div>
                  ))}
                </RadioGroup>
              </div>
            )}

            {/* Payment Details - only show if bill has amount */}
            {total > 0 && (
              <div className="grid gap-3">
                <div>
                  <Label htmlFor="amount-to-pay">Amount to Pay</Label>
                  <Input
                    id="amount-to-pay"
                    type="number"
                    step="0.01"
                    value={amountToPay}
                    onChange={(e) => setAmountToPay(e.target.value)}
                    className="mt-1"
                    placeholder="Enter amount"
                  />
                  {paymentMethod === 'cash' && changeAmount > 0 && (
                    <p className="text-sm text-muted-foreground mt-1">
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
                        className="mt-1"
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
                        className="mt-1"
                        placeholder="e.g. 1234"
                      />
                    </div>
                  )}
              </div>
            )}

            {/* Notes for pending balance or zero amount bills */}
            {(total === 0 || remainingPaise > 0) && (
              <div>
                <Label htmlFor="completion-notes">
                  {total === 0 ? 'Notes (Optional - for free service)' : 'Notes (Optional - for pending balance)'}
                </Label>
                <Input
                  id="completion-notes"
                  value={completionNotes}
                  onChange={(e) => setCompletionNotes(e.target.value)}
                  className="mt-1"
                  placeholder={total === 0 ? 'e.g., Complimentary service for VIP' : 'e.g., Family member - will pay later'}
                />
              </div>
            )}

            {/* Action Buttons */}
            <div className="grid grid-cols-2 gap-2 pt-1">
              <Button
                variant="outline"
                onClick={handleClose}
                disabled={status === 'processing'}
              >
                Cancel
              </Button>

              {/* Regular payment button - only show if bill has amount */}
              {total > 0 && (
                <Button
                  onClick={handlePayment}
                  disabled={status === 'processing' || remainingPaise <= 0 || incompleteServices.length > 0}
                >
                {status === 'processing' ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Processing...
                  </>
                ) : (
                  remainingRupees > parseFloat(amountToPay || '0')
                    ? `Pay ₹${amountToPay}`
                    : 'Complete Payment'
                )}
                </Button>
              )}

              {/* Complete Bill button (for pending balance, free service, or zero amount) */}
              {(total === 0 || (remainingPaise > 0 && payments.length === 0)) && (
                <Button
                  onClick={handleCompleteBill}
                  disabled={status === 'processing' || incompleteServices.length > 0}
                  variant={total === 0 ? "default" : "secondary"}
                >
                  {status === 'processing' ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      Processing...
                    </>
                  ) : total === 0 ? (
                    'Complete (₹0)'
                  ) : (
                    'No Payment'
                  )}
                </Button>
              )}
            </div>

            {/* Complete Bill with Pending Balance button (when partial payment made) */}
            {remainingPaise > 0 && payments.length > 0 && (
              <Button
                onClick={handleCompleteBill}
                disabled={status === 'processing' || incompleteServices.length > 0}
                variant="outline"
                className="w-full"
              >
                {status === 'processing' ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Processing...
                  </>
                ) : (
                  `Complete (Pending ${formatPrice(remainingPaise)})`
                )}
              </Button>
            )}
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
