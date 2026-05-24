'use client';

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
  total_amount: number;
  time_since_checkin: number;
  all_completed: boolean;
}

interface ActiveCustomerCardProps {
  session: CustomerSession;
  onCheckout: (sessionId: string) => void;
  onRefresh?: () => void;
}

function formatRupees(paise: number) {
  return `₹${(paise / 100).toLocaleString('en-IN')}`;
}

function dotClass(status: string): string {
  if (status === 'in_progress') return 'db-svc-dot db-svc-dot-ip';
  if (status === 'completed')   return 'db-svc-dot db-svc-dot-done';
  return 'db-svc-dot db-svc-dot-ci';
}

export function ActiveCustomerCard({ session, onCheckout, onRefresh }: ActiveCustomerCardProps) {
  const { user } = useAuthStore();
  const canManage = user?.role === 'owner' || user?.role === 'receptionist';
  const isAllCheckedIn = session.walkins.every(w => w.status === 'checked_in');
  const isLive = session.walkins.some(w => w.status === 'in_progress');

  const handleStart = async (walkinId: string) => {
    try {
      await apiClient.post(`/appointments/walkins/${walkinId}/start`);
      toast.success('Service started');
      onRefresh?.();
    } catch (err: any) {
      toast.error(err.response?.data?.detail ?? 'Failed to start service');
    }
  };

  const handleComplete = async (walkinId: string) => {
    try {
      await apiClient.post(`/appointments/walkins/${walkinId}/complete`);
      toast.success('Service completed');
      onRefresh?.();
    } catch (err: any) {
      toast.error(err.response?.data?.detail ?? 'Failed to complete service');
    }
  };

  const handleStartAll = async () => {
    const checkedIn = session.walkins.filter(w => w.status === 'checked_in');
    try {
      await Promise.all(checkedIn.map(w => apiClient.post(`/appointments/walkins/${w.id}/start`)));
      toast.success('Services started');
      onRefresh?.();
    } catch (err: any) {
      toast.error(err.response?.data?.detail ?? 'Failed to start services');
    }
  };

  return (
    <div className={`db-card-surface${isLive ? ' db-card-live' : ''}`}>
      {/* Card header */}
      <div style={{ padding: '12px 14px 10px' }}>
        {isLive ? (
          <div className="db-live-badge">
            <span className="db-live-dot" />
            LIVE
          </div>
        ) : (
          <div className="db-ci-badge">
            <span className="db-ci-dot" />
            CHECKED IN · WAITING
          </div>
        )}
        <div style={{ fontFamily: "'DM Sans', system-ui, sans-serif", fontSize: 14, fontWeight: 700, color: 'var(--db-ink)' }}>
          {titleCase(session.customer_name)}
        </div>
        <div style={{ fontFamily: "'DM Sans', system-ui, sans-serif", fontSize: 10, color: 'var(--db-ink-5)', marginTop: 1 }}>
          {session.customer_phone}
        </div>
        <div style={{ fontFamily: "'DM Sans', system-ui, sans-serif", fontSize: 11, color: 'var(--db-ink-4)', marginTop: 3 }}>
          {session.time_since_checkin}m ago
        </div>
      </div>

      {/* Per-service rows */}
      <div className="db-svc-rows">
        {session.walkins.map((walkin) => (
          <div key={walkin.id} className="db-svc-row">
            <span className={dotClass(walkin.status)} />
            <span style={{ flex: 1, fontFamily: "'DM Sans', system-ui, sans-serif", fontSize: 11, fontWeight: 600, color: 'var(--db-ink)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {walkin.service.name}
            </span>
            <span className="db-num" style={{ fontSize: 14, fontWeight: 400, color: 'var(--db-ink-3)', flexShrink: 0, letterSpacing: '-0.5px', fontVariantNumeric: 'tabular-nums' }}>
              {formatRupees(walkin.service.base_price)}
            </span>
            {canManage && walkin.status === 'checked_in' && (
              <button
                className="db-svc-btn db-svc-btn-start"
                title="Start service"
                onClick={() => handleStart(walkin.id)}
              >
                ▶
              </button>
            )}
            {canManage && walkin.status === 'in_progress' && (
              <button
                className="db-svc-btn db-svc-btn-finish"
                title="Complete service"
                onClick={() => handleComplete(walkin.id)}
              >
                ✓
              </button>
            )}
          </div>
        ))}
      </div>

      {/* Footer */}
      <div className="db-card-footer">
        <div>
          <span className="db-label">Total</span>
          <span className="db-num db-num-card">{formatRupees(session.total_amount)}</span>
        </div>
        {isAllCheckedIn ? (
          <button
            style={{ background: 'var(--db-gold)', color: '#fff', border: 'none', borderRadius: 7, padding: '6px 12px', fontSize: 11, fontWeight: 700, cursor: 'pointer', fontFamily: "'DM Sans', system-ui, sans-serif" }}
            aria-label="Start all services"
            onClick={handleStartAll}
          >
            Start Services
          </button>
        ) : (
          <button
            style={{ background: session.all_completed ? 'var(--db-ink)' : 'var(--db-border)', color: session.all_completed ? '#fff' : 'var(--db-ink-5)', border: 'none', borderRadius: 7, padding: '6px 12px', fontSize: 11, fontWeight: 700, cursor: session.all_completed ? 'pointer' : 'not-allowed', fontFamily: "'DM Sans', system-ui, sans-serif" }}
            disabled={!session.all_completed}
            onClick={() => onCheckout(session.session_id)}
            aria-label="End and checkout"
          >
            End &amp; Checkout
          </button>
        )}
      </div>
    </div>
  );
}
