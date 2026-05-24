'use client';

import { useEffect, useState, useMemo } from 'react';
import { useRouter } from 'next/navigation';
import { format } from 'date-fns';
import { Cake } from 'lucide-react';
import { apiClient } from '@/lib/api-client';
import { toast } from 'sonner';
import { useCartStore } from '@/stores/cart-store';
import { useAuthStore } from '@/stores/auth-store';
import { titleCase } from '@/lib/utils';
import { Skeleton } from '@/components/ui/skeleton';

import { StatsBar }           from '@/components/dashboard/stats-bar';
import { GoalsRings }         from '@/components/dashboard/radial-goal-progress';
import { ActiveCustomerCard } from '@/components/dashboard/active-customer-card';
import { ServiceQueue }       from '@/components/dashboard/service-queue';
import { UpNextPanel }        from '@/components/dashboard/up-next-panel';

// ── Types (unchanged from original) ────────────────────────────────────────

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
  status: 'checked_in' | 'in_progress' | 'completed' | 'cancelled';
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

interface DashboardStats {
  today_revenue: number;
  today_services: number;
  today_customers: number;
  active_services: number;
  pending_bills: number;
}

interface SalonSettings {
  daily_revenue_target_paise: number;
  daily_services_target: number;
}

interface ComparisonData {
  revenue_change_paise: number;
  revenue_percent_change: number;
  services_change: number;
  services_percent_change: number;
  customers_change: number;
  customers_percent_change: number;
}

// ── Component ───────────────────────────────────────────────────────────────

export default function DashboardPage() {
  const router = useRouter();
  const { user } = useAuthStore();
  const { addItem, setCustomer, setSessionId, clearCart } = useCartStore();

  const [stats, setStats] = useState<DashboardStats>({
    today_revenue: 0,
    today_services: 0,
    today_customers: 0,
    active_services: 0,
    pending_bills: 0,
  });
  const [activeSessions, setActiveSessions] = useState<CustomerSession[]>([]);
  const [settings, setSettings] = useState<SalonSettings>({
    daily_revenue_target_paise: 2000000,
    daily_services_target: 25,
  });
  const [comparison, setComparison] = useState<ComparisonData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [birthdayUsers, setBirthdayUsers] = useState<{ id: string; full_name: string }[]>([]);
  const [revenueHidden, setRevenueHidden] = useState(false);

  useEffect(() => {
    if (user?.role === 'staff') router.push('/dashboard/staff');
  }, [user, router]);

  useEffect(() => {
    fetchDashboardData();
    const interval = setInterval(() => fetchDashboardData(true), 10_000);
    return () => clearInterval(interval);
  }, []);

  const fetchDashboardData = async (silent = false) => {
    try {
      if (!silent) setIsLoading(true);
      const [walkinsRes, reportsRes, settingsRes, comparisonRes, birthdaysRes] =
        await Promise.all([
          apiClient.get('/appointments/walkins/active'),
          apiClient.get('/reports/dashboard'),
          apiClient.get('/settings'),
          apiClient.get('/reports/dashboard/comparison'),
          apiClient.get('/users/birthdays/today'),
        ]);

      setActiveSessions(walkinsRes.data.sessions ?? []);

      const m = reportsRes.data.metrics;
      setStats({
        today_revenue:   m.net_revenue,
        today_services:  m.completed_appointments,
        today_customers: m.total_bills,
        active_services: m.active_appointments,
        pending_bills:   m.pending_appointments,
      });

      if (settingsRes.data) {
        setSettings({
          daily_revenue_target_paise: settingsRes.data.daily_revenue_target_paise ?? 2000000,
          daily_services_target:      settingsRes.data.daily_services_target      ?? 25,
        });
      }

      if (comparisonRes.data?.comparison) setComparison(comparisonRes.data.comparison);
      if (birthdaysRes.data?.birthdays)    setBirthdayUsers(birthdaysRes.data.birthdays);
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
        ?? 'Failed to load dashboard data';
      if (!silent) toast.error(detail);
    } finally {
      setIsLoading(false);
    }
  };

  const handleCheckoutSession = async (sessionId: string) => {
    const session = activeSessions.find(s => s.session_id === sessionId);
    if (!session) { toast.error('Session not found'); return; }
    clearCart();
    session.walkins.filter(w => w.status !== 'cancelled').forEach(w => {
      addItem({
        isProduct: false,
        serviceId: w.service.id,
        serviceName: w.service.name,
        quantity: 1,
        unitPrice: w.service.base_price,
        discount: 0,
        taxRate: 18,
        staffId: w.assigned_staff.id,
        staffName: w.assigned_staff.display_name,
        duration: w.duration_minutes,
      });
    });
    setCustomer(session.customer_id, titleCase(session.customer_name), session.customer_phone);
    setSessionId(sessionId);
    router.push('/dashboard/pos');
    toast.success(`Ready to bill ${titleCase(session.customer_name)}`);
  };

  // Computed values for StatsBar and GoalsRings
  const revenuePct = settings.daily_revenue_target_paise > 0
    ? Math.min(100, Math.round((stats.today_revenue / settings.daily_revenue_target_paise) * 100))
    : 0;

  const checkedInWaiting = useMemo(
    () => activeSessions.filter(s => s.walkins.every(w => w.status === 'checked_in')).length,
    [activeSessions]
  );

  const avgBillTodayPaise = stats.today_customers > 0
    ? Math.round(stats.today_revenue / stats.today_customers)
    : 0;

  const customersTarget = Math.round(settings.daily_services_target * 0.85);
  const weekdayName = format(new Date(), 'EEEE');

  return (
    <div className="dashboard-page" style={{ display: 'flex', flexDirection: 'column', minHeight: '100dvh' }}>

      {/* Main layout: content + right sidebar */}
      <div style={{ display: 'flex', flex: 1, alignItems: 'stretch' }}>

        {/* Main content */}
        <div style={{ flex: 1, padding: 14, display: 'flex', flexDirection: 'column', gap: 12, minWidth: 0 }}>

          {/* Page action row — "+ New Walk-in" lives here since shell TopBar handles nav/search */}
          <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
            <button
              style={{ background: 'var(--db-ink)', color: '#fff', border: 'none', borderRadius: 8, padding: '8px 16px', fontSize: 12, fontWeight: 700, cursor: 'pointer', whiteSpace: 'nowrap', fontFamily: "'DM Sans', system-ui, sans-serif" }}
              onClick={() => router.push('/dashboard/pos')}
            >
              + New Walk-in
            </button>
          </div>

          {/* Birthday banner */}
          {birthdayUsers.length > 0 && (
            <div className="relative overflow-hidden rounded-xl bg-gradient-to-r from-pink-500 via-purple-500 to-yellow-400 p-[2px]">
              <div className="flex items-center gap-4 rounded-xl bg-surface-card px-5 py-4">
                <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-pink-400 to-purple-500 shadow-lg">
                  <Cake className="h-6 w-6 text-white" />
                </div>
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-bold text-text-primary">
                    {birthdayUsers.length === 1
                      ? `Happy Birthday, ${birthdayUsers[0].full_name}!`
                      : `Happy Birthday to ${birthdayUsers.map(u => u.full_name).join(' & ')}!`}
                  </p>
                  <p className="text-xs text-text-secondary mt-0.5">
                    {birthdayUsers.length === 1 ? 'Wishing them a wonderful day!' : `${birthdayUsers.length} team members celebrating today!`}
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Stats bar */}
          {isLoading ? (
            <Skeleton shape="card" className="h-36" />
          ) : (
            <StatsBar
              revenueToday={stats.today_revenue}
              revenueTarget={settings.daily_revenue_target_paise}
              revenueDeltaPaise={comparison?.revenue_change_paise ?? 0}
              activeServices={stats.active_services}
              checkedInWaiting={checkedInWaiting}
              pendingBills={stats.pending_bills}
              avgBillTodayPaise={avgBillTodayPaise}
              revenueHidden={revenueHidden}
              onToggleRevenue={() => setRevenueHidden(h => !h)}
            />
          )}

          {/* Goals rings */}
          {isLoading ? (
            <Skeleton shape="card" className="h-36" />
          ) : (
            <GoalsRings
              revenueTarget={settings.daily_revenue_target_paise}
              currentRevenue={stats.today_revenue}
              servicesTarget={settings.daily_services_target}
              currentServices={stats.today_services}
              customersTarget={customersTarget}
              currentCustomers={stats.today_customers}
              weekdayName={weekdayName}
              revenuePct={revenuePct}
              revenueHidden={revenueHidden}
            />
          )}

          {/* Active customers */}
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10 }}>
              <span style={{ fontFamily: "'DM Sans', system-ui, sans-serif", fontSize: 14, fontWeight: 800, color: 'var(--db-ink)' }}>
                In service, right now
              </span>
              <span className="db-badge-gold">{stats.active_services} Active</span>
              {checkedInWaiting > 0 && (
                <span className="db-badge-muted">{checkedInWaiting} Checked in</span>
              )}
              <span style={{ fontFamily: "'DM Sans', system-ui, sans-serif", fontSize: 11, color: 'var(--db-ink-5)', fontStyle: 'italic', marginLeft: 'auto' }}>
                Tap to checkout
              </span>
            </div>

            {isLoading ? (
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
                <Skeleton shape="card" className="h-48" />
                <Skeleton shape="card" className="h-48" />
              </div>
            ) : activeSessions.length === 0 ? (
              <div style={{ padding: '32px 0', textAlign: 'center' }}>
                <p className="db-editorial" style={{ fontSize: 16, color: 'var(--db-ink-5)' }}>
                  Floor is clear — no active sessions.
                </p>
              </div>
            ) : (
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
                {activeSessions.map(session => (
                  <ActiveCustomerCard
                    key={session.session_id}
                    session={session}
                    onCheckout={handleCheckoutSession}
                    onRefresh={() => fetchDashboardData(true)}
                  />
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Right sidebar */}
        <div className="db-sidebar">
          {/* Up Next panel */}
          <UpNextPanel />

          {/* Staff Queue */}
          <div className="db-sidebar-section" style={{ flex: 1 }}>
            <span className="db-label">Staff Queue</span>
            <ServiceQueue sessions={activeSessions} variant="sidebar" />
          </div>
        </div>

      </div>
    </div>
  );
}
