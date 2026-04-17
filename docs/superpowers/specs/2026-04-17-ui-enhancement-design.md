# SalonOS UI/UX Enhancement — Design Spec

**Date:** 2026-04-17  
**Author:** Angel Lakra  
**Scope:** Full visual redesign (Premium Dark theme) + all 65+ mobile responsiveness fixes

---

## 1. Goals

1. Extend the login page's existing Premium Dark aesthetic throughout the entire inner app.
2. Fix all 65+ documented mobile responsiveness issues (see `docs/audits/01-mobile-responsiveness-audit.md`).
3. Support 4 swappable accent colour palettes via a theme switcher in Settings.
4. Replace Quick Actions widget with a live Service Queue on the dashboard.
5. Hide revenue by default; let the owner reveal it with an eye toggle.

---

## 2. Design Direction

### 2.1 Colour Tokens

CSS custom properties defined on `:root` (dark mode always-on):

| Token | Value | Role |
|---|---|---|
| `--surface-page` | `#111111` | Page background |
| `--surface-card` | `#161616` | Card / panel background |
| `--surface-row` | `#1a1a1a` | Table rows, list items |
| `--surface-hover` | `#202020` | Hover state |
| `--border` | `#2a2a2a` | Dividers, card borders |
| `--text-primary` | `#f5f5f5` | Headings, values |
| `--text-secondary` | `#a3a3a3` | Labels, sub-text |
| `--text-muted` | `#525252` | Placeholders, disabled |

Accent palettes (one active at a time, set via `data-accent` on `<html>`):

| Name | Primary | Bg tint |
|---|---|---|
| Violet (default) | `#7c3aed` | `#160d2b` |
| Rose | `#e11d48` | `#2b0d14` |
| Amber | `#d97706` | `#2b1a00` |
| Teal | `#0d9488` | `#00211f` |

Accent token names: `--accent`, `--accent-bg`, `--accent-hover`.

### 2.2 Typography & Spacing

- Font stack unchanged (Inter / system-ui).
- Base spacing scale: `p-3 sm:p-4 md:p-6` replaces hard-coded `p-6` throughout.
- Stat values: `text-2xl font-bold` on desktop, `text-xl` on mobile.
- Card radius: `rounded-xl` (12 px) for cards, `rounded-lg` (8 px) for rows/chips.

### 2.3 Surface Depth System

Three levels create visual hierarchy without borders:

```
Page (#111) → Card (#161616) → Row/chip (#1a1a1a)
```

Active sidebar item: `--accent-bg` background + 3 px left border in `--accent`.

---

## 3. Component Designs

### 3.1 App Sidebar (`app-sidebar.tsx`)

- Background: `#0a0a0a` (one step darker than page).
- Logo area: salon name in `--text-primary`, tagline in `--text-secondary`.
- Nav items: flat list (no grouping), `h-9` rows, icon + label.
- Active state: `--accent-bg` fill + `--accent` left border (3 px).
- Hover state: `--surface-hover` fill.
- Footer: avatar chip + dropdown; 4-dot accent ring shows current palette, clicking cycles through all 4.
- Collapsible to icon-only mode (POS page default on desktop).
- **Mobile**: sidebar hidden; replaced by bottom nav (see §3.6).

### 3.2 Dashboard Page (`dashboard/page.tsx`)

#### Stat Cards
- 4 cards: Revenue, Appointments, New Customers, Avg Ticket.
- Revenue card: hidden by default, shows `••••` with eye icon toggle.
- Toggle state persisted to `localStorage` keyed by user ID.
- Staff role: revenue card never rendered (checked via `useAuthStore`).
- Goals bar below revenue: shows percentage only (e.g., "68% of daily goal") — never the raw number — so staff cannot back-calculate revenue.

#### Active Customer Cards (`active-customer-card.tsx`)
- Dark tile: `--surface-card` background, `rounded-xl`.
- Per-service rows inside: `--surface-row` background, `rounded-lg`.
- Status dots: blue = checked-in, amber = in-progress, green = done (replaces Lucide icons).
- Inline action buttons on each row: ▶ **Start** (blue outline) / ✓ **Complete** (green outline).
- Card footer: total amount + **Checkout** button.
- Checkout button: dimmed (`opacity-40`, `cursor-not-allowed`) until `all_completed === true`.
- Auto-refresh every 10 s (existing behaviour preserved).

#### Service Queue Widget (replaces Quick Actions)
- Right column, below the hourly chart.
- Per-staff lanes: one column per staff member currently checked in.
- Each lane header: avatar + name + busyness badge (available / busy / very busy, derived from `StaffBusyness` data already in `service-grid.tsx`).
- Services within a lane: ordered by `checked_in_at` ascending (oldest first = next to serve).
- Service chip: service name, customer name, elapsed time since check-in.
- Data source: pure frontend transform of `/appointments/walkins/active` — no new backend endpoint needed.
- Empty state: "No active services" in `--text-muted`.

### 3.3 POS Page (`pos/page.tsx`)

- Two-panel layout preserved: service browser (flex-1) + CartSidebar (`w-96`).
- Sidebar collapses to icon-only on POS page (more horizontal space).
- Service grid: `--surface-card` cards, staff busyness badge (coloured dot overlay, top-right).
- Search bar: `--surface-row` background, `--border` border, `--text-primary` input.
- Active customer strip: horizontal chip list above search bar showing checked-in customers.
- Keyboard shortcuts unchanged: `/` search, `⌘+.` customer, `⌘+Enter` checkout.

#### CartSidebar dark styling
- Background: `--surface-card`, border-left `--border`.
- Line items: `--surface-row` rows.
- Totals block: subtle separator, GST line in `--text-secondary`.
- Checkout CTA: full `--accent` background, white text.

### 3.4 Settings Page — Theme Switcher

- New "Appearance" section in Settings.
- 4 colour swatch buttons (Violet / Rose / Amber / Teal).
- Active swatch: ring in its own accent colour.
- Selection writes `accent` key to user preferences (backend `UserSettings` model, existing field or new `preferences` JSON column).
- On app load: read preference → set `data-accent` on `<html>`.

### 3.5 Bills / Reconciliation / Reports Tables

All wide tables converted to the **table-to-card pattern**:

```
Desktop (md+):  hidden md:table  (existing table markup)
Mobile (<md):   md:hidden        (card markup, one card per row)
```

Card anatomy for Bills:
- Row 1: invoice number (monospace) + timestamp (right-aligned, `--text-secondary`)
- Row 2: customer name (bold) + total amount (`--accent`)
- Row 3: service list (truncated) + status badge

Same pattern applied to: Purchases, Inventory, Expenses, Reconciliation.

### 3.6 Mobile — Layout Fixes

Global fixes (applied everywhere):

| Fix | Before | After |
|---|---|---|
| Viewport height | `h-screen` | `min-h-dvh` |
| Page padding | `p-6` | `p-3 sm:p-4 md:p-6` |
| Header height | `h-14` | `h-12 md:h-14` |
| Font sizes | Fixed | Responsive (`text-sm md:text-base`) |

**Bottom navigation** (mobile only, `md:hidden`):
- Fixed bottom bar, 4 items: Home · POS · Bills · More.
- Active item: `--accent` icon + label, indicator dot above icon.
- "More" opens a sheet with remaining nav items.

**POS mobile**:
- CartSidebar hidden on mobile (`hidden md:block`).
- Floating FAB (bottom-right, `--accent` bg): cart icon + item count badge.
- Tapping FAB opens cart in a `Sheet` (slides up from bottom).
- Customer chip strip scrolls horizontally.
- Service grid: 2 columns on mobile.

**Dashboard mobile**:
- Stat cards: 2-column grid.
- Service queue: single column (staff lanes stack vertically).
- Charts: full width, reduced height (`h-48` mobile vs `h-64` desktop).

---

## 4. State & Data

| Concern | Storage | Notes |
|---|---|---|
| Revenue visibility toggle | `localStorage` (per user ID key) | Reset on logout |
| Active accent palette | `UserSettings` (backend) + `localStorage` (cache) | Falls back to Violet |
| Service queue data | Derived from `/appointments/walkins/active` | Same 10 s poll as active customers |
| Bottom nav active item | React state / Next.js `usePathname` | No persistence needed |

---

## 5. Implementation Approach

**Token System + Component Layer Rebuild** (Option A from brainstorming):

1. Add CSS variable tokens to `globals.css`. Set `data-accent` on `<html>` at app load.
2. Update Tailwind config: map `bg-surface-page`, `bg-surface-card`, etc. to CSS vars.
3. Rebuild components layer-by-layer (layout → sidebar → dashboard → POS → tables → settings).
4. Mobile fixes folded into each component rewrite — no separate pass.

**File budget per PR:** max 3 files changed (per CLAUDE.md constraint). Ship in phases:
- Phase 1: Tokens + globals + layout shell
- Phase 2: Sidebar + bottom nav
- Phase 3: Dashboard (stat cards, active customer cards, service queue)
- Phase 4: POS page + cart sidebar
- Phase 5: Table-to-card pattern (Bills, Purchases, Inventory, Expenses, Reconciliation)
- Phase 6: Settings theme switcher + accent persistence

---

## 6. Out of Scope

- Backend API changes (service queue uses existing `/appointments/walkins/active`).
- Light mode toggle (dark only for now).
- Animations / transitions beyond simple CSS `transition-colors`.
- New pages or features not currently in the app.

---

## 7. Reference Files

| File | Role |
|---|---|
| `frontend/src/app/(auth)/login/page.tsx` | Design reference (already polished) |
| `frontend/src/app/dashboard/layout.tsx` | Root layout to fix |
| `frontend/src/app/dashboard/page.tsx` | Dashboard page |
| `frontend/src/components/app-sidebar.tsx` | Sidebar component |
| `frontend/src/components/dashboard/active-customer-card.tsx` | Active customer cards |
| `frontend/src/app/dashboard/pos/page.tsx` | POS page |
| `frontend/src/components/pos/cart-sidebar.tsx` | Cart sidebar |
| `frontend/src/components/pos/service-grid.tsx` | Service grid + StaffBusyness |
| `docs/audits/01-mobile-responsiveness-audit.md` | 65+ mobile fixes catalogue |
