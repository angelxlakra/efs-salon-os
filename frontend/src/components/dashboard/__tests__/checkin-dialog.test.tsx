import { render, fireEvent, waitFor } from '@testing-library/react';
import { CheckInDialog } from '../checkin-dialog';
import { describe, it, expect, vi, beforeEach } from 'vitest';

const mockCheckIn = vi.fn();
vi.mock('@/lib/api/appointments', () => ({
  checkInAppointment: (...args: unknown[]) => mockCheckIn(...args),
}));
vi.mock('sonner', () => ({ toast: { success: vi.fn(), error: vi.fn() } }));

const appt = {
  id: 'a1',
  customer_name: 'Priya Menon',
  scheduled_at: '2026-05-22T13:30:00+05:30',
};

describe('CheckInDialog', () => {
  const onCheckedIn = vi.fn();
  const onOpenChange = vi.fn();

  beforeEach(() => { vi.clearAllMocks(); mockCheckIn.mockResolvedValue({}); });

  it('renders customer name', () => {
    const { getByText } = render(
      <CheckInDialog open appointment={appt} staffName="Aman" serviceName="Haircut" onCheckedIn={onCheckedIn} onOpenChange={onOpenChange} />
    );
    expect(getByText('Priya Menon')).toBeTruthy();
  });

  it('shows service and staff name', () => {
    const { getByText } = render(
      <CheckInDialog open appointment={appt} staffName="Aman" serviceName="Haircut" onCheckedIn={onCheckedIn} onOpenChange={onOpenChange} />
    );
    expect(getByText('Haircut')).toBeTruthy();
    expect(getByText(/Aman/)).toBeTruthy();
  });

  it('calls checkInAppointment with appointment id on confirm', async () => {
    const { getByRole } = render(
      <CheckInDialog open appointment={appt} staffName="Aman" serviceName="Haircut" onCheckedIn={onCheckedIn} onOpenChange={onOpenChange} />
    );
    fireEvent.click(getByRole('button', { name: /check in/i }));
    await waitFor(() => expect(mockCheckIn).toHaveBeenCalledWith('a1'));
  });

  it('calls onCheckedIn with id after successful check-in', async () => {
    const { getByRole } = render(
      <CheckInDialog open appointment={appt} staffName="Aman" serviceName="Haircut" onCheckedIn={onCheckedIn} onOpenChange={onOpenChange} />
    );
    fireEvent.click(getByRole('button', { name: /check in/i }));
    await waitFor(() => expect(onCheckedIn).toHaveBeenCalledWith('a1'));
  });

  it('does not render when open is false', () => {
    const { queryByText } = render(
      <CheckInDialog open={false} appointment={appt} staffName="Aman" serviceName="Haircut" onCheckedIn={onCheckedIn} onOpenChange={onOpenChange} />
    );
    expect(queryByText('Priya Menon')).toBeNull();
  });
});
