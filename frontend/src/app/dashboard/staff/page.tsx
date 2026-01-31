'use client';

import { useState, useEffect } from 'react';
import { Loader2, Briefcase, Clock, CheckCircle } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { ServiceCard } from '@/components/staff/service-card';
import { apiClient } from '@/lib/api-client';
import { toast } from 'sonner';
import { useAuthStore } from '@/stores/auth-store';

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

export default function StaffDashboard() {
  const { user } = useAuthStore();
  const [services, setServices] = useState<WalkIn[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);

  useEffect(() => {
    fetchMyServices();

    // Refresh every 30 seconds
    const interval = setInterval(() => {
      fetchMyServices(true);
    }, 30000);

    return () => clearInterval(interval);
  }, []);

  const fetchMyServices = async (silent = false) => {
    try {
      if (!silent) {
        setIsLoading(true);
      } else {
        setIsRefreshing(true);
      }

      const { data } = await apiClient.get('/appointments/walkins/my-services');

      // Sort services by priority: in_progress > checked_in > completed
      const sortedServices = (data.services || []).sort((a: WalkIn, b: WalkIn) => {
        const statusPriority: { [key: string]: number } = {
          in_progress: 1,
          checked_in: 2,
          completed: 3,
        };

        const priorityA = statusPriority[a.status] || 999;
        const priorityB = statusPriority[b.status] || 999;

        if (priorityA !== priorityB) {
          return priorityA - priorityB;
        }

        // If same status, sort by checked_in_at (earliest first)
        if (a.checked_in_at && b.checked_in_at) {
          return new Date(a.checked_in_at).getTime() - new Date(b.checked_in_at).getTime();
        }

        return 0;
      });

      setServices(sortedServices);
    } catch (error: any) {
      console.error('Error fetching services:', error);
      if (!silent) {
        toast.error(
          error.response?.data?.detail || 'Failed to load services'
        );
      }
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  };

  const handleStartService = async (id: string) => {
    try {
      await apiClient.post(`/appointments/walkins/${id}/start`);
      toast.success('Service started');
      fetchMyServices(true);
    } catch (error: any) {
      console.error('Error starting service:', error);
      toast.error(error.response?.data?.detail || 'Failed to start service');
    }
  };

  const handleCompleteService = async (id: string) => {
    try {
      await apiClient.post(`/appointments/walkins/${id}/complete`);
      toast.success('Service completed');
      fetchMyServices(true);
    } catch (error: any) {
      console.error('Error completing service:', error);
      toast.error(error.response?.data?.detail || 'Failed to complete service');
    }
  };

  const handleAddNote = async (id: string, note: string) => {
    try {
      await apiClient.patch(`/appointments/walkins/${id}/notes`, {
        service_notes: note,
      });
      toast.success('Notes saved');
      fetchMyServices(true);
    } catch (error: any) {
      console.error('Error saving notes:', error);
      toast.error(error.response?.data?.detail || 'Failed to save notes');
    }
  };

  const handleCancelService = async (id: string) => {
    const reason = prompt('Please enter the reason for cancelling this service:');

    if (!confirm('Are you sure you want to cancel this service? This cannot be undone.')) {
      return;
    }

    try {
      await apiClient.post(`/appointments/walkins/${id}/cancel`, {
        reason: reason?.trim() || null,
      });
      toast.success('Service cancelled');
      fetchMyServices(true);
    } catch (error: any) {
      console.error('Error cancelling service:', error);
      toast.error(error.response?.data?.detail || 'Failed to cancel service');
    }
  };

  // Calculate stats (excluding cancelled services)
  const upcomingCount = services.filter((s) => s.status === 'checked_in').length;
  const inProgressCount = services.filter((s) => s.status === 'in_progress').length;
  const completedCount = services.filter((s) => s.status === 'completed').length;
  const activeServices = services.filter((s) => s.status !== 'cancelled');

  if (isLoading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="h-8 w-8 animate-spin text-gray-400 mx-auto mb-2" />
          <p className="text-sm text-gray-500">Loading your services...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Header - Mobile Optimized */}
      <div>
        <h1 className="text-2xl md:text-3xl font-bold">My Services</h1>
        <p className="text-sm text-muted-foreground mt-1">
          {new Date().toLocaleDateString('en-IN', {
            weekday: 'short',
            month: 'short',
            day: 'numeric',
          })}
          {isRefreshing && (
            <span className="ml-2 text-xs text-blue-600">
              • Refreshing...
            </span>
          )}
        </p>
      </div>

      {/* Stats Cards - Mobile First */}
      <div className="grid grid-cols-3 gap-2 sm:gap-4">
        <Card>
          <CardContent className="p-3 sm:p-4">
            <div className="flex flex-col items-center text-center">
              <div className="h-8 w-8 sm:h-10 sm:w-10 bg-blue-100 rounded-full flex items-center justify-center mb-2">
                <Briefcase className="h-4 w-4 sm:h-5 sm:w-5 text-blue-600" />
              </div>
              <p className="text-2xl sm:text-3xl font-bold">{upcomingCount}</p>
              <p className="text-xs sm:text-sm font-medium text-muted-foreground mt-1">
                Upcoming
              </p>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-3 sm:p-4">
            <div className="flex flex-col items-center text-center">
              <div className="h-8 w-8 sm:h-10 sm:w-10 bg-amber-100 rounded-full flex items-center justify-center mb-2">
                <Clock className="h-4 w-4 sm:h-5 sm:w-5 text-amber-600" />
              </div>
              <p className="text-2xl sm:text-3xl font-bold">{inProgressCount}</p>
              <p className="text-xs sm:text-sm font-medium text-muted-foreground mt-1">
                In Progress
              </p>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-3 sm:p-4">
            <div className="flex flex-col items-center text-center">
              <div className="h-8 w-8 sm:h-10 sm:w-10 bg-green-100 rounded-full flex items-center justify-center mb-2">
                <CheckCircle className="h-4 w-4 sm:h-5 sm:w-5 text-green-600" />
              </div>
              <p className="text-2xl sm:text-3xl font-bold">{completedCount}</p>
              <p className="text-xs sm:text-sm font-medium text-muted-foreground mt-1">
                Completed
              </p>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Service Cards - Mobile First */}
      {services.length === 0 ? (
        <Card>
          <CardContent className="p-8 sm:p-12 text-center">
            <Briefcase className="h-10 w-10 sm:h-12 sm:w-12 text-gray-300 mx-auto mb-3 sm:mb-4" />
            <h3 className="text-base sm:text-lg font-semibold mb-2">No Services Today</h3>
            <p className="text-sm text-muted-foreground">
              You don't have any services assigned yet today.
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3 sm:grid sm:grid-cols-2 sm:gap-3 sm:space-y-0 lg:grid-cols-3">
          {services.map((service) => (
            <ServiceCard
              key={service.id}
              service={service}
              onStart={handleStartService}
              onComplete={handleCompleteService}
              onAddNote={handleAddNote}
              onCancel={handleCancelService}
            />
          ))}
        </div>
      )}
    </div>
  );
}
