'use client';

import { Button } from '@/components/ui/button';
import { Clock, Play, Check } from 'lucide-react';
import { apiClient } from '@/lib/api-client';
import { toast } from 'sonner';
import { useAuthStore } from '@/stores/auth-store';
import { titleCase } from '@/lib/utils';

interface Service {
  id: string;
  name: string;
  base_price: number;
  duration_minutes: number;
}

interface Staff {
  id: string;
  display_name: string;
}

interface WalkIn {
  id: string;
  ticket_number: string;
  customer_name: string;
  customer_phone: string;
  customer_id: string | null;
  service: Service;
  assigned_staff: Staff;
  status: string;
  checked_in_at: string | null;
  started_at: string | null;
  completed_at: string | null;
  service_notes: string | null;
  duration_minutes: number;
  session_id: string | null;
}

interface CustomerSession {
  session_id: string;
  customer_name: string;
  customer_phone: string;
  customer_id: string | null;
  walkins: WalkIn[];
  total_amount: number; // in paise
  time_since_checkin: number; // minutes
  all_completed: boolean;
}

interface ActiveCustomerCardProps {
  session: CustomerSession;
  onCheckout: (sessionId: string) => void;
  onRefresh?: () => void;
}

const STATUS_COLORS: Record<string, string> = {
  checked_in: 'bg-blue-500',
  in_progress: 'bg-amber-400 animate-pulse',
  completed: 'bg-green-500',
};

const getStatusDot = (status: string) => (
  <span className={`block h-2 w-2 rounded-full shrink-0 ${STATUS_COLORS[status] ?? 'bg-text-muted'}`} />
);

export function ActiveCustomerCard({
  session,
  onCheckout,
  onRefresh,
}: ActiveCustomerCardProps) {
  const { user } = useAuthStore();
  const canManageServices = user?.role === 'owner' || user?.role === 'receptionist';

  const handleStartService = async (walkinId: string) => {
    try {
      await apiClient.post(`/appointments/walkins/${walkinId}/start`);
      toast.success('Service started');
      onRefresh?.();
    } catch (error: any) {
      console.error('Error starting service:', error);
      toast.error(error.response?.data?.detail || 'Failed to start service');
    }
  };

  const handleCompleteService = async (walkinId: string) => {
    try {
      await apiClient.post(`/appointments/walkins/${walkinId}/complete`);
      toast.success('Service completed');
      onRefresh?.();
    } catch (error: any) {
      console.error('Error completing service:', error);
      toast.error(error.response?.data?.detail || 'Failed to complete service');
    }
  };
  const formatPrice = (paise: number) => {
    return `₹${(paise / 100).toFixed(2)}`;
  };

  return (
    <div className="rounded-xl bg-surface-card border border-border-subtle hover:border-accent/30 transition-colors">
      <div className="p-4 pb-2">
        <div className="flex justify-between items-start">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <h3 className="font-semibold text-base truncate leading-none text-text-primary">
                {titleCase(session.customer_name)}
              </h3>
              <span className="inline-flex items-center gap-1 text-[10px] text-text-muted bg-surface-row px-2 py-0.5 rounded-full">
                <Clock className="h-3 w-3" />
                {session.time_since_checkin}m
              </span>
            </div>
            <p className="text-xs text-text-secondary mt-1 truncate">
              {session.customer_phone}
            </p>
          </div>
        </div>
      </div>

      <div className="px-4 py-2">
        <div className="space-y-2">
          {session.walkins.map((walkin) => (
            <div
              key={walkin.id}
              className="flex items-center justify-between text-sm gap-2 rounded-lg bg-surface-row px-3 py-2"
            >
              <div className="flex items-center gap-2 min-w-0 flex-1">
                {getStatusDot(walkin.status)}
                <span className="truncate font-medium text-xs text-text-primary">
                  {walkin.service.name}
                </span>
                <span className="text-[10px] text-text-muted truncate">
                  • {walkin.assigned_staff.display_name}
                </span>
              </div>
              {canManageServices && (
                <div className="flex gap-1">
                  {walkin.status === 'checked_in' && (
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-6 w-6 p-0 text-blue-400 hover:text-blue-300 hover:bg-blue-500/10"
                      onClick={() => handleStartService(walkin.id)}
                      title="Start service"
                    >
                      <Play className="h-3 w-3" />
                    </Button>
                  )}
                  {walkin.status === 'in_progress' && (
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-6 w-6 p-0 text-green-400 hover:text-green-300 hover:bg-green-500/10"
                      onClick={() => handleCompleteService(walkin.id)}
                      title="Complete service"
                    >
                      <Check className="h-3 w-3" />
                    </Button>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>

        <div className="mt-3 pt-2 border-t border-border-subtle flex justify-between items-center">
          <span className="text-xs text-text-secondary">Total Amount</span>
          <span className="font-semibold text-sm text-text-primary">
            {formatPrice(session.total_amount)}
          </span>
        </div>
      </div>

      <div className="px-4 pb-4 pt-2">
        <Button
          className="w-full h-8 text-xs"
          size="sm"
          disabled={!session.all_completed}
          onClick={() => onCheckout(session.session_id)}
        >
          Checkout
        </Button>
      </div>
    </div>
  );
}
