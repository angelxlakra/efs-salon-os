'use client';

import { useState } from 'react';
import { format, parseISO } from 'date-fns';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogBody,
  DialogFooter,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { checkInAppointment } from '@/lib/api/appointments';
import { toast } from 'sonner';

interface AppointmentMinimal {
  id: string;
  customer_name: string;
  scheduled_at: string;
}

interface CheckInDialogProps {
  open: boolean;
  appointment: AppointmentMinimal | null;
  staffName: string;
  serviceName: string;
  onCheckedIn: (id: string) => void;
  onOpenChange: (open: boolean) => void;
}

export function CheckInDialog({
  open,
  appointment,
  staffName,
  serviceName,
  onCheckedIn,
  onOpenChange,
}: CheckInDialogProps) {
  const [loading, setLoading] = useState(false);

  if (!appointment) return null;

  const scheduledTime = format(parseISO(appointment.scheduled_at), 'h:mm a');

  const handleCheckIn = async () => {
    setLoading(true);
    try {
      await checkInAppointment(appointment.id);
      toast.success(`${appointment.customer_name} checked in`);
      onCheckedIn(appointment.id);
      onOpenChange(false);
    } catch {
      toast.error('Failed to check in — please try again');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent size="sm">
        <DialogHeader>
          <DialogTitle>Check In Customer</DialogTitle>
        </DialogHeader>

        <DialogBody>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div>
              <span className="db-label">Customer</span>
              <p style={{ fontFamily: "'DM Sans', system-ui, sans-serif", fontSize: 16, fontWeight: 700, color: 'var(--db-ink)', marginTop: 2 }}>
                {appointment.customer_name}
              </p>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
              <div>
                <span className="db-label">Service</span>
                <p style={{ fontFamily: "'DM Sans', system-ui, sans-serif", fontSize: 13, color: 'var(--db-ink-3)', marginTop: 2 }}>
                  {serviceName}
                </p>
              </div>
              <div>
                <span className="db-label">With</span>
                <p style={{ fontFamily: "'DM Sans', system-ui, sans-serif", fontSize: 13, color: 'var(--db-ink-3)', marginTop: 2 }}>
                  {staffName}
                </p>
              </div>
            </div>

            <div>
              <span className="db-label">Scheduled</span>
              <p style={{ fontFamily: "'Cormorant Garamond', serif", fontSize: 28, fontWeight: 300, letterSpacing: '-1px', color: 'var(--db-ink)', lineHeight: 1, fontVariantNumeric: 'tabular-nums', marginTop: 4 }}>
                {scheduledTime}
              </p>
            </div>
          </div>
        </DialogBody>

        <DialogFooter>
          <Button variant="ghost" onClick={() => onOpenChange(false)} disabled={loading}>
            Cancel
          </Button>
          <Button variant="primary" onClick={handleCheckIn} disabled={loading} loading={loading}>
            {loading ? 'Checking in…' : 'Check In'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
