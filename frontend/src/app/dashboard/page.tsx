'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Users, DollarSign, Scissors, TrendingUp, Clock, CreditCard } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { apiClient } from '@/lib/api-client';
import { toast } from 'sonner';
import { useCartStore } from '@/stores/cart-store';
import { useAuthStore } from '@/stores/auth-store';
import { ActiveCustomerCard } from '@/components/dashboard/active-customer-card';

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

interface DashboardStats {
  today_revenue: number; // in paise
  today_services: number;
  today_customers: number;
  active_services: number;
  pending_bills: number;
}

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
  const [isLoading, setIsLoading] = useState(true);

  // Redirect staff users to their My Services page
  useEffect(() => {
    if (user?.role === 'staff') {
      router.push('/dashboard/staff');
    }
  }, [user, router]);

  useEffect(() => {
    fetchDashboardData();
    // Refresh every 10 seconds for real-time updates (silently)
    const interval = setInterval(() => fetchDashboardData(true), 10000);
    return () => clearInterval(interval);
  }, []);

  const fetchDashboardData = async (silent = false) => {
    try {
      if (!silent) {
        setIsLoading(true);
      }

      // Fetch active walk-ins
      const { data } = await apiClient.get('/appointments/walkins/active');
      setActiveSessions(data.sessions || []);

      // Fetch dashboard statistics
      const { data: reportsData } = await apiClient.get('/reports/dashboard');
      const metrics = reportsData.metrics;

      setStats({
        today_revenue: metrics.net_revenue,
        today_services: metrics.completed_appointments,
        today_customers: metrics.total_bills,
        active_services: metrics.active_appointments,
        pending_bills: metrics.pending_appointments,
      });
    } catch (error: any) {
      console.error('Failed to fetch dashboard data:', error);

      // Set default empty state on error
      setActiveSessions([]);

      // Only show error toast on initial load, not during background refreshes
      if (!silent) {
        toast.error(
          error.response?.data?.detail || 'Failed to load dashboard data'
        );
      }
    } finally {
      setIsLoading(false);
    }
  };

  const formatPrice = (paise: number) => {
    return `₹${(paise / 100).toLocaleString('en-IN')}`;
  };

  const getCurrentDate = () => {
    return new Date().toLocaleDateString('en-IN', {
      weekday: 'long',
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
  };

  const handleCheckoutSession = async (sessionId: string) => {
    try {
      // Find the session
      const session = activeSessions.find((s) => s.session_id === sessionId);
      if (!session) {
        toast.error('Session not found');
        return;
      }

      // Clear any existing cart items
      clearCart();

      // Add all services to cart
      session.walkins.forEach((walkin) => {
        addItem({
          isProduct: false,
          serviceId: walkin.service.id,
          serviceName: walkin.service.name,
          quantity: 1,
          unitPrice: walkin.service.base_price,
          discount: 0,
          taxRate: 18, // GST rate
          staffId: walkin.assigned_staff.id,
          staffName: walkin.assigned_staff.display_name,
          duration: walkin.duration_minutes,
        });
      });

      // Set the customer
      setCustomer(
        session.customer_id,
        session.customer_name,
        session.customer_phone
      );

      // Set the session ID for billing
      setSessionId(sessionId);

      // Navigate to POS
      router.push('/dashboard/pos');
      toast.success(`Ready to bill ${session.customer_name}`);
    } catch (error) {
      console.error('Error loading checkout:', error);
      toast.error('Failed to load customer for checkout');
    }
  };

  return (
    <div className="space-y-3">
      {/* Header with Date */}
      <div className="flex justify-end -mb-1">
        <p className="text-xs font-medium text-gray-500 bg-gray-50 px-2 py-0.5 rounded-full border">
          {getCurrentDate()}
        </p>
      </div>

      {/* Quick Stats - Ultra Compact Design */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-2">
        <Card className="p-2 shadow-sm flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <p className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider">Revenue</p>
            <DollarSign className="h-3 w-3 text-green-600" />
          </div>
          <div className="mt-1">
            <div className="text-lg font-bold text-gray-900 leading-none">
              {formatPrice(stats.today_revenue)}
            </div>
            <p className="text-[10px] text-gray-500 truncate mt-0.5">
              {stats.today_services} services done
            </p>
          </div>
        </Card>

        <Card className="p-2 shadow-sm flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <p className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider">Customers</p>
            <Users className="h-3 w-3 text-blue-600" />
          </div>
          <div className="mt-1">
            <div className="text-lg font-bold text-gray-900 leading-none">
              {stats.today_customers}
            </div>
            <p className="text-[10px] text-gray-500 truncate mt-0.5">Served today</p>
          </div>
        </Card>

        <Card className="p-2 shadow-sm flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <p className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider">Active</p>
            <Scissors className="h-3 w-3 text-purple-600" />
          </div>
          <div className="mt-1">
            <div className="text-lg font-bold text-gray-900 leading-none">
              {activeSessions.length}
            </div>
            <p className="text-[10px] text-gray-500 truncate mt-0.5">In salon</p>
          </div>
        </Card>

        <Card className="p-2 shadow-sm flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <p className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider">Pending</p>
            <Clock className="h-3 w-3 text-orange-600" />
          </div>
          <div className="mt-1">
            <div className="text-lg font-bold text-gray-900 leading-none">
              {stats.pending_bills}
            </div>
            <p className="text-[10px] text-gray-500 truncate mt-0.5">Not billed</p>
          </div>
        </Card>

        <Card className="p-2 shadow-sm flex flex-col justify-between hidden md:flex">
          <div className="flex items-center justify-between">
            <p className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider">Avg Time</p>
            <TrendingUp className="h-3 w-3 text-indigo-600" />
          </div>
          <div className="mt-1">
            <div className="text-lg font-bold text-gray-900 leading-none">{}</div>
            <p className="text-[10px] text-gray-500 truncate mt-0.5">Per service</p>
          </div>
        </Card>
      </div>

      {/* Active Customers Section */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main - Active Customers */}
        <div className="lg:col-span-2">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle>Active Customers</CardTitle>
                  <CardDescription>
                    Customers currently receiving services
                  </CardDescription>
                </div>
                <Badge variant="secondary" className="text-lg px-3 py-1">
                  {activeSessions.length} Active
                </Badge>
              </div>
            </CardHeader>
            <CardContent>
              {activeSessions.length === 0 ? (
                <div className="text-center py-12">
                  <Users className="h-12 w-12 text-gray-300 mx-auto mb-3" />
                  <p className="text-gray-500">No active customers right now</p>
                  <p className="text-sm text-gray-400 mt-1">
                    Customers in service will appear here
                  </p>
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {activeSessions.map((session) => (
                    <ActiveCustomerCard
                      key={session.session_id}
                      session={session}
                      onCheckout={handleCheckoutSession}
                      onRefresh={() => fetchDashboardData(true)}
                    />
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Sidebar - Quick Actions & Stats */}
        <div className="space-y-6">
          {/* Quick Actions */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Quick Actions</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              <a
                href="/dashboard/pos"
                className="flex items-center justify-between p-3 rounded-lg border hover:border-primary hover:bg-primary/5 transition-colors"
              >
                <div className="flex items-center gap-3">
                  <div className="bg-green-100 p-2 rounded-lg">
                    <DollarSign className="h-5 w-5 text-green-600" />
                  </div>
                  <span className="font-medium">New Bill</span>
                </div>
              </a>

              <a
                href="/dashboard/customers"
                className="flex items-center justify-between p-3 rounded-lg border hover:border-primary hover:bg-primary/5 transition-colors"
              >
                <div className="flex items-center gap-3">
                  <div className="bg-blue-100 p-2 rounded-lg">
                    <Users className="h-5 w-5 text-blue-600" />
                  </div>
                  <span className="font-medium">Add Customer</span>
                </div>
              </a>

              <a
                href="/dashboard/services"
                className="flex items-center justify-between p-3 rounded-lg border hover:border-primary hover:bg-primary/5 transition-colors"
              >
                <div className="flex items-center gap-3">
                  <div className="bg-purple-100 p-2 rounded-lg">
                    <Scissors className="h-5 w-5 text-purple-600" />
                  </div>
                  <span className="font-medium">Manage Services</span>
                </div>
              </a>
            </CardContent>
          </Card>

          {/* Today's Performance */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Today's Performance</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm text-gray-600">Revenue Target</span>
                  <span className="text-sm font-medium">
                    {formatPrice(stats.today_revenue)} / ₹20,000
                  </span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div
                    className="bg-green-600 h-2 rounded-full"
                    style={{
                      width: `${Math.min(100, (stats.today_revenue / 2000000) * 100)}%`,
                    }}
                  />
                </div>
              </div>

              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm text-gray-600">Services Goal</span>
                  <span className="text-sm font-medium">
                    {stats.today_services} / 25
                  </span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div
                    className="bg-blue-600 h-2 rounded-full"
                    style={{ width: `${Math.min(100, (stats.today_services / 25) * 100)}%` }}
                  />
                </div>
              </div>

              <div className="pt-2 border-t">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-gray-600">Avg. Bill Value</span>
                  <span className="font-semibold text-gray-900">
                    {formatPrice(Math.round(stats.today_revenue / (stats.today_services || 1)))}
                  </span>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
