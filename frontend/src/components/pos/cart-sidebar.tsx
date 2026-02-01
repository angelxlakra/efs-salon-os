'use client';

import { Trash2, Plus, Minus, ShoppingCart, User, Edit2, ListOrdered } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Badge } from '@/components/ui/badge';
import { useCartStore } from '@/stores/cart-store';
import { useState, useImperativeHandle, RefObject, useEffect, useRef } from 'react';
import { useAuthStore } from '@/stores/auth-store';
import { useSettingsStore } from '@/stores/settings-store';
import { CustomerSearch } from './customer-search';
import { StaffSelector } from './staff-selector';
import { ActiveServicesModal } from './active-services-modal';
import { apiClient } from '@/lib/api-client';
import { toast } from 'sonner';

interface CartSidebarProps {
  onCheckout: () => void;
  customerSearchRef?: RefObject<{ openSearch: () => void } | null>;
}

export function CartSidebar({ onCheckout, customerSearchRef }: CartSidebarProps) {
  const {
    items,
    customerId,
    customerName,
    customerPhone,
    discount,
    sessionId,
    removeItem,
    updateQuantity,
    addItem,
    setCustomer,
    setGlobalDiscount,
    setItemStaff,
    generateSessionId,
    markItemsAsBooked,
    populateFromSession,
    clearCart,
    getSubtotal,
    getTaxAmount,
    getDiscountAmount,
    getTotal,
    getUnbookedItems,
  } = useCartStore();

  const { user } = useAuthStore();
  const { hasGST, fetchSettings, settings } = useSettingsStore();
  const [discountInput, setDiscountInput] = useState('');
  const [isCustomerSearchOpen, setIsCustomerSearchOpen] = useState(false);
  const [isCreatingOrders, setIsCreatingOrders] = useState(false);
  const [isLoadingSession, setIsLoadingSession] = useState(false);
  const [showActiveServicesModal, setShowActiveServicesModal] = useState(false);

  // Track which customer we've loaded session for (to avoid re-fetching)
  const loadedCustomerRef = useRef<string | null>(null);

  // Staff change dialog state
  const [showStaffDialog, setShowStaffDialog] = useState(false);
  const [editingItemId, setEditingItemId] = useState<string | null>(null);
  const [newStaffId, setNewStaffId] = useState<string | null>(null);
  const [newStaffName, setNewStaffName] = useState<string | null>(null);

  // Staff selection for quantity increase
  const [showQuantityStaffDialog, setShowQuantityStaffDialog] = useState(false);
  const [quantityItemId, setQuantityItemId] = useState<string | null>(null);
  const [quantityStaffId, setQuantityStaffId] = useState<string | null>(null);
  const [quantityStaffName, setQuantityStaffName] = useState<string | null>(null);

  // Fetch settings on mount
  useEffect(() => {
    if (!settings) {
      fetchSettings();
    }
  }, []);

  // Expose openSearch method to parent via ref
  useImperativeHandle(customerSearchRef, () => ({
    openSearch: () => {
      setIsCustomerSearchOpen(true);
    },
  }));

  // Fetch and populate cart from active session when customer is selected
  useEffect(() => {
    const fetchActiveSession = async () => {
      // Only fetch if customer is selected
      if (!customerId && !customerPhone) {
        loadedCustomerRef.current = null;
        return;
      }

      // Don't re-fetch if we've already loaded for this customer
      const customerKey = customerId || customerPhone || '';
      if (loadedCustomerRef.current === customerKey) return;

      // Don't override existing cart items (unless they're for a different customer)
      if (items.length > 0 && loadedCustomerRef.current !== null) return;

      try {
        setIsLoadingSession(true);

        // Fetch active walk-ins
        const { data } = await apiClient.get('/appointments/walkins/active');

        // Find session for this customer (by customer_id or phone)
        const customerSession = data.sessions.find((session: any) => {
          if (customerId && session.customer_id === customerId) return true;
          if (customerPhone && session.customer_phone === customerPhone) return true;
          return false;
        });

        if (customerSession) {
          // Convert walk-ins to cart items
          const cartItems = customerSession.walkins.map((walkin: any) => ({
            isProduct: false,
            serviceId: walkin.service.id,
            serviceName: walkin.service.name,
            quantity: 1,
            unitPrice: walkin.service.base_price,
            discount: 0,
            taxRate: 18, // Default GST rate
            staffId: walkin.assigned_staff.id,
            staffName: walkin.assigned_staff.display_name,
            duration: walkin.service.duration_minutes,
          }));

          // Populate cart with booked items
          populateFromSession(customerSession.session_id, cartItems);

          // Mark as loaded for this customer
          loadedCustomerRef.current = customerKey;

          toast.success(
            `Loaded ${cartItems.length} active service${cartItems.length > 1 ? 's' : ''} for ${customerName}`
          );
        } else {
          // No active session found, mark as loaded anyway
          loadedCustomerRef.current = customerKey;
        }
      } catch (error: any) {
        console.error('Error fetching active session:', error);
        // Mark as loaded even on error to prevent retry loops
        loadedCustomerRef.current = customerKey;
        // Don't show error toast, just log it (customer might not have active session)
      } finally {
        setIsLoadingSession(false);
      }
    };

    fetchActiveSession();
  }, [customerId, customerPhone, items.length, customerName, populateFromSession]); // Run when customer changes

  // Format paise to rupees
  const formatPrice = (paise: number) => {
    return `₹${(paise / 100).toLocaleString('en-IN', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    })}`;
  };

  const handleApplyDiscount = () => {
    const amount = parseFloat(discountInput);
    if (isNaN(amount) || amount < 0) return;

    // Convert rupees to paise
    const discountPaise = Math.round(amount * 100);

    setGlobalDiscount(discountPaise);
    setDiscountInput('');
  };

  const handlePercentageDiscount = (percentage: number) => {
    // Check if this percentage is currently active
    const currentPercentage = subtotal > 0 ? Math.round((discount / subtotal) * 100) : 0;

    if (currentPercentage === percentage) {
      // If already active, remove discount
      setGlobalDiscount(0);
    } else {
      // Calculate and apply discount as percentage of subtotal
      const discountPaise = Math.round((subtotal * percentage) / 100);
      setGlobalDiscount(discountPaise);
    }
  };

  // Check if a percentage discount is currently active
  const isPercentageActive = (percentage: number): boolean => {
    if (subtotal === 0 || discount === 0) return false;
    const currentPercentage = Math.round((discount / subtotal) * 100);
    return currentPercentage === percentage;
  };

  const handleClearCart = () => {
    clearCart();
    loadedCustomerRef.current = null; // Reset loaded customer tracking
  };

  const handleCustomerChange = (customerId: string | null, customerName: string | null, customerPhone?: string | null) => {
    console.log('handleCustomerChange called with:', customerId, customerName, customerPhone);
    setCustomer(customerId, customerName || 'Walk-in Customer', customerPhone || null);
    console.log('Customer set in cart store');
  };

  const handleOpenStaffChange = (itemId: string, currentStaffId: string | null) => {
    setEditingItemId(itemId);
    setNewStaffId(currentStaffId);
    setNewStaffName(null);
    setShowStaffDialog(true);
  };

  const handleStaffChange = () => {
    if (!editingItemId || !newStaffId || !newStaffName) {
      toast.error('Please select a staff member');
      return;
    }

    setItemStaff(editingItemId, newStaffId, newStaffName);
    toast.success('Staff assignment updated');
    setShowStaffDialog(false);
    setEditingItemId(null);
    setNewStaffId(null);
    setNewStaffName(null);
  };

  const handleQuantityIncrease = (itemId: string) => {
    const item = items.find((i) => i.id === itemId);
    if (!item) return;

    // For products, just increase quantity directly
    if (item.isProduct) {
      updateQuantity(itemId, item.quantity + 1);
      toast.success('Quantity increased');
      return;
    }

    // For services, show staff selection dialog for quantity increase
    setQuantityItemId(itemId);
    setQuantityStaffId(item.staffId || null);
    setQuantityStaffName(item.staffName || null);
    setShowQuantityStaffDialog(true);
  };

  const handleQuantityStaffSelect = () => {
    if (!quantityItemId || !quantityStaffId || !quantityStaffName) {
      toast.error('Please select a staff member');
      return;
    }

    const item = items.find((i) => i.id === quantityItemId);
    if (!item) return;

    // If same staff, increase quantity
    if (quantityStaffId === item.staffId) {
      updateQuantity(quantityItemId, item.quantity + 1);
      toast.success('Quantity increased');
    } else {
      // Different staff, add as new cart item
      addItem({
        isProduct: false,
        serviceId: item.serviceId,
        serviceName: item.serviceName,
        quantity: 1,
        unitPrice: item.unitPrice,
        discount: item.discount,
        taxRate: item.taxRate,
        staffId: quantityStaffId,
        staffName: quantityStaffName,
        duration: item.duration,
      });
      toast.success(`Added new item with ${quantityStaffName}`);
    }

    // Close dialog
    setShowQuantityStaffDialog(false);
    setQuantityItemId(null);
    setQuantityStaffId(null);
    setQuantityStaffName(null);
  };

  const handleCreateServiceOrders = async () => {
    // Get only unbooked items
    const unbookedItems = getUnbookedItems();

    // Validate unbooked service items (not products) have staff assigned
    const unbookedServices = unbookedItems.filter((item) => !item.isProduct);
    const unassigned = unbookedServices.filter((item) => !item.staffId);
    if (unassigned.length > 0) {
      toast.error('Please assign staff to all services');
      return;
    }

    if (unbookedServices.length === 0) {
      toast.error('No new services to book');
      return;
    }

    // Validate customer info
    if (!customerName) {
      toast.error('Please select or enter customer information');
      return;
    }

    try {
      setIsCreatingOrders(true);

      // Use existing session ID or generate new one
      const currentSessionId = sessionId || generateSessionId();

      // Create bulk walk-ins for unbooked service items only (not products)
      const unbookedServices = unbookedItems.filter((item) => !item.isProduct);
      const response = await apiClient.post('/appointments/walkins/bulk', {
        session_id: currentSessionId,
        customer_name: customerName,
        customer_phone: customerPhone || '',
        customer_id: customerId,
        items: unbookedServices.map((item) => ({
          service_id: item.serviceId,
          assigned_staff_id: item.staffId,
          quantity: item.quantity,
        })),
      });

      // Mark these service items as booked
      const bookedItemIds = unbookedServices.map(item => item.id);
      markItemsAsBooked(bookedItemIds);

      toast.success(
        `Booked ${response.data.total_items} service${response.data.total_items > 1 ? 's' : ''}! Staff notified.`
      );

      // Show success message with option to checkout
      toast.info('Services are now in progress. You can checkout when ready.', {
        duration: 5000,
      });
    } catch (error: any) {
      console.error('Error creating service orders:', error);
      toast.error(
        error.response?.data?.detail || 'Failed to create service orders'
      );
    } finally {
      setIsCreatingOrders(false);
    }
  };

  const subtotal = getSubtotal();
  const taxAmount = getTaxAmount();
  const discountAmount = getDiscountAmount();
  const total = getTotal();

  // Check if all service items have staff assigned (products don't need staff)
  const serviceItems = items.filter((item) => !item.isProduct);
  const allItemsHaveStaff = serviceItems.every((item) => item.staffId);

  // Get unbooked items
  const unbookedItems = getUnbookedItems();
  const unbookedServices = unbookedItems.filter((item) => !item.isProduct);
  const hasUnbookedItems = unbookedServices.length > 0;
  const allUnbookedHaveStaff = unbookedServices.every((item) => item.staffId);

  return (
    <div className="w-full bg-white md:rounded-xl md:border border-gray-200 flex flex-col md:sticky md:top-0 h-full md:h-[calc(100vh-7rem)] md:shadow-sm">
      {/* Header */}
      <div className="p-4 pr-12 md:pr-4 border-b border-gray-200 flex-shrink-0 relative">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <ShoppingCart className="h-5 w-5 text-gray-700" />
            <h2 className="font-semibold text-gray-900">Cart</h2>
            <span className="text-sm text-gray-500">({items.length})</span>
          </div>
          {items.length > 0 && (
            <Button
              variant="ghost"
              size="sm"
              onClick={handleClearCart}
              className="text-red-600 hover:text-red-700 hover:bg-red-50"
            >
              Clear
            </Button>
          )}
        </div>

        {/* Customer */}
        <CustomerSearch
          value={{ id: customerId, name: customerName }}
          onChange={handleCustomerChange}
          isOpen={isCustomerSearchOpen}
          onOpenChange={setIsCustomerSearchOpen}
        />

        {/* Manage Active Services */}
        {customerName && (
          <Button
            variant="outline"
            size="sm"
            onClick={() => setShowActiveServicesModal(true)}
            className="w-full mt-2"
          >
            <ListOrdered className="h-4 w-4 mr-2" />
            Manage Active Services
          </Button>
        )}
      </div>

      {/* Cart Items */}
      <ScrollArea className="flex-1 p-4">
        {isLoadingSession ? (
          <div className="flex flex-col items-center justify-center h-64 text-center">
            <div className="h-12 w-12 rounded-full border-4 border-gray-200 border-t-black animate-spin mb-3" />
            <p className="text-gray-500 text-sm">Loading active services...</p>
          </div>
        ) : items.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-64 text-center">
            <ShoppingCart className="h-12 w-12 text-gray-300 mb-3" />
            <p className="text-gray-500 text-sm">Your cart is empty</p>
            <p className="text-gray-400 text-xs mt-1">
              Add services to get started
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {items.map((item) => (
              <div
                key={item.id}
                className={`rounded-lg p-3 space-y-2 ${
                  item.isBooked
                    ? 'bg-green-50 border-2 border-green-200'
                    : 'bg-gray-50 border-2 border-transparent'
                }`}
              >
                {/* Item Name and Remove */}
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <h4 className="font-medium text-gray-900 text-sm">
                        {item.isProduct ? item.productName : item.serviceName}
                      </h4>
                      {item.isProduct && (
                        <Badge variant="secondary" className="text-xs bg-blue-600 text-white">
                          Product
                        </Badge>
                      )}
                      {item.isBooked && !item.isProduct && (
                        <Badge variant="secondary" className="text-xs bg-green-600 text-white">
                          Booked
                        </Badge>
                      )}
                    </div>
                    <p className="text-xs text-gray-500">
                      {formatPrice(item.unitPrice)} each
                      {!item.isProduct && item.duration && ` • ${item.duration} min`}
                    </p>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => removeItem(item.id)}
                    className="h-7 w-7 p-0 text-gray-400 hover:text-red-600"
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>

                {/* Staff Assignment (Services only) */}
                {!item.isProduct && (
                  item.staffId && item.staffName ? (
                    <div className="flex items-center justify-between">
                      <Badge variant="secondary" className="text-xs">
                        <User className="h-3 w-3 mr-1" />
                        {item.staffName}
                      </Badge>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleOpenStaffChange(item.id, item.staffId!)}
                        className="h-6 px-2 text-xs"
                      >
                        <Edit2 className="h-3 w-3 mr-1" />
                        Change
                      </Button>
                    </div>
                  ) : (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleOpenStaffChange(item.id, null)}
                      className="w-full h-7 text-xs"
                    >
                      <User className="h-3 w-3 mr-1" />
                      Assign Staff
                    </Button>
                  )
                )}

                {/* Quantity Controls */}
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => updateQuantity(item.id, item.quantity - 1)}
                      className="h-7 w-7 p-0"
                    >
                      <Minus className="h-3 w-3" />
                    </Button>
                    <span className="w-8 text-center font-medium text-sm">
                      {item.quantity}
                    </span>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleQuantityIncrease(item.id)}
                      className="h-7 w-7 p-0"
                    >
                      <Plus className="h-3 w-3" />
                    </Button>
                  </div>
                  <span className="font-semibold text-sm">
                    {formatPrice(item.unitPrice * item.quantity)}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </ScrollArea>

      {/* Footer - Totals and Checkout */}
      {items.length > 0 && (
        <div className="border-t border-gray-200 p-4 space-y-3 flex-shrink-0">
          {/* Discount Input */}
          <div className="space-y-2">
            <div className="flex gap-2">
              <Input
                type="number"
                placeholder="Discount (₹)"
                value={discountInput}
                onChange={(e) => setDiscountInput(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleApplyDiscount()}
                className="flex-1"
              />
              <Button
                variant="outline"
                onClick={handleApplyDiscount}
                disabled={!discountInput}
              >
                Apply
              </Button>
            </div>
            {/* Preset Percentage Discounts */}
            <div className="flex gap-2">
              {[5, 10, 15, 20].map((percentage) => {
                const isActive = isPercentageActive(percentage);
                return (
                  <Button
                    key={percentage}
                    variant={isActive ? "default" : "secondary"}
                    size="sm"
                    onClick={() => handlePercentageDiscount(percentage)}
                    className="flex-1"
                  >
                    {percentage}%
                  </Button>
                );
              })}
            </div>
          </div>

          {/* Price Breakdown */}
          <div className="space-y-1.5 text-sm">
            <div className="flex justify-between text-gray-600">
              <span>Subtotal</span>
              <span>{formatPrice(subtotal)}</span>
            </div>
            {discountAmount > 0 && (
              <div className="flex justify-between text-green-600">
                <span>
                  Discount
                  {subtotal > 0 && (
                    <span className="ml-1 text-xs">
                      ({((discountAmount / subtotal) * 100).toFixed(1)}%)
                    </span>
                  )}
                </span>
                <span>-{formatPrice(discountAmount)}</span>
              </div>
            )}
            {hasGST() && (
              <div className="flex justify-between text-gray-600">
                <span>GST (included)</span>
                <span>{formatPrice(taxAmount)}</span>
              </div>
            )}
            <Separator />
            <div className="flex justify-between text-lg font-bold text-gray-900">
              <span>Total</span>
              <span>{formatPrice(total)}</span>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="space-y-2">
            {/* Show Book Services button only if there are unbooked items */}
            {hasUnbookedItems && (
              <Button
                onClick={handleCreateServiceOrders}
                disabled={!allUnbookedHaveStaff || !customerName || isCreatingOrders}
                className="w-full h-11 text-base font-semibold"
                variant="default"
              >
                {isCreatingOrders
                  ? 'Booking...'
                  : `Book ${unbookedServices.length} Service${unbookedServices.length > 1 ? 's' : ''}`}
              </Button>
            )}

            {/* Always show Checkout button */}
            <Button
              onClick={onCheckout}
              disabled={!allItemsHaveStaff || !customerName}
              className="w-full h-11 text-base font-semibold"
              variant="default"
            >
              Checkout
            </Button>
          </div>

          {/* Warnings */}
          {hasUnbookedItems && !allUnbookedHaveStaff && (
            <p className="text-xs text-amber-600 text-center">
              ⚠ Assign staff to all new services before booking
            </p>
          )}
          {!customerName && (
            <p className="text-xs text-amber-600 text-center">
              ⚠ Select a customer to proceed
            </p>
          )}
        </div>
      )}

      {/* Staff Change Dialog */}
      <Dialog open={showStaffDialog} onOpenChange={setShowStaffDialog}>
        <DialogContent className="sm:max-w-[400px]">
          <DialogHeader>
            <DialogTitle>Change Staff Assignment</DialogTitle>
            <DialogDescription>
              Select a different staff member for this service
            </DialogDescription>
          </DialogHeader>

          <div className="py-4">
            <StaffSelector
              value={newStaffId}
              onChange={(staffId, staffName) => {
                setNewStaffId(staffId);
                setNewStaffName(staffName);
              }}
              placeholder="Choose staff..."
            />
          </div>

          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => {
                setShowStaffDialog(false);
                setEditingItemId(null);
                setNewStaffId(null);
                setNewStaffName(null);
              }}
            >
              Cancel
            </Button>
            <Button onClick={handleStaffChange} disabled={!newStaffId}>
              Update Staff
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Quantity Increase Staff Selection Dialog */}
      <Dialog open={showQuantityStaffDialog} onOpenChange={setShowQuantityStaffDialog}>
        <DialogContent className="sm:max-w-[400px]">
          <DialogHeader>
            <DialogTitle>Select Staff for Additional Service</DialogTitle>
            <DialogDescription>
              Choose the staff member for this service. Same staff will increase quantity, different staff will add a new item.
            </DialogDescription>
          </DialogHeader>

          <div className="py-4">
            <StaffSelector
              value={quantityStaffId}
              onChange={(staffId, staffName) => {
                setQuantityStaffId(staffId);
                setQuantityStaffName(staffName);
              }}
              placeholder="Choose staff..."
            />
          </div>

          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => {
                setShowQuantityStaffDialog(false);
                setQuantityItemId(null);
                setQuantityStaffId(null);
                setQuantityStaffName(null);
              }}
            >
              Cancel
            </Button>
            <Button onClick={handleQuantityStaffSelect} disabled={!quantityStaffId}>
              Confirm
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Active Services Modal */}
      <ActiveServicesModal
        open={showActiveServicesModal}
        onOpenChange={setShowActiveServicesModal}
        customerId={customerId}
        customerPhone={customerPhone}
        customerName={customerName}
        onServicesCancelled={() => {
          // Refresh cart when services are cancelled
          loadedCustomerRef.current = null; // Reset loaded state
          // Trigger re-fetch by clearing and setting customer again
          const currentCustomer = { customerId, customerName, customerPhone };
          setCustomer(null, '', '');
          setTimeout(() => {
            setCustomer(currentCustomer.customerId, currentCustomer.customerName || '', currentCustomer.customerPhone || '');
          }, 100);
        }}
      />
    </div>
  );
}
