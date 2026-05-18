# V2 Phase 3 — Dashboard Retrofit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Retrofit the Today/Dashboard page and all its components to use V2 design tokens end-to-end — replacing raw colour literals and Tailwind colour utilities with semantic tokens, adding skeleton loading states, upgrading the empty state to the V2 primitive, and applying the type scale.

**Architecture:** Five focused tasks, each touching a single layer. Tasks 2 and 3 update individual components independently. Task 4 updates the page root and removes dead code. Task 5 closes the typography gap in StatCard. A shared `useChartColors()` hook (Task 1) is the only new file — it reads computed CSS property values from the DOM after mount so Recharts SVG elements receive resolved hex values rather than unresolvable CSS var strings.

**Tech Stack:** Next.js 16 App Router, React 19, TypeScript 5, Tailwind 4 + V2 design tokens (`tokens.css` / `globals.css`), Recharts, Vitest + Testing Library.

---

## File structure

**New files:**
- `frontend/src/lib/use-chart-colors.ts` — hook that reads `--data-series-*`, `--border-subtle`, `--text-muted`, `--surface-card` from computed styles after mount. Returns resolved hex values for use in Recharts props.
- `frontend/src/lib/__tests__/use-chart-colors.test.ts` — unit tests for the hook.
- `frontend/src/components/dashboard/__tests__/trend-indicator.test.tsx`
- `frontend/src/components/dashboard/__tests__/active-customer-card.test.tsx`
- `frontend/src/components/dashboard/__tests__/service-queue.test.tsx`
- `frontend/src/components/dashboard/__tests__/stat-card.test.tsx`

**Modified files:**
- `frontend/src/components/dashboard/trend-indicator.tsx` — `bg-green-50/text-green-600/bg-red-50/text-red-600` → semantic token classes.
- `frontend/src/components/dashboard/active-customer-card.tsx` — STATUS_COLORS raw Tailwind → token classes; button colour classes → semantic tokens.
- `frontend/src/components/dashboard/service-queue.tsx` — STATUS_DOT raw Tailwind → token classes.
- `frontend/src/components/dashboard/radial-goal-progress.tsx` — hardcoded `#10b981`/`#3b82f6` → `colorIndex` prop + `useChartColors`.
- `frontend/src/components/dashboard/hourly-trend-chart.tsx` — all `#` hex literals in chart props → `useChartColors` resolved values; tooltip `bg-white/text-green-600` → token classes.
- `frontend/src/components/dashboard/service-distribution-chart.tsx` — `COLORS` hex array → `useChartColors().series`; tooltip `bg-white` → `bg-surface-card`.
- `frontend/src/components/dashboard/stat-card.tsx` — label typography → `text-overline`; value typography → `text-money-lg`.
- `frontend/src/app/(shell)/dashboard/page.tsx` — remove dead `DailyComparisonSparkline` import + `trendsData` state + `/trends` API call; replace custom "no sessions" markup with `EmptyState`; add `Skeleton` guards for stat cards and chart sections during initial load.
- `docs/design_system.md` — append Phase 3 changelog row.

**Pre-existing files referenced (do NOT modify here):**
- `frontend/src/lib/tokens.ts` — `tokens.dataViz` string array used for fallback reference only.
- `frontend/src/components/ui/empty-state.tsx` — used in dashboard page.
- `frontend/src/components/ui/skeleton.tsx` — used in dashboard page.

---

## Pre-flight (run once before Task 1)

- [ ] Create Phase 3 branch

```bash
cd /Users/angelxlakra/dev/efs-salon/efs-salon-os && git checkout -b feature/v2-phase-3-dashboard
```

- [ ] Capture baseline test count

```bash
cd /Users/angelxlakra/dev/efs-salon/efs-salon-os/frontend && PATH="/Users/angelxlakra/.nvm/versions/node/v22.20.0/bin:$PATH" npm test -- --run 2>&1 | tail -5
```

Expected: all tests pass (≥ 149 across ≥ 30 files; the exact count will have grown from new Phase 2 additions if any were added since the plan was written).

---

## Task 1: `useChartColors` hook

**Files:**
- Create: `frontend/src/lib/use-chart-colors.ts`
- Create: `frontend/src/lib/__tests__/use-chart-colors.test.ts`

### Why

Recharts SVG chart primitives forward `stroke`/`fill` props directly to SVG presentation attributes. CSS custom properties in presentation attributes are not reliably resolved by browsers on first paint. Reading `getComputedStyle` after mount gives already-resolved hex values that work in all browsers and across light/dark theme switches.

---

- [ ] **Step 1: Write the failing test**

Create `frontend/src/lib/__tests__/use-chart-colors.test.ts`:

```ts
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
    // Initial state is the LIGHT_FALLBACK — effect hasn't run yet.
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
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /Users/angelxlakra/dev/efs-salon/efs-salon-os/frontend && PATH="/Users/angelxlakra/.nvm/versions/node/v22.20.0/bin:$PATH" npm test -- --run src/lib/__tests__/use-chart-colors.test.ts
```

Expected: FAIL — `Cannot find module '../use-chart-colors'`.

- [ ] **Step 3: Implement `useChartColors`**

Create `frontend/src/lib/use-chart-colors.ts`:

```ts
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
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd /Users/angelxlakra/dev/efs-salon/efs-salon-os/frontend && PATH="/Users/angelxlakra/.nvm/versions/node/v22.20.0/bin:$PATH" npm test -- --run src/lib/__tests__/use-chart-colors.test.ts
```

Expected: PASS — 2 tests.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/use-chart-colors.ts frontend/src/lib/__tests__/use-chart-colors.test.ts
git commit -m "feat(dashboard): useChartColors hook — resolves CSS vars for Recharts"
```

---

## Task 2: Semantic token fixes — `trend-indicator`, `active-customer-card`, `service-queue`

**Files:**
- Modify: `frontend/src/components/dashboard/trend-indicator.tsx`
- Modify: `frontend/src/components/dashboard/active-customer-card.tsx`
- Modify: `frontend/src/components/dashboard/service-queue.tsx`
- Create: `frontend/src/components/dashboard/__tests__/trend-indicator.test.tsx`
- Create: `frontend/src/components/dashboard/__tests__/active-customer-card.test.tsx`
- Create: `frontend/src/components/dashboard/__tests__/service-queue.test.tsx`

### Why

`bg-green-50`, `bg-red-50`, `bg-blue-500`, `bg-amber-400`, `bg-green-500` are raw Tailwind colour utilities that bypass the semantic token layer. The V2 invariant requires all colour to route through tokens — `success-bg-soft`, `danger-bg-soft`, `info-fg`, `warning-fg` etc.

---

- [ ] **Step 1: Write failing tests**

Create `frontend/src/components/dashboard/__tests__/trend-indicator.test.tsx`:

```tsx
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
```

Create `frontend/src/components/dashboard/__tests__/active-customer-card.test.tsx`:

```tsx
import { render } from '@testing-library/react';
import { ActiveCustomerCard } from '../active-customer-card';

vi.mock('@/stores/auth-store', () => ({
  useAuthStore: () => ({ user: { role: 'owner', id: 'u1' } }),
}));
vi.mock('@/lib/api-client', () => ({
  apiClient: { post: vi.fn() },
}));
vi.mock('sonner', () => ({ toast: { success: vi.fn(), error: vi.fn() } }));

const makeSession = (status: string) => ({
  session_id: 's1',
  customer_name: 'john doe',
  customer_phone: '9999999999',
  customer_id: null,
  walkins: [{
    id: 'w1',
    ticket_number: 'T1',
    customer_name: 'john doe',
    customer_phone: '9999999999',
    customer_id: null,
    service: { id: 'svc1', name: 'Haircut', base_price: 50000, duration_minutes: 30 },
    assigned_staff: { id: 'st1', display_name: 'Ravi' },
    status,
    checked_in_at: '2026-05-18T10:00:00Z',
    started_at: null,
    completed_at: null,
    service_notes: null,
    duration_minutes: 30,
    session_id: 's1',
  }],
  total_amount: 50000,
  time_since_checkin: 15,
  all_completed: false,
});

it('uses bg-info-fg for checked_in status dot', () => {
  const { container } = render(
    <ActiveCustomerCard session={makeSession('checked_in')} onCheckout={vi.fn()} />
  );
  expect(container.querySelector('.bg-info-fg')).not.toBeNull();
  expect(container.querySelector('.bg-blue-500')).toBeNull();
});

it('uses bg-warning-fg for in_progress status dot', () => {
  const { container } = render(
    <ActiveCustomerCard session={makeSession('in_progress')} onCheckout={vi.fn()} />
  );
  expect(container.querySelector('.bg-warning-fg')).not.toBeNull();
  expect(container.querySelector('.bg-amber-400')).toBeNull();
});

it('uses bg-success-fg for completed status dot', () => {
  const { container } = render(
    <ActiveCustomerCard session={makeSession('completed')} onCheckout={vi.fn()} />
  );
  expect(container.querySelector('.bg-success-fg')).not.toBeNull();
  expect(container.querySelector('.bg-green-500')).toBeNull();
});
```

Create `frontend/src/components/dashboard/__tests__/service-queue.test.tsx`:

```tsx
import { render } from '@testing-library/react';
import { ServiceQueue } from '../service-queue';

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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /Users/angelxlakra/dev/efs-salon/efs-salon-os/frontend && PATH="/Users/angelxlakra/.nvm/versions/node/v22.20.0/bin:$PATH" npm test -- --run src/components/dashboard/__tests__/
```

Expected: FAIL — class assertions fail because raw Tailwind classes still present.

- [ ] **Step 3: Update `trend-indicator.tsx`**

Replace the full file content:

```tsx
'use client';

import { ArrowUp, ArrowDown, Minus } from 'lucide-react';

interface TrendIndicatorProps {
  value: number;
  label?: string;
  className?: string;
}

export function TrendIndicator({ value, label, className = '' }: TrendIndicatorProps) {
  const isPositive = value > 0;
  const isNegative = value < 0;
  const isNeutral = value === 0;

  const colorClass = isPositive
    ? 'text-success-fg'
    : isNegative
    ? 'text-danger-fg'
    : 'text-text-muted';

  const bgClass = isPositive
    ? 'bg-success-bg-soft'
    : isNegative
    ? 'bg-danger-bg-soft'
    : 'bg-surface-page';

  const Icon = isPositive ? ArrowUp : isNegative ? ArrowDown : Minus;

  return (
    <div className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded ${bgClass} ${className}`}>
      <Icon className={`h-2.5 w-2.5 ${colorClass}`} />
      <span className={`text-[9px] font-medium ${colorClass}`}>
        {isNeutral ? '0%' : `${Math.abs(value).toFixed(1)}%`}
        {label && ` ${label}`}
      </span>
    </div>
  );
}
```

- [ ] **Step 4: Update `active-customer-card.tsx`**

Change only the two colour sections — leave the rest of the file intact:

Replace:
```tsx
const STATUS_COLORS: Record<string, string> = {
  checked_in: 'bg-blue-500',
  in_progress: 'bg-amber-400 animate-pulse',
  completed: 'bg-green-500',
};
```
With:
```tsx
const STATUS_COLORS: Record<string, string> = {
  checked_in: 'bg-info-fg',
  in_progress: 'bg-warning-fg animate-pulse',
  completed: 'bg-success-fg',
};
```

Replace the Start service button:
```tsx
<Button
  variant="ghost"
  size="sm"
  className="h-6 w-6 p-0 text-info-fg hover:bg-info-bg-soft"
  onClick={() => handleStartService(walkin.id)}
  title="Start service"
>
  <Play className="h-3 w-3" />
</Button>
```

Replace the Complete service button:
```tsx
<Button
  variant="ghost"
  size="sm"
  className="h-6 w-6 p-0 text-success-fg hover:bg-success-bg-soft"
  onClick={() => handleCompleteService(walkin.id)}
  title="Complete service"
>
  <Check className="h-3 w-3" />
</Button>
```

- [ ] **Step 5: Update `service-queue.tsx`**

Replace:
```tsx
const STATUS_DOT: Partial<Record<WalkInStatus, string>> = {
  checked_in: 'bg-blue-500',
  in_progress: 'bg-amber-400 animate-pulse',
};
```
With:
```tsx
const STATUS_DOT: Partial<Record<WalkInStatus, string>> = {
  checked_in: 'bg-info-fg',
  in_progress: 'bg-warning-fg animate-pulse',
};
```

- [ ] **Step 6: Run tests to verify they pass**

```bash
cd /Users/angelxlakra/dev/efs-salon/efs-salon-os/frontend && PATH="/Users/angelxlakra/.nvm/versions/node/v22.20.0/bin:$PATH" npm test -- --run src/components/dashboard/__tests__/
```

Expected: PASS — all 8 tests across the 3 new test files.

- [ ] **Step 7: Commit**

```bash
git add \
  frontend/src/components/dashboard/trend-indicator.tsx \
  frontend/src/components/dashboard/active-customer-card.tsx \
  frontend/src/components/dashboard/service-queue.tsx \
  "frontend/src/components/dashboard/__tests__/trend-indicator.test.tsx" \
  "frontend/src/components/dashboard/__tests__/active-customer-card.test.tsx" \
  "frontend/src/components/dashboard/__tests__/service-queue.test.tsx"
git commit -m "refactor(dashboard): replace raw colour utilities with semantic tokens"
```

---

## Task 3: Chart component token migration

**Files:**
- Modify: `frontend/src/components/dashboard/radial-goal-progress.tsx`
- Modify: `frontend/src/components/dashboard/hourly-trend-chart.tsx`
- Modify: `frontend/src/components/dashboard/service-distribution-chart.tsx`

### Why

All three chart components use hardcoded hex colours (`#10b981`, `#3b82f6`, etc.) or raw Tailwind colours in Recharts props. These bypass the `--data-series-*` tokens entirely and won't update when dark mode activates. The `useChartColors()` hook from Task 1 provides resolved values for each.

Chart component tests are kept shallow (render without throw) because Recharts renders into SVG via `ResizeObserver`/canvas which is unavailable in jsdom, making deep assertions on chart internals unreliable.

---

- [ ] **Step 1: Update `radial-goal-progress.tsx`**

Replace the full file:

```tsx
'use client';

import { RadialBarChart, RadialBar, ResponsiveContainer, PolarAngleAxis } from 'recharts';
import { useChartColors } from '@/lib/use-chart-colors';

interface RadialGoalProgressProps {
  title: string;
  current: number;
  target: number;
  formatter: (value: number) => string;
  /** Index into the data-series palette (0–5). Default 0 = data-series-1 (navy). */
  colorIndex?: number;
}

export function RadialGoalProgress({
  title,
  current,
  target,
  formatter,
  colorIndex = 0,
}: RadialGoalProgressProps) {
  const { series } = useChartColors();
  const color = series[colorIndex] ?? series[0];
  const percentage = Math.min(100, Math.round((current / target) * 100));

  const data = [{ name: title, value: percentage, fill: color }];

  return (
    <div className="flex flex-col items-center">
      <h4 className="text-sm font-medium text-text-secondary mb-2">{title}</h4>
      <div className="relative w-32 h-32">
        <ResponsiveContainer width="100%" height="100%">
          <RadialBarChart
            cx="50%"
            cy="50%"
            innerRadius="60%"
            outerRadius="90%"
            barSize={12}
            data={data}
            startAngle={225}
            endAngle={-45}
          >
            <PolarAngleAxis type="number" domain={[0, 100]} angleAxisId={0} tick={false} />
            <RadialBar background dataKey="value" cornerRadius={10} />
          </RadialBarChart>
        </ResponsiveContainer>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <div className="text-2xl font-bold text-text-primary">{percentage}%</div>
          <div className="text-[10px] text-text-muted mt-0.5">complete</div>
        </div>
      </div>
      <div className="mt-2 text-center">
        <div className="text-xs text-text-secondary">
          <span className="font-semibold">{formatter(current)}</span>
          <span className="text-text-disabled"> / </span>
          <span>{formatter(target)}</span>
        </div>
      </div>
    </div>
  );
}

interface DualRadialGoalsProps {
  revenueTarget: number;
  currentRevenue: number;
  servicesTarget: number;
  currentServices: number;
}

export function DualRadialGoals({
  revenueTarget,
  currentRevenue,
  servicesTarget,
  currentServices,
}: DualRadialGoalsProps) {
  const formatRevenue = (paise: number) => `₹${(paise / 100).toLocaleString('en-IN')}`;
  const formatServices = (count: number) => `${count}`;

  return (
    <div className="grid grid-cols-2 gap-4">
      {/* colorIndex 2 = data-series-3 (green #166534) for revenue */}
      <RadialGoalProgress
        title="Revenue Target"
        current={currentRevenue}
        target={revenueTarget}
        formatter={formatRevenue}
        colorIndex={2}
      />
      {/* colorIndex 1 = data-series-2 (indigo #1e40af) for services */}
      <RadialGoalProgress
        title="Services Goal"
        current={currentServices}
        target={servicesTarget}
        formatter={formatServices}
        colorIndex={1}
      />
    </div>
  );
}
```

- [ ] **Step 2: Update `hourly-trend-chart.tsx`**

Replace the full file:

```tsx
'use client';

import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from 'recharts';
import { useChartColors } from '@/lib/use-chart-colors';

interface HourlyData {
  hour: number;
  hour_label: string;
  revenue_paise: number;
  bills_count: number;
  services_count: number;
}

interface HourlyTrendChartProps {
  data: HourlyData[];
  peakHour?: number;
}

const SALON_OPEN_HOUR = 10;

function formatHour12(hour: number): string {
  const ampm = hour < 12 ? 'AM' : 'PM';
  const h = hour === 0 ? 12 : hour > 12 ? hour - 12 : hour;
  return `${h}${ampm}`;
}

export function HourlyTrendChart({ data, peakHour }: HourlyTrendChartProps) {
  const colors = useChartColors();

  const formatRevenue = (value: number) =>
    `₹${(value / 100).toLocaleString('en-IN', { maximumFractionDigits: 0 })}`;

  const currentHour = new Date().getHours();
  const hasAnyRevenue = data.some(d => d.revenue_paise > 0);
  const visibleData = data.filter(d => {
    if (d.hour < SALON_OPEN_HOUR) return false;
    if (currentHour >= SALON_OPEN_HOUR && d.hour > currentHour) return false;
    return true;
  });

  const displayData = visibleData.length > 0 ? visibleData : data;

  // Suppress linter — hasAnyRevenue is intentionally unused (kept for future filter logic)
  void hasAnyRevenue;

  const CustomTooltip = ({ active, payload }: any) => {
    if (!active || !payload?.length) return null;
    const d = payload[0].payload;
    return (
      <div className="bg-surface-card p-3 rounded-lg shadow-sm border border-border-default">
        <p className="text-xs font-semibold text-text-primary mb-1">{d.hour_label}</p>
        <div className="space-y-0.5">
          <p className="text-xs text-text-secondary">
            Revenue:{' '}
            <span className="font-medium text-success-fg">{formatRevenue(d.revenue_paise)}</span>
          </p>
          <p className="text-xs text-text-secondary">
            Bills: <span className="font-medium">{d.bills_count}</span>
          </p>
          <p className="text-xs text-text-secondary">
            Services: <span className="font-medium">{d.services_count}</span>
          </p>
        </div>
      </div>
    );
  };

  const revenueColor = colors.series[2]; // data-series-3 (green)
  const peakColor    = colors.series[3]; // data-series-4 (amber)
  const gridColor    = colors.borderSubtle;
  const axisColor    = colors.textMuted;

  const peakHourInView =
    peakHour !== undefined && displayData.some(d => d.hour === peakHour);

  return (
    <div className="w-full h-64">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={displayData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
          <defs>
            <linearGradient id="colorRevenue" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%"  stopColor={revenueColor} stopOpacity={0.3} />
              <stop offset="95%" stopColor={revenueColor} stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke={gridColor} />
          <XAxis
            dataKey="hour"
            tickFormatter={formatHour12}
            tick={{ fontSize: 11, fill: axisColor }}
            stroke={gridColor}
            interval={1}
          />
          <YAxis
            tickFormatter={(value) => `₹${Math.round(value / 100)}`}
            tick={{ fontSize: 11, fill: axisColor }}
            stroke={gridColor}
            width={50}
          />
          <Tooltip content={<CustomTooltip />} />
          {peakHourInView && (
            <ReferenceLine
              x={peakHour}
              stroke={peakColor}
              strokeDasharray="4 2"
              label={{ value: 'Peak', position: 'top', fontSize: 10, fill: peakColor }}
            />
          )}
          <Area
            type="monotone"
            dataKey="revenue_paise"
            stroke={revenueColor}
            strokeWidth={2}
            fill="url(#colorRevenue)"
          />
        </AreaChart>
      </ResponsiveContainer>
      {peakHourInView && (
        <div className="mt-2 text-center">
          <p className="text-xs text-text-muted">
            Peak hour:{' '}
            <span className="font-semibold text-text-primary">{formatHour12(peakHour!)}</span>
          </p>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 3: Update `service-distribution-chart.tsx`**

Two targeted changes — replace the `COLORS` constant and the two tooltip `bg-white` classes. Leave all other logic intact.

Replace:
```tsx
const COLORS = ['#10b981', '#3b82f6', '#8b5cf6', '#f59e0b', '#ef4444'];
```
With (inside the component body, after calling the hook):
```tsx
const { series } = useChartColors();
```

And in the `chartData` mapping, change:
```tsx
fill: COLORS[index % COLORS.length],
```
to:
```tsx
fill: series[index % series.length],
```

Change both tooltip divs from `bg-white` to `bg-surface-card`:
```tsx
<div className="bg-surface-card p-3 rounded-lg shadow-sm border border-border-default text-xs">
```

Add the import at the top of the file:
```tsx
import { useChartColors } from '@/lib/use-chart-colors';
```

Remove the now-unused `COLORS` constant entirely.

- [ ] **Step 4: Run the full test suite**

```bash
cd /Users/angelxlakra/dev/efs-salon/efs-salon-os/frontend && PATH="/Users/angelxlakra/.nvm/versions/node/v22.20.0/bin:$PATH" npm test -- --run 2>&1 | tail -5
```

Expected: all tests pass. No regressions.

- [ ] **Step 5: Commit**

```bash
git add \
  frontend/src/components/dashboard/radial-goal-progress.tsx \
  frontend/src/components/dashboard/hourly-trend-chart.tsx \
  frontend/src/components/dashboard/service-distribution-chart.tsx
git commit -m "refactor(dashboard): migrate chart components to useChartColors — kill hex literals"
```

---

## Task 4: Dashboard page — dead code removal, skeletons, EmptyState

**Files:**
- Modify: `frontend/src/app/(shell)/dashboard/page.tsx`

### Why

`DailyComparisonSparkline` is imported but never rendered; `trendsData` state feeds a `/reports/dashboard/trends` API call whose result is never displayed — this is a gratuitous network request on every 10-second poll. The "No active customers" block is a bespoke inline empty state that should use the V2 `EmptyState` primitive. During `isLoading`, stat cards and the chart section show blank zeros — the V2 spec requires Skeleton primitives instead.

---

- [ ] **Step 1: Remove dead code and add skeletons + EmptyState**

Replace `frontend/src/app/(shell)/dashboard/page.tsx` with:

```tsx
'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Users, Cake } from 'lucide-react';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { EmptyState } from '@/components/ui/empty-state';
import { apiClient } from '@/lib/api-client';
import { toast } from 'sonner';
import { useCartStore } from '@/stores/cart-store';
import { useAuthStore } from '@/stores/auth-store';
import { ActiveCustomerCard } from '@/components/dashboard/active-customer-card';
import { TrendIndicator } from '@/components/dashboard/trend-indicator';
import { StatCard } from '@/components/dashboard/stat-card';
import { ServiceQueue } from '@/components/dashboard/service-queue';
import { DualRadialGoals } from '@/components/dashboard/radial-goal-progress';
import { HourlyTrendChart } from '@/components/dashboard/hourly-trend-chart';
import { ServiceDistributionChart } from '@/components/dashboard/service-distribution-chart';
import { titleCase } from '@/lib/utils';

interface Service {
  id: string;
  name: string;
  base_price: number;
  duration_minutes: number;
}

interface Staff {
  id: string;
  display_name: string;
}

interface WalkIn {
  id: string;
  ticket_number: string;
  customer_name: string;
  customer_phone: string;
  customer_id: string | null;
  service: Service;
  assigned_staff: Staff;
  status: 'checked_in' | 'in_progress' | 'completed' | 'cancelled';
  checked_in_at: string | null;
  started_at: string | null;
  completed_at: string | null;
  service_notes: string | null;
  duration_minutes: number;
  session_id: string | null;
}

interface CustomerSession {
  session_id: string;
  customer_name: string;
  customer_phone: string;
  customer_id: string | null;
  walkins: WalkIn[];
  total_amount: number;
  time_since_checkin: number;
  all_completed: boolean;
}

interface DashboardStats {
  today_revenue: number;
  today_services: number;
  today_customers: number;
  active_services: number;
  pending_bills: number;
}

interface SalonSettings {
  daily_revenue_target_paise: number;
  daily_services_target: number;
}

interface ComparisonData {
  revenue_change_paise: number;
  revenue_percent_change: number;
  services_change: number;
  services_percent_change: number;
  customers_change: number;
  customers_percent_change: number;
}

interface HourlyData {
  hour: number;
  hour_label: string;
  revenue_paise: number;
  bills_count: number;
  services_count: number;
}

interface ServicePerformance {
  service_id: string;
  service_name: string;
  count: number;
  total_revenue: number;
}

export default function DashboardPage() {
  const router = useRouter();
  const { user } = useAuthStore();
  const { addItem, setCustomer, setSessionId, clearCart } = useCartStore();

  const [stats, setStats] = useState<DashboardStats>({
    today_revenue: 0,
    today_services: 0,
    today_customers: 0,
    active_services: 0,
    pending_bills: 0,
  });
  const [activeSessions, setActiveSessions] = useState<CustomerSession[]>([]);
  const [settings, setSettings] = useState<SalonSettings>({
    daily_revenue_target_paise: 2000000,
    daily_services_target: 25,
  });
  const [comparison, setComparison] = useState<ComparisonData | null>(null);
  const [hourlyData, setHourlyData] = useState<HourlyData[]>([]);
  const [peakHour, setPeakHour] = useState<number | undefined>(undefined);
  const [topServices, setTopServices] = useState<ServicePerformance[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [birthdayUsers, setBirthdayUsers] = useState<{ id: string; full_name: string }[]>([]);

  useEffect(() => {
    if (user?.role === 'staff') {
      router.push('/dashboard/staff');
    }
  }, [user, router]);

  useEffect(() => {
    fetchDashboardData();
    const interval = setInterval(() => fetchDashboardData(true), 10000);
    return () => clearInterval(interval);
  }, []);

  const fetchDashboardData = async (silent = false) => {
    try {
      if (!silent) setIsLoading(true);

      const [
        walkinsResponse,
        reportsResponse,
        settingsResponse,
        comparisonResponse,
        hourlyResponse,
        birthdaysResponse,
      ] = await Promise.all([
        apiClient.get('/appointments/walkins/active'),
        apiClient.get('/reports/dashboard'),
        apiClient.get('/settings'),
        apiClient.get('/reports/dashboard/comparison'),
        apiClient.get('/reports/dashboard/hourly'),
        apiClient.get('/users/birthdays/today'),
      ]);

      setActiveSessions(walkinsResponse.data.sessions || []);

      const metrics = reportsResponse.data.metrics;
      setStats({
        today_revenue:   metrics.net_revenue,
        today_services:  metrics.completed_appointments,
        today_customers: metrics.total_bills,
        active_services: metrics.active_appointments,
        pending_bills:   metrics.pending_appointments,
      });

      if (settingsResponse.data) {
        setSettings({
          daily_revenue_target_paise: settingsResponse.data.daily_revenue_target_paise || 2000000,
          daily_services_target:      settingsResponse.data.daily_services_target || 25,
        });
      }

      if (comparisonResponse.data?.comparison) {
        setComparison(comparisonResponse.data.comparison);
      }

      if (hourlyResponse.data?.hourly_data) {
        setHourlyData(hourlyResponse.data.hourly_data);
        setPeakHour(hourlyResponse.data.peak_hour);
      }

      if (reportsResponse.data?.top_services) {
        setTopServices(reportsResponse.data.top_services);
      }

      if (birthdaysResponse.data?.birthdays) {
        setBirthdayUsers(birthdaysResponse.data.birthdays);
      }
    } catch (error: unknown) {
      console.error('Failed to fetch dashboard data:', error);
      setActiveSessions([]);
      const detail =
        error instanceof Error && (error as any).response?.data?.detail
          ? (error as any).response.data.detail
          : 'Failed to load dashboard data';
      if (!silent) toast.error(detail);
    } finally {
      setIsLoading(false);
    }
  };

  const formatPrice = (paise: number) =>
    `₹${(paise / 100).toLocaleString('en-IN')}`;

  const getCurrentDate = () =>
    new Date().toLocaleDateString('en-IN', {
      weekday: 'long',
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });

  const handleCheckoutSession = async (sessionId: string) => {
    try {
      const session = activeSessions.find((s) => s.session_id === sessionId);
      if (!session) { toast.error('Session not found'); return; }

      clearCart();
      session.walkins.forEach((walkin) => {
        addItem({
          isProduct: false,
          serviceId: walkin.service.id,
          serviceName: walkin.service.name,
          quantity: 1,
          unitPrice: walkin.service.base_price,
          discount: 0,
          taxRate: 18,
          staffId: walkin.assigned_staff.id,
          staffName: walkin.assigned_staff.display_name,
          duration: walkin.duration_minutes,
        });
      });

      setCustomer(session.customer_id, titleCase(session.customer_name), session.customer_phone);
      setSessionId(sessionId);
      router.push('/dashboard/pos');
      toast.success(`Ready to bill ${titleCase(session.customer_name)}`);
    } catch (error) {
      console.error('Error loading checkout:', error);
      toast.error('Failed to load customer for checkout');
    }
  };

  return (
    <div className="space-y-3">
      {/* Date stamp */}
      <div className="flex justify-end -mb-1">
        <p className="text-xs font-medium text-text-secondary bg-surface-card px-2 py-0.5 rounded-full border border-border-subtle">
          {getCurrentDate()}
        </p>
      </div>

      {/* Birthday banner */}
      {birthdayUsers.length > 0 && (
        <div className="relative overflow-hidden rounded-xl bg-gradient-to-r from-pink-500 via-purple-500 to-yellow-400 p-[2px]">
          <div className="flex items-center gap-4 rounded-xl bg-surface-card px-5 py-4">
            <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-pink-400 to-purple-500 shadow-lg">
              <Cake className="h-6 w-6 text-white" />
            </div>
            <div className="min-w-0 flex-1">
              <p className="text-sm font-bold text-text-primary">
                {birthdayUsers.length === 1
                  ? `Happy Birthday, ${birthdayUsers[0].full_name}!`
                  : `Happy Birthday to ${birthdayUsers.map(u => u.full_name).join(' & ')}!`}
              </p>
              <p className="text-xs text-text-secondary mt-0.5">
                {birthdayUsers.length === 1
                  ? 'Wishing them a wonderful day!'
                  : `${birthdayUsers.length} team members celebrating today!`}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Stat cards — skeleton during initial load */}
      {isLoading ? (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-4" aria-busy="true">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} shape="kpi" />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-4">
          <StatCard
            title="Today's Revenue"
            value={formatPrice(stats.today_revenue)}
            subValue={
              settings.daily_revenue_target_paise > 0
                ? `${Math.min(100, Math.round((stats.today_revenue / settings.daily_revenue_target_paise) * 100))}% of daily goal`
                : undefined
            }
            sensitive
            visibilityKey="revenue-visible"
            trend={comparison ? <TrendIndicator value={comparison.revenue_percent_change} /> : undefined}
          />
          <StatCard
            title="Services"
            value={String(stats.today_services)}
            subValue={`target: ${settings.daily_services_target}`}
            trend={comparison ? <TrendIndicator value={comparison.services_percent_change} /> : undefined}
          />
          <StatCard
            title="Customers"
            value={String(stats.today_customers)}
            trend={comparison ? <TrendIndicator value={comparison.customers_percent_change} /> : undefined}
          />
          <StatCard
            title="Active Now"
            value={String(stats.active_services)}
            subValue={stats.pending_bills ? `${stats.pending_bills} pending` : undefined}
          />
        </div>
      )}

      {/* Active customers + goals sidebar */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2">
          <Card>
            <Card.Header
              title="Active Customers"
              description="Customers currently receiving services"
              action={<Badge variant="secondary">{activeSessions.length} Active</Badge>}
            />
            <Card.Body>
              {isLoading ? (
                <div className="space-y-3" aria-busy="true">
                  <Skeleton shape="row" />
                  <Skeleton shape="row" />
                </div>
              ) : activeSessions.length === 0 ? (
                <EmptyState
                  icon={<Users />}
                  title="Floor is clear"
                  body="Walk-in and appointment customers currently in service will appear here."
                  headingLevel={4}
                />
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {activeSessions.map((session) => (
                    <ActiveCustomerCard
                      key={session.session_id}
                      session={session}
                      onCheckout={handleCheckoutSession}
                      onRefresh={() => fetchDashboardData(true)}
                    />
                  ))}
                </div>
              )}
            </Card.Body>
          </Card>
        </div>

        <div className="space-y-4">
          <Card>
            <Card.Header title="Daily Goals" />
            <Card.Body>
              {isLoading ? (
                <Skeleton shape="kpi" aria-busy="true" />
              ) : (
                <>
                  <DualRadialGoals
                    revenueTarget={settings.daily_revenue_target_paise}
                    currentRevenue={stats.today_revenue}
                    servicesTarget={settings.daily_services_target}
                    currentServices={stats.today_services}
                  />
                  <div className="pt-4 mt-4 border-t border-border-subtle">
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-text-secondary">Avg. Bill Value</span>
                      <span className="font-semibold text-text-primary">
                        {stats.today_services > 0
                          ? formatPrice(Math.round(stats.today_revenue / stats.today_services))
                          : '—'}
                      </span>
                    </div>
                  </div>
                </>
              )}
            </Card.Body>
          </Card>

          <ServiceQueue sessions={activeSessions} />
        </div>
      </div>

      {/* Analytics section */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mt-4">
        <div className="lg:col-span-2">
          <Card>
            <Card.Header
              title="Hourly Revenue Trend"
              description="Revenue breakdown by hour of the day"
            />
            <Card.Body>
              {isLoading ? (
                <Skeleton shape="card" className="h-64" aria-busy="true" />
              ) : hourlyData.length > 0 ? (
                <HourlyTrendChart data={hourlyData} peakHour={peakHour} />
              ) : (
                <EmptyState
                  title="No revenue yet today"
                  body="Hourly revenue will appear as bills are completed."
                  headingLevel={4}
                />
              )}
            </Card.Body>
          </Card>
        </div>

        <div>
          <Card>
            <Card.Header title="Top Services" description="Revenue by service type" />
            <Card.Body>
              {isLoading ? (
                <Skeleton shape="card" className="h-64" aria-busy="true" />
              ) : topServices.length > 0 ? (
                <ServiceDistributionChart
                  services={topServices}
                  totalServices={stats.today_services}
                />
              ) : (
                <EmptyState
                  title="No services today"
                  body="Service revenue distribution will appear after the first bill is completed."
                  headingLevel={4}
                />
              )}
            </Card.Body>
          </Card>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Run full test suite**

```bash
cd /Users/angelxlakra/dev/efs-salon/efs-salon-os/frontend && PATH="/Users/angelxlakra/.nvm/versions/node/v22.20.0/bin:$PATH" npm test -- --run 2>&1 | tail -5
```

Expected: all tests pass. No regressions.

- [ ] **Step 3: Commit**

```bash
git add "frontend/src/app/(shell)/dashboard/page.tsx"
git commit -m "feat(dashboard): skeleton loading + EmptyState + remove dead trends code"
```

---

## Task 5: StatCard typography + design system changelog

**Files:**
- Modify: `frontend/src/components/dashboard/stat-card.tsx`
- Create: `frontend/src/components/dashboard/__tests__/stat-card.test.tsx`
- Modify: `docs/design_system.md`

### Why

The stat card label (`text-xs font-medium uppercase tracking-wide`) is an ad-hoc approximation of the design system's `text-overline` token class (11px / 600 / uppercase / 6% tracking). The value (`text-xl md:text-2xl font-bold tabular-nums`) is an ad-hoc approximation of `text-money-lg` (22px / 700 / tabular). Using the type scale classes keeps the design system as the single source of truth for spacing, weight, and size so any future type-scale change propagates automatically.

---

- [ ] **Step 1: Write failing test**

Create `frontend/src/components/dashboard/__tests__/stat-card.test.tsx`:

```tsx
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
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /Users/angelxlakra/dev/efs-salon/efs-salon-os/frontend && PATH="/Users/angelxlakra/.nvm/versions/node/v22.20.0/bin:$PATH" npm test -- --run "src/components/dashboard/__tests__/stat-card.test.tsx"
```

Expected: FAIL — `text-overline` and `text-money-lg` classes not yet on the elements.

- [ ] **Step 3: Update `stat-card.tsx`**

Replace the two class strings inside the return:

Label span — from:
```tsx
<span className="text-xs font-medium text-text-secondary uppercase tracking-wide">
```
to:
```tsx
<span className="text-overline text-text-secondary">
```

Value span — from:
```tsx
<span className="text-xl md:text-2xl font-bold text-text-primary tabular-nums">
```
to:
```tsx
<span className="text-money-lg text-text-primary">
```

(`text-money-lg` already includes `font-variant-numeric: tabular-nums lining-nums` per `typography.css`.)

- [ ] **Step 4: Run test to verify it passes**

```bash
cd /Users/angelxlakra/dev/efs-salon/efs-salon-os/frontend && PATH="/Users/angelxlakra/.nvm/versions/node/v22.20.0/bin:$PATH" npm test -- --run "src/components/dashboard/__tests__/stat-card.test.tsx"
```

Expected: PASS — 3 tests.

- [ ] **Step 5: Run full test suite one final time**

```bash
cd /Users/angelxlakra/dev/efs-salon/efs-salon-os/frontend && PATH="/Users/angelxlakra/.nvm/versions/node/v22.20.0/bin:$PATH" npm test -- --run 2>&1 | tail -5
```

Expected: all tests pass. New test count is baseline + 14 new tests (2 hook + 4 trend + 3 acc + 3 queue + 3 stat).

- [ ] **Step 6: Append Phase 3 changelog to `docs/design_system.md`**

Find the `## 13. Changelog` section (or the last section) in `docs/design_system.md` and append:

```markdown
### Phase 3 — Dashboard retrofit (2026-05-18)

- **Token sweep:** `trend-indicator`, `active-customer-card`, `service-queue` — raw Tailwind colour utilities (`bg-green-50`, `text-green-600`, `bg-blue-500`, `bg-amber-400`, `bg-green-500`, `bg-red-50`, `text-red-600`) replaced with semantic tokens (`success-fg`, `success-bg-soft`, `danger-fg`, `danger-bg-soft`, `info-fg`, `warning-fg`).
- **Chart colours:** New `useChartColors()` hook reads `--data-series-*`, `--border-subtle`, `--text-muted`, `--surface-card` from `getComputedStyle` after mount. All three chart components (`radial-goal-progress`, `hourly-trend-chart`, `service-distribution-chart`) now use resolved token values instead of hardcoded hex literals.
- **Loading states:** `isLoading` state in `dashboard/page.tsx` now renders `Skeleton` (shape `kpi` for stat cards, `row` for active-customer list, `card` for chart sections) instead of blank zeros.
- **Empty states:** "No active customers" replaced with `EmptyState` primitive. Chart sections show `EmptyState` with action-oriented copy when data is absent.
- **Typography:** `StatCard` label upgraded from ad-hoc `text-xs uppercase tracking-wide` to `text-overline`; value from `text-xl md:text-2xl font-bold` to `text-money-lg`.
- **Dead code removed:** `DailyComparisonSparkline` import, `trendsData` state, and the `/reports/dashboard/trends` API call removed from `dashboard/page.tsx`.
```

- [ ] **Step 7: Commit**

```bash
git add \
  frontend/src/components/dashboard/stat-card.tsx \
  "frontend/src/components/dashboard/__tests__/stat-card.test.tsx" \
  docs/design_system.md
git commit -m "style(dashboard): type-scale tokens on StatCard + Phase 3 design system changelog"
```

---

## Done ✓

At this point:
- All dashboard components use V2 semantic tokens for colour — no raw `text-green-*`, `bg-blue-*`, hex literals in chart props.
- Charts receive resolved hex values from `useChartColors()` — dark-mode-safe.
- Loading states use `Skeleton` primitives.
- Empty states use `EmptyState` with action-oriented copy.
- StatCard typography follows the `text-overline` / `text-money-lg` type scale.
- 14 new tests added; no regressions.

The branch `feature/v2-phase-3-dashboard` is ready for review and merge into `main`, followed by the Phase 4 (POS) plan.
