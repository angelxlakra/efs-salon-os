'use client';

import { useState, useEffect } from 'react';
import { Calendar, DollarSign, TrendingUp, TrendingDown, CheckCircle, AlertCircle, Loader2 } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Label } from '@/components/ui/label';
import { apiClient } from '@/lib/api-client';
import { toast } from 'sonner';

interface PaymentMethodBreakdown {
  cash: number;
  card: number;
  upi: number;
  bank_transfer: number;
}

interface EODSummary {
  date: string;
  total_bills: number;
  total_revenue: number;
  total_tax: number;
  total_discount: number;
  payment_breakdown: PaymentMethodBreakdown;
  bills_by_status: Record<string, number>;
}

interface EODReport {
  date: string;
  summary: EODSummary;
  expected_cash: number;
  actual_cash: number | null;
  cash_difference: number | null;
  reconciled: boolean;
  reconciled_at: string | null;
  reconciled_by: string | null;
  notes: string | null;
}

export default function ReconciliationPage() {
  const [selectedDate, setSelectedDate] = useState<string>(
    new Date().toISOString().split('T')[0]
  );
  const [report, setReport] = useState<EODReport | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [actualCash, setActualCash] = useState<string>('');
  const [notes, setNotes] = useState<string>('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    fetchEODReport();
  }, [selectedDate]);

  const fetchEODReport = async () => {
    try {
      setIsLoading(true);
      const { data } = await apiClient.get<EODReport>('/reconciliation/eod-report', {
        params: { reconciliation_date: selectedDate },
      });

      setReport(data);

      // Pre-fill actual cash if already reconciled
      if (data.actual_cash !== null) {
        setActualCash((data.actual_cash / 100).toFixed(2));
      } else {
        setActualCash('');
      }

      setNotes(data.notes || '');
    } catch (error: any) {
      console.error('Error fetching EOD report:', error);
      toast.error(error.response?.data?.detail || 'Failed to load EOD report');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSubmitReconciliation = async () => {
    if (!actualCash || parseFloat(actualCash) < 0) {
      toast.error('Please enter a valid actual cash amount');
      return;
    }

    if (!report) return;

    const actualCashPaise = Math.round(parseFloat(actualCash) * 100);

    try {
      setIsSubmitting(true);
      const { data } = await apiClient.post<EODReport>('/reconciliation/reconcile', {
        date: selectedDate,
        expected_cash: report.expected_cash,
        actual_cash: actualCashPaise,
        notes: notes.trim() || null,
      });

      setReport(data);
      toast.success('Reconciliation submitted successfully');
    } catch (error: any) {
      console.error('Error submitting reconciliation:', error);
      toast.error(error.response?.data?.detail || 'Failed to submit reconciliation');
    } finally {
      setIsSubmitting(false);
    }
  };

  const formatPrice = (paise: number) => {
    return `₹${(paise / 100).toLocaleString('en-IN', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    })}`;
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-IN', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
    });
  };

  const formatDateTime = (dateString: string) => {
    return new Date(dateString).toLocaleString('en-IN', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  if (isLoading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="h-8 w-8 animate-spin text-gray-400 mx-auto mb-2" />
          <p className="text-sm text-gray-500">Loading EOD report...</p>
        </div>
      </div>
    );
  }

  if (!report) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="text-center">
          <AlertCircle className="h-12 w-12 text-gray-400 mx-auto mb-2" />
          <p className="text-gray-500">Failed to load report</p>
        </div>
      </div>
    );
  }

  const cashDifference = report.cash_difference || 0;
  const isShort = cashDifference < 0;
  const isExact = cashDifference === 0 && report.reconciled;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl md:text-3xl font-bold">End of Day Reconciliation</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Daily cash counting and reconciliation
        </p>
      </div>

      {/* Date Selector */}
      <Card>
        <CardContent className="p-4">
          <div className="flex items-center gap-3">
            <Calendar className="h-5 w-5 text-gray-500" />
            <div className="flex-1">
              <Label htmlFor="date" className="text-sm font-medium">
                Reconciliation Date
              </Label>
              <Input
                id="date"
                type="date"
                value={selectedDate}
                onChange={(e) => setSelectedDate(e.target.value)}
                max={new Date().toISOString().split('T')[0]}
                className="mt-1"
              />
            </div>
            {report.reconciled && (
              <Badge className="bg-green-500">
                <CheckCircle className="h-3 w-3 mr-1" />
                Reconciled
              </Badge>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Total Bills
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{report.summary.total_bills}</div>
            <p className="text-xs text-muted-foreground mt-1">
              Posted: {report.summary.bills_by_status.posted || 0}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Total Revenue
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {formatPrice(report.summary.total_revenue)}
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              Tax: {formatPrice(report.summary.total_tax)}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Discounts Given
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {formatPrice(report.summary.total_discount)}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Payment Breakdown */}
      <Card>
        <CardHeader>
          <CardTitle>Payment Method Breakdown</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="space-y-1">
              <p className="text-sm text-muted-foreground">Cash</p>
              <p className="text-lg font-semibold">
                {formatPrice(report.summary.payment_breakdown.cash)}
              </p>
            </div>
            <div className="space-y-1">
              <p className="text-sm text-muted-foreground">Card</p>
              <p className="text-lg font-semibold">
                {formatPrice(report.summary.payment_breakdown.card)}
              </p>
            </div>
            <div className="space-y-1">
              <p className="text-sm text-muted-foreground">UPI</p>
              <p className="text-lg font-semibold">
                {formatPrice(report.summary.payment_breakdown.upi)}
              </p>
            </div>
            <div className="space-y-1">
              <p className="text-sm text-muted-foreground">Bank Transfer</p>
              <p className="text-lg font-semibold">
                {formatPrice(report.summary.payment_breakdown.bank_transfer)}
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Cash Reconciliation */}
      <Card>
        <CardHeader>
          <CardTitle>Cash Reconciliation</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Expected Cash */}
          <div className="flex justify-between items-center p-3 bg-blue-50 rounded-lg">
            <div>
              <p className="text-sm text-muted-foreground">Expected Cash (From System)</p>
              <p className="text-2xl font-bold text-blue-700">
                {formatPrice(report.expected_cash)}
              </p>
            </div>
            <DollarSign className="h-8 w-8 text-blue-500" />
          </div>

          {/* Actual Cash Input */}
          {!report.reconciled && (
            <div className="space-y-2">
              <Label htmlFor="actualCash">Actual Cash Counted (₹)</Label>
              <Input
                id="actualCash"
                type="number"
                step="0.01"
                min="0"
                placeholder="Enter actual cash amount"
                value={actualCash}
                onChange={(e) => setActualCash(e.target.value)}
              />
            </div>
          )}

          {/* Actual Cash Display (if reconciled) */}
          {report.reconciled && report.actual_cash !== null && (
            <div className={`flex justify-between items-center p-3 rounded-lg ${
              isExact ? 'bg-green-50' : isShort ? 'bg-red-50' : 'bg-yellow-50'
            }`}>
              <div>
                <p className="text-sm text-muted-foreground">Actual Cash Counted</p>
                <p className={`text-2xl font-bold ${
                  isExact ? 'text-green-700' : isShort ? 'text-red-700' : 'text-yellow-700'
                }`}>
                  {formatPrice(report.actual_cash)}
                </p>
              </div>
              {isExact ? (
                <CheckCircle className="h-8 w-8 text-green-500" />
              ) : isShort ? (
                <TrendingDown className="h-8 w-8 text-red-500" />
              ) : (
                <TrendingUp className="h-8 w-8 text-yellow-500" />
              )}
            </div>
          )}

          {/* Cash Difference */}
          {report.reconciled && report.cash_difference !== null && (
            <div className={`p-3 rounded-lg ${
              isExact ? 'bg-green-100 text-green-800' :
              isShort ? 'bg-red-100 text-red-800' :
              'bg-yellow-100 text-yellow-800'
            }`}>
              <p className="text-sm font-medium">
                {isExact ? '✓ Cash matches exactly!' :
                 isShort ? '⚠ Cash Short' :
                 '⚠ Cash Over'}
              </p>
              {!isExact && (
                <p className="text-lg font-bold mt-1">
                  {formatPrice(Math.abs(cashDifference))}
                </p>
              )}
            </div>
          )}

          {/* Notes */}
          <div className="space-y-2">
            <Label htmlFor="notes">Notes (Optional)</Label>
            <Textarea
              id="notes"
              placeholder="Add any notes about the reconciliation (e.g., reasons for variance)"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={3}
              disabled={report.reconciled}
            />
          </div>

          {/* Submit Button */}
          {!report.reconciled && (
            <Button
              onClick={handleSubmitReconciliation}
              disabled={!actualCash || isSubmitting}
              className="w-full"
              size="lg"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Submitting...
                </>
              ) : (
                <>
                  <CheckCircle className="h-4 w-4 mr-2" />
                  Submit Reconciliation
                </>
              )}
            </Button>
          )}

          {/* Reconciliation Info */}
          {report.reconciled && report.reconciled_at && (
            <div className="pt-3 border-t">
              <p className="text-sm text-muted-foreground">
                Reconciled on {formatDateTime(report.reconciled_at)}
              </p>
              {report.notes && (
                <div className="mt-2 p-2 bg-gray-50 rounded text-sm">
                  <p className="font-medium">Notes:</p>
                  <p className="text-muted-foreground">{report.notes}</p>
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
