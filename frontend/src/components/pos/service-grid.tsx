'use client';

import { useState, useEffect, RefObject, useRef } from 'react';
import { Plus, Search, Loader2, User, Check, Clock, ShoppingCart } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { useCartStore } from '@/stores/cart-store';
import { useAuthStore } from '@/stores/auth-store';
import { apiClient } from '@/lib/api-client';
import { toast } from 'sonner';

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

  // Fetch services and staff on mount
  useEffect(() => {
    fetchServices();
    fetchStaffWithBusyness();
  }, []);

  // Scroll to center when service is expanded
  useEffect(() => {
    if (expandedServiceId && expandedCardRef.current) {
      expandedCardRef.current.scrollIntoView({
        behavior: 'smooth',
        block: 'center',
      });
    }
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
      const { data } = await apiClient.get('/catalog/services');
      console.log({data: data.services});

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
        console.log('Staff user detected:', user);
        const staffResponse = await apiClient.get('/staff', {
          params: { is_active: true, service_providers_only: true }
        });
        const staffList = staffResponse.data.items || staffResponse.data || [];
        console.log('Staff list fetched:', staffList);
        console.log('Looking for user_id:', user.id);

        // Find their own staff profile
        const userStaff = staffList.find((s: Staff) => s.user_id === user.id);
        console.log('Found user staff profile:', userStaff);

        if (userStaff) {
          setCurrentUserStaff(userStaff);
          console.log('Set currentUserStaff:', userStaff);
        } else {
          console.error('Staff profile not found. User ID:', user.id, 'Staff list:', staffList);
          toast.error('No staff profile found for your account. Please contact admin.');
        }

        // Don't set staff list for staff users - they don't need to see other staff
        return;
      }

      // For owner/receptionist: Fetch staff list and busyness data in parallel
      // Only show service providers (exclude receptionists)
      const [staffResponse, busynessResponse] = await Promise.all([
        apiClient.get('/staff', { params: { is_active: true, service_providers_only: true } }),
        apiClient.get('/staff/availability/busyness'),
      ]);

      const staffList = staffResponse.data.items || staffResponse.data || [];
      const busynessData = busynessResponse.data || [];

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
    } catch (error: any) {
      console.error('Error fetching staff:', error);
      // Don't show error toast for staff users if they can't access busyness endpoint
      if (user?.role !== 'staff') {
        toast.error('Failed to load staff members');
      }
      setStaff([]);
    } finally {
      setIsLoadingStaff(false);
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
    setExpandedServiceId(expandedServiceId === service.id ? null : service.id);
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

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'available':
        return <Badge className="bg-green-500 text-white text-xs">Available</Badge>;
      case 'busy':
        return <Badge className="bg-yellow-500 text-white text-xs">Busy</Badge>;
      case 'very_busy':
        return <Badge className="bg-red-500 text-white text-xs">Very Busy</Badge>;
      default:
        return null;
    }
  };

  const formatWaitTime = (minutes: number) => {
    if (minutes === 0) return 'No wait';
    if (minutes < 60) return `~${minutes} min`;
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    return mins > 0 ? `~${hours}h ${mins}m` : `~${hours}h`;
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
  console.log({categories, services});
  

  // Format price from paise to rupees
  const formatPrice = (paise: number) => {
    return `₹${(paise / 100).toFixed(2)}`;
  };

  if (isLoading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="h-8 w-8 animate-spin text-gray-400 mx-auto mb-2" />
          <p className="text-sm text-gray-500">Loading services...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col">
      {/* Search and Filter Bar */}
      <div className="mb-4 space-y-3">
        {/* Search */}
        <div className="relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
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
          <div className="flex items-center justify-center h-64">
            <div className="text-center">
              <p className="text-gray-500">No services found</p>
              {searchQuery && (
                <Button
                  variant="link"
                  onClick={() => setSearchQuery('')}
                  className="mt-2"
                >
                  Clear search
                </Button>
              )}
            </div>
          </div>
        ) : (
          <div className="grid grid-cols-2 lg:grid-cols-3 gap-4">
            {filteredServices.map((service) => {
              const isExpanded = expandedServiceId === service.id;
              const cartCount = getServiceCartCount(service.id);
              const isInCart = cartCount > 0;

              return (
                <div
                  key={service.id}
                  ref={isExpanded ? expandedCardRef : null}
                  className={`relative bg-white rounded-xl border-2 transition-all ${
                    isExpanded
                      ? 'border-black shadow-lg col-span-2 lg:col-span-3'
                      : isInCart
                      ? 'border-green-500 shadow-md'
                      : 'border-gray-200'
                  }`}
                >
                  {/* Service Card */}
                  <button
                    onClick={() => handleServiceClick(service)}
                    className={`group w-full p-4 text-left ${
                      isExpanded ? '' : 'hover:border-black hover:shadow-lg'
                    }`}
                  >
                    {/* Cart Count Badge - Top Left */}
                    {isInCart && (
                      <Badge
                        className="absolute top-2 left-2 bg-green-600 text-white text-xs flex items-center gap-1"
                      >
                        <ShoppingCart className="h-3 w-3" />
                        {cartCount}
                      </Badge>
                    )}

                    {/* Category Badge */}
                    <Badge
                      variant="secondary"
                      className="absolute top-2 right-2 text-xs"
                    >
                      {service.category.name}
                    </Badge>

                    {/* Service Name */}
                    <h3 className="font-semibold text-gray-900 mt-6 mb-2 pr-8">
                      {service.name}
                    </h3>

                    {/* Duration */}
                    <p className="text-xs text-gray-500 mb-3">
                      {service.duration_minutes} min
                    </p>

                    {/* Price and Add Button */}
                    <div className="flex items-center justify-between">
                      <span className="text-lg font-bold text-gray-900">
                        {formatPrice(service.base_price)}
                      </span>
                      <div className={`h-8 w-8 rounded-full bg-black flex items-center justify-center transition-opacity ${
                        isExpanded ? 'opacity-100' : 'opacity-0 group-hover:opacity-100'
                      }`}>
                        <Plus className="h-4 w-4 text-white" />
                      </div>
                    </div>
                  </button>

                  {/* Staff Selection - Inline */}
                  {isExpanded && !hideStaffSelection && (
                    <div className="px-4 pb-4 border-t border-gray-100 pt-3">
                      <p className="text-sm font-medium text-gray-700 mb-3">
                        <User className="h-4 w-4 inline mr-1" />
                        Select Staff Member
                      </p>

                      {isLoadingStaff ? (
                        <div className="flex items-center justify-center py-4">
                          <Loader2 className="h-5 w-5 animate-spin text-gray-400" />
                        </div>
                      ) : staff.length === 0 ? (
                        <div className="text-sm text-gray-500 py-2">
                          No active staff available
                        </div>
                      ) : (
                        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
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
                              className="group/staff relative flex flex-col gap-2 px-3 py-3 bg-gray-50 hover:bg-black hover:text-white border border-gray-200 hover:border-black rounded-lg transition-all text-left"
                            >
                              {/* Staff Name and Icon */}
                              <div className="flex items-center gap-2">
                                <User className="h-4 w-4 flex-shrink-0" />
                                <span className="truncate font-medium text-sm">
                                  {staffMember.display_name}
                                </span>
                              </div>

                              {/* Busyness Info */}
                              {staffMember.busyness && (
                                <div className="flex items-center justify-between gap-2 text-xs">
                                  {getStatusBadge(staffMember.busyness.status)}
                                  {staffMember.busyness.total_wait_minutes > 0 && (
                                    <div className="flex items-center gap-1 text-gray-600 group-hover/staff:text-white">
                                      <Clock className="h-3 w-3" />
                                      <span>{formatWaitTime(staffMember.busyness.total_wait_minutes)}</span>
                                    </div>
                                  )}
                                </div>
                              )}

                              {/* Tooltip on hover - using CSS */}
                              <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-3 py-2 bg-gray-900 text-white text-xs rounded-lg shadow-lg opacity-0 group-hover/staff:opacity-100 pointer-events-none transition-opacity whitespace-nowrap z-10">
                                {getStaffBusynessText(staffMember)}
                                <div className="absolute top-full left-1/2 transform -translate-x-1/2 -mt-1 border-4 border-transparent border-t-gray-900"></div>
                              </div>
                            </button>
                          ))}
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
