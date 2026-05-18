import { describe, it, expect, vi } from 'vitest';
import { render } from '@testing-library/react';
import { StatCard } from '../stat-card';

vi.mock('@/stores/auth-store', () => ({
  useAuthStore: () => ({ user: { role: 'owner', id: 'u1' } }),
}));

describe('StatCard', () => {
  it('applies text-overline to the label', () => {
    const { container } = render(<StatCard title="Services" value="12" />);
    const label = container.querySelector('.text-overline');
    expect(label).not.toBeNull();
    expect(label?.textContent).toBe('Services');
  });

  it('applies text-money-lg to the value', () => {
    const { container } = render(<StatCard title="Revenue" value="₹5,000" />);
    const value = container.querySelector('.text-money-lg');
    expect(value).not.toBeNull();
  });

  it('hides sensitive value when not revealed', () => {
    const { getByText } = render(
      <StatCard title="Revenue" value="₹5,000" sensitive visibilityKey="rev" />
    );
    expect(getByText('••••')).toBeTruthy();
  });
});
