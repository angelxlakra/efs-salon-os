import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ServiceGrid } from '../service-grid';

vi.mock('@/lib/api-client', () => ({
  apiClient: {
    get: vi.fn().mockImplementation((url: string) => {
      if (url === '/catalog/services') {
        return Promise.resolve({ data: { services: [] } });
      }
      if (url === '/staff') {
        return Promise.resolve({ data: { items: [] } });
      }
      if (url === '/staff/availability/busyness') {
        return Promise.resolve({ data: [] });
      }
      if (url === '/attendance') {
        return Promise.resolve({ data: { items: [] } });
      }
      return Promise.resolve({ data: {} });
    }),
  },
}));

vi.mock('@/stores/cart-store', () => ({
  useCartStore: () => ({ addItem: vi.fn(), items: [] }),
}));

vi.mock('@/stores/auth-store', () => ({
  useAuthStore: () => ({ user: { role: 'owner', id: 'u1' } }),
}));

describe('ServiceGrid', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders Skeleton grid while loading', () => {
    const { container } = render(<ServiceGrid />);
    const skeletons = container.querySelectorAll('[data-shape="kpi"]');
    expect(skeletons.length).toBeGreaterThan(0);
  });

  it('renders EmptyState when no services returned', async () => {
    const { findByText } = render(<ServiceGrid />);
    expect(await findByText('No services yet')).toBeInTheDocument();
  });
});
