import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render } from '@testing-library/react';
import { StatCard } from '../stat-card';

const mockUseAuthStore = vi.fn();

vi.mock('@/stores/auth-store', () => ({
  useAuthStore: () => mockUseAuthStore(),
}));

beforeEach(() => {
  localStorage.clear();
  mockUseAuthStore.mockReturnValue({ user: { role: 'owner', id: 'u1' } });
});

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

  it('renders nothing for staff user when sensitive', () => {
    mockUseAuthStore.mockReturnValue({ user: { role: 'staff', id: 'u1' } });
    const { container } = render(
      <StatCard title="Revenue" value="₹5,000" sensitive />
    );
    expect(container.firstChild).toBeNull();
  });
});
