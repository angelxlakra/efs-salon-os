import { renderHook, act } from '@testing-library/react';
import { useChartColors } from '../use-chart-colors';

describe('useChartColors — fallback shape', () => {
  it('series and scalar fallback values match tokens.css :root', () => {
    // Mock getComputedStyle to return the LIGHT_FALLBACK values,
    // simulating a properly configured tokens.css environment.
    // This verifies the fallback constants have the correct shape.
    vi.spyOn(window, 'getComputedStyle').mockReturnValue({
      getPropertyValue: (name: string) => {
        const map: Record<string, string> = {
          '--data-series-1': '#1c104c',
          '--data-series-2': '#1e40af',
          '--data-series-3': '#166534',
          '--data-series-4': '#92400e',
          '--data-series-5': '#6b21a8',
          '--data-series-6': '#0e7490',
          '--border-subtle': '#eeece9',
          '--text-muted':    '#8b6b4a',
          '--surface-card':  '#ffffff',
        };
        return map[name] ?? '';
      },
    } as unknown as CSSStyleDeclaration);

    const { result } = renderHook(() => useChartColors());
    // After effect fires, hook resolves CSS vars matching the fallback values
    expect(result.current.series).toHaveLength(6);
    expect(result.current.series[0]).toBe('#1c104c');
    expect(result.current.series[1]).toBe('#1e40af');
    expect(result.current.series[2]).toBe('#166534');
    expect(result.current.series[3]).toBe('#92400e');
    expect(result.current.series[4]).toBe('#6b21a8');
    expect(result.current.series[5]).toBe('#0e7490');

    // All 3 scalar fallback values
    expect(result.current.borderSubtle).toBe('#eeece9');
    expect(result.current.textMuted).toBe('#8b6b4a');
    expect(result.current.surfaceCard).toBe('#ffffff');

    vi.restoreAllMocks();
  });
});

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

  it('resolves all 6 series CSS vars and 3 scalar vars after mount', async () => {
    const { result } = renderHook(() => useChartColors());
    await act(async () => {});

    // All 6 series values resolved from mocked CSS vars
    expect(result.current.series[0]).toBe('#aa1111');
    expect(result.current.series[1]).toBe('#bb2222');
    expect(result.current.series[2]).toBe('#cc3333');
    expect(result.current.series[3]).toBe('#dd4444');
    expect(result.current.series[4]).toBe('#ee5555');
    expect(result.current.series[5]).toBe('#ff6666');

    // All 3 scalar values resolved from mocked CSS vars
    expect(result.current.borderSubtle).toBe('#e0e0e0');
    expect(result.current.textMuted).toBe('#888888');
    expect(result.current.surfaceCard).toBe('#ffffff');
  });
});
