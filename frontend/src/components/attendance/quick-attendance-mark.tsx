'use client';

import { useState, useEffect } from 'react';
import { CheckCircle, Clock, XCircle, LogOut, RefreshCw } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { apiClient } from '@/lib/api-client';
import { toast } from 'sonner';
import { format } from 'date-fns';

interface Staff {
  id: string;
  display_name: string;
  full_name: string;
  is_active: boolean;
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
  staff: Staff;
}

interface QuickAttendanceMarkProps {
  selectedDate: string;
  onRefresh: () => void;
}

export function QuickAttendanceMark({ selectedDate, onRefresh }: QuickAttendanceMarkProps) {
  const [allStaff, setAllStaff] = useState<Staff[]>([]);
  const [markedAttendance, setMarkedAttendance] = useState<Map<string, AttendanceRecord>>(new Map());
  const [isLoading, setIsLoading] = useState(true);
  const [isMarking, setIsMarking] = useState<string | null>(null);

  useEffect(() => {
    fetchData();
  }, [selectedDate]);

  const fetchData = async () => {
    try {
      setIsLoading(true);

      // Fetch all staff
      const { data: staffData } = await apiClient.get('/staff');
      const staff = staffData.items || staffData;
      setAllStaff(staff);

      // Fetch today's attendance
      const { data: attendanceData } = await apiClient.get('/attendance', {
        params: { date_filter: selectedDate, size: 100 },
      });

      // Create a map of staff_id -> attendance record
      const attendanceMap = new Map<string, AttendanceRecord>();
      (attendanceData.items || []).forEach((record: AttendanceRecord) => {
        attendanceMap.set(record.staff_id, record);
      });
      setMarkedAttendance(attendanceMap);
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to fetch data');
    } finally {
      setIsLoading(false);
    }
  };

  const handleQuickMarkPresent = async (staff: Staff) => {
    try {
      setIsMarking(staff.id);
      const now = new Date();
      const signedInAt = `${selectedDate}T${format(now, 'HH:mm:ss')}`;

      await apiClient.post('/attendance', {
        staff_id: staff.id,
        date: selectedDate,
        status: 'present',
        signed_in_at: signedInAt,
        notes: null,
      });

      toast.success(`${staff.display_name} marked present at ${format(now, 'h:mm a')}`);
      await fetchData();
      onRefresh();
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to mark attendance');
    } finally {
      setIsMarking(null);
    }
  };

  const handleQuickCheckout = async (staff: Staff, record: AttendanceRecord) => {
    try {
      setIsMarking(staff.id);
      const now = new Date();
      const signedOutAt = `${selectedDate}T${format(now, 'HH:mm:ss')}`;

      await apiClient.post('/attendance', {
        staff_id: staff.id,
        date: selectedDate,
        status: record.status,
        signed_in_at: record.signed_in_at,
        signed_out_at: signedOutAt,
        notes: record.notes,
      });

      toast.success(`${staff.display_name} checked out at ${format(now, 'h:mm a')}`);
      await fetchData();
      onRefresh();
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to mark checkout');
    } finally {
      setIsMarking(null);
    }
  };

  const unmarkedStaff = allStaff.filter((staff) => !markedAttendance.has(staff.id));
  const presentStaff = allStaff.filter((staff) => {
    const record = markedAttendance.get(staff.id);
    return record && (record.status === 'present' || record.status === 'half_day');
  });

  if (isLoading) {
    return (
      <div className="flex justify-center py-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
      </div>
    );
  }

  const isToday = selectedDate === new Date().toISOString().split('T')[0];

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      {/* Unmarked Staff */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-4">
          <div>
            <CardTitle className="text-lg">Not Marked Yet</CardTitle>
            <p className="text-sm text-muted-foreground mt-1">
              Click to mark present at current time
            </p>
          </div>
          <Badge variant="outline" className="text-lg">
            {unmarkedStaff.length}
          </Badge>
        </CardHeader>
        <CardContent>
          {unmarkedStaff.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              <CheckCircle className="h-12 w-12 mx-auto mb-2 opacity-50" />
              <p>All staff marked!</p>
            </div>
          ) : (
            <div className="space-y-2">
              {unmarkedStaff.map((staff) => (
                <div
                  key={staff.id}
                  className="flex items-center justify-between p-3 border rounded-lg hover:bg-accent transition-colors"
                >
                  <div className="flex items-center gap-3">
                    <Avatar className="h-10 w-10">
                      <AvatarFallback>
                        {staff.display_name.charAt(0)}
                      </AvatarFallback>
                    </Avatar>
                    <div>
                      <p className="font-medium">{staff.display_name}</p>
                      <p className="text-sm text-muted-foreground">
                        {staff.user.full_name}
                      </p>
                    </div>
                  </div>
                  <Button
                    size="sm"
                    onClick={() => handleQuickMarkPresent(staff)}
                    disabled={isMarking === staff.id || !isToday}
                    className="gap-2"
                  >
                    {isMarking === staff.id ? (
                      <RefreshCw className="h-4 w-4 animate-spin" />
                    ) : (
                      <CheckCircle className="h-4 w-4" />
                    )}
                    Mark Present
                  </Button>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Present Staff - Needs Checkout */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-4">
          <div>
            <CardTitle className="text-lg">Present Today</CardTitle>
            <p className="text-sm text-muted-foreground mt-1">
              Click to mark checkout time
            </p>
          </div>
          <Badge variant="outline" className="text-lg bg-green-50 text-green-700 border-green-200">
            {presentStaff.length}
          </Badge>
        </CardHeader>
        <CardContent>
          {presentStaff.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              <Clock className="h-12 w-12 mx-auto mb-2 opacity-50" />
              <p>No one marked present yet</p>
            </div>
          ) : (
            <div className="space-y-2">
              {presentStaff.map((staff) => {
                const record = markedAttendance.get(staff.id)!;
                const hasCheckedOut = !!record.signed_out_at;

                return (
                  <div
                    key={staff.id}
                    className={`flex items-center justify-between p-3 border rounded-lg ${
                      hasCheckedOut ? 'bg-muted/50' : 'hover:bg-accent'
                    } transition-colors`}
                  >
                    <div className="flex items-center gap-3">
                      <Avatar className="h-10 w-10">
                        <AvatarFallback className={hasCheckedOut ? 'bg-muted' : 'bg-green-100 text-green-700'}>
                          {staff.display_name.charAt(0)}
                        </AvatarFallback>
                      </Avatar>
                      <div className="flex-1">
                        <p className="font-medium">{staff.display_name}</p>
                        <div className="flex items-center gap-3 text-sm text-muted-foreground">
                          <span className="flex items-center gap-1">
                            <Clock className="h-3 w-3" />
                            In: {record.signed_in_at ? format(new Date(record.signed_in_at), 'h:mm a') : '-'}
                          </span>
                          {hasCheckedOut && (
                            <span className="flex items-center gap-1">
                              <LogOut className="h-3 w-3" />
                              Out: {format(new Date(record.signed_out_at), 'h:mm a')}
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                    {hasCheckedOut ? (
                      <Badge variant="outline" className="bg-green-50 text-green-700 border-green-200">
                        <CheckCircle className="h-3 w-3 mr-1" />
                        Complete
                      </Badge>
                    ) : (
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => handleQuickCheckout(staff, record)}
                        disabled={isMarking === staff.id || !isToday}
                        className="gap-2"
                      >
                        {isMarking === staff.id ? (
                          <RefreshCw className="h-4 w-4 animate-spin" />
                        ) : (
                          <LogOut className="h-4 w-4" />
                        )}
                        Check Out
                      </Button>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
