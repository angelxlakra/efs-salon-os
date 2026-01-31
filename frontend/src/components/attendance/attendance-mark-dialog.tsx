'use client';

import { useState, useEffect } from 'react';
import { X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Textarea } from '@/components/ui/textarea';
import { apiClient } from '@/lib/api-client';
import { toast } from 'sonner';

interface Staff {
  id: string;
  display_name: string;
  full_name: string;
  is_active: boolean;
  user?: {
    id: string;
    full_name: string;
  };
}

interface AttendanceMarkDialogProps {
  open: boolean;
  onClose: () => void;
  onSuccess: () => void;
  selectedDate: string;
  selectedStaff?: Staff | null;
}

type AttendanceStatus = 'present' | 'half_day' | 'absent' | 'leave';

export function AttendanceMarkDialog({
  open,
  onClose,
  onSuccess,
  selectedDate,
  selectedStaff,
}: AttendanceMarkDialogProps) {
  const [allStaff, setAllStaff] = useState<Staff[]>([]);
  const [staffId, setStaffId] = useState<string>('');
  const [status, setStatus] = useState<AttendanceStatus>('present');
  const [signInTime, setSignInTime] = useState<string>('');
  const [signOutTime, setSignOutTime] = useState<string>('');
  const [notes, setNotes] = useState<string>('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isLoadingStaff, setIsLoadingStaff] = useState(false);

  useEffect(() => {
    if (open) {
      fetchAllStaff();
      // Set default sign-in time to current time
      const now = new Date();
      const hours = now.getHours().toString().padStart(2, '0');
      const minutes = now.getMinutes().toString().padStart(2, '0');
      setSignInTime(`${hours}:${minutes}`);
    }
  }, [open]);

  useEffect(() => {
    if (selectedStaff) {
      setStaffId(selectedStaff.id);
    }
  }, [selectedStaff]);

  const fetchAllStaff = async () => {
    try {
      setIsLoadingStaff(true);
      const { data } = await apiClient.get('/staff');
      setAllStaff(data.items || data);
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to fetch staff list');
    } finally {
      setIsLoadingStaff(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!staffId) {
      toast.error('Please select a staff member');
      return;
    }

    if ((status === 'present' || status === 'half_day') && !signInTime) {
      toast.error('Sign in time is required for present/half-day status');
      return;
    }

    if (signOutTime && signInTime && signOutTime <= signInTime) {
      toast.error('Sign out time must be after sign in time');
      return;
    }

    try {
      setIsSubmitting(true);

      // Combine date with time
      const signedInAt = signInTime
        ? `${selectedDate}T${signInTime}:00`
        : null;
      const signedOutAt = signOutTime
        ? `${selectedDate}T${signOutTime}:00`
        : null;

      await apiClient.post('/attendance', {
        staff_id: staffId,
        date: selectedDate,
        status,
        signed_in_at: signedInAt,
        signed_out_at: signedOutAt,
        notes: notes || null,
      });

      toast.success('Attendance marked successfully');
      onSuccess();
      resetForm();
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to mark attendance');
    } finally {
      setIsSubmitting(false);
    }
  };

  const resetForm = () => {
    setStaffId('');
    setStatus('present');
    setSignInTime('');
    setSignOutTime('');
    setNotes('');
  };

  const handleClose = () => {
    resetForm();
    onClose();
  };

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle>Mark Attendance</DialogTitle>
          <DialogDescription>
            Mark attendance for {new Date(selectedDate).toLocaleDateString()}
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Staff Selection */}
          <div className="space-y-2">
            <Label htmlFor="staff">Staff Member *</Label>
            <Select
              value={staffId}
              onValueChange={setStaffId}
              disabled={!!selectedStaff || isLoadingStaff}
            >
              <SelectTrigger>
                <SelectValue placeholder="Select staff member" />
              </SelectTrigger>
              <SelectContent>
                {allStaff.map((staff) => (
                  <SelectItem key={staff.id} value={staff.id}>
                    {staff.display_name} ({staff.user?.full_name || staff.full_name})
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Status Selection */}
          <div className="space-y-2">
            <Label htmlFor="status">Status *</Label>
            <Select
              value={status}
              onValueChange={(value) => setStatus(value as AttendanceStatus)}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="present">Present (Full Day)</SelectItem>
                <SelectItem value="half_day">Half Day</SelectItem>
                <SelectItem value="absent">Absent</SelectItem>
                <SelectItem value="leave">Leave</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Sign In Time */}
          {(status === 'present' || status === 'half_day') && (
            <div className="space-y-2">
              <Label htmlFor="signIn">Sign In Time *</Label>
              <input
                id="signIn"
                type="time"
                value={signInTime}
                onChange={(e) => setSignInTime(e.target.value)}
                className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                required
              />
            </div>
          )}

          {/* Sign Out Time */}
          {(status === 'present' || status === 'half_day') && (
            <div className="space-y-2">
              <Label htmlFor="signOut">Sign Out Time</Label>
              <input
                id="signOut"
                type="time"
                value={signOutTime}
                onChange={(e) => setSignOutTime(e.target.value)}
                className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
              />
            </div>
          )}

          {/* Notes */}
          <div className="space-y-2">
            <Label htmlFor="notes">Notes</Label>
            <Textarea
              id="notes"
              placeholder="Add notes (optional)"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={3}
              maxLength={500}
            />
            <p className="text-xs text-muted-foreground">
              {notes.length}/500 characters
            </p>
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={handleClose}>
              Cancel
            </Button>
            <Button type="submit" disabled={isSubmitting}>
              {isSubmitting ? 'Marking...' : 'Mark Attendance'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
