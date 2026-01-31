'use client';

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { TrendingUp, TrendingDown, DollarSign, Package, Receipt } from 'lucide-react';
import { reportApi } from '@/lib/api/reports';
import type { ProfitLossReport } from '@/types/reports';
import { toast } from 'sonner';

export default function ProfitLossPage() {
  const [loading, setLoading] = useState(false);
  const [report, setReport] = useState<ProfitLossReport | null>(null);
  const [startDate, setStartDate] = useState(() => {
    const date = new Date();
    date.setDate(1); // First day of current month
    return date.toISOString().split('T')[0];
  });
  const [endDate, setEndDate] = useState(() => new Date().toISOString().split('T')[0]);

  const loadReport = async () => {
    setLoading(true);
    try {
      const data = await reportApi.getProfitLoss({ start_date: startDate, end_date: endDate });
      setReport(data);
    } catch (error) {
      console.error('Failed to load P&L report:', error);
      toast.error('Failed to load report');
    } finally {
      setLoading(false);
    }
  };

  const formatCurrency = (paise: number) => {
    return `₹${(paise / 100).toLocaleString('en-IN', { minimumFractionDigits: 2 })}`;
  };

  const formatPercent = (value: number) => {
    return `${value.toFixed(2)}%`;
  };

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Profit & Loss Statement</h1>
        <p className="text-muted-foreground">View detailed financial performance</p>
      </div>

      {/* Date Range Selector */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex gap-4 items-end">
            <div className="flex-1">
              <label className="text-sm font-medium block mb-2">Start Date</label>
              <Input
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
              />
            </div>
            <div className="flex-1">
              <label className="text-sm font-medium block mb-2">End Date</label>
              <Input
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
              />
            </div>
            <Button onClick={loadReport} disabled={loading}>
              {loading ? 'Loading...' : 'Generate Report'}
            </Button>
          </div>
        </CardContent>
      </Card>

      {report && (
        <>
          {/* Summary Cards */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  Net Revenue
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{formatCurrency(report.revenue.net_revenue)}</div>
                <div className="text-xs text-muted-foreground mt-1">
                  {report.total_bills} bills
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  Total COGS
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{formatCurrency(report.cogs.total_cogs)}</div>
                <div className="text-xs text-muted-foreground mt-1">
                  {formatPercent((report.cogs.total_cogs / report.revenue.net_revenue) * 100)} of revenue
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  Operating Expenses
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {formatCurrency(report.operating_expenses.total_expenses)}
                </div>
                <div className="text-xs text-muted-foreground mt-1">
                  {Object.keys(report.operating_expenses.by_category).length} categories
                </div>
              </CardContent>
            </Card>

            <Card className={report.profitability.net_profit >= 0 ? 'border-green-200 bg-green-50' : 'border-red-200 bg-red-50'}>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
                  Net Profit
                  {report.profitability.net_profit >= 0 ? (
                    <TrendingUp className="h-4 w-4 text-green-600" />
                  ) : (
                    <TrendingDown className="h-4 w-4 text-red-600" />
                  )}
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className={`text-2xl font-bold ${report.profitability.net_profit >= 0 ? 'text-green-700' : 'text-red-700'}`}>
                  {formatCurrency(report.profitability.net_profit)}
                </div>
                <div className="text-xs text-muted-foreground mt-1">
                  {formatPercent(report.profitability.net_margin_percent)} margin
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Revenue Breakdown */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <DollarSign className="h-5 w-5" />
                Revenue Breakdown
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex justify-between">
                <span className="text-sm text-muted-foreground">Gross Revenue</span>
                <span className="font-medium">{formatCurrency(report.revenue.gross_revenue)}</span>
              </div>
              <div className="flex justify-between text-red-600">
                <span className="text-sm">Discounts</span>
                <span className="font-medium">-{formatCurrency(report.revenue.discount_amount)}</span>
              </div>
              <div className="flex justify-between text-red-600">
                <span className="text-sm">Refunds</span>
                <span className="font-medium">-{formatCurrency(report.revenue.refund_amount)}</span>
              </div>
              <div className="flex justify-between pt-2 border-t">
                <span className="font-medium">Net Revenue</span>
                <span className="font-bold">{formatCurrency(report.revenue.net_revenue)}</span>
              </div>
              <div className="flex justify-between text-muted-foreground">
                <span className="text-sm">Tips Collected</span>
                <span className="text-sm">{formatCurrency(report.tips_collected)}</span>
              </div>
            </CardContent>
          </Card>

          {/* COGS Breakdown */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Package className="h-5 w-5" />
                Cost of Goods Sold
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex justify-between">
                <span className="text-sm text-muted-foreground">Service Materials</span>
                <span className="font-medium">{formatCurrency(report.cogs.service_cogs)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm text-muted-foreground">Retail Products</span>
                <span className="font-medium">{formatCurrency(report.cogs.product_cogs)}</span>
              </div>
              <div className="flex justify-between pt-2 border-t">
                <span className="font-medium">Total COGS</span>
                <span className="font-bold">{formatCurrency(report.cogs.total_cogs)}</span>
              </div>
              <div className="flex justify-between pt-2 border-t bg-green-50 -mx-4 px-4 py-2 rounded">
                <span className="font-medium text-green-700">Gross Profit</span>
                <span className="font-bold text-green-700">
                  {formatCurrency(report.profitability.gross_profit)}
                </span>
              </div>
              <div className="text-sm text-muted-foreground">
                Gross Margin: {formatPercent(report.profitability.gross_margin_percent)}
              </div>
            </CardContent>
          </Card>

          {/* Operating Expenses Breakdown */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Receipt className="h-5 w-5" />
                Operating Expenses
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {Object.entries(report.operating_expenses.by_category).map(([category, amount]) => (
                <div key={category} className="flex justify-between">
                  <span className="text-sm text-muted-foreground">
                    {category.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase())}
                  </span>
                  <span className="font-medium">{formatCurrency(amount)}</span>
                </div>
              ))}
              {Object.keys(report.operating_expenses.by_category).length === 0 && (
                <div className="text-sm text-muted-foreground text-center py-4">
                  No expenses recorded for this period
                </div>
              )}
              <div className="flex justify-between pt-2 border-t">
                <span className="font-medium">Total Expenses</span>
                <span className="font-bold">{formatCurrency(report.operating_expenses.total_expenses)}</span>
              </div>
            </CardContent>
          </Card>

          {/* Profitability Summary */}
          <Card className={report.profitability.net_profit >= 0 ? 'border-green-200' : 'border-red-200'}>
            <CardHeader>
              <CardTitle>Profitability Summary</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex justify-between text-lg">
                <span className="font-medium">Net Revenue</span>
                <span className="font-bold">{formatCurrency(report.revenue.net_revenue)}</span>
              </div>
              <div className="flex justify-between text-red-600">
                <span>- Total COGS</span>
                <span className="font-medium">-{formatCurrency(report.cogs.total_cogs)}</span>
              </div>
              <div className="flex justify-between">
                <span className="font-medium text-green-700">= Gross Profit</span>
                <span className="font-bold text-green-700">{formatCurrency(report.profitability.gross_profit)}</span>
              </div>
              <div className="flex justify-between text-red-600">
                <span>- Operating Expenses</span>
                <span className="font-medium">-{formatCurrency(report.operating_expenses.total_expenses)}</span>
              </div>
              <div className={`flex justify-between text-xl pt-3 border-t ${report.profitability.net_profit >= 0 ? 'text-green-700' : 'text-red-700'}`}>
                <span className="font-bold">= Net Profit</span>
                <span className="font-bold">{formatCurrency(report.profitability.net_profit)}</span>
              </div>
              <div className="grid grid-cols-2 gap-4 pt-4 border-t">
                <div className="text-center">
                  <div className="text-sm text-muted-foreground">Gross Margin</div>
                  <div className="text-lg font-bold text-green-600">
                    {formatPercent(report.profitability.gross_margin_percent)}
                  </div>
                </div>
                <div className="text-center">
                  <div className="text-sm text-muted-foreground">Net Margin</div>
                  <div className={`text-lg font-bold ${report.profitability.net_profit >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                    {formatPercent(report.profitability.net_margin_percent)}
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </>
      )}

      {!report && !loading && (
        <Card>
          <CardContent className="py-12 text-center text-muted-foreground">
            <p>Select a date range and click "Generate Report" to view P&L statement</p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
