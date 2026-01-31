'use client';

import { useEffect, useState } from 'react';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { apiClient } from '@/lib/api-client';
import { Clock, User } from 'lucide-react';

interface Staff {
  id: string;
  display_name: string;
  is_active: boolean;
}

interface StaffBusyness {
  staff_id: string;
  staff_name: string;
  active_services: number;
  queued_services: number;
  total_wait_minutes: number;
  status: 'available' | 'busy' | 'very_busy';
}

interface StaffWithBusyness extends Staff {
  busyness?: StaffBusyness;
}

interface StaffSelectorProps {
  value: string | null;
  onChange: (staffId: string, staffName: string) => void;
  disabled?: boolean;
  placeholder?: string;
}

export function StaffSelector({
  value,
  onChange,
  disabled = false,
  placeholder = 'Select staff',
}: StaffSelectorProps) {
  const [staff, setStaff] = useState<StaffWithBusyness[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchStaffWithBusyness();
  }, []);

  const fetchStaffWithBusyness = async () => {
    try {
      setIsLoading(true);

      // Fetch staff list and busyness data in parallel
      const [staffResponse, busynessResponse] = await Promise.all([
        apiClient.get('/staff', { params: { is_active: true } }),
        apiClient.get('/staff/availability/busyness'),
      ]);

      const staffList = staffResponse.data.items || staffResponse.data;
      const busynessData = busynessResponse.data;

      // Merge busyness data with staff list
      const staffWithBusyness: StaffWithBusyness[] = staffList.map((s: Staff) => ({
        ...s,
        busyness: busynessData.find((b: StaffBusyness) => b.staff_id === s.id),
      }));

      // Sort by availability (available first, then by wait time)
      staffWithBusyness.sort((a, b) => {
        const statusOrder = { available: 0, busy: 1, very_busy: 2 };
        const aStatus = a.busyness?.status || 'available';
        const bStatus = b.busyness?.status || 'available';

        if (statusOrder[aStatus] !== statusOrder[bStatus]) {
          return statusOrder[aStatus] - statusOrder[bStatus];
        }

        return (a.busyness?.total_wait_minutes || 0) - (b.busyness?.total_wait_minutes || 0);
      });

      setStaff(staffWithBusyness);
    } catch (err) {
      console.error('Error fetching staff:', err);
      setError('Failed to load staff');
    } finally {
      setIsLoading(false);
    }
  };

  const handleChange = (staffId: string) => {
    const selected = staff.find((s) => s.id === staffId);
    if (selected) {
      onChange(staffId, selected.display_name);
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'available':
        return <Badge className="bg-green-500 text-xs ml-2">Available</Badge>;
      case 'busy':
        return <Badge className="bg-yellow-500 text-xs ml-2">Busy</Badge>;
      case 'very_busy':
        return <Badge className="bg-red-500 text-xs ml-2">Very Busy</Badge>;
      default:
        return null;
    }
  };

  const formatWaitTime = (minutes: number) => {
    if (minutes === 0) return 'No wait';
    if (minutes < 60) return `~${minutes} min`;
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    return `~${hours}h ${mins}m`;
  };

  if (error) {
    return (
      <div className="text-sm text-destructive">
        {error}
      </div>
    );
  }

  return (
    <Select
      value={value || undefined}
      onValueChange={handleChange}
      disabled={disabled || isLoading}
    >
      <SelectTrigger disabled={disabled || isLoading}>
        <SelectValue placeholder={isLoading ? 'Loading...' : placeholder} />
      </SelectTrigger>
      <SelectContent>
        {staff.length === 0 && !isLoading && (
          <div className="p-2 text-sm text-muted-foreground">
            No active staff found
          </div>
        )}
        {staff.map((s) => (
          <SelectItem key={s.id} value={s.id} className="cursor-pointer">
            <div className="flex items-center justify-between w-full gap-2">
              <div className="flex items-center gap-2">
                <User className="h-4 w-4 text-gray-500" />
                <span>{s.display_name}</span>
              </div>
              <div className="flex items-center gap-2">
                {s.busyness && s.busyness.total_wait_minutes > 0 && (
                  <div className="flex items-center gap-1 text-xs text-muted-foreground">
                    <Clock className="h-3 w-3" />
                    <span>{formatWaitTime(s.busyness.total_wait_minutes)}</span>
                  </div>
                )}
                {s.busyness && getStatusBadge(s.busyness.status)}
              </div>
            </div>
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}
