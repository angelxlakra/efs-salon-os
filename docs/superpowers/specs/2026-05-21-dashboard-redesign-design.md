# Dashboard Redesign — Design Spec

**Date:** 2026-05-21  
**Status:** Approved  
**Scope:** `frontend/src/app/(shell)/dashboard/page.tsx` and related dashboard components

---

## Goal

Redesign the main "Today" dashboard to match a warmer, more premium visual language inspired by the provided mockup. Simultaneously add an "Up Next" upcoming appointments panel and move the Staff Queue into the right sidebar. No backend changes.

---

## Visual Design

### Color Tokens (new CSS custom properties on `[data-theme="light"]`)

| Token | Value | Usage |
|---|---|---|
| `--color-dashboard-bg` | `#f5f0e8` | Page background (replaces `bg-surface-page`) |
| `--color-dashboard-card` | `#fffdf9` | Card surfaces |
| `--color-dashboard-border` | `#e8dfc8` | Card borders, dividers |
| `--color-dashboard-muted` | `#f0e8d8` | Progress tracks, row backgrounds |
| `--color-dashboard-gold` | `#c9a84c` | Gold accent (live dots, rings, buttons) |
| `--color-dashboard-gold-light` | `#e8dfc8` | Tier chip backgrounds |
| `--color-dashboard-ink-3` | `#6b5a3a` | Service names, secondary text |
| `--color-dashboard-ink-4` | `#8b7d5e` | Tertiary text |
| `--color-dashboard-ink-5` | `#a08f70` | Muted labels, overlines |

These tokens are **dashboard-scoped only** — defined under a `.dashboard-page` wrapper class so they don't bleed into other pages.

### Typography

Two font families loaded from Google Fonts (add to `frontend/src/app/layout.tsx` `<head>`):

- **Cormorant Garamond** — weights 300, 400, 500 (roman + italic) — all numerals and editorial phrases
- **DM Sans** — weights 400–800 — all labels, UI text, buttons, names

**Numeral CSS recipe** (applied to every number on the dashboard):
```css
font-family: 'Cormorant Garamond', serif;
font-weight: 300;
letter-spacing: -1px;
line-height: 0.95;
font-variant-numeric: tabular-nums;
```

**Size scale by context:**

| Context | Size | Weight | Notes |
|---|---|---|---|
| Hero revenue (₹4,977) | 86px | 300 | Largest element on page |
| "Behind by" warning numeral | 42px | 400 | Slightly heavier for urgency |
| Ring center value | 34px | 300 | |
| At-a-glance mini values | 22px | 300 | |
| Card totals | 20px | 500 | Slightly heavier for action context |
| Slide-over grand total | 40px | 300 | Future use |
| Appointment times (Up Next) | 17px | 300 | |
| Service prices in rows | 14px | 400 | |
| Queue elapsed times | 14px | 300 | |

**Editorial vs. data split:**
- **Italic Cormorant 300** — narrative phrases only: "Behind by", "Three rings to close.", "The next guests through the door." These carry voice and judgment.
- **Roman Cormorant** — all hard numbers. These carry data.

**Label recipe** (DM Sans overline above every numeral block):
```css
font-family: 'DM Sans', sans-serif;
font-size: 10px;
letter-spacing: 3px;
text-transform: uppercase;
color: rgba(28, 16, 76, 0.4);
font-weight: 500;
```

**Tabular numerals** (`font-variant-numeric: tabular-nums`) required on every numeric surface.

---

## Topbar

The topbar spans full width above the main/sidebar split.

- **Title:** "Today" — DM Sans 22px 800 weight
- **Clock/date:** DM Sans 11px, `var(--ink-5)`
- **Search bar:** `flex:1`, min `360px`, max `480px`. Background `var(--cream-card)`, `1.5px` border, `border-radius:10px`, `padding: 9px 16px 9px 38px`, SVG search icon inset left at `12px`. Font 13px DM Sans. Subtle `box-shadow: 0 1px 3px rgba(28,16,76,0.06)`.
- **+ New Walk-in button:** `var(--ink)` background, white text, DM Sans 12px 700, `border-radius:8px`, `padding: 9px 16px`

---

## Layout

```
┌─────────────────────────────────────────┬──────────────┐
│  Topbar: Today · clock · search · + btn │              │
├─────────────────────────────────────────┤              │
│  Stats bar (3 panels)                   │  Up Next     │
│  ┌──────────┬──────────┬─────────────┐  │  (max 5)     │
│  │ Revenue  │  Pace    │  Right Now  │  │              │
│  └──────────┴──────────┴─────────────┘  │  ──────────  │
│                                         │  Staff Queue │
│  Goals rings + contextual message       │  (per-staff  │
│                                         │   lanes)     │
│  "In service, right now"                │              │
│  ┌──────┬──────┐                        │              │
│  │ card │ card │  2-col grid            │              │
│  ├──────┼──────┤                        │              │
│  │ card │ card │                        │              │
│  └──────┴──────┘                        │              │
└─────────────────────────────────────────┴──────────────┘
```

- Main content: `flex-1`, `padding: 14px`, `gap: 12px`
- Right sidebar: `width: 256px`, `flex-shrink: 0`, `border-left`, sticky/full-height
- Sidebar split: "Up Next" top section + "Staff Queue" bottom section, separated by a border

---

## Components

### New: `UpNextPanel`

**File:** `frontend/src/components/dashboard/up-next-panel.tsx`  
**Self-contained** — manages its own data fetching (Approach A).

**Data fetching (on mount + every 2 min):**
1. `listAppointments(today, status='scheduled')` — requires updating `listAppointments` to accept optional `status` param
2. `listActiveStaff()` — for staff name lookup (Map<staffId, name>)
3. `listServices()` — for service name lookup (Map<serviceId, name>)

All three functions already exist in `frontend/src/lib/api/appointments.ts`.

**Display logic:**
- Filter to appointments where `scheduled_at > now` (exclude past-scheduled)
- Sort by `scheduled_at` ASC
- Cap display at **5 rows** (show "N more today" hint if more exist)
- Compute countdown: `Math.floor((scheduledAt - now) / 60000)` minutes, updated every minute via `setInterval`

**Each row:**
- Time (`HH:mm`) + countdown ("in Xm")
- Gold circle dot
- Customer name + service name + staff name
- No tier badge (appointment type doesn't carry `total_visits` without an extra customer fetch — deferred to future enhancement)

**On row click:** opens `CheckInDialog`

**States:** loading (skeleton rows), error (subtle message), empty ("No appointments scheduled for the rest of today"), all-past ("All done for today")

---

### New: `CheckInDialog`

**File:** `frontend/src/components/dashboard/checkin-dialog.tsx`  
A lightweight modal triggered by tapping a row in `UpNextPanel`.

**Contents:**
- Customer name, service, staff, scheduled time
- "Check In" button → calls `checkInAppointment(id)` (already exists in `appointments.ts`)
- On success: removes the row from Up Next list (optimistic), shows toast

---

### Modified: `ActiveCustomerCard`

**File:** `frontend/src/components/dashboard/active-customer-card.tsx`  
Restyled to match the new visual language. **No logic changes** — the per-service start/complete buttons already exist.

Visual changes only:
- Warm cream card background + gold border when `live`
- `LIVE` badge with animated gold dot (replaces current neutral badge)
- `CHECKED IN · WAITING` state shown distinctly
- Per-service rows: status dot (gold animated = in-progress, grey = waiting, green = done) + ▶ / ✓ action buttons
- Service progress bar (gold fill, cream track)
- Total + "End & Checkout" footer (button disabled until `all_completed`)
- "Start Services" button (gold) for fully-waiting sessions

---

### Modified: `ServiceQueue` → sidebar variant

**File:** `frontend/src/components/dashboard/service-queue.tsx`  
Add a `variant="sidebar"` prop. In sidebar mode, renders staff lanes vertically (one per row) instead of a horizontal grid, to fit the 256px sidebar width.

---

### Modified: `StatCard` → replaced by inline stats bar

The current `StatCard` grid is removed and replaced with a single 3-panel stats bar card:

| Panel | Content |
|---|---|
| Revenue | Large `₹X,XXX` number, ↓/↑ vs yesterday, progress bar, "X% of target" |
| Pace | Instrument Serif italic "Behind/Ahead by ~₹X,XXX", one-line context note |
| Right Now | 4 operational rows: Active services, Checked in waiting, Pending bills, Avg. bill (7d) |

**Pace derivation** (no new API call): uses existing `comparison.revenue_change_paise` (already fetched). If negative → "Behind by ~₹X,XXX" in red; if positive → "Ahead by ~₹X,XXX" in green.

---

### Modified: `DualRadialGoals` → 3-ring layout

**File:** `frontend/src/components/dashboard/radial-goal-progress.tsx`  
Extend to render 3 rings (Revenue, Services, Customers) instead of 2. Add contextual message panel alongside the rings using Instrument Serif italic.

**Contextual message logic:**
- Derived entirely from existing fetched data: `stats`, `comparison`, `settings`
- Pattern: "Hit your target X of 5 [weekdays]. Typical [weekday] closes N services across M customers. At X% by noon — [assessment]."
- Assessment: `< 20%` → "time to push", `20–40%` → "within striking range", `> 40%` → "on track"

---

### Dashboard page layout

**File:** `frontend/src/app/(shell)/dashboard/page.tsx`

Changes:
1. Add `dashboard-page` wrapper class for scoped tokens
2. Replace stat card grid with 3-panel `StatsBar` component
3. Replace `DualRadialGoals` section with updated 3-ring component
4. Replace "Active Customers" grid with restyled `ActiveCustomerCard` components
5. Remove `ServiceQueue` from main content
6. Add `flex` layout: main content + `UpNextPanel` sidebar column containing `ServiceQueue` below it
7. Remove `HourlyTrendChart` and `ServiceDistributionChart` sections — moved out of scope (too much vertical real estate for a redesigned Today page; can be revisited in a Reports tab)

---

## API Changes

### `frontend/src/lib/api/appointments.ts`

```ts
// Before
export async function listAppointments(date: string): Promise<Appointment[]>

// After
export async function listAppointments(
  date: string,
  status?: AppointmentStatus
): Promise<Appointment[]>
```

Passes `status` as a query param when provided. Fully backwards-compatible.

---

## What's Preserved

- All walk-in session state and workflow (start, complete, checkout)
- Per-service start/complete buttons on `ActiveCustomerCard` (already exist — restyled only)
- Birthday banner (stays **above** the stats bar, same position as today — restyled to warm color scheme only)
- Poll interval (10s for active sessions, 2 min for Up Next)
- Role-based visibility (`canManageServices` check on action buttons)

---

## Out of Scope

- Tier badges on Up Next rows (requires customer fetch per appointment — future enhancement)
- Hourly revenue chart and Top Services chart (remain available on a future Analytics/Reports section)
- Dark mode adaptation of new tokens (follow-up task)
- Mobile responsiveness of the new sidebar layout (follow-up task)
- Backend changes of any kind

---

## Files Touched

| File | Change type |
|---|---|
| `frontend/src/lib/api/appointments.ts` | Minor — add optional `status` param |
| `frontend/src/components/dashboard/up-next-panel.tsx` | New |
| `frontend/src/components/dashboard/checkin-dialog.tsx` | New |
| `frontend/src/components/dashboard/active-customer-card.tsx` | Restyle only |
| `frontend/src/components/dashboard/service-queue.tsx` | Add `variant` prop |
| `frontend/src/components/dashboard/radial-goal-progress.tsx` | Extend to 3 rings + message |
| `frontend/src/app/(shell)/dashboard/page.tsx` | Layout restructure + new components |
| `frontend/src/styles/tokens.css` (or globals) | Add dashboard-scoped color tokens |
