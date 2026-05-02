'use client';

import { useState, useEffect } from 'react';
import { ArrowLeft, Download, Calendar } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { MonthlyCalendar } from '@/components/attendance/monthly-calendar';
import { apiClient } from '@/lib/api-client';
import { toast } from 'sonner';
import { useAuthStore } from '@/stores/auth-store';
import Link from 'next/link';

interface Staff {
  id: string;
  display_name: string;
  full_name: string;
  user: {
    id: string;
    full_name: string;
  };
}

interface AttendanceRecord {
  id: string;
  staff_id: string;
  date: string;
  status: 'present' | 'half_day' | 'absent' | 'leave';
  signed_in_at: string | null;
  signed_out_at: string | null;
  notes: string | null;
}

interface MonthlyStaffSummary {
  year: number;
  month: number;
  staff_id: string;
  staff_name: string;
  total_days: number;
  present_days: number;
  half_days: number;
  absent_days: number;
  leave_days: number;
  attendance_percentage: number;
  records: AttendanceRecord[];
}

interface MonthlyAllSummary {
  year: number;
  month: number;
  summaries: MonthlyStaffSummary[];
}

export default function MonthlyAttendancePage() {
  const { user } = useAuthStore();
  const [allStaff, setAllStaff] = useState<Staff[]>([]);
  const [selectedStaffId, setSelectedStaffId] = useState<string>('all');
  const [selectedYear, setSelectedYear] = useState<number>(new Date().getFullYear());
  const [selectedMonth, setSelectedMonth] = useState<number>(new Date().getMonth() + 1);
  const [monthlySummary, setMonthlySummary] = useState<MonthlyAllSummary | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Check if user has permission
  const canViewAttendance = user?.role === 'owner' || user?.role === 'receptionist';

  useEffect(() => {
    if (canViewAttendance) {
      fetchAllStaff();
    }
  }, [canViewAttendance]);

  useEffect(() => {
    if (canViewAttendance) {
      fetchMonthlyReport();
    }
  }, [selectedYear, selectedMonth, canViewAttendance]);

  const fetchAllStaff = async () => {
    try {
      const { data } = await apiClient.get('/staff');
      setAllStaff(data.items || data);
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to fetch staff list');
    }
  };

  const fetchMonthlyReport = async () => {
    try {
      setIsLoading(true);
      const { data } = await apiClient.get<MonthlyAllSummary>('/attendance/monthly-all', {
        params: { year: selectedYear, month: selectedMonth },
      });
      setMonthlySummary(data);
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to fetch monthly report');
    } finally {
      setIsLoading(false);
    }
  };

  const handleExport = () => {
    // TODO: Implement CSV/Excel export
    toast.info('Export functionality coming soon');
  };

  const getYearOptions = () => {
    const currentYear = new Date().getFullYear();
    const years = [];
    for (let i = currentYear; i >= currentYear - 5; i--) {
      years.push(i);
    }
    return years;
  };

  const getMonthOptions = () => {
    return [
      { value: 1, label: 'January' },
      { value: 2, label: 'February' },
      { value: 3, label: 'March' },
      { value: 4, label: 'April' },
      { value: 5, label: 'May' },
      { value: 6, label: 'June' },
      { value: 7, label: 'July' },
      { value: 8, label: 'August' },
      { value: 9, label: 'September' },
      { value: 10, label: 'October' },
      { value: 11, label: 'November' },
      { value: 12, label: 'December' },
    ];
  };

  const filteredSummaries =
    selectedStaffId === 'all'
      ? monthlySummary?.summaries || []
      : monthlySummary?.summaries.filter((s) => s.staff_id === selectedStaffId) || [];

  if (!canViewAttendance) {
    return (
      <div className="p-6">
        <Card>
          <CardContent className="p-6">
            <p className="text-muted-foreground">
              You do not have permission to view attendance reports.
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link href="/dashboard/attendance">
            <Button variant="ghost" size="sm">
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back
            </Button>
          </Link>
          <div>
            <h1 className="text-3xl font-bold">Monthly Attendance Report</h1>
            <p className="text-muted-foreground mt-1">
              View attendance summary and calendar view
            </p>
          </div>
        </div>
        <Button onClick={handleExport} variant="outline">
          <Download className="h-4 w-4 mr-2" />
          Export
        </Button>
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="p-4">
          <div className="flex items-center gap-4 flex-wrap">
            {/* Staff Filter */}
            <div className="flex items-center gap-2">
              <label htmlFor="staff" className="text-sm font-medium">
                Staff:
              </label>
              <select
                id="staff"
                value={selectedStaffId}
                onChange={(e) => setSelectedStaffId(e.target.value)}
                className="px-3 py-2 border rounded-md"
              >
                <option value="all">All Staff</option>
                {allStaff.map((staff) => (
                  <option key={staff.id} value={staff.id}>
                    {staff.display_name}
                  </option>
                ))}
              </select>
            </div>

            {/* Year Filter */}
            <div className="flex items-center gap-2">
              <label htmlFor="year" className="text-sm font-medium">
                Year:
              </label>
              <select
                id="year"
                value={selectedYear}
                onChange={(e) => setSelectedYear(parseInt(e.target.value))}
                className="px-3 py-2 border rounded-md"
              >
                {getYearOptions().map((year) => (
                  <option key={year} value={year}>
                    {year}
                  </option>
                ))}
              </select>
            </div>

            {/* Month Filter */}
            <div className="flex items-center gap-2">
              <label htmlFor="month" className="text-sm font-medium">
                Month:
              </label>
              <select
                id="month"
                value={selectedMonth}
                onChange={(e) => setSelectedMonth(parseInt(e.target.value))}
                className="px-3 py-2 border rounded-md"
              >
                {getMonthOptions().map((month) => (
                  <option key={month.value} value={month.value}>
                    {month.label}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Monthly Report Cards */}
      {isLoading ? (
        <div className="flex justify-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
        </div>
      ) : filteredSummaries.length > 0 ? (
        <div className="space-y-6">
          {filteredSummaries.map((summary) => (
            <Card key={summary.staff_id}>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle>{summary.staff_name}</CardTitle>
                  <div className="text-right">
                    <p className="text-2xl font-bold text-green-600">
                      {summary.attendance_percentage.toFixed(1)}%
                    </p>
                    <p className="text-sm text-muted-foreground">Attendance Rate</p>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="space-y-6">
                {/* Summary Stats */}
                <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
                  <div>
                    <p className="text-sm text-muted-foreground">Working Days</p>
                    <p className="text-2xl font-bold">{summary.total_days}</p>
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Present</p>
                    <p className="text-2xl font-bold text-green-600">
                      {summary.present_days}
                    </p>
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Half Days</p>
                    <p className="text-2xl font-bold text-orange-600">
                      {summary.half_days}
                    </p>
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Absent</p>
                    <p className="text-2xl font-bold text-red-600">
                      {summary.absent_days}
                    </p>
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Leave</p>
                    <p className="text-2xl font-bold text-blue-600">
                      {summary.leave_days}
                    </p>
                  </div>
                </div>

                {/* Calendar View */}
                <MonthlyCalendar
                  year={summary.year}
                  month={summary.month}
                  records={summary.records}
                />
              </CardContent>
            </Card>
          ))}
        </div>
      ) : (
        <Card>
          <CardContent className="p-12">
            <div className="text-center text-muted-foreground">
              <Calendar className="h-12 w-12 mx-auto mb-4 opacity-50" />
              <p>No attendance data available for this period</p>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
