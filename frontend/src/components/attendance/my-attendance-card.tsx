'use client';

import { useState, useEffect } from 'react';
import { CheckCircle, Clock, XCircle, Coffee, User } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { apiClient } from '@/lib/api-client';
import { toast } from 'sonner';
import { useAuthStore } from '@/stores/auth-store';

interface TodayAttendance {
  id: string;
  status: 'present' | 'half_day' | 'absent' | 'leave';
  signed_in_at: string | null;
  signed_out_at: string | null;
  date: string;
}

export function MyAttendanceCard() {
  const { user } = useAuthStore();
  const [todayAttendance, setTodayAttendance] = useState<TodayAttendance | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isMarking, setIsMarking] = useState(false);

  useEffect(() => {
    if (user?.staff_id) {
      fetchTodayAttendance();
    }
  }, [user]);

  const fetchTodayAttendance = async () => {
    try {
      setIsLoading(true);
      const today = new Date().toISOString().split('T')[0];
      const { data } = await apiClient.get('/attendance/my-attendance', {
        params: { start_date: today, end_date: today },
      });

      if (data.items && data.items.length > 0) {
        setTodayAttendance(data.items[0]);
      } else {
        setTodayAttendance(null);
      }
    } catch (error: any) {
      console.error('Error fetching today attendance:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleMarkPresent = async () => {
    if (!user?.staff_id) {
      toast.error('No staff profile found');
      return;
    }

    try {
      setIsMarking(true);
      const today = new Date().toISOString().split('T')[0];
      const now = new Date().toISOString();

      await apiClient.post('/attendance/my-attendance/mark', {
        staff_id: user.staff_id,
        date: today,
        status: 'present',
        signed_in_at: now,
      });

      toast.success('Attendance marked successfully!');
      fetchTodayAttendance();
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to mark attendance');
    } finally {
      setIsMarking(false);
    }
  };

  const handleCheckOut = async () => {
    if (!user?.staff_id || !todayAttendance) {
      return;
    }

    try {
      setIsMarking(true);
      const today = new Date().toISOString().split('T')[0];
      const now = new Date().toISOString();

      await apiClient.post('/attendance/my-attendance/mark', {
        staff_id: user.staff_id,
        date: today,
        status: todayAttendance.status,
        signed_in_at: todayAttendance.signed_in_at,
        signed_out_at: now,
      });

      toast.success('Checked out successfully!');
      fetchTodayAttendance();
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to check out');
    } finally {
      setIsMarking(false);
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'present':
        return (
          <Badge className="bg-green-500">
            <CheckCircle className="h-3 w-3 mr-1" />
            Present
          </Badge>
        );
      case 'half_day':
        return (
          <Badge className="bg-orange-500">
            <Clock className="h-3 w-3 mr-1" />
            Half Day
          </Badge>
        );
      case 'absent':
        return (
          <Badge className="bg-red-500">
            <XCircle className="h-3 w-3 mr-1" />
            Absent
          </Badge>
        );
      case 'leave':
        return (
          <Badge className="bg-blue-500">
            <Coffee className="h-3 w-3 mr-1" />
            Leave
          </Badge>
        );
      default:
        return null;
    }
  };

  const formatTime = (timestamp: string | null) => {
    if (!timestamp) return '--:--';
    return new Date(timestamp).toLocaleTimeString('en-IN', {
      hour: '2-digit',
      minute: '2-digit',
      hour12: true,
    });
  };

  if (!user?.staff_id) {
    return null;
  }

  if (isLoading) {
    return (
      <Card>
        <CardContent className="p-6">
          <div className="animate-pulse space-y-4">
            <div className="h-4 bg-muted rounded w-1/2" />
            <div className="h-20 bg-muted rounded" />
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="border-primary/20 bg-gradient-to-br from-primary/5 to-primary/10">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <User className="h-5 w-5" />
          My Attendance Today
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {todayAttendance ? (
          <>
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">Status:</span>
              {getStatusBadge(todayAttendance.status)}
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-sm text-muted-foreground mb-1">Check In</p>
                <p className="text-lg font-semibold">
                  {formatTime(todayAttendance.signed_in_at)}
                </p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground mb-1">Check Out</p>
                <p className="text-lg font-semibold">
                  {formatTime(todayAttendance.signed_out_at)}
                </p>
              </div>
            </div>

            {todayAttendance.status === 'present' && !todayAttendance.signed_out_at && (
              <Button
                onClick={handleCheckOut}
                disabled={isMarking}
                variant="outline"
                className="w-full"
              >
                Check Out
              </Button>
            )}
          </>
        ) : (
          <>
            <p className="text-sm text-muted-foreground">
              You haven't marked your attendance today.
            </p>
            <Button
              onClick={handleMarkPresent}
              disabled={isMarking}
              className="w-full"
            >
              <CheckCircle className="h-4 w-4 mr-2" />
              Mark Present
            </Button>
          </>
        )}
      </CardContent>
    </Card>
  );
}
