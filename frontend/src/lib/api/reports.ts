import { apiClient } from '../api-client';
import type { ProfitLossReport, PLReportFilters } from '@/types/reports';

export const reportApi = {
  /**
   * Get Profit & Loss report
   */
  async getProfitLoss(filters: PLReportFilters): Promise<ProfitLossReport> {
    const response = await apiClient.get('/reports/profit-loss', {
      params: {
        start_date: filters.start_date,
        end_date: filters.end_date,
      },
    });
    return response.data;
  },
};
