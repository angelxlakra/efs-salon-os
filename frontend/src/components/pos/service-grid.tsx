'use client';

import { useState, useEffect, RefObject, useRef } from 'react';
import { Plus, Search, Loader2, User, Clock, ShoppingCart } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { EmptyState } from '@/components/ui/empty-state';
import { useCartStore } from '@/stores/cart-store';
import { useAuthStore } from '@/stores/auth-store';
import { apiClient } from '@/lib/api-client';
import { toast } from 'sonner';
import { ServiceStaffTemplate, StaffContributionCreate } from '@/types/multi-staff';
import { StaffAssignmentSelector } from '@/components/checkout/StaffAssignmentSelector';

interface ServiceCategory {
  id: string;
  name: string;
}

interface Service {
  id: string;
  name: string;
  category: ServiceCategory;
  base_price: number; // in paise
  duration_minutes: number;
  tax_rate: number;
  is_active: boolean;
}

interface Staff {
  id: string;
  display_name: string;
  is_active: boolean;
  user_id: string;
  specialization?: string[]; // Optional for now, as existing API may not return it
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

interface ServiceGridProps {
  searchInputRef?: RefObject<HTMLInputElement | null>;
  hideStaffSelection?: boolean;
  onServiceSelect?: (serviceId: string, serviceName: string, price: number, duration: number, staffId?: string | null) => void;
}

const CATEGORY_STYLES = [
  'bg-success-bg-soft text-success-fg',
  'bg-warning-bg-soft text-warning-fg',
  'bg-danger-bg-soft text-danger-fg',
  'bg-accent-bg-soft text-accent-default',
];

function getCategoryStyle(name: string): string {
  let hash = 0;
  for (let i = 0; i < name.length; i++) {
    hash = (hash * 31 + name.charCodeAt(i)) >>> 0;
  }
  return CATEGORY_STYLES[hash % CATEGORY_STYLES.length];
}

// Format price from paise to rupees
function formatServicePrice(paise: number) {
  return `₹${(paise / 100).toFixed(2)}`;
}

function formatWait(minutes: number) {
  if (minutes === 0) return 'No wait';
  if (minutes < 60) return `~${minutes} min`;
  const hours = Math.floor(minutes / 60);
  const mins = minutes % 60;
  return mins > 0 ? `~${hours}h ${mins}m` : `~${hours}h`;
}

export function ServiceGrid({ searchInputRef, hideStaffSelection = false, onServiceSelect }: ServiceGridProps) {
  const [services, setServices] = useState<Service[]>([]);
  const [filteredServices, setFilteredServices] = useState<Service[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string>('All');
  const [isLoading, setIsLoading] = useState(true);
  const { addItem, items } = useCartStore();
  const { user } = useAuthStore();

  // Staff selection state
  const [expandedServiceId, setExpandedServiceId] = useState<string | null>(null);
  const [staff, setStaff] = useState<StaffWithBusyness[]>([]);
  const [isLoadingStaff, setIsLoadingStaff] = useState(false);
  const [currentUserStaff, setCurrentUserStaff] = useState<StaffWithBusyness | null>(null);
  const expandedCardRef = useRef<HTMLDivElement | null>(null);

  // Multi-staff service state
  const [serviceTemplates, setServiceTemplates] = useState<Record<string, ServiceStaffTemplate[]>>({});
  const [isLoadingTemplates, setIsLoadingTemplates] = useState(false);

  // Fetch services and staff on mount
  useEffect(() => {
    fetchServices();
    fetchStaffWithBusyness();
  }, []);

  // Scroll the expanded card into view if it gets pushed off-screen by the expansion
  useEffect(() => {
    if (!expandedServiceId) return;
    const timer = setTimeout(() => {
      expandedCardRef.current?.scrollIntoView({
        behavior: 'smooth',
        block: 'nearest',
      });
    }, 50);
    return () => clearTimeout(timer);
  }, [expandedServiceId]);

  // Filter services based on search and category
  useEffect(() => {
    let filtered = services;

    if (selectedCategory !== 'All') {
      filtered = filtered.filter(s => s.category.name === selectedCategory);
    }

    if (searchQuery) {
      // Split search query into tokens (words)
      const tokens = searchQuery.toLowerCase().trim().split(/\s+/).filter(t => t.length > 0);

      // Filter: ALL tokens must match somewhere (service name OR category)
      filtered = filtered.filter(service => {
        const serviceName = service.name.toLowerCase();
        const categoryName = service.category.name.toLowerCase();
        const searchText = `${serviceName} ${categoryName}`;

        // Every token must appear in the combined text
        return tokens.every(token => searchText.includes(token));
      });
    }

    setFilteredServices(filtered);
  }, [services, searchQuery, selectedCategory]);

  const fetchServices = async () => {
    try {
      setIsLoading(true);
      const { data } = await apiClient.get('/catalog/services', { params: { sort_by: 'popularity' } });

      setServices(data.services || []);
      setFilteredServices(data.services || []);
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to load services');
      setServices([]);
    } finally {
      setIsLoading(false);
    }
  };

  const fetchStaffWithBusyness = async () => {
    try {
      setIsLoadingStaff(true);

      // If current user is staff, only fetch staff list (no busyness - they can't access it)
      if (user?.role === 'staff') {
        const staffResponse = await apiClient.get('/staff', {
          params: { is_active: true, service_providers_only: true }
        });
        const staffList = staffResponse.data.items || staffResponse.data || [];

        // Find their own staff profile
        const userStaff = staffList.find((s: Staff) => s.user_id === user.id);

        if (userStaff) {
          setCurrentUserStaff(userStaff);
        } else {
          toast.error('No staff profile found for your account. Please contact admin.');
        }

        // Don't set staff list for staff users - they don't need to see other staff
        return;
      }

      // For owner/receptionist: Fetch staff list, busyness, and today's attendance in parallel
      // Only show service providers (exclude receptionists)
      const [staffResponse, busynessResponse, attendanceResponse] = await Promise.all([
        apiClient.get('/staff', { params: { is_active: true, service_providers_only: true } }),
        apiClient.get('/staff/availability/busyness'),
        apiClient.get('/attendance', { params: { size: 100 } }),
      ]);

      const staffList = staffResponse.data.items || staffResponse.data || [];
      const busynessData = busynessResponse.data || [];
      const attendanceRecords: { staff_id: string; status: string }[] =
        attendanceResponse.data.items || [];

      // Build set of staff who are present or on a half day today
      const presentStaffIds = new Set<string>(
        attendanceRecords
          .filter((r) => r.status === 'present' || r.status === 'half_day')
          .map((r) => r.staff_id)
      );

      // Filter to present staff only; if attendance hasn't been marked yet show all
      const presentStaff = attendanceRecords.length > 0
        ? staffList.filter((s: Staff) => presentStaffIds.has(s.id))
        : staffList;

      // Merge busyness data with present staff list
      const staffWithBusyness: StaffWithBusyness[] = presentStaff.map((s: Staff) => ({
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
    } catch (error: any) {
      // Don't show error toast for staff users if they can't access busyness endpoint
      if (user?.role !== 'staff') {
        toast.error('Failed to load staff members');
      }
      setStaff([]);
    } finally {
      setIsLoadingStaff(false);
    }
  };

  const fetchServiceTemplates = async (serviceId: string) => {
    // Don't fetch if already cached
    if (serviceTemplates[serviceId]) {
      return;
    }

    try {
      setIsLoadingTemplates(true);
      const { data } = await apiClient.get(`/catalog/services/${serviceId}/staff-templates`);

      if (data.templates && data.templates.length > 0) {
        setServiceTemplates(prev => ({ ...prev, [serviceId]: data.templates }));
      }
    } catch (error: any) {
      // If 404, service doesn't have templates - that's okay
      if (error.response?.status !== 404) {
        // swallow other errors silently for templates
      }
    } finally {
      setIsLoadingTemplates(false);
    }
  };

  const handleServiceClick = (service: Service) => {
    // If user is staff, auto-assign service to themselves using staff_id from user object
    if (user?.role === 'staff') {
      if (!user.staff_id) {
        toast.error('No staff profile found. Please contact admin to create your staff profile.');
        return;
      }

      // Use user's full name as staff name
      const staffName = user.fullName || 'Staff';

      // Add directly to cart with staff assigned
      addItem({
        isProduct: false,
        serviceId: service.id,
        serviceName: service.name,
        quantity: 1,
        unitPrice: service.base_price,
        discount: 0,
        taxRate: service.tax_rate,
        staffId: user.staff_id,
        staffName: staffName,
        duration: service.duration_minutes,
      });

      toast.success(`${service.name} added to cart (assigned to you)`);
      return;
    }

    // If hiding staff selection, call the callback immediately
    if (hideStaffSelection && onServiceSelect) {
      onServiceSelect(
        service.id,
        service.name,
        service.base_price,
        service.duration_minutes,
        null
      );
      return;
    }

    // Toggle expansion: if already expanded, collapse it; otherwise expand it
    const willExpand = expandedServiceId !== service.id;
    setExpandedServiceId(willExpand ? service.id : null);

    // Fetch templates when expanding
    if (willExpand) {
      fetchServiceTemplates(service.id);
    }
  };

  const handleStaffClick = (service: Service, staffId: string, staffName: string) => {
    // If custom callback provided, use it
    if (onServiceSelect) {
      onServiceSelect(
        service.id,
        service.name,
        service.base_price,
        service.duration_minutes,
        staffId
      );
      setExpandedServiceId(null);
      return;
    }

    // Default behavior: add to cart
    addItem({
      isProduct: false,
      serviceId: service.id,
      serviceName: service.name,
      quantity: 1,
      unitPrice: service.base_price,
      discount: 0,
      taxRate: service.tax_rate,
      staffId: staffId,
      staffName: staffName,
      duration: service.duration_minutes,
    });

    toast.success(`${service.name} added to cart (${staffName})`);

    // Collapse the service card
    setExpandedServiceId(null);
  };

  const handleMultiStaffAssignment = (service: Service, contributions: StaffContributionCreate[]) => {
    // Add to cart with multi-staff contributions
    const newItem = {
      isProduct: false,
      serviceId: service.id,
      serviceName: service.name,
      quantity: 1,
      unitPrice: service.base_price,
      discount: 0,
      taxRate: service.tax_rate,
      duration: service.duration_minutes,
      isMultiStaff: true,
      staffContributions: contributions,
    };

    addItem(newItem);

    const staffNames = contributions.map(c => {
      const staffMember = staff.find(s => s.id === c.staff_id);
      return staffMember?.display_name || 'Unknown';
    }).join(', ');

    toast.success(`${service.name} added to cart (${staffNames})`);

    // Collapse the service card
    setExpandedServiceId(null);
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'available':
        return <Badge className="bg-success-bg-soft text-success-fg text-xs">Available</Badge>;
      case 'busy':
        return <Badge className="bg-warning-bg-soft text-warning-fg text-xs">Busy</Badge>;
      case 'very_busy':
        return <Badge className="bg-danger-bg-soft text-danger-fg text-xs">Very Busy</Badge>;
      default:
        return null;
    }
  };

  const getStaffBusynessText = (staffMember: StaffWithBusyness) => {
    const busyness = staffMember.busyness;
    if (!busyness) {
      return `${staffMember.display_name} is available`;
    }

    const totalServices = busyness.active_services + busyness.queued_services;

    if (totalServices === 0) {
      return `${staffMember.display_name} is available`;
    }

    const serviceText = totalServices === 1 ? 'service' : 'services';
    const waitText = busyness.total_wait_minutes > 0
      ? ` and might take ${Math.round(busyness.total_wait_minutes)} minutes more`
      : '';

    return `${staffMember.display_name} has ${totalServices} pending ${serviceText}${waitText}`;
  };

  // Get count of how many times a service is in the cart
  const getServiceCartCount = (serviceId: string) => {
    return items.filter(item => !item.isProduct && item.serviceId === serviceId).length;
  };

  // Get unique categories
  const categories = ['All', ...Array.from(new Set(services.map(s => s.category.name)))];

  if (isLoading) {
    return (
      <div className="grid grid-cols-2 lg:grid-cols-3 gap-4" aria-busy="true">
        {Array.from({ length: 6 }).map((_, i) => (
          <Skeleton key={i} shape="kpi" />
        ))}
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col">
      {/* Search and Filter Bar */}
      <div className="mb-4 space-y-3">
        {/* Search */}
        <div className="relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-text-disabled" />
          <Input
            ref={searchInputRef}
            type="text"
            placeholder="Search services..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-10"
          />
        </div>

        {/* Category Filter */}
        <div className="flex gap-2 overflow-x-auto pb-2">
          {categories.map((category) => (
            <Button
              key={category}
              variant={selectedCategory === category ? 'default' : 'outline'}
              size="sm"
              onClick={() => setSelectedCategory(category)}
              className="whitespace-nowrap"
            >
              {category}
            </Button>
          ))}
        </div>
      </div>

      {/* Service Grid */}
      <div className="flex-1 overflow-auto">
        {filteredServices.length === 0 ? (
          <div className="col-span-full">
            <EmptyState
              title={searchQuery ? 'No matching services' : 'No services yet'}
              body={searchQuery
                ? 'Try a different search term or clear the filter to see all services.'
                : 'Add services in the Services catalogue to see them here.'}
              headingLevel={4}
              primaryAction={searchQuery
                ? <Button variant="outline" onClick={() => setSearchQuery('')}>Clear search</Button>
                : undefined
              }
            />
          </div>
        ) : (
          <div className="grid grid-cols-2 lg:grid-cols-3 gap-4 items-start">
            {filteredServices.map((service) => {
              const isExpanded = expandedServiceId === service.id;
              const cartCount = getServiceCartCount(service.id);
              const isInCart = cartCount > 0;

              return (
                <div
                  key={service.id}
                  ref={isExpanded ? expandedCardRef : null}
                  className={`relative bg-surface-card rounded-xl border-2 transition-all ${
                    isExpanded
                      ? 'border-accent-default shadow-lg col-span-2 lg:col-span-3'
                      : isInCart
                      ? 'border-success-border shadow-md'
                      : 'border-border-default'
                  }`}
                >
                  {/* Service Card */}
                  <button
                    onClick={() => handleServiceClick(service)}
                    className={`group w-full p-4 text-left ${
                      isExpanded ? '' : 'hover:border-black hover:shadow-lg'
                    }`}
                  >
                    {/* Top Row: Cart Badge (left) + Category Badge (right) */}
                    <div className="flex items-start justify-between mb-2 min-h-[1.5rem]">
                      <div>
                        {isInCart && (
                          <Badge className="bg-success-bg-soft text-success-fg border border-success-border text-xs flex items-center gap-1">
                            <ShoppingCart className="h-3 w-3" />
                            {cartCount}
                          </Badge>
                        )}
                      </div>
                      <span
                        className={`text-[10px] font-semibold leading-tight px-1.5 py-0.5 rounded whitespace-normal break-words ml-2 ${getCategoryStyle(service.category.name)}`}
                      >
                        {service.category.name}
                      </span>
                    </div>

                    {/* Service Name */}
                    <h3 className="font-semibold text-text-primary mb-2">
                      {service.name}
                    </h3>

                    {/* Duration */}
                    <p className="text-xs text-text-muted mb-3">
                      {service.duration_minutes} min
                    </p>

                    {/* Price and Add Button */}
                    <div className="flex items-center justify-between">
                      <span className="text-lg font-bold text-text-primary">
                        {formatServicePrice(service.base_price)}
                      </span>
                      <div className={`h-8 w-8 rounded-full bg-accent flex items-center justify-center transition-opacity ${
                        isExpanded ? 'opacity-100' : 'opacity-0 group-hover:opacity-100'
                      }`}>
                        <Plus className="h-4 w-4 text-accent-fg" />
                      </div>
                    </div>
                  </button>

                  {/* Staff Selection - Inline */}
                  {isExpanded && !hideStaffSelection && (
                    <div className="px-4 pb-4 border-t border-border-subtle pt-3">
                      {/* Check if this service has multi-staff templates */}
                      {serviceTemplates[service.id] && serviceTemplates[service.id].length > 0 ? (
                        // Multi-staff service with predefined roles
                        <div>
                          <p className="text-sm font-medium text-text-secondary mb-3">
                            <User className="h-4 w-4 inline mr-1" />
                            Assign Staff to Roles
                          </p>
                          {isLoadingTemplates ? (
                            <div className="flex items-center justify-center py-4">
                              <Loader2 className="h-5 w-5 animate-spin text-text-disabled" />
                            </div>
                          ) : (
                            <StaffAssignmentSelector
                              serviceId={service.id}
                              serviceName={service.name}
                              servicePrice={service.base_price}
                              templates={serviceTemplates[service.id]}
                              availableStaff={staff}
                              splitType="hybrid"
                              onAssignmentsChange={(contributions) => {
                                handleMultiStaffAssignment(service, contributions);
                              }}
                            />
                          )}
                        </div>
                      ) : (
                        // Regular single-staff service
                        <div>
                          <p className="text-sm font-medium text-text-secondary mb-3">
                            <User className="h-4 w-4 inline mr-1" />
                            Select Staff Member
                          </p>

                          {isLoadingStaff || isLoadingTemplates ? (
                            <div className="flex items-center justify-center py-4">
                              <Loader2 className="h-5 w-5 animate-spin text-text-disabled" />
                            </div>
                          ) : staff.length === 0 ? (
                            <div className="text-sm text-text-muted py-2">
                              No active staff available
                            </div>
                          ) : (
                            <div className="grid grid-cols-2 lg:grid-cols-4 gap-1.5">
                              {staff.map((staffMember) => (
                                <button
                                  key={staffMember.id}
                                  onClick={() =>
                                    handleStaffClick(
                                      service,
                                      staffMember.id,
                                      staffMember.display_name
                                    )
                                  }
                                  title={getStaffBusynessText(staffMember)}
                                  className="flex items-center justify-between gap-2 w-full px-2.5 py-2 bg-surface-page hover:bg-accent hover:text-accent-fg border border-border-default hover:border-accent-default rounded-lg transition-all text-left"
                                >
                                  <div className="flex items-center gap-1.5 min-w-0">
                                    <User className="h-3 w-3 flex-shrink-0" />
                                    <span className="truncate font-medium text-xs">
                                      {staffMember.display_name}
                                    </span>
                                  </div>
                                  <div className="flex items-center gap-1.5 flex-shrink-0 text-xs">
                                    {staffMember.busyness && getStatusBadge(staffMember.busyness.status)}
                                    {staffMember.busyness && staffMember.busyness.total_wait_minutes > 0 && (
                                      <span className="text-text-muted flex items-center gap-0.5">
                                        <Clock className="h-3 w-3" />
                                        {formatWait(staffMember.busyness.total_wait_minutes)}
                                      </span>
                                    )}
                                  </div>
                                </button>
                              ))}
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
