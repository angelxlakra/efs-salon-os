import { create } from 'zustand';
import { ulid } from 'ulid';
import { StaffContributionCreate } from '@/types/multi-staff';

export interface CartItem {
  id: string;
  // Service fields (when isProduct=false)
  serviceId?: string;
  serviceName?: string;
  staffId?: string | null; // assigned staff ID (for single-staff services)
  staffName?: string | null; // staff display name (for single-staff services)
  duration?: number; // service duration in minutes
  // Multi-staff service fields
  isMultiStaff?: boolean; // true if this service requires multiple staff
  staffContributions?: StaffContributionCreate[]; // staff contributions for multi-staff services
  // Product fields (when isProduct=true)
  skuId?: string;
  productName?: string;
  // Common fields
  isProduct: boolean; // true for retail products, false for services
  quantity: number;
  unitPrice: number; // in paise
  discount: number; // in paise
  taxRate: number; // percentage (e.g., 18 for 18%)
  isBooked: boolean; // whether this item has been added to a service order
}

export interface CartState {
  items: CartItem[];
  customerId: string | null;
  customerName: string | null;
  customerPhone: string | null;
  discount: number; // global discount in paise
  sessionId: string | null; // session ID for linking walk-ins

  // Actions
  addItem: (item: Omit<CartItem, 'id' | 'isBooked'>) => void;
  removeItem: (id: string) => void;
  updateQuantity: (id: string, quantity: number) => void;
  updateDiscount: (id: string, discount: number) => void;
  setItemStaff: (itemId: string, staffId: string | null, staffName: string | null) => void;
  setItemStaffContributions: (itemId: string, contributions: StaffContributionCreate[]) => void;
  setCustomer: (customerId: string | null, customerName: string | null, customerPhone?: string | null) => void;
  setGlobalDiscount: (discount: number) => void;
  generateSessionId: () => string;
  setSessionId: (sessionId: string | null) => void;
  markItemsAsBooked: (itemIds: string[]) => void;
  populateFromSession: (sessionId: string, items: Omit<CartItem, 'id' | 'isBooked'>[]) => void;
  clearCart: () => void;

  // Computed values
  getSubtotal: () => number;
  getTaxAmount: () => number;
  getDiscountAmount: () => number;
  getTotal: () => number;
  getUnbookedItems: () => CartItem[];
}

export const useCartStore = create<CartState>((set, get) => ({
  items: [],
  customerId: null,
  customerName: null,
  customerPhone: null,
  discount: 0,
  sessionId: null,

  addItem: (item) => {
    const items = get().items;
    // For services: Don't combine items with different staff assignments or booking status
    // For products: Combine if same SKU and not yet booked
    let existingItem;

    if (item.isProduct) {
      // For products, combine by SKU
      existingItem = items.find(
        i => i.isProduct && i.skuId === item.skuId && !i.isBooked
      );
    } else if (item.isMultiStaff) {
      // For multi-staff services, NEVER combine - each assignment is unique
      existingItem = undefined;
    } else {
      // For single-staff services, combine by service and staff
      existingItem = items.find(
        i => !i.isProduct && !i.isMultiStaff && i.serviceId === item.serviceId && i.staffId === item.staffId && !i.isBooked
      );
    }

    if (existingItem) {
      // If item exists, increase quantity
      set({
        items: items.map(i =>
          i.id === existingItem.id
            ? { ...i, quantity: i.quantity + item.quantity }
            : i
        ),
      });
    } else {
      // Add new item with unique ID and isBooked = false
      const newItem: CartItem = {
        ...item,
        id: `cart-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
        isBooked: false,
      };
      set({ items: [...items, newItem] });
    }
  },

  removeItem: (id) => {
    set({ items: get().items.filter(item => item.id !== id) });
  },

  updateQuantity: (id, quantity) => {
    if (quantity <= 0) {
      get().removeItem(id);
      return;
    }
    set({
      items: get().items.map(item =>
        item.id === id ? { ...item, quantity } : item
      ),
    });
  },

  updateDiscount: (id, discount) => {
    set({
      items: get().items.map(item =>
        item.id === id ? { ...item, discount } : item
      ),
    });
  },

  setItemStaff: (itemId, staffId, staffName) => {
    set({
      items: get().items.map(item =>
        item.id === itemId ? { ...item, staffId, staffName } : item
      ),
    });
  },

  setItemStaffContributions: (itemId, contributions) => {
    set({
      items: get().items.map(item =>
        item.id === itemId ? { ...item, staffContributions: contributions, isMultiStaff: true } : item
      ),
    });
  },

  setCustomer: (customerId, customerName, customerPhone = null) => {
    set({ customerId, customerName, customerPhone });
  },

  setGlobalDiscount: (discount) => {
    set({ discount });
  },

  generateSessionId: () => {
    const sessionId = ulid();
    set({ sessionId });
    return sessionId;
  },

  setSessionId: (sessionId) => {
    set({ sessionId });
  },

  markItemsAsBooked: (itemIds) => {
    set({
      items: get().items.map(item =>
        itemIds.includes(item.id) ? { ...item, isBooked: true } : item
      ),
    });
  },

  populateFromSession: (sessionId, items) => {
    // Add items as booked with unique IDs
    const bookedItems: CartItem[] = items.map(item => ({
      ...item,
      id: `cart-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      isBooked: true,
    }));

    // Set cart state with booked items and session ID
    set({
      items: bookedItems,
      sessionId: sessionId,
    });
  },

  clearCart: () => {
    set({
      items: [],
      customerId: null,
      customerName: null,
      customerPhone: null,
      discount: 0,
      sessionId: null,
    });
  },

  // Calculate subtotal (before tax and discount)
  getSubtotal: () => {
    return get().items.reduce((sum, item) => {
      return sum + (item.unitPrice * item.quantity);
    }, 0);
  },

  // Calculate total tax amount
  getTaxAmount: () => {
    return get().items.reduce((sum, item) => {
      const itemTotal = item.unitPrice * item.quantity;
      // Tax is already included in price, extract it
      // Formula: tax = (inclusive_price * rate) / (100 + rate)
      const tax = Math.round((itemTotal * item.taxRate) / (100 + item.taxRate));
      return sum + tax;
    }, 0);
  },

  // Calculate total discount amount
  getDiscountAmount: () => {
    const itemDiscounts = get().items.reduce((sum, item) => {
      return sum + (item.discount * item.quantity);
    }, 0);
    return itemDiscounts + get().discount;
  },

  // Calculate final total
  getTotal: () => {
    const subtotal = get().getSubtotal();
    const discount = get().getDiscountAmount();
    // Round to nearest rupee (100 paise)
    return Math.round((subtotal - discount) / 100) * 100;
  },

  // Get items that haven't been booked yet
  getUnbookedItems: () => {
    return get().items.filter(item => !item.isBooked);
  },
}));
