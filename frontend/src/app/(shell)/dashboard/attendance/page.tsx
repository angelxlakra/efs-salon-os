'use client';

import { useState, useEffect } from 'react';
import { Calendar, Users, CheckCircle, Clock, XCircle, Coffee, Plus, Zap, List } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { AttendanceTable } from '@/components/attendance/attendance-table';
import { AttendanceMarkDialog } from '@/components/attendance/attendance-mark-dialog';
import { QuickAttendanceMark } from '@/components/attendance/quick-attendance-mark';
import { MyAttendanceCard } from '@/components/attendance/my-attendance-card';
import { apiClient } from '@/lib/api-client';
import { toast } from 'sonner';
import { useAuthStore } from '@/stores/auth-store';
import Link from 'next/link';

interface Staff {
  id: string;
  display_name: string;
  full_name: string;
  is_active: boolean;
}

interface AttendanceRecord {
  id: string;
  staff_id: string;
  date: string;
  status: 'present' | 'half_day' | 'absent' | 'leave';
  signed_in_at: string | null;
  signed_out_at: string | null;
  notes: string | null;
  marked_by_id: string;
  created_at: string;
  updated_at: string;
  staff: Staff;
}

interface DailySummary {
  date: string;
  total_staff: number;
  present: number;
  half_day: number;
  absent: number;
  leave: number;
  attendance_records: AttendanceRecord[];
}

export default function AttendancePage() {
  const { user } = useAuthStore();
  const [summary, setSummary] = useState<DailySummary | null>(null);
  const [selectedDate, setSelectedDate] = useState<string>(
    new Date().toISOString().split('T')[0]
  );
  const [isLoading, setIsLoading] = useState(true);
  const [isMarkDialogOpen, setIsMarkDialogOpen] = useState(false);
  const [selectedStaff, setSelectedStaff] = useState<Staff | null>(null);
  const [activeTab, setActiveTab] = useState('quick');

  // Check if user has permission to mark attendance
  const canMarkAttendance = user?.role === 'owner' || user?.role === 'receptionist';

  // Check if selected date is today
  const isToday = selectedDate === new Date().toISOString().split('T')[0];

  useEffect(() => {
    fetchDailySummary();
  }, [selectedDate]);

  const fetchDailySummary = async () => {
    try {
      setIsLoading(true);
      const { data } = await apiClient.get<DailySummary>('/attendance/daily-summary', {
        params: { date_filter: selectedDate },
      });
      setSummary(data);
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to fetch attendance summary');
    } finally {
      setIsLoading(false);
    }
  };

  const handleMarkAttendance = (staff?: Staff) => {
    setSelectedStaff(staff || null);
    setIsMarkDialogOpen(true);
  };

  const handleAttendanceMarked = () => {
    fetchDailySummary();
    setIsMarkDialogOpen(false);
    setSelectedStaff(null);
  };

  if (!canMarkAttendance) {
    return (
      <div className="p-6">
        <Card>
          <CardContent className="p-6">
            <p className="text-muted-foreground">
              You do not have permission to view attendance records.
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
        <div>
          <h1 className="text-3xl font-bold">Attendance</h1>
          <p className="text-muted-foreground mt-1">
            Track and manage staff attendance
          </p>
        </div>
        <div className="flex gap-2">
          <Link href="/dashboard/attendance/monthly">
            <Button variant="outline">
              <Calendar className="h-4 w-4 mr-2" />
              Monthly Report
            </Button>
          </Link>
          {canMarkAttendance && (
            <Button onClick={() => handleMarkAttendance()}>
              <Plus className="h-4 w-4 mr-2" />
              Mark Attendance
            </Button>
          )}
        </div>
      </div>

      {/* Date Selector */}
      <Card>
        <CardContent className="p-4">
          <div className="flex items-center gap-4">
            <label htmlFor="date" className="text-sm font-medium">
              Select Date:
            </label>
            <input
              id="date"
              type="date"
              value={selectedDate}
              onChange={(e) => setSelectedDate(e.target.value)}
              className="px-3 py-2 border rounded-md"
              max={new Date().toISOString().split('T')[0]}
            />
          </div>
        </CardContent>
      </Card>

      {/* My Attendance Card - Show for users with staff profiles */}
      {user?.staff_id && <MyAttendanceCard />}

      {/* Summary Cards */}
      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
          {[...Array(5)].map((_, i) => (
            <Card key={i}>
              <CardContent className="p-6">
                <div className="h-20 animate-pulse bg-muted rounded" />
              </CardContent>
            </Card>
          ))}
        </div>
      ) : summary ? (
        <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total Staff</CardTitle>
              <Users className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{summary.total_staff}</div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium text-green-600">Present</CardTitle>
              <CheckCircle className="h-4 w-4 text-green-600" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-green-600">{summary.present}</div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium text-orange-600">Half Day</CardTitle>
              <Clock className="h-4 w-4 text-orange-600" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-orange-600">{summary.half_day}</div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium text-red-600">Absent</CardTitle>
              <XCircle className="h-4 w-4 text-red-600" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-red-600">{summary.absent}</div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium text-blue-600">Leave</CardTitle>
              <Coffee className="h-4 w-4 text-blue-600" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-blue-600">{summary.leave}</div>
            </CardContent>
          </Card>
        </div>
      ) : null}

      {/* Tabs for Quick Mark and Detailed View */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-4">
        <TabsList className="w-auto">
          <TabsTrigger value="quick">
            <Zap className="h-4 w-4 mr-2" />
            Quick Mark
          </TabsTrigger>
          <TabsTrigger value="detailed">
            <List className="h-4 w-4 mr-2" />
            Detailed View
          </TabsTrigger>
        </TabsList>

        {/* Quick Mark Tab */}
        <TabsContent value="quick" className="space-y-4">
          {!isToday && (
            <Card className="border-orange-200 bg-orange-50">
              <CardContent className="p-4">
                <p className="text-sm text-orange-800">
                  Quick marking is only available for today's date. Viewing past attendance records.
                </p>
              </CardContent>
            </Card>
          )}
          <QuickAttendanceMark
            selectedDate={selectedDate}
            onRefresh={fetchDailySummary}
          />
        </TabsContent>

        {/* Detailed View Tab */}
        <TabsContent value="detailed" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Staff Attendance</CardTitle>
            </CardHeader>
            <CardContent>
              {isLoading ? (
                <div className="flex justify-center py-8">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
                </div>
              ) : summary ? (
                <AttendanceTable
                  records={summary.attendance_records}
                  onEdit={handleMarkAttendance}
                  canEdit={canMarkAttendance}
                />
              ) : (
                <p className="text-center text-muted-foreground py-8">
                  No attendance data available
                </p>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Mark Attendance Dialog */}
      {isMarkDialogOpen && (
        <AttendanceMarkDialog
          open={isMarkDialogOpen}
          onClose={() => {
            setIsMarkDialogOpen(false);
            setSelectedStaff(null);
          }}
          onSuccess={handleAttendanceMarked}
          selectedDate={selectedDate}
          selectedStaff={selectedStaff}
        />
      )}
    </div>
  );
}
