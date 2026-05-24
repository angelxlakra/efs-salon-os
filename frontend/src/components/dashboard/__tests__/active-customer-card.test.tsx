import { render, fireEvent } from '@testing-library/react';
import { ActiveCustomerCard } from '../active-customer-card';
import { describe, it, expect, vi, beforeEach } from 'vitest';

vi.mock('@/stores/auth-store', () => ({
  useAuthStore: () => ({ user: { role: 'owner', id: 'u1' } }),
}));
vi.mock('@/lib/api-client', () => ({
  apiClient: { post: vi.fn().mockResolvedValue({}) },
}));
vi.mock('sonner', () => ({ toast: { success: vi.fn(), error: vi.fn() } }));

const makeSession = (status: string, allCompleted = false) => ({
  session_id: 's1',
  customer_name: 'John Doe',
  customer_phone: '9999999999',
  customer_id: null,
  walkins: [{
    id: 'w1',
    ticket_number: 'T1',
    customer_name: 'John Doe',
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
  all_completed: allCompleted,
});

describe('ActiveCustomerCard', () => {
  const mockOnCheckout = vi.fn();
  const mockOnRefresh = vi.fn();
  beforeEach(() => { vi.clearAllMocks(); });

  it('renders customer name', () => {
    const { getByText } = render(
      <ActiveCustomerCard session={makeSession('in_progress')} onCheckout={mockOnCheckout} onRefresh={mockOnRefresh} />
    );
    expect(getByText('John Doe')).toBeTruthy();
  });

  it('shows LIVE badge for in_progress session', () => {
    const { getByText } = render(
      <ActiveCustomerCard session={makeSession('in_progress')} onCheckout={mockOnCheckout} />
    );
    expect(getByText('LIVE')).toBeTruthy();
  });

  it('shows CHECKED IN badge for checked_in session', () => {
    const { getByText } = render(
      <ActiveCustomerCard session={makeSession('checked_in')} onCheckout={mockOnCheckout} />
    );
    expect(getByText(/CHECKED IN/)).toBeTruthy();
  });

  it('uses db-svc-dot-ip class for in_progress walkin', () => {
    const { container } = render(
      <ActiveCustomerCard session={makeSession('in_progress')} onCheckout={mockOnCheckout} />
    );
    expect(container.querySelector('.db-svc-dot-ip')).not.toBeNull();
  });

  it('uses db-svc-dot-ci class for checked_in walkin', () => {
    const { container } = render(
      <ActiveCustomerCard session={makeSession('checked_in')} onCheckout={mockOnCheckout} />
    );
    expect(container.querySelector('.db-svc-dot-ci')).not.toBeNull();
  });

  it('uses db-svc-dot-done class for completed walkin', () => {
    const { container } = render(
      <ActiveCustomerCard session={makeSession('completed', true)} onCheckout={mockOnCheckout} />
    );
    expect(container.querySelector('.db-svc-dot-done')).not.toBeNull();
  });

  it('disables checkout button when not all_completed', () => {
    const { getByRole } = render(
      <ActiveCustomerCard session={makeSession('in_progress', false)} onCheckout={mockOnCheckout} />
    );
    expect((getByRole('button', { name: /checkout/i }) as HTMLButtonElement).disabled).toBe(true);
  });

  it('enables checkout when all_completed', () => {
    const { getByRole } = render(
      <ActiveCustomerCard session={makeSession('completed', true)} onCheckout={mockOnCheckout} />
    );
    expect((getByRole('button', { name: /checkout/i }) as HTMLButtonElement).disabled).toBe(false);
  });

  it('calls onCheckout with session_id when checkout clicked', () => {
    const { getByRole } = render(
      <ActiveCustomerCard session={makeSession('completed', true)} onCheckout={mockOnCheckout} />
    );
    fireEvent.click(getByRole('button', { name: /checkout/i }));
    expect(mockOnCheckout).toHaveBeenCalledWith('s1');
  });
});
