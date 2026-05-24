import { render } from '@testing-library/react';
import { GoalsRings } from '../radial-goal-progress';
import { describe, it, expect } from 'vitest';

const baseProps = {
  revenueTarget: 2000000,
  currentRevenue: 500000,
  servicesTarget: 25,
  currentServices: 6,
  customersTarget: 22,
  currentCustomers: 4,
  weekdayName: 'Monday',
  revenuePct: 25,
};

describe('GoalsRings', () => {
  it('renders three ring items', () => {
    const { container } = render(<GoalsRings {...baseProps} />);
    expect(container.querySelectorAll('[data-ring]').length).toBe(3);
  });

  it('displays the revenue percentage in the ring center', () => {
    const { getAllByText } = render(<GoalsRings {...baseProps} />);
    expect(getAllByText('25').length).toBeGreaterThan(0);
  });

  it('shows "time to push" message when revenue pct < 20', () => {
    const { getByText } = render(<GoalsRings {...baseProps} revenuePct={15} />);
    expect(getByText(/time to push/i)).toBeTruthy();
  });

  it('shows "within striking range" when revenue pct is 20–40', () => {
    const { getByText } = render(<GoalsRings {...baseProps} revenuePct={30} />);
    expect(getByText(/striking range/i)).toBeTruthy();
  });

  it('shows "on track" when revenue pct > 40', () => {
    const { getByText } = render(<GoalsRings {...baseProps} revenuePct={55} />);
    expect(getByText(/on track/i)).toBeTruthy();
  });
});
