import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ServiceGrid } from '../service-grid';

vi.mock('@/lib/api-client', () => ({
  apiClient: {
    get: vi.fn().mockResolvedValue({ data: { services: [] } }),
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
