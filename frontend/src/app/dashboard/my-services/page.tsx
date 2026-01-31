'use client';

import { useState, useEffect } from 'react';
import { Clock, User, CheckCircle, PlayCircle, PauseCircle, Plus } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from '@/components/ui/sheet';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Textarea } from '@/components/ui/textarea';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { ScrollArea } from '@/components/ui/scroll-area';
import { apiClient } from '@/lib/api-client';
import { toast } from 'sonner';
import { useAuthStore } from '@/stores/auth-store';
import { ServiceGrid } from '@/components/pos/service-grid';

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

interface WalkInService {
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

interface MyServicesResponse {
  services: WalkInService[];
  date: string;
  total: number;
}

export default function MyServicesPage() {
  const { user } = useAuthStore();
  const [services, setServices] = useState<WalkInService[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [activeService, setActiveService] = useState<WalkInService | null>(null);
  const [isAddingService, setIsAddingService] = useState(false);
  const [customerName, setCustomerName] = useState('');
  const [customerPhone, setCustomerPhone] = useState('');
  const [selectedServiceId, setSelectedServiceId] = useState<string | null>(null);
  const [notes, setNotes] = useState('');

  useEffect(() => {
    fetchMyServices();
    // Refresh every 30 seconds
    const interval = setInterval(() => fetchMyServices(true), 30000);
    return () => clearInterval(interval);
  }, []);

  const fetchMyServices = async (silent = false) => {
    try {
      if (!silent) setIsLoading(true);

      const { data } = await apiClient.get<MyServicesResponse>('/appointments/walkins/my-services');
      setServices(data.services || []);
    } catch (error: any) {
      console.error('Failed to fetch services:', error);
      if (!silent) {
        toast.error(error.response?.data?.detail || 'Failed to load your services');
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleStartService = async (serviceId: string) => {
    try {
      await apiClient.post(`/appointments/walkins/${serviceId}/start`);
      toast.success('Service started!');
      fetchMyServices(true);
    } catch (error: any) {
      console.error('Failed to start service:', error);
      toast.error(error.response?.data?.detail || 'Failed to start service');
    }
  };

  const handleCompleteService = async (serviceId: string) => {
    try {
      await apiClient.post(`/appointments/walkins/${serviceId}/complete`);
      toast.success('Service completed!');
      fetchMyServices(true);
      setActiveService(null);
    } catch (error: any) {
      console.error('Failed to complete service:', error);
      toast.error(error.response?.data?.detail || 'Failed to complete service');
    }
  };

  const handleAddNotes = async () => {
    if (!activeService) return;

    try {
      await apiClient.patch(`/appointments/walkins/${activeService.id}/notes`, {
        service_notes: notes
      });
      toast.success('Notes added!');
      fetchMyServices(true);
      setActiveService(null);
      setNotes('');
    } catch (error: any) {
      console.error('Failed to add notes:', error);
      toast.error(error.response?.data?.detail || 'Failed to add notes');
    }
  };

  const handleAddNewService = async (serviceId: string, serviceName: string, price: number, duration: number) => {
    if (!customerName.trim()) {
      toast.error('Please enter customer name');
      return;
    }

    try {
      // Create walk-in - staff can only create for themselves
      await apiClient.post('/appointments/walkins', {
        customer_name: customerName.trim(),
        customer_phone: customerPhone.trim() || '0000000000',
        service_id: serviceId,
        duration_minutes: duration,
        // assigned_staff_id will be auto-set to current staff on backend
      });

      toast.success(`Added ${serviceName} for ${customerName}`);
      setCustomerName('');
      setCustomerPhone('');
      setSelectedServiceId(null);
      setIsAddingService(false);
      fetchMyServices(true);
    } catch (error: any) {
      console.error('Failed to add service:', error);
      toast.error(error.response?.data?.detail || 'Failed to add service');
    }
  };

  const formatTime = (dateString: string | null) => {
    if (!dateString) return '-';
    return new Date(dateString).toLocaleTimeString('en-IN', {
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const formatPrice = (paise: number) => {
    return `₹${(paise / 100).toLocaleString('en-IN')}`;
  };

  const getStatusBadge = (status: string) => {
    const statusMap: Record<string, { label: string; variant: 'default' | 'secondary' | 'destructive' | 'outline' }> = {
      CHECKED_IN: { label: 'Checked In', variant: 'secondary' },
      IN_PROGRESS: { label: 'In Progress', variant: 'default' },
      COMPLETED: { label: 'Completed', variant: 'outline' },
    };
    const config = statusMap[status] || { label: status, variant: 'secondary' };
    return <Badge variant={config.variant}>{config.label}</Badge>;
  };

  const getTimeSinceCheckIn = (checkedInAt: string | null) => {
    if (!checkedInAt) return null;
    const minutes = Math.floor((Date.now() - new Date(checkedInAt).getTime()) / 60000);
    if (minutes < 60) return `${minutes}m ago`;
    const hours = Math.floor(minutes / 60);
    return `${hours}h ${minutes % 60}m ago`;
  };

  const pendingServices = services.filter(s => s.status === 'CHECKED_IN');
  const inProgressServices = services.filter(s => s.status === 'IN_PROGRESS');
  const completedServices = services.filter(s => s.status === 'COMPLETED');

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-[calc(100vh-10rem)]">
        <div className="text-center">
          <div className="h-12 w-12 rounded-full border-4 border-gray-200 border-t-black animate-spin mb-3 mx-auto" />
          <p className="text-gray-500">Loading your services...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">My Services</h1>
          <p className="text-sm text-gray-500 mt-1">
            Manage your assigned services for today
          </p>
        </div>

        {/* Add Service Button */}
        <Sheet open={isAddingService} onOpenChange={setIsAddingService}>
          <SheetTrigger asChild>
            <Button size="lg">
              <Plus className="h-5 w-5 mr-2" />
              Add Service
            </Button>
          </SheetTrigger>
          <SheetContent side="right" className="w-full sm:max-w-2xl p-0">
            <div className="h-full flex flex-col">
              <SheetHeader className="p-6 border-b">
                <SheetTitle>Add New Service</SheetTitle>
              </SheetHeader>

              <div className="flex-1 overflow-hidden flex flex-col">
                {/* Customer Info */}
                <div className="p-6 border-b space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="customer-name">Customer Name *</Label>
                    <Input
                      id="customer-name"
                      placeholder="Enter customer name"
                      value={customerName}
                      onChange={(e) => setCustomerName(e.target.value)}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="customer-phone">Phone Number (optional)</Label>
                    <Input
                      id="customer-phone"
                      placeholder="Enter phone number"
                      value={customerPhone}
                      onChange={(e) => setCustomerPhone(e.target.value)}
                    />
                  </div>
                </div>

                {/* Service Selection */}
                <div className="flex-1 p-6 overflow-hidden">
                  <h3 className="text-sm font-semibold text-gray-700 mb-4">Select Service</h3>
                  <ScrollArea className="h-full">
                    <ServiceGrid
                      onServiceSelect={(serviceId, serviceName, price, duration, staffId) => {
                        handleAddNewService(serviceId, serviceName, price, duration);
                      }}
                      hideStaffSelection={true}
                    />
                  </ScrollArea>
                </div>
              </div>
            </div>
          </SheetContent>
        </Sheet>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-3 gap-4">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">Pending</p>
                <p className="text-2xl font-bold mt-1">{pendingServices.length}</p>
              </div>
              <Clock className="h-8 w-8 text-orange-500" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">In Progress</p>
                <p className="text-2xl font-bold mt-1">{inProgressServices.length}</p>
              </div>
              <PlayCircle className="h-8 w-8 text-blue-500" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">Completed</p>
                <p className="text-2xl font-bold mt-1">{completedServices.length}</p>
              </div>
              <CheckCircle className="h-8 w-8 text-green-500" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Services List */}
      <Tabs defaultValue="pending" className="space-y-4">
        <TabsList>
          <TabsTrigger value="pending">
            Pending ({pendingServices.length})
          </TabsTrigger>
          <TabsTrigger value="in-progress">
            In Progress ({inProgressServices.length})
          </TabsTrigger>
          <TabsTrigger value="completed">
            Completed ({completedServices.length})
          </TabsTrigger>
        </TabsList>

        <TabsContent value="pending" className="space-y-4">
          {pendingServices.length === 0 ? (
            <Card>
              <CardContent className="py-12 text-center">
                <Clock className="h-12 w-12 text-gray-300 mx-auto mb-3" />
                <p className="text-gray-500">No pending services</p>
              </CardContent>
            </Card>
          ) : (
            pendingServices.map((service) => (
              <Card key={service.id}>
                <CardContent className="p-6">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-2">
                        <h3 className="text-lg font-semibold text-gray-900">
                          {service.customer_name}
                        </h3>
                        {getStatusBadge(service.status)}
                        <Badge variant="outline">{service.ticket_number}</Badge>
                      </div>

                      <div className="space-y-1 text-sm text-gray-600">
                        <p className="font-medium text-gray-900">{service.service.name}</p>
                        <p>{formatPrice(service.service.base_price)} • {service.service.duration_minutes} min</p>
                        <p className="text-xs text-gray-500">
                          Checked in {getTimeSinceCheckIn(service.checked_in_at)}
                        </p>
                      </div>
                    </div>

                    <div className="flex gap-2">
                      <Button
                        onClick={() => handleStartService(service.id)}
                        size="lg"
                      >
                        <PlayCircle className="h-5 w-5 mr-2" />
                        Start
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))
          )}
        </TabsContent>

        <TabsContent value="in-progress" className="space-y-4">
          {inProgressServices.length === 0 ? (
            <Card>
              <CardContent className="py-12 text-center">
                <PlayCircle className="h-12 w-12 text-gray-300 mx-auto mb-3" />
                <p className="text-gray-500">No services in progress</p>
              </CardContent>
            </Card>
          ) : (
            inProgressServices.map((service) => (
              <Card key={service.id}>
                <CardContent className="p-6">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-2">
                        <h3 className="text-lg font-semibold text-gray-900">
                          {service.customer_name}
                        </h3>
                        {getStatusBadge(service.status)}
                        <Badge variant="outline">{service.ticket_number}</Badge>
                      </div>

                      <div className="space-y-1 text-sm text-gray-600">
                        <p className="font-medium text-gray-900">{service.service.name}</p>
                        <p>{formatPrice(service.service.base_price)} • {service.service.duration_minutes} min</p>
                        <p className="text-xs text-gray-500">
                          Started at {formatTime(service.started_at)}
                        </p>
                      </div>
                    </div>

                    <div className="flex gap-2">
                      <Button
                        variant="outline"
                        onClick={() => {
                          setActiveService(service);
                          setNotes(service.service_notes || '');
                        }}
                      >
                        Add Notes
                      </Button>
                      <Button
                        onClick={() => handleCompleteService(service.id)}
                        variant="default"
                        size="lg"
                      >
                        <CheckCircle className="h-5 w-5 mr-2" />
                        Complete
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))
          )}
        </TabsContent>

        <TabsContent value="completed" className="space-y-4">
          {completedServices.length === 0 ? (
            <Card>
              <CardContent className="py-12 text-center">
                <CheckCircle className="h-12 w-12 text-gray-300 mx-auto mb-3" />
                <p className="text-gray-500">No completed services today</p>
              </CardContent>
            </Card>
          ) : (
            completedServices.map((service) => (
              <Card key={service.id} className="bg-green-50/50">
                <CardContent className="p-6">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-2">
                        <h3 className="text-lg font-semibold text-gray-900">
                          {service.customer_name}
                        </h3>
                        {getStatusBadge(service.status)}
                        <Badge variant="outline">{service.ticket_number}</Badge>
                      </div>

                      <div className="space-y-1 text-sm text-gray-600">
                        <p className="font-medium text-gray-900">{service.service.name}</p>
                        <p>{formatPrice(service.service.base_price)} • {service.service.duration_minutes} min</p>
                        <p className="text-xs text-gray-500">
                          Completed at {formatTime(service.completed_at)}
                        </p>
                        {service.service_notes && (
                          <div className="mt-2 p-2 bg-white rounded border">
                            <p className="text-xs font-medium text-gray-700">Notes:</p>
                            <p className="text-sm text-gray-600">{service.service_notes}</p>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))
          )}
        </TabsContent>
      </Tabs>

      {/* Notes Dialog */}
      {activeService && (
        <Sheet open={!!activeService} onOpenChange={() => setActiveService(null)}>
          <SheetContent side="right" className="w-full sm:max-w-md">
            <SheetHeader className="mb-4">
              <SheetTitle>Add Service Notes</SheetTitle>
            </SheetHeader>

            <div className="space-y-4">
              <div>
                <p className="text-sm text-gray-600 mb-1">Customer</p>
                <p className="font-semibold">{activeService.customer_name}</p>
              </div>

              <div>
                <p className="text-sm text-gray-600 mb-1">Service</p>
                <p className="font-semibold">{activeService.service.name}</p>
              </div>

              <div className="space-y-2">
                <Label htmlFor="notes">Service Notes</Label>
                <Textarea
                  id="notes"
                  placeholder="Add notes about the service..."
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  rows={6}
                />
              </div>

              <div className="flex gap-2">
                <Button
                  variant="outline"
                  onClick={() => setActiveService(null)}
                  className="flex-1"
                >
                  Cancel
                </Button>
                <Button
                  onClick={handleAddNotes}
                  className="flex-1"
                >
                  Save Notes
                </Button>
              </div>
            </div>
          </SheetContent>
        </Sheet>
      )}
    </div>
  );
}
