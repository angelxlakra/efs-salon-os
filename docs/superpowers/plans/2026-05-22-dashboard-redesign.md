# Dashboard Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign the "Today" dashboard page with a warm cream/gold visual language, Cormorant Garamond numerals, a 3-panel stats bar, 3-ring goals section, restyled active-customer cards, a new "Up Next" upcoming-appointments sidebar panel, and the Staff Queue moved into the right sidebar.

**Architecture:** All changes are frontend-only. New components (`StatsBar`, `GoalsRings`, `UpNextPanel`, `CheckInDialog`) are written as self-contained units. A `dashboard.css` file holds all scoped design tokens and typography classes under `.dashboard-page` so nothing bleeds into other pages. `UpNextPanel` manages its own data fetching.

**Tech Stack:** Next.js 16, React 19, TypeScript, Tailwind CSS 4, Vitest + Testing Library, `date-fns` (already installed), shadcn/ui Dialog.

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `frontend/src/styles/dashboard.css` | **Create** | All `.dashboard-page` scoped tokens + typography classes |
| `frontend/src/app/globals.css` | **Modify** | `@import` the new `dashboard.css` |
| `frontend/src/app/layout.tsx` | **Modify** | Add Cormorant Garamond + DM Sans Google Fonts `<link>` |
| `frontend/src/lib/api/appointments.ts` | **Modify** | Add optional `status?` param to `listAppointments` |
| `frontend/src/components/dashboard/stats-bar.tsx` | **Create** | 3-panel stats bar (Revenue + Pace + Right Now) |
| `frontend/src/components/dashboard/radial-goal-progress.tsx` | **Modify** | Replace Recharts rings with SVG rings; add 3rd customers ring + contextual message; export as `GoalsRings` in addition to keeping `DualRadialGoals` |
| `frontend/src/components/dashboard/active-customer-card.tsx` | **Modify** | Restyle to warm visual language; no logic changes |
| `frontend/src/components/dashboard/service-queue.tsx` | **Modify** | Add `variant="sidebar"` prop for vertical lane layout |
| `frontend/src/components/dashboard/checkin-dialog.tsx` | **Create** | Modal to check in a scheduled appointment |
| `frontend/src/components/dashboard/up-next-panel.tsx` | **Create** | Self-contained sidebar panel showing next 5 scheduled appointments |
| `frontend/src/app/(shell)/dashboard/page.tsx` | **Modify** | Wire all new components; restructure layout to flex + sidebar |
| `frontend/src/components/dashboard/__tests__/stats-bar.test.tsx` | **Create** | Tests for StatsBar |
| `frontend/src/components/dashboard/__tests__/radial-goal-progress.test.tsx` | **Create** | Tests for GoalsRings |
| `frontend/src/components/dashboard/__tests__/checkin-dialog.test.tsx` | **Create** | Tests for CheckInDialog |
| `frontend/src/components/dashboard/__tests__/up-next-panel.test.tsx` | **Create** | Tests for UpNextPanel |

---

## Task 1: Foundation — `dashboard.css` + Google Fonts

**Files:**
- Create: `frontend/src/styles/dashboard.css`
- Modify: `frontend/src/app/globals.css` (add `@import`)
- Modify: `frontend/src/app/layout.tsx` (add font `<link>` tags)

- [ ] **Step 1: Create `frontend/src/styles/dashboard.css`**

```css
/* ─── Dashboard-page scoped design tokens ─────────────────────────────────── */
.dashboard-page {
  --db-bg:          #f5f0e8;
  --db-card:        #fffdf9;
  --db-border:      #e8dfc8;
  --db-muted:       #f0e8d8;
  --db-gold:        #c9a84c;
  --db-gold-light:  #e8dfc8;
  --db-ink:         #1a1710;
  --db-ink-3:       #6b5a3a;
  --db-ink-4:       #8b7d5e;
  --db-ink-5:       #a08f70;
  --db-label:       rgba(28, 16, 76, 0.4);
  --db-red:         #c0392b;
  --db-green:       #16a34a;
  background: var(--db-bg);
}

/* ─── Numeral label recipe ─────────────────────────────────────────────────── */
/* Apply above every Cormorant numeral */
.db-label {
  font-family: 'DM Sans', system-ui, sans-serif;
  font-size: 10px;
  letter-spacing: 3px;
  text-transform: uppercase;
  color: var(--db-label);
  font-weight: 500;
  display: block;
  margin-bottom: 4px;
}

/* ─── Cormorant numeral base + size scale ──────────────────────────────────── */
.db-num {
  font-family: 'Cormorant Garamond', serif;
  font-weight: 300;
  letter-spacing: -1px;
  line-height: 0.95;
  font-variant-numeric: tabular-nums;
  display: block;
}
.db-num-hero  { font-size: 86px; }
.db-num-warn  { font-size: 42px; font-weight: 400; }
.db-num-ring  { font-size: 34px; }
.db-num-mini  { font-size: 22px; }
.db-num-card  { font-size: 20px; font-weight: 500; }

/* ─── Editorial italic (narrative phrases only) ────────────────────────────── */
.db-editorial {
  font-family: 'Cormorant Garamond', serif;
  font-style: italic;
  font-weight: 300;
  line-height: 1.15;
  letter-spacing: 0;
}

/* ─── Topbar ───────────────────────────────────────────────────────────────── */
.db-topbar {
  background: var(--db-bg);
  border-bottom: 1px solid var(--db-border);
  padding: 9px 18px;
  display: flex;
  align-items: center;
  gap: 14px;
}
.db-search {
  background: var(--db-card);
  border: 1.5px solid var(--db-border);
  border-radius: 10px;
  padding: 9px 16px 9px 38px;
  font-size: 13px;
  color: var(--db-ink-3);
  flex: 1;
  max-width: 480px;
  outline: none;
  box-shadow: 0 1px 3px rgba(28, 16, 76, 0.06);
  font-family: 'DM Sans', system-ui, sans-serif;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='16' height='16' fill='none' viewBox='0 0 24 24'%3E%3Ccircle cx='11' cy='11' r='7' stroke='%23a08f70' stroke-width='2'/%3E%3Cpath d='m16.5 16.5 4 4' stroke='%23a08f70' stroke-width='2' stroke-linecap='round'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: 12px center;
}
.db-search::placeholder { color: var(--db-ink-5); }

/* ─── Stats bar ────────────────────────────────────────────────────────────── */
.db-stats-bar {
  background: var(--db-card);
  border: 1px solid var(--db-border);
  border-radius: 12px;
  display: grid;
  grid-template-columns: 1.5fr 1fr 1fr;
  overflow: hidden;
}
.db-stats-panel { padding: 16px 20px; }
.db-stats-panel + .db-stats-panel { border-left: 1px solid var(--db-muted); }
.db-stats-sub {
  font-family: 'DM Sans', system-ui, sans-serif;
  font-size: 11px;
  color: var(--db-ink-5);
  margin-top: 6px;
}
.db-progress-track { height: 3px; background: var(--db-muted); border-radius: 2px; margin-top: 10px; }
.db-progress-fill  { height: 3px; background: var(--db-gold);  border-radius: 2px; transition: width 0.4s ease; }
.db-glance-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 5px 0;
  border-bottom: 1px solid var(--db-muted);
}
.db-glance-row:last-child { border-bottom: none; }
.db-glance-key {
  font-family: 'DM Sans', system-ui, sans-serif;
  font-size: 11px;
  color: var(--db-ink-5);
}

/* ─── Goals rings section ──────────────────────────────────────────────────── */
.db-goals-section {
  background: var(--db-card);
  border: 1px solid var(--db-border);
  border-radius: 12px;
  padding: 18px 20px;
  display: flex;
  align-items: center;
}
.db-goals-msg {
  flex: 1;
  padding-left: 24px;
  margin-left: 24px;
  border-left: 1px solid var(--db-muted);
}
.db-ring-sub {
  font-family: 'DM Sans', system-ui, sans-serif;
  font-size: 10px;
  color: var(--db-ink-5);
  margin-top: 3px;
  text-align: center;
}

/* ─── Customer cards ───────────────────────────────────────────────────────── */
.db-card-surface {
  background: var(--db-card);
  border: 1px solid var(--db-border);
  border-radius: 10px;
  overflow: hidden;
}
.db-card-live { border-color: var(--db-gold); }

@keyframes db-pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.35; } }

.db-live-badge {
  font-family: 'DM Sans', system-ui, sans-serif;
  font-size: 10px;
  font-weight: 700;
  color: var(--db-gold);
  letter-spacing: 0.5px;
  display: flex;
  align-items: center;
  gap: 4px;
  margin-bottom: 7px;
}
.db-live-dot {
  width: 6px; height: 6px;
  border-radius: 50%;
  background: var(--db-gold);
  animation: db-pulse 2s infinite;
  flex-shrink: 0;
}
.db-ci-badge {
  font-family: 'DM Sans', system-ui, sans-serif;
  font-size: 10px;
  font-weight: 600;
  color: var(--db-ink-5);
  display: flex;
  align-items: center;
  gap: 4px;
  margin-bottom: 7px;
}
.db-ci-dot { width: 6px; height: 6px; border-radius: 50%; background: var(--db-border); flex-shrink: 0; }

.db-tier {
  font-family: 'DM Sans', system-ui, sans-serif;
  font-size: 9px;
  background: var(--db-gold-light);
  border-radius: 3px;
  padding: 1px 5px;
  color: var(--db-ink-3);
  font-weight: 700;
  letter-spacing: 0.4px;
  margin-left: 5px;
  vertical-align: middle;
}
.db-tier-gold { background: var(--db-gold); color: #fff; }
.db-tier-new  { background: #d1fae5; color: #065f46; }

.db-svc-rows { padding: 8px 14px; border-top: 1px solid var(--db-muted); display: flex; flex-direction: column; gap: 5px; }
.db-svc-row  { display: flex; align-items: center; gap: 7px; border-radius: 7px; padding: 5px 8px; background: var(--db-bg); }

.db-svc-dot       { width: 7px; height: 7px; border-radius: 50%; flex-shrink: 0; }
.db-svc-dot-ip    { background: var(--db-gold); animation: db-pulse 2s infinite; }
.db-svc-dot-ci    { background: var(--db-border); }
.db-svc-dot-done  { background: var(--db-green); }

.db-svc-btn        { background: transparent; border: 1px solid var(--db-border); border-radius: 5px; width: 22px; height: 22px; cursor: pointer; display: inline-flex; align-items: center; justify-content: center; flex-shrink: 0; color: var(--db-ink-4); font-size: 10px; }
.db-svc-btn-start  { border-color: var(--db-gold);  color: var(--db-gold);  }
.db-svc-btn-finish { border-color: var(--db-green); color: var(--db-green); }

.db-svc-prog-bar  { height: 3px; background: var(--db-muted); border-radius: 2px; }
.db-svc-prog-fill { height: 3px; background: var(--db-gold);  border-radius: 2px; }
.db-prog-meta {
  display: flex;
  justify-content: space-between;
  font-family: 'DM Sans', system-ui, sans-serif;
  font-size: 9px;
  color: var(--db-ink-5);
  margin-top: 2px;
}
.db-card-footer { display: flex; justify-content: space-between; align-items: center; padding: 10px 14px; border-top: 1px solid var(--db-muted); }

/* ─── Badges (section header) ──────────────────────────────────────────────── */
.db-badge-gold {
  font-family: 'DM Sans', system-ui, sans-serif;
  font-size: 10px; font-weight: 700;
  border-radius: 20px; padding: 3px 9px; letter-spacing: 0.3px;
  background: var(--db-gold); color: #fff;
}
.db-badge-muted {
  font-family: 'DM Sans', system-ui, sans-serif;
  font-size: 10px; font-weight: 700;
  border-radius: 20px; padding: 3px 9px; letter-spacing: 0.3px;
  background: var(--db-card); color: var(--db-ink-4); border: 1px solid var(--db-border);
}

/* ─── Right sidebar ────────────────────────────────────────────────────────── */
.db-sidebar { width: 256px; flex-shrink: 0; border-left: 1px solid var(--db-border); display: flex; flex-direction: column; }
.db-sidebar-section { padding: 16px 14px; }
.db-sidebar-section + .db-sidebar-section { border-top: 1px solid var(--db-border); }

.db-appt-dot { width: 9px; height: 9px; border-radius: 50%; border: 2px solid var(--db-gold); background: var(--db-bg); flex-shrink: 0; margin-top: 4px; }
.db-appt-row { display: flex; align-items: flex-start; gap: 9px; padding: 10px 0; border-bottom: 1px solid var(--db-muted); }
.db-appt-row:last-child { border-bottom: none; }

.db-queue-lane-hd  { font-family: 'DM Sans', system-ui, sans-serif; font-size: 11px; font-weight: 700; color: var(--db-ink); padding-bottom: 3px; border-bottom: 1px solid var(--db-muted); margin-bottom: 2px; }
.db-queue-item     { background: var(--db-bg); border-radius: 6px; padding: 5px 8px; display: flex; align-items: center; gap: 6px; }
.db-q-dot          { width: 6px; height: 6px; border-radius: 50%; flex-shrink: 0; }
.db-q-dot-ip       { background: var(--db-gold); animation: db-pulse 2s infinite; }
.db-q-dot-ci       { background: var(--db-border); }
.db-q-dot-done     { background: var(--db-green); }
```

- [ ] **Step 2: Import `dashboard.css` in `globals.css`**

Add after the existing `@import` lines at the top of `frontend/src/app/globals.css`:
```css
@import "../styles/dashboard.css";
```

The file currently has:
```css
@import "tailwindcss";
@import "tw-animate-css";
@import "../styles/tokens.css";
@import "../styles/typography.css";
```

Add the new import so it becomes:
```css
@import "tailwindcss";
@import "tw-animate-css";
@import "../styles/tokens.css";
@import "../styles/typography.css";
@import "../styles/dashboard.css";
```

- [ ] **Step 3: Add Google Fonts to `layout.tsx`**

In `frontend/src/app/layout.tsx`, add inside `<head>` after the existing inline script:
```tsx
<link rel="preconnect" href="https://fonts.googleapis.com" />
<link
  href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;0,400;0,500;1,300;1,400&family=DM+Sans:wght@400;500;600;700;800&display=swap"
  rel="stylesheet"
/>
```

- [ ] **Step 4: Verify CSS loads without errors**

```bash
cd frontend && npm run dev
```

Open `http://localhost:3000` and confirm no CSS import errors in the console. Stop the server (`Ctrl+C`).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/styles/dashboard.css frontend/src/app/globals.css frontend/src/app/layout.tsx
git commit -m "feat: add dashboard.css scoped tokens and Cormorant Garamond/DM Sans fonts"
```

---

## Task 2: API — add `status?` param to `listAppointments`

**Files:**
- Modify: `frontend/src/lib/api/appointments.ts`

- [ ] **Step 1: Write the test first**

Create `frontend/src/lib/__tests__/appointments-api.test.ts`:
```ts
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { listAppointments } from '../api/appointments';

const mockGet = vi.fn();
vi.mock('../api-client', () => ({
  apiClient: { get: (...args: unknown[]) => mockGet(...args) },
}));

beforeEach(() => {
  mockGet.mockResolvedValue({ data: [] });
});

describe('listAppointments', () => {
  it('sends only date param when status is omitted', async () => {
    await listAppointments('2026-05-22');
    expect(mockGet).toHaveBeenCalledWith('/appointments', {
      params: { date: '2026-05-22' },
    });
  });

  it('includes status param when provided', async () => {
    await listAppointments('2026-05-22', 'scheduled');
    expect(mockGet).toHaveBeenCalledWith('/appointments', {
      params: { date: '2026-05-22', status: 'scheduled' },
    });
  });
});
```

- [ ] **Step 2: Run test — expect failure**

```bash
cd frontend && npm test -- --reporter verbose src/lib/__tests__/appointments-api.test.ts
```

Expected: FAIL — `listAppointments` doesn't accept a second param yet.

- [ ] **Step 3: Update `listAppointments` in `frontend/src/lib/api/appointments.ts`**

Replace the existing function:
```ts
export async function listAppointments(date: string): Promise<Appointment[]> {
  const { data } = await apiClient.get<Appointment[]>("/appointments", {
    params: { date },
  });
  return data;
}
```

With:
```ts
export async function listAppointments(
  date: string,
  status?: AppointmentStatus
): Promise<Appointment[]> {
  const params: Record<string, string> = { date };
  if (status) params.status = status;
  const { data } = await apiClient.get<Appointment[]>("/appointments", { params });
  return data;
}
```

- [ ] **Step 4: Run test — expect pass**

```bash
cd frontend && npm test -- --reporter verbose src/lib/__tests__/appointments-api.test.ts
```

Expected: PASS (2 tests).

- [ ] **Step 5: Confirm the appointments calendar page still compiles**

```bash
cd frontend && npx tsc --noEmit 2>&1 | grep appointments
```

Expected: no new errors related to `listAppointments`.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/lib/api/appointments.ts frontend/src/lib/__tests__/appointments-api.test.ts
git commit -m "feat: add optional status param to listAppointments"
```

---

## Task 3: New `StatsBar` component

**Files:**
- Create: `frontend/src/components/dashboard/stats-bar.tsx`
- Create: `frontend/src/components/dashboard/__tests__/stats-bar.test.tsx`

- [ ] **Step 1: Write the failing tests**

Create `frontend/src/components/dashboard/__tests__/stats-bar.test.tsx`:
```tsx
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
    expect(fill.style.width).toBe('24%'); // 497700/2000000 = 24.885 → 24%
  });
});
```

- [ ] **Step 2: Run test — expect failure**

```bash
cd frontend && npm test -- --reporter verbose src/components/dashboard/__tests__/stats-bar.test.tsx
```

Expected: FAIL — module not found.

- [ ] **Step 3: Create `frontend/src/components/dashboard/stats-bar.tsx`**

```tsx
'use client';

interface StatsBarProps {
  revenueToday: number;       // paise
  revenueTarget: number;      // paise
  revenueDeltaPaise: number;  // positive = ahead vs yesterday, negative = behind
  activeServices: number;
  checkedInWaiting: number;
  pendingBills: number;
  avgBillTodayPaise: number;  // paise; 0 if no bills yet
}

function formatRupees(paise: number): string {
  return `₹${Math.round(paise / 100).toLocaleString('en-IN')}`;
}

interface GlanceRowProps { label: string; value: string | number }
function GlanceRow({ label, value }: GlanceRowProps) {
  return (
    <div className="db-glance-row">
      <span className="db-glance-key">{label}</span>
      <span className="db-num db-num-mini">{value}</span>
    </div>
  );
}

export function StatsBar({
  revenueToday,
  revenueTarget,
  revenueDeltaPaise,
  activeServices,
  checkedInWaiting,
  pendingBills,
  avgBillTodayPaise,
}: StatsBarProps) {
  const pct = revenueTarget > 0
    ? Math.min(100, Math.round((revenueToday / revenueTarget) * 100))
    : 0;
  const toGo = Math.max(0, revenueTarget - revenueToday);
  const isAhead = revenueDeltaPaise >= 0;
  const deltaAbs = Math.abs(revenueDeltaPaise);

  return (
    <div className="db-stats-bar">
      {/* Panel 1: Revenue */}
      <div className="db-stats-panel">
        <span className="db-label">Today's Revenue</span>
        <span className="db-num db-num-hero">{formatRupees(revenueToday)}</span>
        <p className="db-stats-sub">
          <span style={{ color: isAhead ? 'var(--db-green)' : 'var(--db-red)', fontWeight: 600 }}>
            {isAhead ? '↑' : '↓'} {formatRupees(deltaAbs)}
          </span>
          {' '}vs same time yesterday
        </p>
        <div className="db-progress-track">
          <div className="db-progress-fill" style={{ width: `${pct}%` }} />
        </div>
        <p className="db-stats-sub" style={{ marginTop: 4 }}>
          {pct}% of {formatRupees(revenueTarget)} target · {formatRupees(toGo)} to go
        </p>
      </div>

      {/* Panel 2: Pace */}
      <div className="db-stats-panel">
        <span className="db-label">Pace</span>
        <span className="db-editorial" style={{ fontSize: 15, color: 'var(--db-ink-4)', display: 'block', marginBottom: 2 }}>
          {isAhead ? 'Ahead by' : 'Behind by'}
        </span>
        <span
          className="db-num db-num-warn"
          style={{ color: isAhead ? 'var(--db-green)' : 'var(--db-red)' }}
        >
          ~{formatRupees(deltaAbs)}
        </span>
        <p className="db-stats-sub" style={{ marginTop: 8 }}>
          {isAhead
            ? "You're tracking ahead of yesterday — keep the momentum."
            : 'Afternoon walk-ins typically close the gap on busy days.'}
        </p>
      </div>

      {/* Panel 3: Right Now (operational, no goal duplication) */}
      <div className="db-stats-panel">
        <span className="db-label">Right Now</span>
        <GlanceRow label="Active services" value={activeServices} />
        <GlanceRow label="Checked in, waiting" value={checkedInWaiting} />
        <GlanceRow label="Pending bills" value={pendingBills} />
        <GlanceRow
          label="Avg. bill today"
          value={avgBillTodayPaise > 0 ? formatRupees(avgBillTodayPaise) : '—'}
        />
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Run tests — expect pass**

```bash
cd frontend && npm test -- --reporter verbose src/components/dashboard/__tests__/stats-bar.test.tsx
```

Expected: PASS (5 tests).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/dashboard/stats-bar.tsx frontend/src/components/dashboard/__tests__/stats-bar.test.tsx
git commit -m "feat: add StatsBar component (3-panel: Revenue, Pace, Right Now)"
```

---

## Task 4: `GoalsRings` — SVG rings with contextual message

**Files:**
- Modify: `frontend/src/components/dashboard/radial-goal-progress.tsx`
- Create: `frontend/src/components/dashboard/__tests__/radial-goal-progress.test.tsx`

The existing `RadialGoalProgress` and `DualRadialGoals` exports are **kept** to avoid breaking any existing references. `GoalsRings` is added as a new named export.

- [ ] **Step 1: Write the failing test**

Create `frontend/src/components/dashboard/__tests__/radial-goal-progress.test.tsx`:
```tsx
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
```

- [ ] **Step 2: Run test — expect failure**

```bash
cd frontend && npm test -- --reporter verbose src/components/dashboard/__tests__/radial-goal-progress.test.tsx
```

Expected: FAIL — `GoalsRings` not exported.

- [ ] **Step 3: Append `GoalsRings` to `frontend/src/components/dashboard/radial-goal-progress.tsx`**

Keep all existing code, then add at the bottom of the file:

```tsx
// SVG ring circumference for r=35 on 84×84 viewBox: 2π×35 ≈ 219.9
const CIRCUM = 219.9;

function svgDash(pct: number) {
  const fill = Math.min(100, pct) / 100 * CIRCUM;
  return `${fill} ${CIRCUM - fill}`;
}

function getAssessment(pct: number): string {
  if (pct < 20) return 'time to push hard this afternoon.';
  if (pct < 40) return 'within striking range of today\'s target.';
  return 'on track for a strong finish.';
}

interface RingItemProps {
  label: string;
  pct: number;
  value: string;
  color: string;
}

function RingItem({ label, pct, value, color }: RingItemProps) {
  const dash = svgDash(pct);
  // Start at 12 o'clock: dashoffset shifts arc by quarter-circumference
  const offset = CIRCUM * 0.25;
  return (
    <div data-ring style={{ textAlign: 'center', width: 86 }}>
      <div style={{ width: 84, height: 84, position: 'relative', margin: '0 auto 8px', display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column' }}>
        <svg style={{ position: 'absolute', top: 0, left: 0 }} width="84" height="84" viewBox="0 0 84 84">
          <circle cx="42" cy="42" r="35" fill="none" stroke="var(--db-muted)" strokeWidth="6" />
          <circle
            cx="42" cy="42" r="35" fill="none"
            stroke={color} strokeWidth="6"
            strokeDasharray={dash}
            strokeDashoffset={offset}
            strokeLinecap="round"
          />
        </svg>
        <span className="db-num db-num-ring">{pct}</span>
      </div>
      <span className="db-label" style={{ textAlign: 'center' }}>{label}</span>
      <div className="db-ring-sub">{value}</div>
    </div>
  );
}

interface GoalsRingsProps {
  revenueTarget: number;    // paise
  currentRevenue: number;   // paise
  servicesTarget: number;
  currentServices: number;
  customersTarget: number;
  currentCustomers: number;
  weekdayName: string;
  revenuePct: number;       // pre-computed, same as used in StatsBar
}

export function GoalsRings({
  revenueTarget,
  currentRevenue,
  servicesTarget,
  currentServices,
  customersTarget,
  currentCustomers,
  weekdayName,
  revenuePct,
}: GoalsRingsProps) {
  const svcPct = servicesTarget > 0
    ? Math.min(100, Math.round((currentServices / servicesTarget) * 100))
    : 0;
  const custPct = customersTarget > 0
    ? Math.min(100, Math.round((currentCustomers / customersTarget) * 100))
    : 0;
  const formatRupees = (p: number) => `₹${Math.round(p / 100).toLocaleString('en-IN')}`;
  const assessment = getAssessment(revenuePct);

  return (
    <div className="db-goals-section">
      <div style={{ display: 'flex', gap: 16, flexShrink: 0 }}>
        <RingItem
          label="Revenue"
          pct={revenuePct}
          value={formatRupees(currentRevenue)}
          color="var(--db-gold)"
        />
        <RingItem
          label="Services"
          pct={svcPct}
          value={`${currentServices} / ${servicesTarget}`}
          color="var(--db-gold)"
        />
        <RingItem
          label="Customers"
          pct={custPct}
          value={`${currentCustomers} / ${customersTarget}`}
          color="var(--db-ink-3)"
        />
      </div>
      <div className="db-goals-msg">
        <span
          className="db-editorial"
          style={{ fontSize: 20, color: 'var(--db-ink)', display: 'block', marginBottom: 8 }}
        >
          {revenuePct < 40 ? 'Three rings to close.' : 'Looking strong today.'}
        </span>
        <p style={{ fontFamily: "'DM Sans', system-ui, sans-serif", fontSize: 12, color: 'var(--db-ink-4)', lineHeight: 1.7 }}>
          At <strong style={{ color: 'var(--db-ink)' }}>{revenuePct}%</strong> of today's revenue target
          with <strong style={{ color: 'var(--db-ink)' }}>{currentServices} services</strong> and{' '}
          <strong style={{ color: 'var(--db-ink)' }}>{currentCustomers} customers</strong> so far
          this <strong style={{ color: 'var(--db-ink)' }}>{weekdayName}</strong> — {assessment}
        </p>
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Run tests — expect pass**

```bash
cd frontend && npm test -- --reporter verbose src/components/dashboard/__tests__/radial-goal-progress.test.tsx
```

Expected: PASS (5 tests).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/dashboard/radial-goal-progress.tsx frontend/src/components/dashboard/__tests__/radial-goal-progress.test.tsx
git commit -m "feat: add GoalsRings component with SVG rings and contextual message"
```

---

## Task 5: Restyle `ActiveCustomerCard`

**Files:**
- Modify: `frontend/src/components/dashboard/active-customer-card.tsx`
- Modify: `frontend/src/components/dashboard/__tests__/active-customer-card.test.tsx`

This is a **visual restyle only** — no logic changes. All `apiClient.post` calls, RBAC checks, and `onCheckout`/`onRefresh` callbacks remain identical.

- [ ] **Step 1: Update the existing test to match new class names**

The existing test checks for class names like `bg-info-fg`, `bg-warning-fg`. The restyle replaces these with `db-svc-dot-ci` and `db-svc-dot-ip`. Update `frontend/src/components/dashboard/__tests__/active-customer-card.test.tsx`:

```tsx
import { render, fireEvent } from '@testing-library/react';
import { ActiveCustomerCard } from '../active-customer-card';
import { describe, it, expect, vi, beforeEach } from 'vitest';

vi.mock('@/stores/auth-store', () => ({
  useAuthStore: () => ({ user: { role: 'owner', id: 'u1' } }),
}));
vi.mock('@/lib/api-client', () => ({
  apiClient: { post: vi.fn().mockResolvedValue({}) },
}));
vi.mock('sonner', () => ({ toast: { success: vi.fn(), error: vi.fn() } }));

const makeSession = (status: string, allCompleted = false) => ({
  session_id: 's1',
  customer_name: 'John Doe',
  customer_phone: '9999999999',
  customer_id: null,
  walkins: [{
    id: 'w1',
    ticket_number: 'T1',
    customer_name: 'John Doe',
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
  all_completed: allCompleted,
});

describe('ActiveCustomerCard', () => {
  const mockOnCheckout = vi.fn();
  const mockOnRefresh = vi.fn();
  beforeEach(() => { vi.clearAllMocks(); });

  it('renders customer name', () => {
    const { getByText } = render(
      <ActiveCustomerCard session={makeSession('in_progress')} onCheckout={mockOnCheckout} onRefresh={mockOnRefresh} />
    );
    expect(getByText('John Doe')).toBeTruthy();
  });

  it('shows LIVE badge for in_progress session', () => {
    const { getByText } = render(
      <ActiveCustomerCard session={makeSession('in_progress')} onCheckout={mockOnCheckout} />
    );
    expect(getByText('LIVE')).toBeTruthy();
  });

  it('shows CHECKED IN badge for checked_in session', () => {
    const { getByText } = render(
      <ActiveCustomerCard session={makeSession('checked_in')} onCheckout={mockOnCheckout} />
    );
    expect(getByText(/CHECKED IN/)).toBeTruthy();
  });

  it('uses db-svc-dot-ip class for in_progress walkin', () => {
    const { container } = render(
      <ActiveCustomerCard session={makeSession('in_progress')} onCheckout={mockOnCheckout} />
    );
    expect(container.querySelector('.db-svc-dot-ip')).not.toBeNull();
  });

  it('uses db-svc-dot-ci class for checked_in walkin', () => {
    const { container } = render(
      <ActiveCustomerCard session={makeSession('checked_in')} onCheckout={mockOnCheckout} />
    );
    expect(container.querySelector('.db-svc-dot-ci')).not.toBeNull();
  });

  it('disables checkout button when not all_completed', () => {
    const { getByRole } = render(
      <ActiveCustomerCard session={makeSession('in_progress', false)} onCheckout={mockOnCheckout} />
    );
    expect((getByRole('button', { name: /checkout/i }) as HTMLButtonElement).disabled).toBe(true);
  });

  it('enables checkout when all_completed', () => {
    const { getByRole } = render(
      <ActiveCustomerCard session={makeSession('completed', true)} onCheckout={mockOnCheckout} />
    );
    expect((getByRole('button', { name: /checkout/i }) as HTMLButtonElement).disabled).toBe(false);
  });

  it('calls onCheckout with session_id when checkout clicked', () => {
    const { getByRole } = render(
      <ActiveCustomerCard session={makeSession('completed', true)} onCheckout={mockOnCheckout} />
    );
    fireEvent.click(getByRole('button', { name: /checkout/i }));
    expect(mockOnCheckout).toHaveBeenCalledWith('s1');
  });
});
```

- [ ] **Step 2: Run test — expect failure** (old class names still in component)

```bash
cd frontend && npm test -- --reporter verbose src/components/dashboard/__tests__/active-customer-card.test.tsx
```

Expected: some tests fail on class name assertions.

- [ ] **Step 3: Replace `active-customer-card.tsx` with restyled version**

Fully replace the file content:

```tsx
'use client';

import { apiClient } from '@/lib/api-client';
import { toast } from 'sonner';
import { useAuthStore } from '@/stores/auth-store';
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
  status: string;
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

interface ActiveCustomerCardProps {
  session: CustomerSession;
  onCheckout: (sessionId: string) => void;
  onRefresh?: () => void;
}

function formatRupees(paise: number) {
  return `₹${(paise / 100).toLocaleString('en-IN')}`;
}

function dotClass(status: string): string {
  if (status === 'in_progress') return 'db-svc-dot db-svc-dot-ip';
  if (status === 'completed')   return 'db-svc-dot db-svc-dot-done';
  return 'db-svc-dot db-svc-dot-ci';
}

export function ActiveCustomerCard({ session, onCheckout, onRefresh }: ActiveCustomerCardProps) {
  const { user } = useAuthStore();
  const canManage = user?.role === 'owner' || user?.role === 'receptionist';
  const isAllCheckedIn = session.walkins.every(w => w.status === 'checked_in');
  const isLive = session.walkins.some(w => w.status === 'in_progress');

  const handleStart = async (walkinId: string) => {
    try {
      await apiClient.post(`/appointments/walkins/${walkinId}/start`);
      toast.success('Service started');
      onRefresh?.();
    } catch (err: any) {
      toast.error(err.response?.data?.detail ?? 'Failed to start service');
    }
  };

  const handleComplete = async (walkinId: string) => {
    try {
      await apiClient.post(`/appointments/walkins/${walkinId}/complete`);
      toast.success('Service completed');
      onRefresh?.();
    } catch (err: any) {
      toast.error(err.response?.data?.detail ?? 'Failed to complete service');
    }
  };

  return (
    <div className={`db-card-surface${isLive ? ' db-card-live' : ''}`}>
      {/* Card header */}
      <div style={{ padding: '12px 14px 10px' }}>
        {isLive ? (
          <div className="db-live-badge">
            <span className="db-live-dot" />
            LIVE
          </div>
        ) : (
          <div className="db-ci-badge">
            <span className="db-ci-dot" />
            CHECKED IN · WAITING
          </div>
        )}
        <div style={{ fontFamily: "'DM Sans', system-ui, sans-serif", fontSize: 14, fontWeight: 700, color: 'var(--db-ink)' }}>
          {titleCase(session.customer_name)}
        </div>
        <div style={{ fontFamily: "'DM Sans', system-ui, sans-serif", fontSize: 10, color: 'var(--db-ink-5)', marginTop: 1 }}>
          {session.customer_phone}
        </div>
        <div style={{ fontFamily: "'DM Sans', system-ui, sans-serif", fontSize: 11, color: 'var(--db-ink-4)', marginTop: 3 }}>
          {session.time_since_checkin}m ago
        </div>
      </div>

      {/* Per-service rows */}
      <div className="db-svc-rows">
        {session.walkins.map((walkin) => (
          <div key={walkin.id} className="db-svc-row">
            <span className={dotClass(walkin.status)} />
            <span style={{ flex: 1, fontFamily: "'DM Sans', system-ui, sans-serif", fontSize: 11, fontWeight: 600, color: 'var(--db-ink)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {walkin.service.name}
            </span>
            <span className="db-num" style={{ fontSize: 14, fontWeight: 400, color: 'var(--db-ink-3)', flexShrink: 0, letterSpacing: '-0.5px', fontVariantNumeric: 'tabular-nums' }}>
              {formatRupees(walkin.service.base_price)}
            </span>
            {canManage && walkin.status === 'checked_in' && (
              <button
                className="db-svc-btn db-svc-btn-start"
                title="Start service"
                onClick={() => handleStart(walkin.id)}
              >
                ▶
              </button>
            )}
            {canManage && walkin.status === 'in_progress' && (
              <button
                className="db-svc-btn db-svc-btn-finish"
                title="Complete service"
                onClick={() => handleComplete(walkin.id)}
              >
                ✓
              </button>
            )}
          </div>
        ))}
      </div>

      {/* Footer */}
      <div className="db-card-footer">
        <div>
          <span className="db-label">Total</span>
          <span className="db-num db-num-card">{formatRupees(session.total_amount)}</span>
        </div>
        {isAllCheckedIn ? (
          <button
            style={{ background: 'var(--db-gold)', color: '#fff', border: 'none', borderRadius: 7, padding: '6px 12px', fontSize: 11, fontWeight: 700, cursor: 'pointer', fontFamily: "'DM Sans', system-ui, sans-serif" }}
            onClick={() => onRefresh?.()}
          >
            Start Services
          </button>
        ) : (
          <button
            style={{ background: session.all_completed ? 'var(--db-ink)' : 'var(--db-border)', color: session.all_completed ? '#fff' : 'var(--db-ink-5)', border: 'none', borderRadius: 7, padding: '6px 12px', fontSize: 11, fontWeight: 700, cursor: session.all_completed ? 'pointer' : 'not-allowed', fontFamily: "'DM Sans', system-ui, sans-serif" }}
            disabled={!session.all_completed}
            onClick={() => onCheckout(session.session_id)}
            aria-label="End and checkout"
          >
            End & Checkout
          </button>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Run tests — expect pass**

```bash
cd frontend && npm test -- --reporter verbose src/components/dashboard/__tests__/active-customer-card.test.tsx
```

Expected: PASS (8 tests).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/dashboard/active-customer-card.tsx frontend/src/components/dashboard/__tests__/active-customer-card.test.tsx
git commit -m "feat: restyle ActiveCustomerCard with warm visual language and per-service controls"
```

---

## Task 6: `ServiceQueue` sidebar variant

**Files:**
- Modify: `frontend/src/components/dashboard/service-queue.tsx`
- Modify: `frontend/src/components/dashboard/__tests__/service-queue.test.tsx`

- [ ] **Step 1: Add sidebar variant test**

Append to `frontend/src/components/dashboard/__tests__/service-queue.test.tsx`:

```tsx
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
});
```

- [ ] **Step 2: Run test — expect failure**

```bash
cd frontend && npm test -- --reporter verbose src/components/dashboard/__tests__/service-queue.test.tsx
```

Expected: FAIL on `variant="sidebar"` tests.

- [ ] **Step 3: Add sidebar variant to `service-queue.tsx`**

Update the `ServiceQueueProps` interface and component:

```tsx
interface ServiceQueueProps {
  sessions: CustomerSession[];
  variant?: 'default' | 'sidebar';
}

export function ServiceQueue({ sessions, variant = 'default' }: ServiceQueueProps) {
  const lanes = buildLanes(sessions);

  if (lanes.length === 0) {
    return (
      <div className={variant === 'sidebar' ? '' : 'rounded-xl bg-surface-card border border-border-subtle p-6'} style={{ textAlign: 'center', padding: variant === 'sidebar' ? '8px 0' : undefined }}>
        <p className="text-sm text-text-muted">No active services</p>
      </div>
    );
  }

  if (variant === 'sidebar') {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        {lanes.map((lane) => (
          <div key={lane.staffId} style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
            <div className="db-queue-lane-hd">{lane.staffName}</div>
            {lane.items.map((item) => (
              <div key={item.walkinId} className="db-queue-item">
                <span
                  className={`db-q-dot ${
                    item.status === 'in_progress' ? 'db-q-dot-ip' :
                    item.status === 'completed'   ? 'db-q-dot-done' : 'db-q-dot-ci'
                  }`}
                />
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontFamily: "'DM Sans', system-ui, sans-serif", fontSize: 10, fontWeight: 600, color: 'var(--db-ink)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {item.serviceName}
                  </div>
                  <div style={{ fontFamily: "'DM Sans', system-ui, sans-serif", fontSize: 9, color: 'var(--db-ink-5)' }}>
                    {item.customerName}
                  </div>
                </div>
                <span className="db-num" style={{ fontSize: 14, fontWeight: 300, color: 'var(--db-ink-5)', flexShrink: 0, letterSpacing: '-0.5px', fontVariantNumeric: 'tabular-nums' }}>
                  {elapsedMinutes(item.checkedInAt)}m
                </span>
              </div>
            ))}
          </div>
        ))}
      </div>
    );
  }

  // Default variant (existing grid layout — unchanged)
  const colCount = Math.min(lanes.length, 3);
  return (
    <div className="rounded-xl bg-surface-card border border-border-subtle p-4">
      <h3 className="text-xs font-medium text-text-secondary uppercase tracking-wide mb-3">
        Service Queue
      </h3>
      <div className="grid gap-3" style={{ gridTemplateColumns: `repeat(${colCount}, minmax(0, 1fr))` }}>
        {lanes.map((lane) => (
          <div key={lane.staffId} className="flex flex-col gap-2">
            <div className="text-xs font-semibold text-text-primary truncate pb-1 border-b border-border-subtle">
              {lane.staffName}
            </div>
            {lane.items.map((item) => (
              <div key={item.walkinId} className="flex items-start gap-2 rounded-lg bg-surface-row p-2">
                <span className="mt-1 shrink-0">
                  <span className={`block h-2 w-2 rounded-full ${STATUS_DOT[item.status] ?? 'bg-text-muted'}`} />
                </span>
                <div className="min-w-0 flex-1">
                  <p className="text-xs font-medium text-text-primary truncate">{item.serviceName}</p>
                  <p className="text-[10px] text-text-secondary truncate">{item.customerName}</p>
                </div>
                <span className="shrink-0 flex items-center gap-0.5 text-[10px] text-text-muted">
                  <Clock className="h-3 w-3" aria-hidden="true" />
                  {elapsedMinutes(item.checkedInAt)}m
                </span>
              </div>
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Run all service-queue tests — expect pass**

```bash
cd frontend && npm test -- --reporter verbose src/components/dashboard/__tests__/service-queue.test.tsx
```

Expected: PASS (5 tests including the 2 new ones).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/dashboard/service-queue.tsx frontend/src/components/dashboard/__tests__/service-queue.test.tsx
git commit -m "feat: add sidebar variant to ServiceQueue for vertical lane layout"
```

---

## Task 7: New `CheckInDialog`

**Files:**
- Create: `frontend/src/components/dashboard/checkin-dialog.tsx`
- Create: `frontend/src/components/dashboard/__tests__/checkin-dialog.test.tsx`

- [ ] **Step 1: Write the failing test**

Create `frontend/src/components/dashboard/__tests__/checkin-dialog.test.tsx`:
```tsx
import { render, fireEvent, waitFor } from '@testing-library/react';
import { CheckInDialog } from '../checkin-dialog';
import { describe, it, expect, vi, beforeEach } from 'vitest';

const mockCheckIn = vi.fn();
vi.mock('@/lib/api/appointments', () => ({
  checkInAppointment: (...args: unknown[]) => mockCheckIn(...args),
}));
vi.mock('sonner', () => ({ toast: { success: vi.fn(), error: vi.fn() } }));

const appt = {
  id: 'a1',
  customer_name: 'Priya Menon',
  scheduled_at: '2026-05-22T13:30:00+05:30',
};

describe('CheckInDialog', () => {
  const onCheckedIn = vi.fn();
  const onOpenChange = vi.fn();

  beforeEach(() => { vi.clearAllMocks(); mockCheckIn.mockResolvedValue({}); });

  it('renders customer name', () => {
    const { getByText } = render(
      <CheckInDialog open appointment={appt} staffName="Aman" serviceName="Haircut" onCheckedIn={onCheckedIn} onOpenChange={onOpenChange} />
    );
    expect(getByText('Priya Menon')).toBeTruthy();
  });

  it('shows service and staff name', () => {
    const { getByText } = render(
      <CheckInDialog open appointment={appt} staffName="Aman" serviceName="Haircut" onCheckedIn={onCheckedIn} onOpenChange={onOpenChange} />
    );
    expect(getByText('Haircut')).toBeTruthy();
    expect(getByText(/Aman/)).toBeTruthy();
  });

  it('calls checkInAppointment with appointment id on confirm', async () => {
    const { getByRole } = render(
      <CheckInDialog open appointment={appt} staffName="Aman" serviceName="Haircut" onCheckedIn={onCheckedIn} onOpenChange={onOpenChange} />
    );
    fireEvent.click(getByRole('button', { name: /check in/i }));
    await waitFor(() => expect(mockCheckIn).toHaveBeenCalledWith('a1'));
  });

  it('calls onCheckedIn with id after successful check-in', async () => {
    const { getByRole } = render(
      <CheckInDialog open appointment={appt} staffName="Aman" serviceName="Haircut" onCheckedIn={onCheckedIn} onOpenChange={onOpenChange} />
    );
    fireEvent.click(getByRole('button', { name: /check in/i }));
    await waitFor(() => expect(onCheckedIn).toHaveBeenCalledWith('a1'));
  });

  it('does not render when open is false', () => {
    const { queryByText } = render(
      <CheckInDialog open={false} appointment={appt} staffName="Aman" serviceName="Haircut" onCheckedIn={onCheckedIn} onOpenChange={onOpenChange} />
    );
    expect(queryByText('Priya Menon')).toBeNull();
  });
});
```

- [ ] **Step 2: Run test — expect failure**

```bash
cd frontend && npm test -- --reporter verbose src/components/dashboard/__tests__/checkin-dialog.test.tsx
```

Expected: FAIL — module not found.

- [ ] **Step 3: Create `frontend/src/components/dashboard/checkin-dialog.tsx`**

```tsx
'use client';

import { useState } from 'react';
import { format, parseISO } from 'date-fns';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogBody, DialogFooter,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { checkInAppointment } from '@/lib/api/appointments';
import { toast } from 'sonner';

interface AppointmentMinimal {
  id: string;
  customer_name: string;
  scheduled_at: string;
}

interface CheckInDialogProps {
  open: boolean;
  appointment: AppointmentMinimal | null;
  staffName: string;
  serviceName: string;
  onCheckedIn: (id: string) => void;
  onOpenChange: (open: boolean) => void;
}

export function CheckInDialog({
  open,
  appointment,
  staffName,
  serviceName,
  onCheckedIn,
  onOpenChange,
}: CheckInDialogProps) {
  const [loading, setLoading] = useState(false);

  if (!appointment) return null;

  const scheduledTime = format(parseISO(appointment.scheduled_at), 'h:mm a');

  const handleCheckIn = async () => {
    setLoading(true);
    try {
      await checkInAppointment(appointment.id);
      toast.success(`${appointment.customer_name} checked in`);
      onCheckedIn(appointment.id);
      onOpenChange(false);
    } catch {
      toast.error('Failed to check in — please try again');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent size="sm">
        <DialogHeader>
          <DialogTitle>Check In Customer</DialogTitle>
        </DialogHeader>
        <DialogBody>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div>
              <span className="db-label">Customer</span>
              <p style={{ fontFamily: "'DM Sans', system-ui, sans-serif", fontSize: 16, fontWeight: 700, color: 'var(--db-ink)' }}>
                {appointment.customer_name}
              </p>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
              <div>
                <span className="db-label">Service</span>
                <p style={{ fontFamily: "'DM Sans', system-ui, sans-serif", fontSize: 13, color: 'var(--db-ink-3)', marginTop: 2 }}>
                  {serviceName}
                </p>
              </div>
              <div>
                <span className="db-label">With</span>
                <p style={{ fontFamily: "'DM Sans', system-ui, sans-serif", fontSize: 13, color: 'var(--db-ink-3)', marginTop: 2 }}>
                  {staffName}
                </p>
              </div>
            </div>
            <div>
              <span className="db-label">Scheduled</span>
              <p style={{ fontFamily: "'Cormorant Garamond', serif", fontSize: 28, fontWeight: 300, letterSpacing: '-1px', color: 'var(--db-ink)', lineHeight: 1, fontVariantNumeric: 'tabular-nums' }}>
                {scheduledTime}
              </p>
            </div>
          </div>
        </DialogBody>
        <DialogFooter>
          <Button variant="ghost" onClick={() => onOpenChange(false)} disabled={loading}>
            Cancel
          </Button>
          <Button onClick={handleCheckIn} disabled={loading}>
            {loading ? 'Checking in…' : 'Check In'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
```

- [ ] **Step 4: Run tests — expect pass**

```bash
cd frontend && npm test -- --reporter verbose src/components/dashboard/__tests__/checkin-dialog.test.tsx
```

Expected: PASS (5 tests).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/dashboard/checkin-dialog.tsx frontend/src/components/dashboard/__tests__/checkin-dialog.test.tsx
git commit -m "feat: add CheckInDialog for quick appointment check-in from dashboard"
```

---

## Task 8: New `UpNextPanel`

**Files:**
- Create: `frontend/src/components/dashboard/up-next-panel.tsx`
- Create: `frontend/src/components/dashboard/__tests__/up-next-panel.test.tsx`

- [ ] **Step 1: Write the failing test**

Create `frontend/src/components/dashboard/__tests__/up-next-panel.test.tsx`:
```tsx
import { render, waitFor } from '@testing-library/react';
import { UpNextPanel } from '../up-next-panel';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { format, addMinutes } from 'date-fns';

const mockListAppointments = vi.fn();
const mockListActiveStaff = vi.fn();
const mockListServices = vi.fn();

vi.mock('@/lib/api/appointments', () => ({
  listAppointments: (...args: unknown[]) => mockListAppointments(...args),
  listActiveStaff:  (...args: unknown[]) => mockListActiveStaff(...args),
  listServices:     (...args: unknown[]) => mockListServices(...args),
}));

function makeAppt(minutesFromNow: number, id = 'a1') {
  return {
    id,
    ticket_number: 'T1',
    visit_id: null,
    customer_id: null,
    customer_name: 'Test Customer',
    customer_phone: '9999999999',
    service_id: 'svc1',
    assigned_staff_id: 'st1',
    scheduled_at: addMinutes(new Date(), minutesFromNow).toISOString(),
    duration_minutes: 30,
    status: 'scheduled' as const,
    booking_notes: null,
    service_notes: null,
    checked_in_at: null,
    started_at: null,
    completed_at: null,
    cancelled_at: null,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  };
}

beforeEach(() => {
  vi.clearAllMocks();
  mockListActiveStaff.mockResolvedValue([{ id: 'st1', display_name: 'Aman', specialization: null, is_active: true, is_service_provider: true }]);
  mockListServices.mockResolvedValue([{ id: 'svc1', name: 'Haircut', base_price: 50000, duration_minutes: 30, category_name: 'Hair' }]);
});

describe('UpNextPanel', () => {
  it('shows loading state initially', () => {
    mockListAppointments.mockResolvedValue([makeAppt(30)]);
    const { getByText } = render(<UpNextPanel />);
    expect(getByText(/loading/i)).toBeTruthy();
  });

  it('renders a customer name after data loads', async () => {
    mockListAppointments.mockResolvedValue([makeAppt(30)]);
    const { getByText } = render(<UpNextPanel />);
    await waitFor(() => expect(getByText('Test Customer')).toBeTruthy());
  });

  it('filters out past appointments', async () => {
    mockListAppointments.mockResolvedValue([makeAppt(-10), makeAppt(30)]);
    const { getAllByText } = render(<UpNextPanel />);
    await waitFor(() => {
      expect(getAllByText('Test Customer').length).toBe(1); // only future one shown
    });
  });

  it('caps display at 5 appointments', async () => {
    const appts = Array.from({ length: 7 }, (_, i) => makeAppt(i * 10 + 5, `a${i}`));
    mockListAppointments.mockResolvedValue(appts);
    const { getAllByText } = render(<UpNextPanel />);
    await waitFor(() => {
      expect(getAllByText('Test Customer').length).toBe(5);
    });
  });

  it('shows empty state when no upcoming appointments', async () => {
    mockListAppointments.mockResolvedValue([makeAppt(-5)]);
    const { getByText } = render(<UpNextPanel />);
    await waitFor(() => expect(getByText(/no appointments/i)).toBeTruthy());
  });

  it('shows service name from lookup', async () => {
    mockListAppointments.mockResolvedValue([makeAppt(30)]);
    const { getByText } = render(<UpNextPanel />);
    await waitFor(() => expect(getByText('Haircut')).toBeTruthy());
  });

  it('shows staff name from lookup', async () => {
    mockListAppointments.mockResolvedValue([makeAppt(30)]);
    const { getByText } = render(<UpNextPanel />);
    await waitFor(() => expect(getByText(/Aman/)).toBeTruthy());
  });
});
```

- [ ] **Step 2: Run test — expect failure**

```bash
cd frontend && npm test -- --reporter verbose src/components/dashboard/__tests__/up-next-panel.test.tsx
```

Expected: FAIL — module not found.

- [ ] **Step 3: Create `frontend/src/components/dashboard/up-next-panel.tsx`**

```tsx
'use client';

import { useState, useEffect, useCallback } from 'react';
import { format, parseISO, differenceInMinutes } from 'date-fns';
import {
  listAppointments,
  listActiveStaff,
  listServices,
  type Appointment,
  type StaffMember,
  type ServiceItem,
} from '@/lib/api/appointments';
import { CheckInDialog } from './checkin-dialog';

const MAX_VISIBLE = 5;
const POLL_INTERVAL_MS = 2 * 60 * 1000;

interface EnrichedAppointment {
  appt: Appointment;
  staffName: string;
  serviceName: string;
  minsUntil: number;
}

function enrich(
  appointments: Appointment[],
  staffMap: Map<string, string>,
  serviceMap: Map<string, string>,
  now: Date
): EnrichedAppointment[] {
  return appointments
    .filter(a => a.status === 'scheduled' && differenceInMinutes(parseISO(a.scheduled_at), now) > -1)
    .sort((a, b) => parseISO(a.scheduled_at).getTime() - parseISO(b.scheduled_at).getTime())
    .slice(0, MAX_VISIBLE)
    .map(appt => ({
      appt,
      staffName: staffMap.get(appt.assigned_staff_id ?? '') ?? 'Unassigned',
      serviceName: serviceMap.get(appt.service_id) ?? 'Service',
      minsUntil: Math.max(0, differenceInMinutes(parseISO(appt.scheduled_at), now)),
    }));
}

export function UpNextPanel() {
  const [items, setItems] = useState<EnrichedAppointment[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [staffMap, setStaffMap] = useState<Map<string, string>>(new Map());
  const [serviceMap, setServiceMap] = useState<Map<string, string>>(new Map());
  const [selectedAppt, setSelectedAppt] = useState<EnrichedAppointment | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);

  const fetchData = useCallback(async () => {
    try {
      const today = format(new Date(), 'yyyy-MM-dd');
      const [appts, staff, services] = await Promise.all([
        listAppointments(today, 'scheduled'),
        listActiveStaff(),
        listServices(),
      ]);
      const sMap = new Map<string, string>(staff.map((s: StaffMember) => [s.id, s.display_name]));
      const svMap = new Map<string, string>(services.map((s: ServiceItem) => [s.id, s.name]));
      setStaffMap(sMap);
      setServiceMap(svMap);
      setItems(enrich(appts, sMap, svMap, new Date()));
      setError(null);
    } catch {
      setError('Could not load upcoming appointments');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
    const poll = setInterval(fetchData, POLL_INTERVAL_MS);
    return () => clearInterval(poll);
  }, [fetchData]);

  // Refresh countdowns every minute
  useEffect(() => {
    const tick = setInterval(() => {
      setItems(prev => prev.map(i => ({
        ...i,
        minsUntil: Math.max(0, differenceInMinutes(parseISO(i.appt.scheduled_at), new Date())),
      })));
    }, 60_000);
    return () => clearInterval(tick);
  }, []);

  const handleCheckedIn = (id: string) => {
    setItems(prev => prev.filter(i => i.appt.id !== id));
  };

  const handleRowClick = (item: EnrichedAppointment) => {
    setSelectedAppt(item);
    setDialogOpen(true);
  };

  return (
    <>
      <div className="db-sidebar-section">
        <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', marginBottom: 2 }}>
          <span className="db-upnext-title">Up next</span>
          <span style={{ fontFamily: "'DM Sans', system-ui, sans-serif", fontSize: 12, color: 'var(--db-ink-5)' }}>
            {loading ? '' : `${items.length} today`}
          </span>
        </div>
        <span
          className="db-editorial"
          style={{ fontSize: 14, color: 'var(--db-ink-4)', display: 'block', marginBottom: 12 }}
        >
          The next guests through the door.
        </span>

        {loading && (
          <p style={{ fontFamily: "'DM Sans', system-ui, sans-serif", fontSize: 12, color: 'var(--db-ink-5)' }}>
            Loading…
          </p>
        )}

        {!loading && error && (
          <p style={{ fontFamily: "'DM Sans', system-ui, sans-serif", fontSize: 12, color: 'var(--db-red)' }}>
            {error}
          </p>
        )}

        {!loading && !error && items.length === 0 && (
          <p style={{ fontFamily: "'DM Sans', system-ui, sans-serif", fontSize: 12, color: 'var(--db-ink-5)', fontStyle: 'italic' }}>
            No appointments scheduled for the rest of today.
          </p>
        )}

        {!loading && items.map((item) => (
          <div
            key={item.appt.id}
            className="db-appt-row"
            style={{ cursor: 'pointer' }}
            onClick={() => handleRowClick(item)}
            role="button"
            tabIndex={0}
            onKeyDown={e => e.key === 'Enter' && handleRowClick(item)}
          >
            {/* Time column */}
            <div style={{ textAlign: 'center', minWidth: 40, flexShrink: 0 }}>
              <div className="db-num" style={{ fontSize: 17, fontWeight: 300, letterSpacing: '-0.5px', fontVariantNumeric: 'tabular-nums', color: 'var(--db-ink)', lineHeight: 1 }}>
                {format(parseISO(item.appt.scheduled_at), 'HH:mm')}
              </div>
              <div style={{ fontFamily: "'DM Sans', system-ui, sans-serif", fontSize: 10, color: 'var(--db-ink-5)', marginTop: 1 }}>
                in {item.minsUntil}m
              </div>
            </div>

            {/* Dot */}
            <div className="db-appt-dot" />

            {/* Info */}
            <div>
              <div style={{ fontFamily: "'DM Sans', system-ui, sans-serif", fontSize: 12, fontWeight: 700, color: 'var(--db-ink)' }}>
                {item.appt.customer_name}
              </div>
              <div style={{ fontFamily: "'DM Sans', system-ui, sans-serif", fontSize: 11, color: 'var(--db-ink-3)', marginTop: 1 }}>
                {item.serviceName}
              </div>
              <div style={{ fontFamily: "'DM Sans', system-ui, sans-serif", fontSize: 10, color: 'var(--db-ink-5)', marginTop: 1 }}>
                with {item.staffName}
              </div>
            </div>
          </div>
        ))}

        {!loading && items.length === MAX_VISIBLE && (
          <p className="db-editorial" style={{ fontSize: 12, color: 'var(--db-ink-5)', textAlign: 'center', paddingTop: 8 }}>
            Tap a row to check in →
          </p>
        )}
      </div>

      <CheckInDialog
        open={dialogOpen}
        appointment={selectedAppt?.appt ?? null}
        staffName={selectedAppt?.staffName ?? ''}
        serviceName={selectedAppt?.serviceName ?? ''}
        onCheckedIn={handleCheckedIn}
        onOpenChange={setDialogOpen}
      />
    </>
  );
}
```

- [ ] **Step 4: Run tests — expect pass**

```bash
cd frontend && npm test -- --reporter verbose src/components/dashboard/__tests__/up-next-panel.test.tsx
```

Expected: PASS (7 tests).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/dashboard/up-next-panel.tsx frontend/src/components/dashboard/__tests__/up-next-panel.test.tsx
git commit -m "feat: add UpNextPanel — self-contained upcoming appointments sidebar (max 5)"
```

---

## Task 9: Rewire `dashboard/page.tsx`

**Files:**
- Modify: `frontend/src/app/(shell)/dashboard/page.tsx`

This task wires all new components into the page and restructures the layout.

- [ ] **Step 1: Check TypeScript compiles cleanly before touching the page**

```bash
cd frontend && npx tsc --noEmit 2>&1 | grep -c "error TS"
```

Note the count. After this task the count must not increase.

- [ ] **Step 2: Replace `dashboard/page.tsx` with the rewired version**

```tsx
'use client';

import { useEffect, useState, useMemo } from 'react';
import { useRouter } from 'next/navigation';
import { format } from 'date-fns';
import { Cake } from 'lucide-react';
import { apiClient } from '@/lib/api-client';
import { toast } from 'sonner';
import { useCartStore } from '@/stores/cart-store';
import { useAuthStore } from '@/stores/auth-store';
import { titleCase } from '@/lib/utils';
import { Skeleton } from '@/components/ui/skeleton';

import { StatsBar }          from '@/components/dashboard/stats-bar';
import { GoalsRings }        from '@/components/dashboard/radial-goal-progress';
import { ActiveCustomerCard } from '@/components/dashboard/active-customer-card';
import { ServiceQueue }      from '@/components/dashboard/service-queue';
import { UpNextPanel }       from '@/components/dashboard/up-next-panel';

// ── Types (unchanged from original) ────────────────────────────────────────

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

// ── Component ───────────────────────────────────────────────────────────────

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
  const [isLoading, setIsLoading] = useState(true);
  const [birthdayUsers, setBirthdayUsers] = useState<{ id: string; full_name: string }[]>([]);

  useEffect(() => {
    if (user?.role === 'staff') router.push('/dashboard/staff');
  }, [user, router]);

  useEffect(() => {
    fetchDashboardData();
    const interval = setInterval(() => fetchDashboardData(true), 10_000);
    return () => clearInterval(interval);
  }, []);

  const fetchDashboardData = async (silent = false) => {
    try {
      if (!silent) setIsLoading(true);
      const [walkinsRes, reportsRes, settingsRes, comparisonRes, birthdaysRes] =
        await Promise.all([
          apiClient.get('/appointments/walkins/active'),
          apiClient.get('/reports/dashboard'),
          apiClient.get('/settings'),
          apiClient.get('/reports/dashboard/comparison'),
          apiClient.get('/users/birthdays/today'),
        ]);

      setActiveSessions(walkinsRes.data.sessions ?? []);

      const m = reportsRes.data.metrics;
      setStats({
        today_revenue:   m.net_revenue,
        today_services:  m.completed_appointments,
        today_customers: m.total_bills,
        active_services: m.active_appointments,
        pending_bills:   m.pending_appointments,
      });

      if (settingsRes.data) {
        setSettings({
          daily_revenue_target_paise: settingsRes.data.daily_revenue_target_paise ?? 2000000,
          daily_services_target:      settingsRes.data.daily_services_target      ?? 25,
        });
      }

      if (comparisonRes.data?.comparison) setComparison(comparisonRes.data.comparison);
      if (birthdaysRes.data?.birthdays)    setBirthdayUsers(birthdaysRes.data.birthdays);
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
        ?? 'Failed to load dashboard data';
      if (!silent) toast.error(detail);
    } finally {
      setIsLoading(false);
    }
  };

  const handleCheckoutSession = async (sessionId: string) => {
    const session = activeSessions.find(s => s.session_id === sessionId);
    if (!session) { toast.error('Session not found'); return; }
    clearCart();
    session.walkins.filter(w => w.status !== 'cancelled').forEach(w => {
      addItem({
        isProduct: false,
        serviceId: w.service.id,
        serviceName: w.service.name,
        quantity: 1,
        unitPrice: w.service.base_price,
        discount: 0,
        taxRate: 18,
        staffId: w.assigned_staff.id,
        staffName: w.assigned_staff.display_name,
        duration: w.duration_minutes,
      });
    });
    setCustomer(session.customer_id, titleCase(session.customer_name), session.customer_phone);
    setSessionId(sessionId);
    router.push('/dashboard/pos');
    toast.success(`Ready to bill ${titleCase(session.customer_name)}`);
  };

  // Computed values for StatsBar
  const revenuePct = settings.daily_revenue_target_paise > 0
    ? Math.min(100, Math.round((stats.today_revenue / settings.daily_revenue_target_paise) * 100))
    : 0;

  const checkedInWaiting = useMemo(
    () => activeSessions.filter(s => s.walkins.every(w => w.status === 'checked_in')).length,
    [activeSessions]
  );

  const avgBillTodayPaise = stats.today_customers > 0
    ? Math.round(stats.today_revenue / stats.today_customers)
    : 0;

  const customersTarget = Math.round(settings.daily_services_target * 0.85);
  const weekdayName = format(new Date(), 'EEEE');

  return (
    <div className="dashboard-page" style={{ display: 'flex', flexDirection: 'column', minHeight: '100dvh' }}>

      {/* Topbar */}
      <div className="db-topbar">
        <span style={{ fontFamily: "'DM Sans', system-ui, sans-serif", fontSize: 22, fontWeight: 800, letterSpacing: '-0.5px', color: 'var(--db-ink)' }}>
          Today
        </span>
        <span style={{ fontFamily: "'DM Sans', system-ui, sans-serif", fontSize: 11, color: 'var(--db-ink-5)', whiteSpace: 'nowrap' }}>
          {format(new Date(), 'h:mm a · EEE, d MMM yyyy')}
        </span>
        <input
          type="search"
          className="db-search"
          placeholder="Search customers, bills, services…"
          aria-label="Search"
        />
        <button
          style={{ background: 'var(--db-ink)', color: '#fff', border: 'none', borderRadius: 8, padding: '9px 16px', fontSize: 12, fontWeight: 700, cursor: 'pointer', whiteSpace: 'nowrap', fontFamily: "'DM Sans', system-ui, sans-serif" }}
          onClick={() => router.push('/dashboard/pos')}
        >
          + New Walk-in
        </button>
      </div>

      {/* Main layout: content + right sidebar */}
      <div style={{ display: 'flex', flex: 1, alignItems: 'flex-start' }}>

        {/* Main content */}
        <div style={{ flex: 1, padding: 14, display: 'flex', flexDirection: 'column', gap: 12, minWidth: 0 }}>

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
                    {birthdayUsers.length === 1 ? 'Wishing them a wonderful day!' : `${birthdayUsers.length} team members celebrating today!`}
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Stats bar */}
          {isLoading ? (
            <Skeleton shape="card" className="h-36" />
          ) : (
            <StatsBar
              revenueToday={stats.today_revenue}
              revenueTarget={settings.daily_revenue_target_paise}
              revenueDeltaPaise={comparison?.revenue_change_paise ?? 0}
              activeServices={stats.active_services}
              checkedInWaiting={checkedInWaiting}
              pendingBills={stats.pending_bills}
              avgBillTodayPaise={avgBillTodayPaise}
            />
          )}

          {/* Goals rings */}
          {isLoading ? (
            <Skeleton shape="card" className="h-36" />
          ) : (
            <GoalsRings
              revenueTarget={settings.daily_revenue_target_paise}
              currentRevenue={stats.today_revenue}
              servicesTarget={settings.daily_services_target}
              currentServices={stats.today_services}
              customersTarget={customersTarget}
              currentCustomers={stats.today_customers}
              weekdayName={weekdayName}
              revenuePct={revenuePct}
            />
          )}

          {/* Active customers */}
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10 }}>
              <span style={{ fontFamily: "'DM Sans', system-ui, sans-serif", fontSize: 14, fontWeight: 800, color: 'var(--db-ink)' }}>
                In service, right now
              </span>
              <span className="db-badge-gold">{stats.active_services} Active</span>
              {checkedInWaiting > 0 && (
                <span className="db-badge-muted">{checkedInWaiting} Checked in</span>
              )}
              <span style={{ fontFamily: "'DM Sans', system-ui, sans-serif", fontSize: 11, color: 'var(--db-ink-5)', fontStyle: 'italic', marginLeft: 'auto' }}>
                Tap to checkout
              </span>
            </div>

            {isLoading ? (
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
                <Skeleton shape="card" className="h-48" />
                <Skeleton shape="card" className="h-48" />
              </div>
            ) : activeSessions.length === 0 ? (
              <div style={{ padding: '32px 0', textAlign: 'center' }}>
                <p className="db-editorial" style={{ fontSize: 16, color: 'var(--db-ink-5)' }}>
                  Floor is clear — no active sessions.
                </p>
              </div>
            ) : (
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
                {activeSessions.map(session => (
                  <ActiveCustomerCard
                    key={session.session_id}
                    session={session}
                    onCheckout={handleCheckoutSession}
                    onRefresh={() => fetchDashboardData(true)}
                  />
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Right sidebar */}
        <div className="db-sidebar">
          {/* Up Next panel */}
          <UpNextPanel />

          {/* Staff Queue */}
          <div className="db-sidebar-section" style={{ flex: 1 }}>
            <span className="db-label">Staff Queue</span>
            <ServiceQueue sessions={activeSessions} variant="sidebar" />
          </div>
        </div>

      </div>
    </div>
  );
}
```

- [ ] **Step 3: Run the full test suite**

```bash
cd frontend && npm test
```

Expected: all existing tests pass; new tests pass.

- [ ] **Step 4: Check TypeScript**

```bash
cd frontend && npx tsc --noEmit 2>&1 | tail -5
```

Expected: same error count as Step 1 (no new errors introduced).

- [ ] **Step 5: Start dev server and verify the page loads**

```bash
cd frontend && npm run dev
```

Open `http://localhost:3000`. Confirm:
- Topbar shows "Today", clock, search bar, "+ New Walk-in" button
- Stats bar renders with 3 panels
- Goals rings section visible
- Active customers grid renders (or empty state)
- Right sidebar shows "Up next" and "Staff Queue"
- No console errors

Stop dev server.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/app/\(shell\)/dashboard/page.tsx
git commit -m "feat: rewire Today dashboard — new layout, StatsBar, GoalsRings, UpNextPanel, sidebar"
```

---

## Self-Review

**Spec coverage check:**

| Spec requirement | Covered in |
|---|---|
| Dashboard-scoped color tokens | Task 1 |
| Cormorant Garamond + DM Sans fonts | Task 1 |
| Topbar: wider search bar, clock, New Walk-in btn | Task 9 |
| 3-panel stats bar (Revenue, Pace, Right Now) | Task 3 + Task 9 |
| Pace derived from `comparison.revenue_change_paise` | Task 3 |
| 3-ring goals section with contextual message | Task 4 + Task 9 |
| Restyled ActiveCustomerCard (warm visual, per-service controls) | Task 5 |
| ServiceQueue sidebar variant | Task 6 |
| `listAppointments` status param | Task 2 |
| UpNextPanel (max 5, self-contained, 2-min poll) | Task 8 |
| CheckInDialog (check-in from sidebar row) | Task 7 |
| Birthday banner preserved above stats bar | Task 9 |
| HourlyTrendChart + ServiceDistributionChart removed | Task 9 |
| No backend changes | ✓ confirmed throughout |

All requirements covered. No placeholders.
