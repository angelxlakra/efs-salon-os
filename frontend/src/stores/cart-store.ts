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
  // Package-sale fields (when kind === 'package_sale'). A package enters the
  // cart as ONE line; it is never combined with anything else.
  kind?: 'service' | 'product' | 'package_sale';
  packageDefinitionId?: string;
  packageName?: string;
  lockedChoices?: { service_id: string; service_name: string }[]; // choices fixed at purchase
  expiresLabel?: string; // e.g. "expires 12 Sep 2026"
  // Live-in-cart redemption: when set, this service line is covered by an owned
  // package — it contributes 0 to the cash total and is sent to the backend with
  // package_sale_id so the package is decremented at checkout.
  redemption?: {
    packageSaleId: string | null; // owned package (null when redeeming from a cart package)
    fromDefinitionId?: string; // cart package being sold this checkout
    packageName: string;
    // How many of this line's `quantity` units the package covers (free).
    // The remaining (quantity - coveredQuantity) units are charged.
    coveredQuantity: number;
  } | null;
  // Common fields
  isProduct: boolean; // true for retail products, false for services
  quantity: number;
  unitPrice: number; // in paise
  discount: number; // in paise
  taxRate: number; // percentage (e.g., 18 for 18%)
  isBooked: boolean; // whether this item has been added to a service order
  // Backend walk-in tracking (set when item is booked or loaded from session)
  walkinId?: string; // backend walk-in ID for cancellation
  walkinStatus?: string; // backend walk-in status (checked_in, in_progress, completed)
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
  setLineRedemption: (itemId: string, redemption: CartItem['redemption']) => void;
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

// ---------------------------------------------------------------------------
// GST split-billing preview math (must match backend tax_calculator EXACTLY:
// integer arithmetic with floor; payable per bill floors to whole rupee).
// Used only when settings.gst_registered is true; legacy totals untouched.
// ---------------------------------------------------------------------------

export interface GstSectionTotals {
  items: CartItem[];
  subtotal: number; // gross (before any discount), paise
  discount: number; // item discounts + allocated share of bill discount, paise
  cgst: number; // paise
  sgst: number; // paise
  total: number; // customer pays for this bill, floored to whole rupee, paise
}

export interface GstCartBreakdown {
  serviceSection: GstSectionTotals;
  productSection: GstSectionTotals;
  grandTotal: number; // sum of per-bill totals, paise
}

const floorToRupee = (paise: number) => Math.floor(paise / 100) * 100;

/**
 * Compute the split-billing cart preview: products at 18% inclusive (extracted
 * from MRP) on their own bill; services at 5% exclusive (added on top) when the
 * salon is GST-registered, otherwise no GST. The bill-level discount applies to
 * services only (floor per line, remainder one paise at a time to largest lines
 * first, ties by position).
 */
/** Units of a line that are actually charged (uncovered by any redemption). */
export function chargedUnits(item: CartItem): number {
  if (!item.redemption) return item.quantity;
  return Math.max(0, item.quantity - item.redemption.coveredQuantity);
}

export function computeGstBreakdown(
  items: CartItem[],
  globalDiscount: number,
  servicesTaxed = true,
): GstCartBreakdown {
  // Fully-covered lines drop out (charged units = 0); a partially-covered line
  // contributes only its uncovered units to the GST cash split.
  const lines = items
    .filter((item) => chargedUnits(item) > 0)
    .map((item) => {
      const gross = item.unitPrice * chargedUnits(item);
      const itemDiscount = item.discount * chargedUnits(item);
      return {
        item,
        gross,
        itemDiscount,
        base: gross - itemDiscount, // line total before bill-level discount
        alloc: 0, // allocated share of bill-level discount
      };
    });

  // Bill-level discount applies to SERVICE lines only — retail products are
  // sold at MRP and packages at their fixed price, neither discounted here.
  // Allocate proportionally across the service lines, capped at each line's
  // base (mirrors the backend allocator).
  const serviceLines = lines.filter(
    (l) => !l.item.isProduct && l.item.kind !== 'package_sale',
  );
  const totalServiceBase = serviceLines.reduce((sum, l) => sum + l.base, 0);
  if (globalDiscount > 0 && totalServiceBase > 0) {
    let allocated = 0;
    for (const line of serviceLines) {
      line.alloc = Math.floor((line.base * globalDiscount) / totalServiceBase);
      allocated += line.alloc;
    }
    // Remainder: one paise at a time to largest lines first (ties by position),
    // skipping lines already at their cap.
    let remainder = globalDiscount - allocated;
    const order = serviceLines
      .map((_, i) => i)
      .sort((a, b) => serviceLines[b].base - serviceLines[a].base || a - b);
    let k = 0;
    while (remainder > 0 && order.some((i) => serviceLines[i].alloc < serviceLines[i].base)) {
      const line = serviceLines[order[k % order.length]];
      if (line.alloc < line.base) {
        line.alloc += 1;
        remainder -= 1;
      }
      k += 1;
    }
  }

  const makeSection = (): Omit<GstSectionTotals, 'total'> & { pays: number } => ({
    items: [],
    subtotal: 0,
    discount: 0,
    cgst: 0,
    sgst: 0,
    pays: 0,
  });
  const service = makeSection();
  const product = makeSection();

  for (const line of lines) {
    const amountAfterDiscount = line.base - line.alloc;
    const section = line.item.isProduct ? product : service;
    section.items.push(line.item);
    section.subtotal += line.gross;
    section.discount += line.itemDiscount + line.alloc;

    if (line.item.kind === 'package_sale') {
      // Packages are GST-exempt — the backend taxes PACKAGE_SALE_LINE as NONE.
      // The customer pays the package's fixed price, no CGST/SGST added.
      section.pays += amountAfterDiscount;
    } else if (line.item.isProduct) {
      // 18% inclusive in MRP: extract tax from the discounted price
      const half = Math.floor((amountAfterDiscount * 18) / 236);
      section.cgst += half;
      section.sgst += half;
      section.pays += amountAfterDiscount; // customer pays the (discounted) MRP
    } else {
      // Services: 5% exclusive (added on top) only when GST-registered,
      // otherwise no GST — the customer pays the discounted menu price.
      const half = servicesTaxed ? Math.floor((amountAfterDiscount * 5) / 200) : 0;
      section.cgst += half;
      section.sgst += half;
      section.pays += amountAfterDiscount + half + half;
    }
  }

  const serviceSection: GstSectionTotals = {
    items: service.items,
    subtotal: service.subtotal,
    discount: service.discount,
    cgst: service.cgst,
    sgst: service.sgst,
    total: service.items.length > 0 ? floorToRupee(service.pays) : 0,
  };
  const productSection: GstSectionTotals = {
    items: product.items,
    subtotal: product.subtotal,
    discount: product.discount,
    cgst: product.cgst,
    sgst: product.sgst,
    total: product.items.length > 0 ? floorToRupee(product.pays) : 0,
  };

  return {
    serviceSection,
    productSection,
    grandTotal: serviceSection.total + productSection.total,
  };
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

    if (item.kind === 'package_sale') {
      // Packages are always a distinct line — never merge.
      existingItem = undefined;
    } else if (item.isProduct) {
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

  setLineRedemption: (itemId, redemption) => {
    set({
      items: get().items.map(item =>
        item.id === itemId ? { ...item, redemption } : item
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

  // Calculate subtotal (before tax and discount). For a redeemed line, only the
  // UNCOVERED units are charged (the package covers `coveredQuantity` of them).
  getSubtotal: () => {
    return get().items.reduce((sum, item) => {
      return sum + (item.unitPrice * chargedUnits(item));
    }, 0);
  },

  // Calculate total tax amount
  getTaxAmount: () => {
    return get().items.reduce((sum, item) => {
      const itemTotal = item.unitPrice * chargedUnits(item);
      // Tax is already included in price, extract it
      // Formula: tax = (inclusive_price * rate) / (100 + rate)
      // Guard against a missing/invalid taxRate (services carry no tax_rate
      // field) — fall back to the legacy 18% so the display never shows NaN.
      const rate = Number.isFinite(item.taxRate) ? item.taxRate : 18;
      const tax = Math.round((itemTotal * rate) / (100 + rate));
      return sum + tax;
    }, 0);
  },

  // Calculate total discount amount
  getDiscountAmount: () => {
    const itemDiscounts = get().items.reduce((sum, item) => {
      if (item.redemption) return sum;
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
