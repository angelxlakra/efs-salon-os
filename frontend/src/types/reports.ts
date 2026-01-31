// Report types for P&L and other financial reports

export interface PLRevenue {
  gross_revenue: number;
  discount_amount: number;
  refund_amount: number;
  net_revenue: number;
}

export interface PLCostOfGoodsSold {
  service_cogs: number;
  product_cogs: number;
  total_cogs: number;
}

export interface PLOperatingExpenses {
  by_category: Record<string, number>;
  total_expenses: number;
}

export interface PLProfitability {
  gross_profit: number;
  net_profit: number;
  gross_margin_percent: number;
  net_margin_percent: number;
}

export interface ProfitLossReport {
  period_start: string;
  period_end: string;
  revenue: PLRevenue;
  cogs: PLCostOfGoodsSold;
  operating_expenses: PLOperatingExpenses;
  profitability: PLProfitability;
  total_bills: number;
  tips_collected: number;
  generated_at: string;
}

export interface PLReportFilters {
  start_date: string;
  end_date: string;
}
