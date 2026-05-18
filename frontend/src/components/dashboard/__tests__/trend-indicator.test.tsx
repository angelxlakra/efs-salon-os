import { render } from '@testing-library/react';
import { TrendIndicator } from '../trend-indicator';

describe('TrendIndicator', () => {
  it('uses success token classes for positive value', () => {
    const { container } = render(<TrendIndicator value={5.2} />);
    const wrapper = container.firstChild as HTMLElement;
    expect(wrapper.className).toContain('bg-success-bg-soft');
    expect(wrapper.className).not.toContain('bg-green-50');
  });

  it('uses danger token classes for negative value', () => {
    const { container } = render(<TrendIndicator value={-3.1} />);
    const wrapper = container.firstChild as HTMLElement;
    expect(wrapper.className).toContain('bg-danger-bg-soft');
    expect(wrapper.className).not.toContain('bg-red-50');
  });

  it('uses neutral surface class for zero', () => {
    const { container } = render(<TrendIndicator value={0} />);
    const wrapper = container.firstChild as HTMLElement;
    expect(wrapper.className).toContain('bg-surface-page');
  });

  it('renders formatted percentage text', () => {
    const { getByText } = render(<TrendIndicator value={12.5} />);
    expect(getByText('12.5%')).toBeTruthy();
  });
});
