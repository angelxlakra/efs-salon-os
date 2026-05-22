import { render } from '@testing-library/react';
import { ServiceQueue } from '../service-queue';
import { describe, it, expect } from 'vitest';

const makeSessions = (status: 'checked_in' | 'in_progress') => [{
  session_id: 's1',
  customer_name: 'Alice',
  walkins: [{
    id: 'w1',
    service: { id: 'svc1', name: 'Haircut' },
    assigned_staff: { id: 'st1', display_name: 'Ravi' },
    status,
    checked_in_at: '2026-05-18T10:00:00Z',
  }],
}];

describe('ServiceQueue', () => {
  it('renders empty state when no sessions', () => {
    const { getByText } = render(<ServiceQueue sessions={[]} />);
    expect(getByText('No active services')).toBeTruthy();
  });

  it('uses bg-info-fg for checked_in walkin dot', () => {
    const { container } = render(<ServiceQueue sessions={makeSessions('checked_in')} />);
    expect(container.querySelector('.bg-info-fg')).not.toBeNull();
    expect(container.querySelector('.bg-blue-500')).toBeNull();
  });

  it('uses bg-warning-fg for in_progress walkin dot', () => {
    const { container } = render(<ServiceQueue sessions={makeSessions('in_progress')} />);
    expect(container.querySelector('.bg-warning-fg')).not.toBeNull();
    expect(container.querySelector('.bg-amber-400')).toBeNull();
  });
});

describe('ServiceQueue sidebar variant', () => {
  it('renders db-queue-lane-hd class in sidebar mode', () => {
    const sessions = makeSessions('in_progress');
    const { container } = render(<ServiceQueue sessions={sessions} variant="sidebar" />);
    expect(container.querySelector('.db-queue-lane-hd')).not.toBeNull();
  });

  it('renders empty state in sidebar mode too', () => {
    const { getByText } = render(<ServiceQueue sessions={[]} variant="sidebar" />);
    expect(getByText('No active services')).toBeTruthy();
  });

  it('renders db-queue-item and db-q-dot-ip for in_progress walkin in sidebar mode', () => {
    const { container } = render(
      <ServiceQueue sessions={makeSessions('in_progress')} variant="sidebar" />
    );
    expect(container.querySelector('.db-queue-item')).not.toBeNull();
    expect(container.querySelector('.db-q-dot-ip')).not.toBeNull();
  });
});
