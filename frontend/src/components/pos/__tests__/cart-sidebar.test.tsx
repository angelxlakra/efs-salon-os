import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { CartSidebar } from '../cart-sidebar';

vi.mock('@/lib/api-client', () => ({
  apiClient: {
    get: vi.fn().mockResolvedValue({ data: { sessions: [] } }),
  },
}));

vi.mock('@/stores/cart-store', () => ({
  useCartStore: () => ({
    items: [],
    customerId: null,
    customerName: null,
    customerPhone: null,
    discount: 0,
    sessionId: null,
    removeItem: vi.fn(),
    updateQuantity: vi.fn(),
    addItem: vi.fn(),
    setCustomer: vi.fn(),
    setGlobalDiscount: vi.fn(),
    setItemStaff: vi.fn(),
    setItemStaffContributions: vi.fn(),
    generateSessionId: vi.fn(() => 'sess-1'),
    setSessionId: vi.fn(),
    markItemsAsBooked: vi.fn(),
    populateFromSession: vi.fn(),
    clearCart: vi.fn(),
    getSubtotal: vi.fn(() => 0),
    getTaxAmount: vi.fn(() => 0),
    getDiscountAmount: vi.fn(() => 0),
    getTotal: vi.fn(() => 0),
    getUnbookedItems: vi.fn(() => []),
  }),
}));

vi.mock('@/stores/auth-store', () => ({
  useAuthStore: () => ({ user: { role: 'owner', id: 'u1' } }),
}));

vi.mock('@/stores/settings-store', () => ({
  useSettingsStore: () => ({ hasGST: () => false, isGstMode: () => false, servicesTaxed: () => false, fetchSettings: vi.fn(), settings: {} }),
}));

vi.mock('next/navigation', () => ({ useRouter: () => ({ push: vi.fn() }) }));

describe('CartSidebar', () => {
  beforeEach(() => vi.clearAllMocks());

  it('renders EmptyState when cart is empty', () => {
    render(<CartSidebar onCheckout={vi.fn()} />);
    expect(screen.getByText('Cart is empty')).toBeInTheDocument();
  });
});
