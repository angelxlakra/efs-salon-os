import { render } from '@testing-library/react';
import { ActiveCustomerCard } from '../active-customer-card';
import { describe, it, expect, vi, beforeEach } from 'vitest';

vi.mock('@/stores/auth-store', () => ({
  useAuthStore: () => ({ user: { role: 'owner', id: 'u1' } }),
}));
vi.mock('@/lib/api-client', () => ({
  apiClient: { post: vi.fn() },
}));
vi.mock('sonner', () => ({ toast: { success: vi.fn(), error: vi.fn() } }));

const makeSession = (status: string) => ({
  session_id: 's1',
  customer_name: 'john doe',
  customer_phone: '9999999999',
  customer_id: null,
  walkins: [{
    id: 'w1',
    ticket_number: 'T1',
    customer_name: 'john doe',
    customer_phone: '9999999999',
    customer_id: null,
    service: { id: 'svc1', name: 'Haircut', base_price: 50000, duration_minutes: 30 },
    assigned_staff: { id: 'st1', display_name: 'Ravi' },
    status,
    checked_in_at: '2026-05-18T10:00:00Z',
    started_at: null,
    completed_at: null,
    service_notes: null,
    duration_minutes: 30,
    session_id: 's1',
  }],
  total_amount: 50000,
  time_since_checkin: 15,
  all_completed: false,
});

describe('ActiveCustomerCard', () => {
  const mockOnCheckout = vi.fn();

  beforeEach(() => {
    mockOnCheckout.mockClear();
  });

  it('uses bg-info-fg for checked_in status dot', () => {
    const { container } = render(
      <ActiveCustomerCard session={makeSession('checked_in')} onCheckout={mockOnCheckout} />
    );
    expect(container.querySelector('.bg-info-fg')).not.toBeNull();
    expect(container.querySelector('.bg-blue-500')).toBeNull();
  });

  it('uses bg-warning-fg for in_progress status dot', () => {
    const { container } = render(
      <ActiveCustomerCard session={makeSession('in_progress')} onCheckout={mockOnCheckout} />
    );
    expect(container.querySelector('.bg-warning-fg')).not.toBeNull();
    expect(container.querySelector('.bg-amber-400')).toBeNull();
  });

  it('uses bg-success-fg for completed status dot', () => {
    const { container } = render(
      <ActiveCustomerCard session={makeSession('completed')} onCheckout={mockOnCheckout} />
    );
    expect(container.querySelector('.bg-success-fg')).not.toBeNull();
    expect(container.querySelector('.bg-green-500')).toBeNull();
  });
});
