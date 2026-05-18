import { renderHook, act } from '@testing-library/react';
import { useChartColors } from '../use-chart-colors';

describe('useChartColors', () => {
  beforeEach(() => {
    vi.spyOn(window, 'getComputedStyle').mockReturnValue({
      getPropertyValue: (name: string) => {
        const map: Record<string, string> = {
          '--data-series-1': '#aa1111',
          '--data-series-2': '#bb2222',
          '--data-series-3': '#cc3333',
          '--data-series-4': '#dd4444',
          '--data-series-5': '#ee5555',
          '--data-series-6': '#ff6666',
          '--border-subtle': '#e0e0e0',
          '--text-muted':    '#888888',
          '--surface-card':  '#ffffff',
        };
        return map[name] ?? '';
      },
    } as unknown as CSSStyleDeclaration);
  });

  afterEach(() => vi.restoreAllMocks());

  it('returns light-mode fallback values before mount effect fires', () => {
    const { result } = renderHook(() => useChartColors());
    expect(result.current.series).toHaveLength(6);
    expect(result.current.series[0]).toBeTruthy();
  });

  it('resolves CSS vars from getComputedStyle after mount', async () => {
    const { result } = renderHook(() => useChartColors());
    await act(async () => {});
    expect(result.current.series[0]).toBe('#aa1111');
    expect(result.current.series[5]).toBe('#ff6666');
    expect(result.current.borderSubtle).toBe('#e0e0e0');
    expect(result.current.textMuted).toBe('#888888');
    expect(result.current.surfaceCard).toBe('#ffffff');
  });
});
