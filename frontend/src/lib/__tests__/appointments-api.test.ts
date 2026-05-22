import { describe, it, expect, vi, beforeEach } from 'vitest';
import { listAppointments } from '../api/appointments';

const mockGet = vi.fn();
vi.mock('../api-client', () => ({
  apiClient: { get: (...args: unknown[]) => mockGet(...args) },
}));

beforeEach(() => {
  mockGet.mockResolvedValue({ data: [] });
});

describe('listAppointments', () => {
  it('sends only date param when status is omitted', async () => {
    await listAppointments('2026-05-22');
    expect(mockGet).toHaveBeenCalledWith('/appointments', {
      params: { date: '2026-05-22' },
    });
  });

  it('includes status param when provided', async () => {
    await listAppointments('2026-05-22', 'scheduled');
    expect(mockGet).toHaveBeenCalledWith('/appointments', {
      params: { date: '2026-05-22', status: 'scheduled' },
    });
  });
});
