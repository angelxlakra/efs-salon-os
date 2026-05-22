import { render } from '@testing-library/react';
import { StatsBar } from '../stats-bar';
import { describe, it, expect } from 'vitest';

const baseProps = {
  revenueToday: 497700,        // ₹4,977
  revenueTarget: 2000000,      // ₹20,000
  revenueDeltaPaise: -91700,   // behind by ₹917
  activeServices: 7,
  checkedInWaiting: 2,
  pendingBills: 3,
  avgBillTodayPaise: 248900,   // ₹2,489
};

describe('StatsBar', () => {
  it('renders the hero revenue in rupees', () => {
    const { getByText } = render(<StatsBar {...baseProps} />);
    expect(getByText('₹4,977')).toBeTruthy();
  });

  it('shows "Behind by" when revenueDelta is negative', () => {
    const { getByText } = render(<StatsBar {...baseProps} />);
    expect(getByText(/Behind by/)).toBeTruthy();
  });

  it('shows "Ahead by" when revenueDelta is positive', () => {
    const { getByText } = render(
      <StatsBar {...baseProps} revenueDeltaPaise={50000} />
    );
    expect(getByText(/Ahead by/)).toBeTruthy();
  });

  it('renders the active services count', () => {
    const { getAllByText } = render(<StatsBar {...baseProps} />);
    expect(getAllByText('7').length).toBeGreaterThan(0);
  });

  it('renders progress fill width based on percentage', () => {
    const { container } = render(<StatsBar {...baseProps} />);
    const fill = container.querySelector('.db-progress-fill') as HTMLElement;
    expect(fill.style.width).toBe('25%'); // Math.round(497700/2000000 * 100) = 25
  });

  it('shows dash when avgBillTodayPaise is zero', () => {
    const { getByText } = render(<StatsBar {...baseProps} avgBillTodayPaise={0} />);
    expect(getByText('—')).toBeTruthy();
  });

  it('shows Ahead by when revenueDelta is exactly zero', () => {
    const { getByText } = render(<StatsBar {...baseProps} revenueDeltaPaise={0} />);
    expect(getByText(/Ahead by/)).toBeTruthy();
  });
});
