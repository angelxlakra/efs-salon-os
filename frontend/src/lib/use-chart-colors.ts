'use client';

import { useEffect, useState } from 'react';

// Light-theme resolved hex values — used as initial state so charts render
// immediately with correct colours before the useEffect fires.
// Must stay in sync with tokens.css :root values.
const LIGHT_FALLBACK = {
  series: [
    '#1c104c', // --data-series-1  navy
    '#1e40af', // --data-series-2  indigo
    '#166534', // --data-series-3  green
    '#92400e', // --data-series-4  amber
    '#6b21a8', // --data-series-5  purple
    '#0e7490', // --data-series-6  cyan
  ],
  borderSubtle: '#eeece9',
  textMuted:    '#8b6b4a',
  surfaceCard:  '#ffffff',
};

export type ChartColors = typeof LIGHT_FALLBACK;

export function useChartColors(): ChartColors {
  const [colors, setColors] = useState<ChartColors>(LIGHT_FALLBACK);

  useEffect(() => {
    const root = document.documentElement;
    const get = (name: string) =>
      getComputedStyle(root).getPropertyValue(name).trim();
    setColors({
      series: [
        get('--data-series-1'),
        get('--data-series-2'),
        get('--data-series-3'),
        get('--data-series-4'),
        get('--data-series-5'),
        get('--data-series-6'),
      ],
      borderSubtle: get('--border-subtle'),
      textMuted:    get('--text-muted'),
      surfaceCard:  get('--surface-card'),
    });
  }, []);

  return colors;
}
