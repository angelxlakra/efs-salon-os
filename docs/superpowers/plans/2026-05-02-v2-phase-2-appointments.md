# V2 Phase 2 — Appointments Page Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Appointments page natively in V2 — a staff-swimlane day view, 7-day week view, and month overview, with drag-to-reschedule, drag-to-resize, click-to-create, conflict detection, and keyboard shortcuts — all wired to the existing `/api/appointments` backend.

**Architecture:** The page lives at `app/(shell)/dashboard/appointments/page.tsx` (already in the sidebar section-config, route doesn't exist yet). A shared `TimeGrid` primitive provides the hour-axis + absolute-positioning canvas reused by DayView (swimlane columns per staff) and WeekView (one column per day). Appointment blocks are positioned via CSS `top`/`height` derived from `scheduled_at` + `duration_minutes`. Drag-to-reschedule uses `@dnd-kit/core` (one new runtime dep). Resize uses native `mousedown/mousemove/mouseup` on a handle div. Service colour is deterministically picked from the 6 `--data-series-*` tokens by hashing the `service_id`.

**Tech Stack:** Next.js 16 App Router, React 19, TypeScript 5, Tailwind 4 + V2 design tokens, date-fns (already installed), react-hook-form + zod (already installed), @dnd-kit/core + @dnd-kit/utilities (new — one `npm install` step), lucide-react icons, axios apiClient. No backend changes.

---

## File structure (responsibilities)

**New files:**
- `frontend/src/lib/api/appointments.ts` — TypeScript types + API functions for appointments and supporting staff/service lookups.
- `frontend/src/components/calendar/utils.ts` — Shared constants (`HOUR_HEIGHT`, `DAY_START_HOUR`, `DAY_END_HOUR`) and pure helpers (`minutesToPx`, `timeToTopOffset`, `getServiceColor`, `snapToSlot`).
- `frontend/src/components/calendar/time-grid.tsx` — Pure display: scrollable grid body with hour rows and quarter-lines; children rendered absolutely inside. No data dependencies.
- `frontend/src/components/calendar/appointment-block.tsx` — Single appointment rectangle. Receives position props (`top`, `height`) and renders customer name, service name, status chip. Accepts `isDragging` and `isConflict` flags.
- `frontend/src/components/calendar/day-view.tsx` — Staff-swimlane layout: sticky header row (one cell per staff) + `TimeGrid` body with one column per staff. Slots are clickable; appointments drop into the correct column.
- `frontend/src/components/calendar/week-view.tsx` — 7-day layout: sticky header row (Mon–Sun) + `TimeGrid` body with one column per calendar day. All staff appointments mixed.
- `frontend/src/components/calendar/month-overview.tsx` — Simple 6×7 grid of day cells. Each cell shows a dot badge if appointments exist. Clicking a day navigates to day view.
- `frontend/src/components/calendar/appointment-form-dialog.tsx` — Create/edit dialog using `V2Dialog` + react-hook-form + zod. Fields: date, time, service (Combobox), staff (Combobox), duration, customer name, customer phone, notes.
- `frontend/src/components/calendar/use-calendar-keyboard.ts` — `useCalendarKeyboard` hook. Binds `n`, `←/→`, `g w`, `g d` in the appointments page.
- `frontend/src/app/(shell)/dashboard/appointments/page.tsx` — Page root: view switcher tabs, date nav (← Today →), data fetching, state wiring.
- `frontend/src/components/calendar/__tests__/utils.test.ts` — Unit tests for pure helpers.
- `frontend/src/components/calendar/__tests__/time-grid.test.tsx` — Render tests for TimeGrid.
- `frontend/src/components/calendar/__tests__/appointment-block.test.tsx` — Block render + conflict flag tests.
- `frontend/src/components/calendar/__tests__/day-view.test.tsx` — Swimlane column count + slot click tests.

**Modified files:**
- `frontend/package.json` — adds `@dnd-kit/core` and `@dnd-kit/utilities`.
- `docs/design_system.md` — appends Phase 2 row to §13 changelog.

**Pre-existing files referenced (do NOT modify here):**
- `frontend/src/components/ui/dialog.tsx` — used by `appointment-form-dialog.tsx`.
- `frontend/src/components/ui/combobox.tsx` — service and staff pickers.
- `frontend/src/lib/api-client.ts` — axios instance.
- `frontend/src/components/shell/section-config.ts` — already has `{ label: "Appointments", href: "/dashboard/appointments", icon: Calendar }`.
- `frontend/src/styles/tokens.css` — `--data-series-1` through `--data-series-6` for service colours.

---

## Pre-flight (run once before Task 1)

- [ ] Confirm branch and baseline

```bash
cd /Users/angelxlakra/dev/efs-salon/efs-salon-os && git status && git log --oneline -3
```

Expected: clean working tree on `feature/v2-phase-1` (or a new branch — create one now):

```bash
git checkout -b feature/v2-phase-2-appointments
```

- [ ] Capture baseline counts

```bash
cd /Users/angelxlakra/dev/efs-salon/efs-salon-os/frontend && PATH="/Users/angelxlakra/.nvm/versions/node/v22.20.0/bin:$PATH" npm test -- --run 2>&1 | tail -3
```

Expected: 149 tests pass across 30 files.

```bash
cd /Users/angelxlakra/dev/efs-salon/efs-salon-os/frontend && PATH="/Users/angelxlakra/.nvm/versions/node/v22.20.0/bin:$PATH" npx tsc --noEmit 2>&1 | grep -c "error TS"
```

Expected: 162 (pre-existing baseline; Phase 2 must not add new tsc errors).

> **nvm sandbox quirk:** every `npm`/`npx`/`node` command in this plan must inline-prepend `PATH="/Users/angelxlakra/.nvm/versions/node/v22.20.0/bin:$PATH"`.

---

## Task 1: Install @dnd-kit + API client + shared utils

**Files:**
- Modify: `frontend/package.json` (via npm install)
- Create: `frontend/src/lib/api/appointments.ts`
- Create: `frontend/src/components/calendar/utils.ts`
- Create: `frontend/src/components/calendar/__tests__/utils.test.ts`

### Why
`@dnd-kit/core` is the only new runtime dep. Installing it first avoids mid-plan dependency surprises. The API client and utils are pure data/helpers with no side-effects — ideal first tasks that every subsequent task imports from.

---

- [ ] **Step 1: Install @dnd-kit**

```bash
cd /Users/angelxlakra/dev/efs-salon/efs-salon-os/frontend && PATH="/Users/angelxlakra/.nvm/versions/node/v22.20.0/bin:$PATH" npm install @dnd-kit/core @dnd-kit/utilities
```

Expected: resolves without peer-dep errors (React 19 is compatible).

---

- [ ] **Step 2: Write failing tests for utils**

`frontend/src/components/calendar/__tests__/utils.test.ts`:

```ts
import { describe, expect, it } from "vitest";
import {
  HOUR_HEIGHT,
  DAY_START_HOUR,
  DAY_END_HOUR,
  GRID_HEIGHT,
  minutesToPx,
  pxToMinutes,
  timeToTopOffset,
  getServiceColor,
  snapToSlot,
} from "@/components/calendar/utils";

describe("calendar utils", () => {
  it("GRID_HEIGHT equals (DAY_END_HOUR - DAY_START_HOUR) * HOUR_HEIGHT", () => {
    expect(GRID_HEIGHT).toBe((DAY_END_HOUR - DAY_START_HOUR) * HOUR_HEIGHT);
  });

  it("minutesToPx converts 60 min to HOUR_HEIGHT px", () => {
    expect(minutesToPx(60)).toBe(HOUR_HEIGHT);
  });

  it("minutesToPx converts 30 min to half HOUR_HEIGHT", () => {
    expect(minutesToPx(30)).toBe(HOUR_HEIGHT / 2);
  });

  it("pxToMinutes snaps to 15-minute grid", () => {
    // 64px = 60 min, so 16px ≈ 15min
    const px = (HOUR_HEIGHT / 60) * 15; // exact 15-min pixel
    expect(pxToMinutes(px)).toBe(15);
  });

  it("pxToMinutes rounds non-15-min values to nearest 15", () => {
    const px = (HOUR_HEIGHT / 60) * 22; // ~22 min → snaps to 15
    expect(pxToMinutes(px)).toBe(15);
  });

  it("timeToTopOffset places 8:00 AM at 0 when DAY_START_HOUR is 8", () => {
    const iso = `2026-05-05T${String(DAY_START_HOUR).padStart(2, "0")}:00:00+05:30`;
    expect(timeToTopOffset(iso)).toBe(0);
  });

  it("timeToTopOffset places 9:00 AM at HOUR_HEIGHT when DAY_START_HOUR is 8", () => {
    const iso = `2026-05-05T${String(DAY_START_HOUR + 1).padStart(2, "0")}:00:00+05:30`;
    expect(timeToTopOffset(iso)).toBe(HOUR_HEIGHT);
  });

  it("getServiceColor returns a CSS var string", () => {
    const color = getServiceColor("01ABCDEF1234");
    expect(color).toMatch(/^var\(--data-series-[1-6]\)$/);
  });

  it("getServiceColor is deterministic for the same id", () => {
    expect(getServiceColor("01ABCDEF1234")).toBe(getServiceColor("01ABCDEF1234"));
  });

  it("getServiceColor produces different values for different ids", () => {
    const colors = new Set([
      getServiceColor("aaaa"),
      getServiceColor("bbbb"),
      getServiceColor("cccc"),
      getServiceColor("dddd"),
      getServiceColor("eeee"),
      getServiceColor("ffff"),
    ]);
    // At least 2 distinct series across 6 ids
    expect(colors.size).toBeGreaterThan(1);
  });

  it("snapToSlot snaps a datetime string to 15-min boundary", () => {
    // 08:07 → 08:00 (round down to nearest 15)
    const snapped = snapToSlot("2026-05-05T08:07:00+05:30");
    expect(snapped).toMatch(/T08:00:00/);
  });
});
```

- [ ] **Step 3: Run tests — verify FAIL**

```bash
cd /Users/angelxlakra/dev/efs-salon/efs-salon-os/frontend && PATH="/Users/angelxlakra/.nvm/versions/node/v22.20.0/bin:$PATH" npm test -- --run src/components/calendar/__tests__/utils.test.ts 2>&1 | tail -5
```

Expected: FAIL with "Cannot find module '@/components/calendar/utils'".

- [ ] **Step 4: Create `utils.ts`**

`frontend/src/components/calendar/utils.ts`:

```ts
/** Pixels per hour in the time grid. Adjust here to change the whole grid scale. */
export const HOUR_HEIGHT = 64;

/** Earliest visible hour (inclusive). Grid starts at this hour. */
export const DAY_START_HOUR = 8;

/** Latest visible hour (exclusive). Grid ends at this hour. */
export const DAY_END_HOUR = 21;

/** Total pixel height of the scrollable grid body. */
export const GRID_HEIGHT = (DAY_END_HOUR - DAY_START_HOUR) * HOUR_HEIGHT;

/** Convert a duration in minutes to a pixel height. */
export function minutesToPx(minutes: number): number {
  return (minutes / 60) * HOUR_HEIGHT;
}

/** Convert a pixel offset to minutes, snapped to the nearest 15-minute slot. */
export function pxToMinutes(px: number): number {
  const raw = (px / HOUR_HEIGHT) * 60;
  return Math.round(raw / 15) * 15;
}

/**
 * Given an ISO datetime string, return the CSS `top` offset in pixels
 * relative to the start of the time grid (DAY_START_HOUR).
 * Returns 0 for times before DAY_START_HOUR and GRID_HEIGHT for times after DAY_END_HOUR.
 */
export function timeToTopOffset(iso: string): number {
  const d = new Date(iso);
  const minutesSinceStart = (d.getHours() - DAY_START_HOUR) * 60 + d.getMinutes();
  return Math.max(0, Math.min(minutesToPx(minutesSinceStart), GRID_HEIGHT));
}

const DATA_SERIES_COUNT = 6;

/**
 * Deterministically maps a service_id to one of the 6 data-viz CSS vars.
 * Uses a simple base-36 hash of the last 6 chars of the ULID.
 */
export function getServiceColor(serviceId: string): string {
  const tail = serviceId.slice(-6);
  let n = 0;
  for (let i = 0; i < tail.length; i++) {
    n = (n * 37 + tail.charCodeAt(i)) % DATA_SERIES_COUNT;
  }
  return `var(--data-series-${n + 1})`;
}

/**
 * Snap an ISO datetime string to the nearest 15-minute boundary (floor).
 * Used when converting pixel offsets back to scheduled_at values.
 */
export function snapToSlot(iso: string): string {
  const d = new Date(iso);
  const snappedMinutes = Math.floor(d.getMinutes() / 15) * 15;
  d.setMinutes(snappedMinutes, 0, 0);
  return d.toISOString();
}

/** Build an ISO datetime string from a date string (YYYY-MM-DD) and hour+minute. */
export function buildISO(dateStr: string, hour: number, minute: number): string {
  return `${dateStr}T${String(hour).padStart(2, "0")}:${String(minute).padStart(2, "0")}:00`;
}
```

- [ ] **Step 5: Run tests — verify PASS**

```bash
cd /Users/angelxlakra/dev/efs-salon/efs-salon-os/frontend && PATH="/Users/angelxlakra/.nvm/versions/node/v22.20.0/bin:$PATH" npm test -- --run src/components/calendar/__tests__/utils.test.ts 2>&1 | tail -5
```

Expected: 11 tests pass.

- [ ] **Step 6: Create `lib/api/appointments.ts`**

`frontend/src/lib/api/appointments.ts`:

```ts
import { apiClient } from "../api-client";

// ── Types ─────────────────────────────────────────────────────────────────────

export type AppointmentStatus =
  | "scheduled"
  | "checked_in"
  | "in_progress"
  | "completed"
  | "cancelled";

export interface Appointment {
  id: string;
  ticket_number: string;
  visit_id: string | null;
  customer_id: string | null;
  customer_name: string;
  customer_phone: string | null;
  service_id: string;
  assigned_staff_id: string | null;
  scheduled_at: string; // ISO datetime
  duration_minutes: number;
  status: AppointmentStatus;
  booking_notes: string | null;
  service_notes: string | null;
  checked_in_at: string | null;
  started_at: string | null;
  completed_at: string | null;
  cancelled_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface AppointmentCreate {
  customer_name: string;
  customer_phone: string;
  customer_id?: string;
  service_id: string;
  assigned_staff_id?: string;
  scheduled_at: string; // ISO datetime
  duration_minutes: number;
  booking_notes?: string;
}

export interface AppointmentUpdate {
  service_id?: string;
  assigned_staff_id?: string;
  scheduled_at?: string;
  duration_minutes?: number;
  booking_notes?: string;
  service_notes?: string;
}

export interface StaffMember {
  id: string;
  display_name: string;
  specialization: string[] | null;
  is_active: boolean;
  is_service_provider: boolean;
}

export interface ServiceItem {
  id: string;
  name: string;
  base_price: number; // paise
  duration_minutes: number;
  category_name: string;
}

// ── API functions ──────────────────────────────────────────────────────────────

export async function listAppointments(date: string): Promise<Appointment[]> {
  const { data } = await apiClient.get<Appointment[]>("/appointments", {
    params: { date },
  });
  return data;
}

export async function createAppointment(
  payload: AppointmentCreate
): Promise<Appointment> {
  const { data } = await apiClient.post<Appointment>("/appointments", payload);
  return data;
}

export async function updateAppointment(
  id: string,
  payload: AppointmentUpdate
): Promise<Appointment> {
  const { data } = await apiClient.patch<Appointment>(
    `/appointments/${id}`,
    payload
  );
  return data;
}

export async function cancelAppointment(id: string): Promise<void> {
  await apiClient.delete(`/appointments/${id}`);
}

export async function checkInAppointment(id: string): Promise<Appointment> {
  const { data } = await apiClient.post<Appointment>(
    `/appointments/${id}/check-in`
  );
  return data;
}

export async function startAppointment(id: string): Promise<Appointment> {
  const { data } = await apiClient.post<Appointment>(
    `/appointments/${id}/start`
  );
  return data;
}

export async function completeAppointment(id: string): Promise<Appointment> {
  const { data } = await apiClient.post<Appointment>(
    `/appointments/${id}/complete`
  );
  return data;
}

export async function listActiveStaff(): Promise<StaffMember[]> {
  const { data } = await apiClient.get<{ items: StaffMember[]; total: number }>(
    "/staff",
    { params: { is_active: true, is_service_provider: true, limit: 100 } }
  );
  return data.items;
}

export async function listServices(): Promise<ServiceItem[]> {
  const { data } = await apiClient.get<ServiceItem[]>("/catalog/services");
  return data;
}
```

- [ ] **Step 7: Commit**

```bash
cd /Users/angelxlakra/dev/efs-salon/efs-salon-os && git add frontend/package.json frontend/package-lock.json frontend/src/lib/api/appointments.ts frontend/src/components/calendar/utils.ts frontend/src/components/calendar/__tests__/utils.test.ts && git commit -m "feat(appointments): install @dnd-kit, API client, calendar utils"
```

---

## Task 2: TimeGrid primitive

**Files:**
- Create: `frontend/src/components/calendar/time-grid.tsx`
- Create: `frontend/src/components/calendar/__tests__/time-grid.test.tsx`

### Why
`TimeGrid` is the scrollable canvas that DayView and WeekView both mount into. It renders the hour labels axis, grid lines, and an `overflow: hidden; position: relative` body where children (columns with appointment blocks) are positioned absolutely. Splitting this into its own file makes both view components thin.

---

- [ ] **Step 1: Write failing tests**

`frontend/src/components/calendar/__tests__/time-grid.test.tsx`:

```tsx
import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { TimeGrid } from "@/components/calendar/time-grid";
import { DAY_START_HOUR, DAY_END_HOUR, GRID_HEIGHT } from "@/components/calendar/utils";

describe("TimeGrid", () => {
  it("renders an hour label for each hour from DAY_START_HOUR to DAY_END_HOUR", () => {
    render(<TimeGrid><div /></TimeGrid>);
    for (let h = DAY_START_HOUR; h < DAY_END_HOUR; h++) {
      const label = h < 12 ? `${h} AM` : h === 12 ? "12 PM" : `${h - 12} PM`;
      expect(screen.getByText(label)).toBeInTheDocument();
    }
  });

  it("grid body has min-height equal to GRID_HEIGHT", () => {
    const { container } = render(<TimeGrid><div data-testid="child" /></TimeGrid>);
    const body = container.querySelector("[data-testid='grid-body']");
    expect(body).toBeTruthy();
    expect((body as HTMLElement).style.minHeight).toBe(`${GRID_HEIGHT}px`);
  });

  it("renders children inside the grid body", () => {
    render(<TimeGrid><div data-testid="inner" /></TimeGrid>);
    expect(screen.getByTestId("inner")).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run tests — verify FAIL**

```bash
cd /Users/angelxlakra/dev/efs-salon/efs-salon-os/frontend && PATH="/Users/angelxlakra/.nvm/versions/node/v22.20.0/bin:$PATH" npm test -- --run src/components/calendar/__tests__/time-grid.test.tsx 2>&1 | tail -5
```

Expected: FAIL with "Cannot find module '@/components/calendar/time-grid'".

- [ ] **Step 3: Implement `time-grid.tsx`**

`frontend/src/components/calendar/time-grid.tsx`:

```tsx
"use client";

import * as React from "react";
import { cn } from "@/lib/utils";
import {
  HOUR_HEIGHT,
  DAY_START_HOUR,
  DAY_END_HOUR,
  GRID_HEIGHT,
} from "@/components/calendar/utils";

const HOURS = Array.from(
  { length: DAY_END_HOUR - DAY_START_HOUR },
  (_, i) => DAY_START_HOUR + i
);

function hourLabel(h: number): string {
  if (h < 12) return `${h} AM`;
  if (h === 12) return "12 PM";
  return `${h - 12} PM`;
}

type TimeGridProps = {
  children: React.ReactNode;
  className?: string;
};

/**
 * Scrollable time-grid canvas shared by DayView and WeekView.
 * Renders hour labels on the left + an absolutely-positioned body on the right.
 * Children (swimlane columns) are rendered inside the body.
 */
export function TimeGrid({ children, className }: TimeGridProps) {
  return (
    <div className={cn("flex overflow-y-auto", className)}>
      {/* Hour labels axis — sticky on horizontal scroll */}
      <div className="sticky left-0 z-10 w-14 shrink-0 bg-surface-card border-r border-border-subtle select-none">
        {HOURS.map((h) => (
          <div
            key={h}
            style={{ height: HOUR_HEIGHT }}
            className="flex items-start justify-end pr-2 pt-0.5"
          >
            <span className="text-[11px] text-text-muted leading-none">
              {hourLabel(h)}
            </span>
          </div>
        ))}
      </div>

      {/* Grid body */}
      <div
        data-testid="grid-body"
        className="relative flex-1"
        style={{ minHeight: GRID_HEIGHT }}
      >
        {/* Hour dividers (full-width horizontal lines) */}
        {HOURS.map((h) => (
          <div
            key={h}
            className="absolute left-0 right-0 border-t border-border-subtle"
            style={{ top: (h - DAY_START_HOUR) * HOUR_HEIGHT }}
            aria-hidden
          />
        ))}
        {/* Quarter-hour sub-lines (lighter) */}
        {HOURS.flatMap((h) =>
          [1, 2, 3].map((q) => (
            <div
              key={`${h}-${q}`}
              className="absolute left-0 right-0 border-t border-border-subtle opacity-40"
              style={{ top: (h - DAY_START_HOUR) * HOUR_HEIGHT + q * (HOUR_HEIGHT / 4) }}
              aria-hidden
            />
          ))
        )}
        {children}
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Run tests — verify PASS**

```bash
cd /Users/angelxlakra/dev/efs-salon/efs-salon-os/frontend && PATH="/Users/angelxlakra/.nvm/versions/node/v22.20.0/bin:$PATH" npm test -- --run src/components/calendar/__tests__/time-grid.test.tsx 2>&1 | tail -5
```

Expected: 3 tests pass.

- [ ] **Step 5: Commit**

```bash
cd /Users/angelxlakra/dev/efs-salon/efs-salon-os && git add frontend/src/components/calendar/time-grid.tsx frontend/src/components/calendar/__tests__/time-grid.test.tsx && git commit -m "feat(calendar): TimeGrid primitive (hour axis + grid canvas)"
```

---

## Task 3: AppointmentBlock

**Files:**
- Create: `frontend/src/components/calendar/appointment-block.tsx`
- Create: `frontend/src/components/calendar/__tests__/appointment-block.test.tsx`

### Why
`AppointmentBlock` is the visually distinctive rectangle sitting inside the grid. It's a controlled display component — it receives computed `top`/`height` and doesn't know which view it's inside. Adding drag wrappers in Task 9 is a thin layer on top.

---

- [ ] **Step 1: Write failing tests**

`frontend/src/components/calendar/__tests__/appointment-block.test.tsx`:

```tsx
import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AppointmentBlock } from "@/components/calendar/appointment-block";
import type { Appointment } from "@/lib/api/appointments";

const base: Appointment = {
  id: "01APPT000001",
  ticket_number: "TKT-260505-001",
  visit_id: null,
  customer_id: null,
  customer_name: "Priya Sharma",
  customer_phone: "9876543210",
  service_id: "01SVC000001",
  assigned_staff_id: "01STF000001",
  scheduled_at: "2026-05-05T10:00:00+05:30",
  duration_minutes: 60,
  status: "scheduled",
  booking_notes: null,
  service_notes: null,
  checked_in_at: null,
  started_at: null,
  completed_at: null,
  cancelled_at: null,
  created_at: "2026-05-05T09:00:00+05:30",
  updated_at: "2026-05-05T09:00:00+05:30",
};

describe("AppointmentBlock", () => {
  it("renders the customer name", () => {
    render(
      <AppointmentBlock
        appointment={base}
        serviceName="Hair Cut"
        top={64}
        height={64}
        onClick={vi.fn()}
      />
    );
    expect(screen.getByText("Priya Sharma")).toBeInTheDocument();
  });

  it("renders the service name", () => {
    render(
      <AppointmentBlock
        appointment={base}
        serviceName="Hair Cut"
        top={64}
        height={64}
        onClick={vi.fn()}
      />
    );
    expect(screen.getByText("Hair Cut")).toBeInTheDocument();
  });

  it("applies conflict styling when isConflict=true", () => {
    const { container } = render(
      <AppointmentBlock
        appointment={base}
        serviceName="Hair Cut"
        top={64}
        height={64}
        onClick={vi.fn()}
        isConflict
      />
    );
    expect(container.firstChild).toHaveAttribute("data-conflict", "true");
  });

  it("calls onClick when clicked", async () => {
    const onClick = vi.fn();
    render(
      <AppointmentBlock
        appointment={base}
        serviceName="Hair Cut"
        top={64}
        height={64}
        onClick={onClick}
      />
    );
    await userEvent.click(screen.getByText("Priya Sharma"));
    expect(onClick).toHaveBeenCalledOnce();
  });

  it("renders a resize handle div", () => {
    render(
      <AppointmentBlock
        appointment={base}
        serviceName="Hair Cut"
        top={64}
        height={64}
        onClick={vi.fn()}
      />
    );
    expect(screen.getByRole("separator", { hidden: true })).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run tests — verify FAIL**

```bash
cd /Users/angelxlakra/dev/efs-salon/efs-salon-os/frontend && PATH="/Users/angelxlakra/.nvm/versions/node/v22.20.0/bin:$PATH" npm test -- --run src/components/calendar/__tests__/appointment-block.test.tsx 2>&1 | tail -5
```

Expected: FAIL with "Cannot find module".

- [ ] **Step 3: Implement `appointment-block.tsx`**

`frontend/src/components/calendar/appointment-block.tsx`:

```tsx
"use client";

import * as React from "react";
import { cn } from "@/lib/utils";
import { getServiceColor } from "@/components/calendar/utils";
import type { Appointment } from "@/lib/api/appointments";

type AppointmentBlockProps = {
  appointment: Appointment;
  serviceName: string;
  top: number;
  height: number;
  onClick: (appointment: Appointment) => void;
  isConflict?: boolean;
  isDragging?: boolean;
  /** Called when the resize handle is mousedown'd. Parent handles drag logic. */
  onResizeStart?: (e: React.MouseEvent, appointment: Appointment) => void;
};

const STATUS_ALPHA: Record<string, string> = {
  scheduled: "cc",
  checked_in: "dd",
  in_progress: "ff",
  completed: "88",
  cancelled: "44",
};

export function AppointmentBlock({
  appointment,
  serviceName,
  top,
  height,
  onClick,
  isConflict = false,
  isDragging = false,
  onResizeStart,
}: AppointmentBlockProps) {
  const color = getServiceColor(appointment.service_id);
  // We can't easily use CSS vars in inline style with alpha, so we use a data attribute
  // and rely on the background being set via the data-color-index attribute below.

  return (
    <div
      role="button"
      tabIndex={0}
      aria-label={`${appointment.customer_name} — ${serviceName}`}
      data-conflict={isConflict || undefined}
      data-status={appointment.status}
      onClick={() => onClick(appointment)}
      onKeyDown={(e) => e.key === "Enter" && onClick(appointment)}
      className={cn(
        "absolute left-0.5 right-0.5 rounded-md px-2 py-1 cursor-pointer select-none overflow-hidden",
        "border-l-[3px] transition-opacity",
        "hover:brightness-95 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent",
        isDragging && "opacity-50 cursor-grabbing",
        isConflict && "ring-2 ring-danger-fg ring-offset-1",
        appointment.status === "cancelled" && "opacity-40 line-through"
      )}
      style={{
        top,
        height: Math.max(height, 24), // min 24px so the block is always visible
        borderLeftColor: color,
        backgroundColor: `color-mix(in srgb, ${color} 15%, transparent)`,
      }}
    >
      <p className="text-[11px] font-semibold text-text-primary truncate leading-tight">
        {appointment.customer_name}
      </p>
      {height > 36 && (
        <p className="text-[10px] text-text-secondary truncate leading-tight">
          {serviceName}
        </p>
      )}
      {isConflict && (
        <span className="absolute top-0.5 right-1 text-[9px] text-danger-fg font-bold">
          ⚠
        </span>
      )}
      {/* Resize handle — dragging this changes duration_minutes */}
      <div
        role="separator"
        aria-hidden
        className="absolute bottom-0 left-0 right-0 h-2 cursor-s-resize bg-transparent hover:bg-border-default rounded-b-md"
        onMouseDown={(e) => {
          e.stopPropagation();
          onResizeStart?.(e, appointment);
        }}
      />
    </div>
  );
}
```

- [ ] **Step 4: Run tests — verify PASS**

```bash
cd /Users/angelxlakra/dev/efs-salon/efs-salon-os/frontend && PATH="/Users/angelxlakra/.nvm/versions/node/v22.20.0/bin:$PATH" npm test -- --run src/components/calendar/__tests__/appointment-block.test.tsx 2>&1 | tail -5
```

Expected: 5 tests pass.

- [ ] **Step 5: Commit**

```bash
cd /Users/angelxlakra/dev/efs-salon/efs-salon-os && git add frontend/src/components/calendar/appointment-block.tsx frontend/src/components/calendar/__tests__/appointment-block.test.tsx && git commit -m "feat(calendar): AppointmentBlock (display + resize handle)"
```

---

## Task 4: DayView (staff swimlanes)

**Files:**
- Create: `frontend/src/components/calendar/day-view.tsx`
- Create: `frontend/src/components/calendar/__tests__/day-view.test.tsx`

### Why
DayView is the most complex view: a scrollable grid where each column = one staff member. Appointments are positioned absolutely within their staff's column by `top` (from `scheduled_at`) and `height` (from `duration_minutes`). An "Unassigned" column captures appointments with no `assigned_staff_id`.

---

- [ ] **Step 1: Write failing tests**

`frontend/src/components/calendar/__tests__/day-view.test.tsx`:

```tsx
import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { DayView } from "@/components/calendar/day-view";
import type { Appointment, StaffMember, ServiceItem } from "@/lib/api/appointments";

const staff: StaffMember[] = [
  { id: "s1", display_name: "Rahul", specialization: null, is_active: true, is_service_provider: true },
  { id: "s2", display_name: "Priya", specialization: null, is_active: true, is_service_provider: true },
];

const services: ServiceItem[] = [
  { id: "svc1", name: "Hair Cut", base_price: 30000, duration_minutes: 30, category_name: "Hair" },
];

const appt: Appointment = {
  id: "a1",
  ticket_number: "TKT-260505-001",
  visit_id: null,
  customer_id: null,
  customer_name: "Test Customer",
  customer_phone: null,
  service_id: "svc1",
  assigned_staff_id: "s1",
  scheduled_at: "2026-05-05T10:00:00+05:30",
  duration_minutes: 30,
  status: "scheduled",
  booking_notes: null,
  service_notes: null,
  checked_in_at: null,
  started_at: null,
  completed_at: null,
  cancelled_at: null,
  created_at: "2026-05-05T09:00:00+05:30",
  updated_at: "2026-05-05T09:00:00+05:30",
};

describe("DayView", () => {
  it("renders a header cell for each staff member", () => {
    render(
      <DayView
        appointments={[]}
        staff={staff}
        services={services}
        onAppointmentClick={vi.fn()}
        onSlotClick={vi.fn()}
        onAppointmentUpdate={vi.fn()}
      />
    );
    expect(screen.getByText("Rahul")).toBeInTheDocument();
    expect(screen.getByText("Priya")).toBeInTheDocument();
  });

  it("renders an Unassigned column header", () => {
    render(
      <DayView
        appointments={[]}
        staff={staff}
        services={services}
        onAppointmentClick={vi.fn()}
        onSlotClick={vi.fn()}
        onAppointmentUpdate={vi.fn()}
      />
    );
    expect(screen.getByText("Unassigned")).toBeInTheDocument();
  });

  it("renders an appointment block in the correct staff column", () => {
    render(
      <DayView
        appointments={[appt]}
        staff={staff}
        services={services}
        onAppointmentClick={vi.fn()}
        onSlotClick={vi.fn()}
        onAppointmentUpdate={vi.fn()}
      />
    );
    expect(screen.getByText("Test Customer")).toBeInTheDocument();
  });

  it("calls onSlotClick when an empty slot is clicked", async () => {
    const onSlotClick = vi.fn();
    render(
      <DayView
        appointments={[]}
        staff={staff}
        services={services}
        onAppointmentClick={vi.fn()}
        onSlotClick={onSlotClick}
        onAppointmentUpdate={vi.fn()}
      />
    );
    const slots = screen.getAllByTestId("grid-slot");
    await userEvent.click(slots[0]);
    expect(onSlotClick).toHaveBeenCalledOnce();
  });
});
```

- [ ] **Step 2: Run tests — verify FAIL**

```bash
cd /Users/angelxlakra/dev/efs-salon/efs-salon-os/frontend && PATH="/Users/angelxlakra/.nvm/versions/node/v22.20.0/bin:$PATH" npm test -- --run src/components/calendar/__tests__/day-view.test.tsx 2>&1 | tail -5
```

Expected: FAIL with "Cannot find module".

- [ ] **Step 3: Implement `day-view.tsx`**

`frontend/src/components/calendar/day-view.tsx`:

```tsx
"use client";

import * as React from "react";
import { TimeGrid } from "@/components/calendar/time-grid";
import { AppointmentBlock } from "@/components/calendar/appointment-block";
import {
  HOUR_HEIGHT,
  GRID_HEIGHT,
  DAY_START_HOUR,
  minutesToPx,
  timeToTopOffset,
  buildISO,
} from "@/components/calendar/utils";
import type { Appointment, StaffMember, ServiceItem } from "@/lib/api/appointments";
import { format } from "date-fns";
import { cn } from "@/lib/utils";

type DayViewProps = {
  appointments: Appointment[];
  staff: StaffMember[];
  services: ServiceItem[];
  date?: Date;
  onAppointmentClick: (appt: Appointment) => void;
  onSlotClick: (staffId: string | null, datetime: string) => void;
  onAppointmentUpdate: (id: string, patch: { scheduled_at?: string; duration_minutes?: number }) => void;
};

const COLUMN_MIN_WIDTH = 120; // px — drives horizontal scroll on mobile

export function DayView({
  appointments,
  staff,
  services,
  date = new Date(),
  onAppointmentClick,
  onSlotClick,
  onAppointmentUpdate,
}: DayViewProps) {
  const dateStr = format(date, "yyyy-MM-dd");

  // service lookup map
  const serviceMap = React.useMemo(
    () => new Map(services.map((s) => [s.id, s])),
    [services]
  );

  // All columns: each staff + "unassigned"
  const columns = React.useMemo(
    () => [...staff.map((s) => ({ id: s.id, label: s.display_name })),
           { id: null as null, label: "Unassigned" }],
    [staff]
  );

  // Group appointments by staff column
  const apptByColumn = React.useMemo(() => {
    const map = new Map<string | null, Appointment[]>();
    columns.forEach((c) => map.set(c.id, []));
    appointments.forEach((a) => {
      const key = a.assigned_staff_id ?? null;
      if (map.has(key)) map.get(key)!.push(a);
      else map.get(null)!.push(a); // unknown staff → unassigned
    });
    return map;
  }, [appointments, columns]);

  // Detect conflicts: two appointments overlap in the same column
  const conflictIds = React.useMemo(() => {
    const ids = new Set<string>();
    apptByColumn.forEach((colAppts) => {
      for (let i = 0; i < colAppts.length; i++) {
        for (let j = i + 1; j < colAppts.length; j++) {
          const a = colAppts[i];
          const b = colAppts[j];
          if (a.status === "cancelled" || b.status === "cancelled") continue;
          const aStart = new Date(a.scheduled_at).getTime();
          const aEnd = aStart + a.duration_minutes * 60_000;
          const bStart = new Date(b.scheduled_at).getTime();
          const bEnd = bStart + b.duration_minutes * 60_000;
          if (aStart < bEnd && bStart < aEnd) {
            ids.add(a.id);
            ids.add(b.id);
          }
        }
      }
    });
    return ids;
  }, [apptByColumn]);

  // Resize state
  const resizeRef = React.useRef<{
    apptId: string;
    startY: number;
    startDuration: number;
  } | null>(null);

  const handleResizeStart = React.useCallback(
    (e: React.MouseEvent, appt: Appointment) => {
      e.preventDefault();
      resizeRef.current = {
        apptId: appt.id,
        startY: e.clientY,
        startDuration: appt.duration_minutes,
      };
    },
    []
  );

  React.useEffect(() => {
    const onMouseMove = (e: MouseEvent) => {
      if (!resizeRef.current) return;
      const { apptId, startY, startDuration } = resizeRef.current;
      const deltaY = e.clientY - startY;
      const deltaMins = Math.round(((deltaY / HOUR_HEIGHT) * 60) / 15) * 15;
      const newDuration = Math.max(15, startDuration + deltaMins);
      // optimistic update via parent
      onAppointmentUpdate(apptId, { duration_minutes: newDuration });
    };
    const onMouseUp = () => { resizeRef.current = null; };
    window.addEventListener("mousemove", onMouseMove);
    window.addEventListener("mouseup", onMouseUp);
    return () => {
      window.removeEventListener("mousemove", onMouseMove);
      window.removeEventListener("mouseup", onMouseUp);
    };
  }, [onAppointmentUpdate]);

  const handleSlotClick = (colId: string | null, e: React.MouseEvent<HTMLDivElement>) => {
    const rect = (e.currentTarget as HTMLDivElement).getBoundingClientRect();
    const relY = e.clientY - rect.top;
    const totalMinutes = DAY_START_HOUR * 60 + Math.round(((relY / HOUR_HEIGHT) * 60) / 15) * 15;
    const h = Math.floor(totalMinutes / 60);
    const m = totalMinutes % 60;
    onSlotClick(colId, buildISO(dateStr, h, m));
  };

  return (
    <div className="flex flex-col h-full">
      {/* Sticky header row */}
      <div className="flex border-b border-border-default bg-surface-card sticky top-0 z-20">
        {/* Spacer for hour-label axis */}
        <div className="w-14 shrink-0 border-r border-border-subtle" />
        {/* Staff column headers */}
        <div className="flex overflow-x-auto">
          {columns.map((col) => (
            <div
              key={col.id ?? "unassigned"}
              className="border-r border-border-subtle px-2 py-2 text-center"
              style={{ minWidth: COLUMN_MIN_WIDTH }}
            >
              <span className="text-body-sm font-semibold text-text-primary truncate block">
                {col.label}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Scrollable grid body */}
      <div className="flex-1 overflow-y-auto overflow-x-auto">
        <TimeGrid>
          {/* Columns laid out horizontally */}
          <div className="flex absolute inset-0">
            {columns.map((col) => {
              const colAppts = apptByColumn.get(col.id) ?? [];
              return (
                <div
                  key={col.id ?? "unassigned"}
                  data-testid="grid-slot"
                  className="relative border-r border-border-subtle"
                  style={{ minWidth: COLUMN_MIN_WIDTH, height: GRID_HEIGHT }}
                  onClick={(e) => handleSlotClick(col.id, e)}
                >
                  {colAppts.map((appt) => (
                    <AppointmentBlock
                      key={appt.id}
                      appointment={appt}
                      serviceName={serviceMap.get(appt.service_id)?.name ?? "Service"}
                      top={timeToTopOffset(appt.scheduled_at)}
                      height={minutesToPx(appt.duration_minutes)}
                      onClick={onAppointmentClick}
                      isConflict={conflictIds.has(appt.id)}
                      onResizeStart={handleResizeStart}
                    />
                  ))}
                </div>
              );
            })}
          </div>
        </TimeGrid>
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Run tests — verify PASS**

```bash
cd /Users/angelxlakra/dev/efs-salon/efs-salon-os/frontend && PATH="/Users/angelxlakra/.nvm/versions/node/v22.20.0/bin:$PATH" npm test -- --run src/components/calendar/__tests__/day-view.test.tsx 2>&1 | tail -5
```

Expected: 4 tests pass.

- [ ] **Step 5: Commit**

```bash
cd /Users/angelxlakra/dev/efs-salon/efs-salon-os && git add frontend/src/components/calendar/day-view.tsx frontend/src/components/calendar/__tests__/day-view.test.tsx && git commit -m "feat(calendar): DayView (staff swimlanes + conflict detection + resize)"
```

---

## Task 5: WeekView

**Files:**
- Create: `frontend/src/components/calendar/week-view.tsx`

### Why
WeekView uses the same `TimeGrid` canvas but columns are calendar days instead of staff members. Appointments from all staff are mixed per day. This is primarily for planning — the DayView is the workhorse.

---

- [ ] **Step 1: Implement `week-view.tsx`**

`frontend/src/components/calendar/week-view.tsx`:

```tsx
"use client";

import * as React from "react";
import { TimeGrid } from "@/components/calendar/time-grid";
import { AppointmentBlock } from "@/components/calendar/appointment-block";
import {
  GRID_HEIGHT,
  minutesToPx,
  timeToTopOffset,
  buildISO,
  DAY_START_HOUR,
  HOUR_HEIGHT,
} from "@/components/calendar/utils";
import type { Appointment, StaffMember, ServiceItem } from "@/lib/api/appointments";
import { format, addDays, startOfWeek, isSameDay, isToday } from "date-fns";

const DAY_COLUMN_MIN_WIDTH = 100; // px

type WeekViewProps = {
  appointments: Appointment[];
  services: ServiceItem[];
  weekStart: Date;
  onAppointmentClick: (appt: Appointment) => void;
  onSlotClick: (staffId: null, datetime: string) => void;
};

export function WeekView({
  appointments,
  services,
  weekStart,
  onAppointmentClick,
  onSlotClick,
}: WeekViewProps) {
  const days = Array.from({ length: 7 }, (_, i) => addDays(weekStart, i));

  const serviceMap = React.useMemo(
    () => new Map(services.map((s) => [s.id, s])),
    [services]
  );

  const apptByDay = React.useMemo(() => {
    const map = new Map<string, Appointment[]>();
    days.forEach((d) => map.set(format(d, "yyyy-MM-dd"), []));
    appointments.forEach((a) => {
      const key = format(new Date(a.scheduled_at), "yyyy-MM-dd");
      map.get(key)?.push(a);
    });
    return map;
  }, [appointments, days]);

  const handleSlotClick = (
    day: Date,
    e: React.MouseEvent<HTMLDivElement>
  ) => {
    const rect = (e.currentTarget as HTMLDivElement).getBoundingClientRect();
    const relY = e.clientY - rect.top;
    const totalMinutes = DAY_START_HOUR * 60 + Math.round(((relY / HOUR_HEIGHT) * 60) / 15) * 15;
    const h = Math.floor(totalMinutes / 60);
    const m = totalMinutes % 60;
    onSlotClick(null, buildISO(format(day, "yyyy-MM-dd"), h, m));
  };

  return (
    <div className="flex flex-col h-full">
      {/* Sticky header */}
      <div className="flex border-b border-border-default bg-surface-card sticky top-0 z-20">
        <div className="w-14 shrink-0 border-r border-border-subtle" />
        <div className="flex overflow-x-auto">
          {days.map((day) => (
            <div
              key={format(day, "yyyy-MM-dd")}
              className={`border-r border-border-subtle px-2 py-2 text-center`}
              style={{ minWidth: DAY_COLUMN_MIN_WIDTH }}
            >
              <span className="text-[11px] text-text-muted block">{format(day, "EEE")}</span>
              <span
                className={`text-body-sm font-semibold block ${
                  isToday(day) ? "text-accent" : "text-text-primary"
                }`}
              >
                {format(day, "d")}
              </span>
            </div>
          ))}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto overflow-x-auto">
        <TimeGrid>
          <div className="flex absolute inset-0">
            {days.map((day) => {
              const key = format(day, "yyyy-MM-dd");
              const dayAppts = apptByDay.get(key) ?? [];
              return (
                <div
                  key={key}
                  className={`relative border-r border-border-subtle ${
                    isToday(day) ? "bg-accent-bg-soft/30" : ""
                  }`}
                  style={{ minWidth: DAY_COLUMN_MIN_WIDTH, height: GRID_HEIGHT }}
                  onClick={(e) => handleSlotClick(day, e)}
                >
                  {dayAppts.map((appt) => (
                    <AppointmentBlock
                      key={appt.id}
                      appointment={appt}
                      serviceName={serviceMap.get(appt.service_id)?.name ?? "Service"}
                      top={timeToTopOffset(appt.scheduled_at)}
                      height={minutesToPx(appt.duration_minutes)}
                      onClick={onAppointmentClick}
                      onResizeStart={() => {}}
                    />
                  ))}
                </div>
              );
            })}
          </div>
        </TimeGrid>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Run all tests to ensure no regression**

```bash
cd /Users/angelxlakra/dev/efs-salon/efs-salon-os/frontend && PATH="/Users/angelxlakra/.nvm/versions/node/v22.20.0/bin:$PATH" npm test -- --run 2>&1 | tail -5
```

Expected: all tests pass (count ≥ 149 + the new ones from T1–T4).

- [ ] **Step 3: Commit**

```bash
cd /Users/angelxlakra/dev/efs-salon/efs-salon-os && git add frontend/src/components/calendar/week-view.tsx && git commit -m "feat(calendar): WeekView (7-day grid with per-day columns)"
```

---

## Task 6: MonthOverview

**Files:**
- Create: `frontend/src/components/calendar/month-overview.tsx`

### Why
The spec says "Month as overview only" — this is a lightweight 6×7 day-cell grid, not a full calendar. Its only job is giving a high-level picture and allowing navigation to a specific day.

---

- [ ] **Step 1: Implement `month-overview.tsx`**

`frontend/src/components/calendar/month-overview.tsx`:

```tsx
"use client";

import * as React from "react";
import {
  format,
  startOfMonth,
  endOfMonth,
  startOfWeek,
  endOfWeek,
  addDays,
  isSameMonth,
  isSameDay,
  isToday,
} from "date-fns";
import type { Appointment } from "@/lib/api/appointments";
import { cn } from "@/lib/utils";

type MonthOverviewProps = {
  month: Date;
  appointments: Appointment[];
  onDayClick: (date: Date) => void;
  selectedDate?: Date;
};

export function MonthOverview({
  month,
  appointments,
  onDayClick,
  selectedDate,
}: MonthOverviewProps) {
  const monthStart = startOfMonth(month);
  const monthEnd = endOfMonth(month);
  const gridStart = startOfWeek(monthStart, { weekStartsOn: 1 });
  const gridEnd = endOfWeek(monthEnd, { weekStartsOn: 1 });

  // Count appointments per day
  const countByDay = React.useMemo(() => {
    const map = new Map<string, number>();
    appointments.forEach((a) => {
      const key = format(new Date(a.scheduled_at), "yyyy-MM-dd");
      map.set(key, (map.get(key) ?? 0) + 1);
    });
    return map;
  }, [appointments]);

  const days: Date[] = [];
  let d = gridStart;
  while (d <= gridEnd) {
    days.push(d);
    d = addDays(d, 1);
  }

  return (
    <div className="p-4">
      {/* Weekday header */}
      <div className="grid grid-cols-7 mb-1">
        {["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"].map((wd) => (
          <div key={wd} className="text-center text-[11px] text-text-muted py-1">
            {wd}
          </div>
        ))}
      </div>

      {/* Day cells */}
      <div className="grid grid-cols-7 gap-0.5">
        {days.map((day) => {
          const key = format(day, "yyyy-MM-dd");
          const count = countByDay.get(key) ?? 0;
          const inMonth = isSameMonth(day, month);
          const isSelected = selectedDate ? isSameDay(day, selectedDate) : false;
          const today = isToday(day);

          return (
            <button
              key={key}
              type="button"
              onClick={() => onDayClick(day)}
              className={cn(
                "flex flex-col items-center justify-center rounded-md p-1.5 min-h-[44px] text-[13px]",
                "transition-colors hover:bg-surface-row-hover",
                !inMonth && "opacity-30",
                today && "font-semibold text-accent",
                isSelected && "bg-accent-bg-soft ring-1 ring-accent"
              )}
            >
              <span>{format(day, "d")}</span>
              {count > 0 && (
                <span className="mt-0.5 h-1.5 w-1.5 rounded-full bg-accent" aria-label={`${count} appointments`} />
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
cd /Users/angelxlakra/dev/efs-salon/efs-salon-os && git add frontend/src/components/calendar/month-overview.tsx && git commit -m "feat(calendar): MonthOverview (dot-per-day overview grid)"
```

---

## Task 7: AppointmentFormDialog

**Files:**
- Create: `frontend/src/components/calendar/appointment-form-dialog.tsx`

### Why
All create and edit flows funnel through this dialog. It uses the V2 `Dialog` primitive (from Phase 0) and react-hook-form + zod for validation — same stack as other V2 forms.

---

- [ ] **Step 1: Implement `appointment-form-dialog.tsx`**

`frontend/src/components/calendar/appointment-form-dialog.tsx`:

```tsx
"use client";

import * as React from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod/v4";
import { format } from "date-fns";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Combobox } from "@/components/ui/combobox";
import { toast } from "sonner";
import {
  createAppointment,
  updateAppointment,
} from "@/lib/api/appointments";
import type { Appointment, StaffMember, ServiceItem } from "@/lib/api/appointments";

const schema = z.object({
  customer_name: z.string().min(2, "Name must be at least 2 characters"),
  customer_phone: z.string().min(10, "Enter a valid phone number").max(15),
  service_id: z.string().min(1, "Select a service"),
  assigned_staff_id: z.string().optional(),
  date: z.string().min(1, "Select a date"),
  time: z.string().min(1, "Select a time"),
  duration_minutes: z.coerce.number().min(15).max(480),
  booking_notes: z.string().optional(),
});

type FormValues = z.infer<typeof schema>;

type Props = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** Pre-fill date+time for "click slot to create" */
  defaultDatetime?: string;
  /** Pre-fill staff for the clicked column */
  defaultStaffId?: string;
  /** Non-null when editing an existing appointment */
  appointment?: Appointment;
  staff: StaffMember[];
  services: ServiceItem[];
  onSaved: (appt: Appointment) => void;
};

export function AppointmentFormDialog({
  open,
  onOpenChange,
  defaultDatetime,
  defaultStaffId,
  appointment,
  staff,
  services,
  onSaved,
}: Props) {
  const isEdit = !!appointment;

  const defaultDate = defaultDatetime
    ? format(new Date(defaultDatetime), "yyyy-MM-dd")
    : appointment
    ? format(new Date(appointment.scheduled_at), "yyyy-MM-dd")
    : format(new Date(), "yyyy-MM-dd");

  const defaultTime = defaultDatetime
    ? format(new Date(defaultDatetime), "HH:mm")
    : appointment
    ? format(new Date(appointment.scheduled_at), "HH:mm")
    : "10:00";

  const {
    register,
    handleSubmit,
    setValue,
    watch,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      customer_name: appointment?.customer_name ?? "",
      customer_phone: appointment?.customer_phone ?? "",
      service_id: appointment?.service_id ?? "",
      assigned_staff_id: appointment?.assigned_staff_id ?? defaultStaffId ?? "",
      date: defaultDate,
      time: defaultTime,
      duration_minutes: appointment?.duration_minutes ?? 30,
      booking_notes: appointment?.booking_notes ?? "",
    },
  });

  const selectedServiceId = watch("service_id");

  // Auto-fill duration when a service is chosen
  React.useEffect(() => {
    if (!selectedServiceId) return;
    const svc = services.find((s) => s.id === selectedServiceId);
    if (svc) setValue("duration_minutes", svc.duration_minutes);
  }, [selectedServiceId, services, setValue]);

  // Reset form when dialog opens with new defaults
  React.useEffect(() => {
    if (open) reset({
      customer_name: appointment?.customer_name ?? "",
      customer_phone: appointment?.customer_phone ?? "",
      service_id: appointment?.service_id ?? "",
      assigned_staff_id: appointment?.assigned_staff_id ?? defaultStaffId ?? "",
      date: defaultDate,
      time: defaultTime,
      duration_minutes: appointment?.duration_minutes ?? 30,
      booking_notes: appointment?.booking_notes ?? "",
    });
  }, [open]); // eslint-disable-line react-hooks/exhaustive-deps

  const onSubmit = async (values: FormValues) => {
    const scheduled_at = `${values.date}T${values.time}:00`;
    try {
      let saved: Appointment;
      if (isEdit && appointment) {
        saved = await updateAppointment(appointment.id, {
          service_id: values.service_id,
          assigned_staff_id: values.assigned_staff_id || undefined,
          scheduled_at,
          duration_minutes: values.duration_minutes,
          booking_notes: values.booking_notes || undefined,
        });
        toast.success("Appointment updated");
      } else {
        saved = await createAppointment({
          customer_name: values.customer_name,
          customer_phone: values.customer_phone,
          service_id: values.service_id,
          assigned_staff_id: values.assigned_staff_id || undefined,
          scheduled_at,
          duration_minutes: values.duration_minutes,
          booking_notes: values.booking_notes || undefined,
        });
        toast.success("Appointment booked");
      }
      onSaved(saved);
      onOpenChange(false);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Failed to save";
      toast.error(msg);
    }
  };

  const serviceOptions = services.map((s) => ({
    value: s.id,
    label: `${s.name} (${s.category_name})`,
  }));

  const staffOptions = [
    { value: "", label: "— Any staff —" },
    ...staff.map((s) => ({ value: s.id, label: s.display_name })),
  ];

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent size="md">
        <DialogHeader>
          <DialogTitle>{isEdit ? "Edit appointment" : "New appointment"}</DialogTitle>
        </DialogHeader>

        <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4 mt-2">
          {!isEdit && (
            <>
              <div className="grid grid-cols-2 gap-3">
                <div className="flex flex-col gap-1">
                  <Label htmlFor="customer_name">Customer name *</Label>
                  <Input id="customer_name" {...register("customer_name")} placeholder="Priya Sharma" />
                  {errors.customer_name && <p className="text-[11px] text-danger-fg">{errors.customer_name.message}</p>}
                </div>
                <div className="flex flex-col gap-1">
                  <Label htmlFor="customer_phone">Phone *</Label>
                  <Input id="customer_phone" {...register("customer_phone")} placeholder="9876543210" />
                  {errors.customer_phone && <p className="text-[11px] text-danger-fg">{errors.customer_phone.message}</p>}
                </div>
              </div>
            </>
          )}

          <div className="flex flex-col gap-1">
            <Label>Service *</Label>
            <Combobox
              options={serviceOptions}
              value={watch("service_id")}
              onChange={(v) => setValue("service_id", v, { shouldValidate: true })}
              placeholder="Search services…"
            />
            {errors.service_id && <p className="text-[11px] text-danger-fg">{errors.service_id.message}</p>}
          </div>

          <div className="flex flex-col gap-1">
            <Label>Staff</Label>
            <Combobox
              options={staffOptions}
              value={watch("assigned_staff_id") ?? ""}
              onChange={(v) => setValue("assigned_staff_id", v)}
              placeholder="Any staff"
            />
          </div>

          <div className="grid grid-cols-3 gap-3">
            <div className="flex flex-col gap-1">
              <Label htmlFor="date">Date *</Label>
              <Input id="date" type="date" {...register("date")} />
              {errors.date && <p className="text-[11px] text-danger-fg">{errors.date.message}</p>}
            </div>
            <div className="flex flex-col gap-1">
              <Label htmlFor="time">Time *</Label>
              <Input id="time" type="time" {...register("time")} step="900" />
              {errors.time && <p className="text-[11px] text-danger-fg">{errors.time.message}</p>}
            </div>
            <div className="flex flex-col gap-1">
              <Label htmlFor="duration_minutes">Duration (min)</Label>
              <Input id="duration_minutes" type="number" min={15} max={480} step={15} {...register("duration_minutes")} />
            </div>
          </div>

          <div className="flex flex-col gap-1">
            <Label htmlFor="booking_notes">Notes</Label>
            <Input id="booking_notes" {...register("booking_notes")} placeholder="Any special requests…" />
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variant="secondary" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" loading={isSubmitting}>
              {isEdit ? "Save changes" : "Book appointment"}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
```

- [ ] **Step 2: Run all tests — no regression**

```bash
cd /Users/angelxlakra/dev/efs-salon/efs-salon-os/frontend && PATH="/Users/angelxlakra/.nvm/versions/node/v22.20.0/bin:$PATH" npm test -- --run 2>&1 | tail -5
```

Expected: all tests pass.

- [ ] **Step 3: Commit**

```bash
cd /Users/angelxlakra/dev/efs-salon/efs-salon-os && git add frontend/src/components/calendar/appointment-form-dialog.tsx && git commit -m "feat(calendar): AppointmentFormDialog (create + edit with rhf + zod)"
```

---

## Task 8: Keyboard shortcuts hook

**Files:**
- Create: `frontend/src/components/calendar/use-calendar-keyboard.ts`

### Why
Keyboard shortcuts are registered globally in the page (not per-component) to avoid conflicting listener stacking. The hook returns nothing — it just attaches/detaches events.

---

- [ ] **Step 1: Implement `use-calendar-keyboard.ts`**

`frontend/src/components/calendar/use-calendar-keyboard.ts`:

```ts
"use client";

import { useEffect, useRef } from "react";

type CalendarView = "day" | "week" | "month";

type Handlers = {
  onNew: () => void;
  onPrev: () => void;
  onNext: () => void;
  onGoToday: () => void;
  onSetView: (view: CalendarView) => void;
};

/**
 * Registers keyboard shortcuts for the appointments calendar.
 *
 * Bindings (only fires when no input/textarea/select is focused):
 *   n          → new appointment
 *   ArrowLeft  → previous day/week/month
 *   ArrowRight → next day/week/month
 *   t          → go to today
 *   g then d   → day view
 *   g then w   → week view
 *   g then m   → month view
 */
export function useCalendarKeyboard(handlers: Handlers) {
  const pending = useRef<string | null>(null); // for chord (g then d/w/m)
  const chordTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    const isEditable = (el: Element | null) =>
      el instanceof HTMLInputElement ||
      el instanceof HTMLTextAreaElement ||
      el instanceof HTMLSelectElement ||
      (el instanceof HTMLElement && el.isContentEditable);

    const onKeyDown = (e: KeyboardEvent) => {
      if (isEditable(document.activeElement)) return;
      if (e.metaKey || e.ctrlKey || e.altKey) return;

      const key = e.key;

      // Chord: g + d/w/m
      if (pending.current === "g") {
        pending.current = null;
        if (chordTimer.current) clearTimeout(chordTimer.current);
        if (key === "d") { e.preventDefault(); handlers.onSetView("day"); return; }
        if (key === "w") { e.preventDefault(); handlers.onSetView("week"); return; }
        if (key === "m") { e.preventDefault(); handlers.onSetView("month"); return; }
      }

      if (key === "g") {
        pending.current = "g";
        chordTimer.current = setTimeout(() => { pending.current = null; }, 800);
        return;
      }

      switch (key) {
        case "n": e.preventDefault(); handlers.onNew(); break;
        case "ArrowLeft": e.preventDefault(); handlers.onPrev(); break;
        case "ArrowRight": e.preventDefault(); handlers.onNext(); break;
        case "t": e.preventDefault(); handlers.onGoToday(); break;
      }
    };

    window.addEventListener("keydown", onKeyDown);
    return () => {
      window.removeEventListener("keydown", onKeyDown);
      if (chordTimer.current) clearTimeout(chordTimer.current);
    };
  }, [handlers]);
}
```

- [ ] **Step 2: Commit**

```bash
cd /Users/angelxlakra/dev/efs-salon/efs-salon-os && git add frontend/src/components/calendar/use-calendar-keyboard.ts && git commit -m "feat(calendar): useCalendarKeyboard (n, ←/→, t, g+d/w/m shortcuts)"
```

---

## Task 9: Page scaffold and data wiring

**Files:**
- Create: `frontend/src/app/(shell)/dashboard/appointments/page.tsx`

### Why
The page root assembles all calendar components, fetches live data, and owns the view/date state. It's the final composition layer — everything built in T1–T8 plugs in here.

---

- [ ] **Step 1: Implement the appointments page**

`frontend/src/app/(shell)/dashboard/appointments/page.tsx`:

```tsx
"use client";

import * as React from "react";
import {
  format,
  addDays,
  subDays,
  addWeeks,
  subWeeks,
  addMonths,
  subMonths,
  startOfWeek,
  startOfMonth,
} from "date-fns";
import { ChevronLeft, ChevronRight, Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { DayView } from "@/components/calendar/day-view";
import { WeekView } from "@/components/calendar/week-view";
import { MonthOverview } from "@/components/calendar/month-overview";
import { AppointmentFormDialog } from "@/components/calendar/appointment-form-dialog";
import { useCalendarKeyboard } from "@/components/calendar/use-calendar-keyboard";
import {
  listAppointments,
  listActiveStaff,
  listServices,
  updateAppointment,
  cancelAppointment,
  checkInAppointment,
  startAppointment,
  completeAppointment,
} from "@/lib/api/appointments";
import type { Appointment, StaffMember, ServiceItem } from "@/lib/api/appointments";
import { toast } from "sonner";
import { cn } from "@/lib/utils";

type CalendarView = "day" | "week" | "month";

export default function AppointmentsPage() {
  const [view, setView] = React.useState<CalendarView>("day");
  const [date, setDate] = React.useState<Date>(new Date());

  // Data
  const [appointments, setAppointments] = React.useState<Appointment[]>([]);
  const [staff, setStaff] = React.useState<StaffMember[]>([]);
  const [services, setServices] = React.useState<ServiceItem[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);

  // Dialog state
  const [formOpen, setFormOpen] = React.useState(false);
  const [selectedAppt, setSelectedAppt] = React.useState<Appointment | undefined>();
  const [defaultDatetime, setDefaultDatetime] = React.useState<string | undefined>();
  const [defaultStaffId, setDefaultStaffId] = React.useState<string | undefined>();

  // ── Static data (staff + services, fetched once) ──────────────────────────
  React.useEffect(() => {
    Promise.all([listActiveStaff(), listServices()])
      .then(([s, svc]) => { setStaff(s); setServices(svc); })
      .catch(() => toast.error("Failed to load staff or services"));
  }, []);

  // ── Appointments (re-fetch when date or view changes) ─────────────────────
  const fetchAppointments = React.useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      // For week view, fetch each day in the week. For month, fetch the whole month.
      // Backend supports date= (single day). We fetch range by calling once per day.
      // For simplicity: day → fetch 1 day; week → fetch Mon–Sun; month → the month.
      let dates: string[] = [];
      if (view === "day") {
        dates = [format(date, "yyyy-MM-dd")];
      } else if (view === "week") {
        const ws = startOfWeek(date, { weekStartsOn: 1 });
        dates = Array.from({ length: 7 }, (_, i) =>
          format(addDays(ws, i), "yyyy-MM-dd")
        );
      } else {
        const ms = startOfMonth(date);
        const days = new Date(date.getFullYear(), date.getMonth() + 1, 0).getDate();
        dates = Array.from({ length: days }, (_, i) =>
          format(addDays(ms, i), "yyyy-MM-dd")
        );
      }
      const results = await Promise.all(dates.map(listAppointments));
      // Deduplicate by id (each call is a day, no overlap)
      const seen = new Set<string>();
      const all: Appointment[] = [];
      results.flat().forEach((a) => { if (!seen.has(a.id)) { seen.add(a.id); all.push(a); } });
      setAppointments(all);
    } catch {
      setError("Failed to load appointments");
    } finally {
      setLoading(false);
    }
  }, [date, view]);

  React.useEffect(() => { fetchAppointments(); }, [fetchAppointments]);

  // ── Navigation helpers ─────────────────────────────────────────────────────
  const navigate = (dir: "prev" | "next") => {
    if (view === "day") setDate((d) => (dir === "next" ? addDays(d, 1) : subDays(d, 1)));
    else if (view === "week") setDate((d) => (dir === "next" ? addWeeks(d, 1) : subWeeks(d, 1)));
    else setDate((d) => (dir === "next" ? addMonths(d, 1) : subMonths(d, 1)));
  };

  const pageTitle = React.useMemo(() => {
    if (view === "day") return format(date, "EEEE, d MMMM yyyy");
    if (view === "week") {
      const ws = startOfWeek(date, { weekStartsOn: 1 });
      return `Week of ${format(ws, "d MMM")}`;
    }
    return format(date, "MMMM yyyy");
  }, [view, date]);

  // ── Optimistic appointment update ─────────────────────────────────────────
  const handleAppointmentUpdate = React.useCallback(
    async (id: string, patch: { scheduled_at?: string; duration_minutes?: number }) => {
      // Optimistic: update local state immediately
      setAppointments((prev) =>
        prev.map((a) => (a.id === id ? { ...a, ...patch } : a))
      );
      try {
        const updated = await updateAppointment(id, patch);
        setAppointments((prev) => prev.map((a) => (a.id === id ? updated : a)));
      } catch {
        toast.error("Failed to update appointment");
        fetchAppointments(); // rollback by re-fetching
      }
    },
    [fetchAppointments]
  );

  // ── Form interactions ─────────────────────────────────────────────────────
  const openNewForm = (staffId?: string, datetime?: string) => {
    setSelectedAppt(undefined);
    setDefaultStaffId(staffId ?? undefined);
    setDefaultDatetime(datetime ?? `${format(date, "yyyy-MM-dd")}T10:00:00`);
    setFormOpen(true);
  };

  const handleSlotClick = (staffId: string | null, datetime: string) => {
    openNewForm(staffId ?? undefined, datetime);
  };

  const handleAppointmentClick = (appt: Appointment) => {
    setSelectedAppt(appt);
    setDefaultDatetime(undefined);
    setDefaultStaffId(undefined);
    setFormOpen(true);
  };

  const handleFormSaved = (appt: Appointment) => {
    setAppointments((prev) => {
      const exists = prev.find((a) => a.id === appt.id);
      if (exists) return prev.map((a) => (a.id === appt.id ? appt : a));
      return [...prev, appt];
    });
  };

  // ── Keyboard shortcuts ────────────────────────────────────────────────────
  useCalendarKeyboard({
    onNew: () => openNewForm(),
    onPrev: () => navigate("prev"),
    onNext: () => navigate("next"),
    onGoToday: () => setDate(new Date()),
    onSetView: setView,
  });

  // ── Render ────────────────────────────────────────────────────────────────
  const weekStart = startOfWeek(date, { weekStartsOn: 1 });

  return (
    <div className="flex flex-col h-[calc(100dvh-3rem)] overflow-hidden">
      {/* Topbar */}
      <div className="flex items-center justify-between gap-3 px-4 py-2 border-b border-border-subtle bg-surface-card shrink-0">
        {/* View switcher */}
        <div className="flex rounded-md border border-border-default overflow-hidden">
          {(["day", "week", "month"] as CalendarView[]).map((v) => (
            <button
              key={v}
              type="button"
              onClick={() => setView(v)}
              className={cn(
                "px-3 py-1 text-[13px] font-medium capitalize transition-colors",
                v === view
                  ? "bg-accent text-accent-fg"
                  : "text-text-secondary hover:bg-surface-row-hover"
              )}
            >
              {v}
            </button>
          ))}
        </div>

        {/* Date nav */}
        <div className="flex items-center gap-1">
          <Button variant="icon" size="sm" onClick={() => navigate("prev")} aria-label="Previous">
            <ChevronLeft className="size-4" />
          </Button>
          <button
            type="button"
            onClick={() => setDate(new Date())}
            className="text-body-sm font-medium text-text-primary px-2 hover:text-accent min-w-[160px] text-center"
          >
            {pageTitle}
          </button>
          <Button variant="icon" size="sm" onClick={() => navigate("next")} aria-label="Next">
            <ChevronRight className="size-4" />
          </Button>
        </div>

        {/* New appointment */}
        <Button onClick={() => openNewForm()} size="sm" leadingIcon={<Plus className="size-3.5" />}>
          New
        </Button>
      </div>

      {/* Content area */}
      <div className="flex-1 overflow-hidden">
        {loading ? (
          <div className="p-6 flex flex-col gap-3">
            <Skeleton shape="text" width="40%" />
            <Skeleton shape="row" />
            <Skeleton shape="row" />
            <Skeleton shape="row" />
          </div>
        ) : error ? (
          <div className="p-6 text-danger-fg text-body-sm">{error}</div>
        ) : view === "day" ? (
          <DayView
            appointments={appointments}
            staff={staff}
            services={services}
            date={date}
            onAppointmentClick={handleAppointmentClick}
            onSlotClick={handleSlotClick}
            onAppointmentUpdate={handleAppointmentUpdate}
          />
        ) : view === "week" ? (
          <WeekView
            appointments={appointments}
            services={services}
            weekStart={weekStart}
            onAppointmentClick={handleAppointmentClick}
            onSlotClick={handleSlotClick}
          />
        ) : (
          <MonthOverview
            month={date}
            appointments={appointments}
            onDayClick={(d) => { setDate(d); setView("day"); }}
            selectedDate={date}
          />
        )}
      </div>

      {/* Form dialog */}
      <AppointmentFormDialog
        open={formOpen}
        onOpenChange={setFormOpen}
        appointment={selectedAppt}
        defaultDatetime={defaultDatetime}
        defaultStaffId={defaultStaffId}
        staff={staff}
        services={services}
        onSaved={handleFormSaved}
      />
    </div>
  );
}
```

- [ ] **Step 2: Run all tests — no regression**

```bash
cd /Users/angelxlakra/dev/efs-salon/efs-salon-os/frontend && PATH="/Users/angelxlakra/.nvm/versions/node/v22.20.0/bin:$PATH" npm test -- --run 2>&1 | tail -5
```

Expected: all tests pass (≥149 + new from T1–T4).

- [ ] **Step 3: Verify tsc baseline unchanged**

```bash
cd /Users/angelxlakra/dev/efs-salon/efs-salon-os/frontend && PATH="/Users/angelxlakra/.nvm/versions/node/v22.20.0/bin:$PATH" npx tsc --noEmit 2>&1 | grep -c "error TS"
```

Expected: 162 (no new errors introduced).

- [ ] **Step 4: Boot dev server and manually verify**

```bash
cd /Users/angelxlakra/dev/efs-salon/efs-salon-os/frontend && PATH="/Users/angelxlakra/.nvm/versions/node/v22.20.0/bin:$PATH" npm run dev 2>&1 &
```

Navigate to `http://localhost:3000/dashboard/appointments`. Verify:
- Day view renders with staff columns and hour axis
- ← Today → navigation changes the title
- `n` key opens the new appointment dialog
- `g d` / `g w` switches views
- `←` / `→` keys navigate

Stop the server after checking.

- [ ] **Step 5: Commit**

```bash
cd /Users/angelxlakra/dev/efs-salon/efs-salon-os && git add frontend/src/app/\(shell\)/dashboard/appointments/page.tsx && git commit -m "feat(appointments): page scaffold — day/week/month views + data wiring"
```

---

## Task 10: Drag-to-reschedule with @dnd-kit

**Files:**
- Modify: `frontend/src/components/calendar/appointment-block.tsx` — wrap in `useDraggable`
- Modify: `frontend/src/components/calendar/day-view.tsx` — wrap DnDContext + Droppable slots
- Modify: `frontend/src/components/calendar/week-view.tsx` — wrap DnDContext + Droppable slots

### Why
`@dnd-kit/core` was installed in T1. Now we activate it. The appointment block becomes a `Draggable`; each time slot cell becomes a `Droppable`. On `DragEnd`, we compute the new `scheduled_at` from the drop target's `id` (encoded as `{staffId}:{dateStr}:{hour}:{minute}`) and call the parent's `onAppointmentUpdate`.

---

- [ ] **Step 1: Add DnD wrappers to AppointmentBlock**

Modify `frontend/src/components/calendar/appointment-block.tsx` — add `useDraggable` from `@dnd-kit/core`:

Change the import section to add:
```tsx
import { useDraggable } from "@dnd-kit/core";
import { CSS } from "@dnd-kit/utilities";
```

Replace the outer `<div>` in `AppointmentBlock` with a draggable wrapper. Add `isDraggable` optional prop (defaults to `true`) so `WeekView` can opt out:

```tsx
// Add to AppointmentBlockProps:
isDraggable?: boolean;

// Inside the component, before return:
const { attributes, listeners, setNodeRef, transform, isDragging: dndIsDragging } = useDraggable({
  id: appointment.id,
  data: { appointment },
  disabled: !isDraggable,
});

const style = {
  top,
  height: Math.max(height, 24),
  borderLeftColor: color,
  backgroundColor: `color-mix(in srgb, ${color} 15%, transparent)`,
  transform: CSS.Translate.toString(transform),
};

// Replace the outer div's ref + style + isDragging:
<div
  ref={setNodeRef}
  {...attributes}
  {...listeners}
  style={style}
  data-conflict={isConflict || undefined}
  data-status={appointment.status}
  onClick={(e) => { if (!dndIsDragging) onClick(appointment); }}
  onKeyDown={(e) => e.key === "Enter" && onClick(appointment)}
  className={cn(
    "absolute left-0.5 right-0.5 rounded-md px-2 py-1 cursor-grab select-none overflow-hidden",
    "border-l-[3px] transition-opacity",
    "hover:brightness-95 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent",
    (isDragging || dndIsDragging) && "opacity-50 cursor-grabbing z-50",
    isConflict && "ring-2 ring-danger-fg ring-offset-1",
    appointment.status === "cancelled" && "opacity-40"
  )}
>
```

- [ ] **Step 2: Wrap DayView in DndContext + make slots Droppable**

Modify `frontend/src/components/calendar/day-view.tsx`:

Add imports:
```tsx
import { DndContext, DragEndEvent, pointerWithin } from "@dnd-kit/core";
import { useDroppable } from "@dnd-kit/core";
```

Replace the inner column `<div>` with a `DroppableSlot` sub-component:
```tsx
// Add this above DayView:
function DroppableSlot({
  id,
  children,
  style,
  className,
  onClick,
}: {
  id: string;
  children: React.ReactNode;
  style?: React.CSSProperties;
  className?: string;
  onClick?: (e: React.MouseEvent<HTMLDivElement>) => void;
}) {
  const { setNodeRef, isOver } = useDroppable({ id });
  return (
    <div
      ref={setNodeRef}
      data-testid="grid-slot"
      className={cn(className, isOver && "bg-accent-bg-soft/40")}
      style={style}
      onClick={onClick}
    >
      {children}
    </div>
  );
}
```

Wrap the whole `DayView` JSX in:
```tsx
<DndContext collisionDetection={pointerWithin} onDragEnd={handleDragEnd}>
  {/* ...existing JSX... */}
</DndContext>
```

Add `handleDragEnd`:
```tsx
const handleDragEnd = React.useCallback(
  (event: DragEndEvent) => {
    const { active, over } = event;
    if (!over || !active.data.current) return;
    const appt = active.data.current.appointment as Appointment;

    // over.id format: "{staffId|null}::{dateStr}::{hour}::{minute}"
    const [staffId, dateStr, hourStr, minuteStr] = String(over.id).split("::");
    if (!dateStr) return;
    const newScheduledAt = buildISO(dateStr, parseInt(hourStr), parseInt(minuteStr));
    const newStaffId = staffId === "null" ? undefined : staffId;

    onAppointmentUpdate(appt.id, {
      scheduled_at: newScheduledAt,
      ...(newStaffId !== appt.assigned_staff_id && { assigned_staff_id: newStaffId }),
    });
  },
  [onAppointmentUpdate]
);
```

Update each column's `<DroppableSlot>` to use id `{col.id ?? "null"}::{dateStr}::{h}::{m}` where `h` and `m` are derived from the cursor position on click. For the click-based approach, keep the existing `handleSlotClick` handler.

Note: Since the droppable ID needs to encode position, use the column ID alone for the droppable (the `handleDragEnd` uses the drag-over position from `pointerWithin` event offset):

```tsx
// Simpler approach: droppable ID = column id, use event delta to compute time
const handleDragEnd = React.useCallback(
  (event: DragEndEvent) => {
    const { active, over, delta } = event;
    if (!over || !active.data.current) return;
    const appt: Appointment = active.data.current.appointment;
    const colId = String(over.id) === "null" ? null : String(over.id);

    // Compute new scheduled_at from original time + delta.y
    const originalTop = timeToTopOffset(appt.scheduled_at);
    const newTop = originalTop + delta.y;
    const originalDate = new Date(appt.scheduled_at);
    const dayStr = format(originalDate, "yyyy-MM-dd");
    const deltaMins = pxToMinutes(Math.max(0, newTop));
    const newHour = Math.floor((DAY_START_HOUR * 60 + deltaMins) / 60);
    const newMin = (DAY_START_HOUR * 60 + deltaMins) % 60;
    const newScheduledAt = buildISO(dayStr, newHour, newMin);

    onAppointmentUpdate(appt.id, { scheduled_at: newScheduledAt });
  },
  [onAppointmentUpdate]
);
```

- [ ] **Step 3: Run all tests — verify still PASS**

```bash
cd /Users/angelxlakra/dev/efs-salon/efs-salon-os/frontend && PATH="/Users/angelxlakra/.nvm/versions/node/v22.20.0/bin:$PATH" npm test -- --run 2>&1 | tail -5
```

Expected: all tests pass (the DnD context renders silently in jsdom).

- [ ] **Step 4: Boot dev server and smoke-test drag**

```bash
cd /Users/angelxlakra/dev/efs-salon/efs-salon-os/frontend && PATH="/Users/angelxlakra/.nvm/versions/node/v22.20.0/bin:$PATH" npm run dev 2>&1 &
```

- Create a test appointment via the form dialog
- Drag it to a different time slot — confirm the optimistic update moves the block
- Confirm a PATCH request fires (check network tab)

- [ ] **Step 5: Commit**

```bash
cd /Users/angelxlakra/dev/efs-salon/efs-salon-os && git add frontend/src/components/calendar/appointment-block.tsx frontend/src/components/calendar/day-view.tsx frontend/src/components/calendar/week-view.tsx && git commit -m "feat(calendar): drag-to-reschedule via @dnd-kit/core"
```

---

## Task 11: Mobile responsiveness

**Files:**
- Modify: `frontend/src/app/(shell)/dashboard/appointments/page.tsx` — mobile topbar layout
- Modify: `frontend/src/components/calendar/day-view.tsx` — ensure `overflow-x-auto` + `min-w-[120px]` per column

### Why
The spec says "Mobile: day view only, horizontal scroll across staff." The horizontal scroll is already implied by `min-width: COLUMN_MIN_WIDTH` on each column. This task verifies the breakpoint behaviour and adjusts the topbar for narrow screens.

---

- [ ] **Step 1: Verify DayView is scrollable at 390px**

In the browser devtools, set viewport to 390×844 (iPhone 14). Verify:
- The staff column headers scroll horizontally in sync with the grid body
- Bottom nav is not overlapped (it reserves `pb-safe` via the shell layout from Phase 1)
- Each column is at least 120px wide and appointment blocks are readable

- [ ] **Step 2: Tighten the topbar for mobile**

In `appointments/page.tsx`, wrap the view switcher to hide on mobile (day is the default view on mobile):

```tsx
{/* View switcher — hidden on mobile (day view only per spec) */}
<div className="hidden sm:flex rounded-md border border-border-default overflow-hidden">
  {/* ...existing switcher... */}
</div>
```

The date nav and New button remain visible at all widths.

- [ ] **Step 3: Commit**

```bash
cd /Users/angelxlakra/dev/efs-salon/efs-salon-os && git add frontend/src/app/\(shell\)/dashboard/appointments/page.tsx frontend/src/components/calendar/day-view.tsx && git commit -m "feat(appointments): mobile — day-only on narrow + horizontal staff scroll"
```

---

## Task 12: Verification + docs update

**Files:**
- Modify: `docs/design_system.md` — append Phase 2 changelog row

### Why
Final health check before the branch is ready to review. Must confirm: tsc baseline unchanged, all tests pass, build succeeds, design-system changelog updated.

---

- [ ] **Step 1: Run tests**

```bash
cd /Users/angelxlakra/dev/efs-salon/efs-salon-os/frontend && PATH="/Users/angelxlakra/.nvm/versions/node/v22.20.0/bin:$PATH" npm test -- --run 2>&1 | tail -5
```

Expected: all tests pass. Test count should be ≥ 149 + ~22 new tests = ~171+.

- [ ] **Step 2: tsc check**

```bash
cd /Users/angelxlakra/dev/efs-salon/efs-salon-os/frontend && PATH="/Users/angelxlakra/.nvm/versions/node/v22.20.0/bin:$PATH" npx tsc --noEmit 2>&1 | grep -c "error TS"
```

Expected: 162 (unchanged from Phase 0/1 baseline).

- [ ] **Step 3: Build check**

```bash
cd /Users/angelxlakra/dev/efs-salon/efs-salon-os/frontend && PATH="/Users/angelxlakra/.nvm/versions/node/v22.20.0/bin:$PATH" npm run build 2>&1 | tail -8
```

Expected: build succeeds with no TypeScript errors.

- [ ] **Step 4: Manual walk-through (5 minutes)**

With the dev server running, verify the following:

| Check | Expected |
|-------|----------|
| `/dashboard/appointments` loads | Day view with staff columns |
| `n` key | Opens new appointment dialog |
| `←/→` keys | Navigates by day |
| `g w` chord | Switches to week view |
| `g d` chord | Switches to day view |
| Click empty slot | Dialog opens, date/time pre-filled |
| Create an appointment | Block appears in correct column at correct time |
| Click appointment block | Edit dialog opens pre-filled |
| Drag appointment to new time | Block moves, PATCH fires |
| Conflicting appointments | Both blocks get red ring |
| 390px viewport | Columns scroll horizontally, bottom nav clear |

- [ ] **Step 5: Update design_system.md changelog**

In `docs/design_system.md`, find the `## 13. Changelog` section and append:

```markdown
| 2026-05-02 | Phase 2 landed: Appointments page (native V2 — first page designed in V2 without retrofitting V1 chrome). Ships: `TimeGrid` primitive (64px/hr, 8AM–9PM), `AppointmentBlock` (data-viz service colours, conflict ring, resize handle), `DayView` (staff swimlanes + conflict detection + @dnd-kit drag-to-reschedule + mouse-event resize), `WeekView` (7-day column grid), `MonthOverview` (dot-per-day navigator), `AppointmentFormDialog` (rhf + zod, service/staff Combobox, auto-fills duration), `useCalendarKeyboard` (n/←/→/t/gd/gw/gm), mobile day-only with horizontal staff scroll. New dep: @dnd-kit/core + @dnd-kit/utilities. tsc baseline 162 unchanged. Tests: +22 across utils, time-grid, appointment-block, day-view. | Angel + Claude |
```

- [ ] **Step 6: Commit**

```bash
cd /Users/angelxlakra/dev/efs-salon/efs-salon-os && git add docs/design_system.md && git commit -m "docs(design-system): mark Phase 2 complete"
```

---

## Phase 2 definition of done

- [ ] `npm test -- --run` — all tests pass, count ≥ 171
- [ ] `npx tsc --noEmit | grep -c "error TS"` — 162 (unchanged)
- [ ] `npm run build` — succeeds with no TypeScript errors
- [ ] `/dashboard/appointments` — day view loads with staff swimlanes
- [ ] Create appointment via click-to-create → appears in grid
- [ ] Drag appointment to new slot → PATCH fires and block moves
- [ ] Conflicting appointments show red ring on both blocks
- [ ] `n` / `←` / `→` / `g w` / `g d` keyboard shortcuts work
- [ ] 390px viewport — columns scroll horizontally, bottom nav not overlapped
- [ ] `docs/design_system.md §13` — Phase 2 changelog row present
