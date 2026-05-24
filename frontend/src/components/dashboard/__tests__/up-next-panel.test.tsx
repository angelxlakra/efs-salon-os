import { render, waitFor } from '@testing-library/react';
import { UpNextPanel } from '../up-next-panel';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { format, addMinutes } from 'date-fns';

const mockListAppointments = vi.fn();
const mockListActiveStaff = vi.fn();
const mockListServices = vi.fn();

vi.mock('@/lib/api/appointments', () => ({
  listAppointments: (...args: unknown[]) => mockListAppointments(...args),
  listActiveStaff:  (...args: unknown[]) => mockListActiveStaff(...args),
  listServices:     (...args: unknown[]) => mockListServices(...args),
}));

// Stub out CheckInDialog — the 7 tests never click a row so the dialog is irrelevant;
// mocking prevents transitive resolution of @/components/ui/dialog in the test runner.
vi.mock('../checkin-dialog', () => ({
  CheckInDialog: () => null,
}));

function makeAppt(minutesFromNow: number, id = 'a1') {
  return {
    id,
    ticket_number: 'T1',
    visit_id: null,
    customer_id: null,
    customer_name: 'Test Customer',
    customer_phone: '9999999999',
    service_id: 'svc1',
    assigned_staff_id: 'st1',
    scheduled_at: addMinutes(new Date(), minutesFromNow).toISOString(),
    duration_minutes: 30,
    status: 'scheduled' as const,
    booking_notes: null,
    service_notes: null,
    checked_in_at: null,
    started_at: null,
    completed_at: null,
    cancelled_at: null,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  };
}

// Suppress unused import warning — format is imported to match the spec's import list
void format;

beforeEach(() => {
  vi.clearAllMocks();
  mockListActiveStaff.mockResolvedValue([{ id: 'st1', display_name: 'Aman', specialization: null, is_active: true, is_service_provider: true }]);
  mockListServices.mockResolvedValue([{ id: 'svc1', name: 'Haircut', base_price: 50000, duration_minutes: 30, category_name: 'Hair' }]);
});

describe('UpNextPanel', () => {
  it('shows loading state initially', () => {
    mockListAppointments.mockResolvedValue([makeAppt(30)]);
    const { getByText } = render(<UpNextPanel />);
    expect(getByText(/loading/i)).toBeTruthy();
  });

  it('renders a customer name after data loads', async () => {
    mockListAppointments.mockResolvedValue([makeAppt(30)]);
    const { getByText } = render(<UpNextPanel />);
    await waitFor(() => expect(getByText('Test Customer')).toBeTruthy());
  });

  it('filters out past appointments', async () => {
    mockListAppointments.mockResolvedValue([makeAppt(-10), makeAppt(30)]);
    const { getAllByText } = render(<UpNextPanel />);
    await waitFor(() => {
      expect(getAllByText('Test Customer').length).toBe(1); // only future one shown
    });
  });

  it('caps display at 5 appointments', async () => {
    const appts = Array.from({ length: 7 }, (_, i) => makeAppt(i * 10 + 5, `a${i}`));
    mockListAppointments.mockResolvedValue(appts);
    const { getAllByText } = render(<UpNextPanel />);
    await waitFor(() => {
      expect(getAllByText('Test Customer').length).toBe(5);
    });
  });

  it('shows empty state when no upcoming appointments', async () => {
    mockListAppointments.mockResolvedValue([makeAppt(-5)]);
    const { getByText } = render(<UpNextPanel />);
    await waitFor(() => expect(getByText(/no appointments/i)).toBeTruthy());
  });

  it('shows service name from lookup', async () => {
    mockListAppointments.mockResolvedValue([makeAppt(30)]);
    const { getByText } = render(<UpNextPanel />);
    await waitFor(() => expect(getByText('Haircut')).toBeTruthy());
  });

  it('shows staff name from lookup', async () => {
    mockListAppointments.mockResolvedValue([makeAppt(30)]);
    const { getByText } = render(<UpNextPanel />);
    await waitFor(() => expect(getByText(/Aman/)).toBeTruthy());
  });
});
