'use client';

import { useState, useEffect } from 'react';
import { XCircle, Loader2, User, Clock } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { apiClient } from '@/lib/api-client';
import { toast } from 'sonner';

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
  service: Service;
  assigned_staff: Staff;
  status: string;
  checked_in_at: string | null;
  started_at: string | null;
  completed_at: string | null;
}

interface ActiveServicesModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  customerId?: string | null;
  customerPhone?: string | null;
  customerName?: string | null;
  onServicesCancelled?: () => void;
}

export function ActiveServicesModal({
  open,
  onOpenChange,
  customerId,
  customerPhone,
  customerName,
  onServicesCancelled,
}: ActiveServicesModalProps) {
  const [services, setServices] = useState<WalkIn[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    if (open && (customerId || customerPhone)) {
      fetchActiveServices();
    }
  }, [open, customerId, customerPhone]);

  const fetchActiveServices = async () => {
    try {
      setIsLoading(true);
      const { data } = await apiClient.get('/appointments/walkins/active');

      // Find services for this customer
      const customerSession = data.sessions.find((session: any) => {
        if (customerId && session.customer_id === customerId) return true;
        if (customerPhone && session.customer_phone === customerPhone) return true;
        return false;
      });

      if (customerSession) {
        // Filter out completed and cancelled services
        const activeServices = customerSession.walkins.filter(
          (w: WalkIn) => w.status !== 'completed' && w.status !== 'cancelled'
        );
        setServices(activeServices);
      } else {
        setServices([]);
      }
    } catch (error: any) {
      console.error('Error fetching active services:', error);
      toast.error('Failed to load active services');
    } finally {
      setIsLoading(false);
    }
  };

  const handleCancelService = async (serviceId: string) => {
    const reason = prompt('Please enter the reason for cancelling this service:');

    if (!confirm('Are you sure you want to cancel this service?')) {
      return;
    }

    try {
      await apiClient.post(`/appointments/walkins/${serviceId}/cancel`, {
        reason: reason?.trim() || null,
      });
      toast.success('Service cancelled');

      // Refresh the list
      await fetchActiveServices();

      // Notify parent
      if (onServicesCancelled) {
        onServicesCancelled();
      }
    } catch (error: any) {
      console.error('Error cancelling service:', error);
      toast.error(error.response?.data?.detail || 'Failed to cancel service');
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'checked_in':
        return <Badge variant="secondary">Checked In</Badge>;
      case 'in_progress':
        return <Badge className="bg-amber-500">In Progress</Badge>;
      default:
        return <Badge variant="outline">{status}</Badge>;
    }
  };

  const formatTime = (timestamp: string | null) => {
    if (!timestamp) return 'Not set';
    return new Date(timestamp).toLocaleTimeString('en-IN', {
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[600px] max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Active Services - {customerName}</DialogTitle>
        </DialogHeader>

        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-8 w-8 animate-spin text-gray-400" />
          </div>
        ) : services.length === 0 ? (
          <div className="text-center py-12 text-gray-500">
            <p>No active services found</p>
          </div>
        ) : (
          <div className="space-y-3">
            {services.map((service) => (
              <div
                key={service.id}
                className={`border rounded-lg p-4 ${
                  service.status === 'in_progress' ? 'bg-amber-50 border-amber-200' : 'bg-blue-50 border-blue-200'
                }`}
              >
                <div className="flex items-start justify-between mb-3">
                  <div className="flex-1">
                    <h4 className="font-semibold text-base">{service.service.name}</h4>
                    <p className="text-xs text-muted-foreground mt-1">
                      {service.ticket_number}
                    </p>
                  </div>
                  {getStatusBadge(service.status)}
                </div>

                <div className="space-y-2 text-sm">
                  <div className="flex items-center gap-2 text-muted-foreground">
                    <User className="h-4 w-4" />
                    <span>{service.assigned_staff.display_name}</span>
                  </div>
                  <div className="flex items-center gap-2 text-muted-foreground">
                    <Clock className="h-4 w-4" />
                    <span>
                      {service.service.duration_minutes} min • Checked in: {formatTime(service.checked_in_at)}
                    </span>
                  </div>
                  {service.started_at && (
                    <div className="text-xs text-muted-foreground">
                      Started: {formatTime(service.started_at)}
                    </div>
                  )}
                </div>

                <div className="mt-3 pt-3 border-t">
                  <Button
                    onClick={() => handleCancelService(service.id)}
                    variant="outline"
                    size="sm"
                    className="w-full text-destructive hover:bg-destructive/10"
                  >
                    <XCircle className="h-4 w-4 mr-2" />
                    Cancel Service
                  </Button>
                </div>
              </div>
            ))}
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
