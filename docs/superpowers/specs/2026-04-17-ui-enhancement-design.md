# Aasan UI/UX Enhancement — Design Spec

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

### 3.5 Shared Layout Patterns

All pages follow one of five structural archetypes. Each inherits the token system automatically.

#### Archetype A — List Pages
Applies to: Bills, Customers, Purchases (invoices), Inventory, Expenses.

Structure: `[Stat row] → [Filter bar] → [Table/card list] → [Pagination]`

**Table-to-card pattern** (all wide tables):
```
Desktop (md+):  hidden md:table  (existing table markup)
Mobile (<md):   md:hidden        (card markup, one card per row)
```

Card anatomy for **Bills**:
- Row 1: invoice number (monospace) + timestamp (`--text-secondary`)
- Row 2: customer name (bold) + total amount (`--accent`)
- Row 3: service list (truncated) + status badge + View button

Card anatomy for **Customers**:
- Row 1: name + gender chip + last-visit date (`--text-secondary`)
- Row 2: phone number + total visits badge
- Row 3: total spent (right) + pending balance highlighted in amber if > 0
- Action icons: Edit · History · Pending payment · Delete

Card anatomy for **Inventory SKUs**:
- Row 1: SKU code (monospace) + category chip
- Row 2: product name (bold) + brand
- Row 3: stock count (red if low) + unit + avg cost + retail price (if sellable)
- Action: +/− stock adjustment inline

Card anatomy for **Purchase Invoices**:
- Row 1: invoice ref (monospace) + date
- Row 2: supplier name + status badge (draft/received/paid)
- Row 3: total amount + outstanding amount if unpaid
- Action: View button

Card anatomy for **Expenses**:
- Row 1: date + category chip
- Row 2: description (bold) + amount (`--accent`)
- Row 3: payment method + added-by name

#### Archetype B — Queue / Staff-facing Pages
Applies to: Staff Dashboard (`/staff`), My Services (`/my-services`).

Structure: `[Today's summary chips] → [Active service cards] → [Completed tab]`

Both pages are staff-facing (hidden from owner/receptionist nav). Cards show:
- Service name + customer name + ticket number
- Status badge: checked-in / in-progress / completed
- Elapsed timer (live, for in-progress)
- ▶ Start / ✓ Complete inline buttons (same API calls as active-customer-card)
- Service notes (expandable)

My Services also has an "+ Add Service" sheet (existing Sheet component) for walk-in self-assignment.

#### Archetype C — Report Pages
Applies to: Reports Hub, Profit & Loss, Reconciliation.

**Reports Hub** (`/reports`): Card grid of report links.
- Enabled cards: `--surface-card`, hover border `--accent`.
- Disabled cards: `opacity-50`, "Coming soon" chip instead of hover border.
- No light-mode `bg-green-50` / `bg-blue-50` colours — replace with `--accent-bg` on hover.

**Profit & Loss** (`/reports/profit-loss`):
- Date range pickers (start / end) + Generate button.
- Results in structured dark card sections: Revenue → COGS → Gross Profit → Operating Expenses → Net Profit.
- Each row: label + amount + % of revenue (right-aligned).
- Net Profit row: highlighted green if positive, red if negative.

**Reconciliation** (`/reconciliation`):
- Date picker + EOD summary card (total bills, revenue, payment method breakdown — cash/card/UPI/bank).
- Cash reconciliation form: "Expected cash" (read-only) vs "Actual cash counted" (input).
- Variance row: green if within ±₹50, amber if ±₹200, red if beyond.
- Already reconciled state: shows reconciled-by + time stamp, lock icon.

#### Archetype D — Management Pages
Applies to: Users & Staff, Services/Catalog, Attendance.

Structure: `[Page header + action button] → [Search/filter bar] → [Tabs] → [Table/card list]`

**Users & Staff** (`/users`): Tabs: Users | Staff.
- User cards: avatar initials + name + role badge (owner=violet, receptionist=blue, staff=slate) + phone/email chips.
- Staff cards: same but with "active/inactive" badge instead of role.
- Action buttons: Edit + Reset password (users), Edit + Deactivate (staff).

**Services/Catalog** (`/services`):
- Left: category list (vertical chips, `--surface-row`, active = `--accent-bg` + `--accent` border).
- Right: service cards grid — name + price + duration + active/inactive badge.
- Mobile: category list becomes horizontal scrollable chip row above the grid.
- Import button preserved (CSV import dialog).

**Attendance** (`/attendance`):
- Tabs: Quick Mark | Full Table | My Attendance (staff-only tab).
- Stat chips row: Present (green) · Half Day (amber) · Absent (red) · Leave (blue) — counts for selected date.
- Quick Mark: staff list with one-tap status buttons (P / H / A / L).
- Full Table: table → card pattern, one row per staff.
- Monthly view (`/attendance/monthly`): calendar grid, each cell is a coloured dot per attendance status.

#### Archetype E — Operations Pages
Applies to: Cash Drawer, Purchases Suppliers.

**Cash Drawer** (`/cash-drawer`):
- Two states: drawer closed → Opening flow; drawer open → Closing flow.
- Opening: float input (quick entry) or denomination counter (detailed mode toggle).
- Live summary card: opening float, cash payments today, expected cash.
- Closing: denomination counter → counted total auto-summed → variance row (same colour rules as reconciliation).
- Variance amber/red rows pulse with a subtle ring animation.

**Purchases Suppliers** (`/purchases/suppliers`): Simple list page.
- Supplier cards: name + contact + outstanding balance chip (amber if > 0).
- Add/Edit via dialog (existing pattern).

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
- Phase 1: Tokens + globals + layout shell (`globals.css`, `tailwind.config.ts`, `layout.tsx`)
- Phase 2: Sidebar + bottom nav (`app-sidebar.tsx`, new `bottom-nav.tsx`)
- Phase 3: Dashboard — stat cards + revenue hide (`dashboard/page.tsx`, `active-customer-card.tsx`)
- Phase 4: Dashboard — service queue widget (new `service-queue.tsx`)
- Phase 5: POS page + cart sidebar (`pos/page.tsx`, `cart-sidebar.tsx`)
- Phase 6: Bills page (Archetype A — table-to-card)
- Phase 7: Customers page (Archetype A)
- Phase 8: Inventory page (Archetype A)
- Phase 9: Expenses page (Archetype A)
- Phase 10: Purchases invoices + suppliers (Archetype A + E)
- Phase 11: Staff Dashboard + My Services (Archetype B)
- Phase 12: Reports hub + P&L page (Archetype C)
- Phase 13: Reconciliation + Cash Drawer (Archetype C + E)
- Phase 14: Users & Staff + Services/Catalog (Archetype D)
- Phase 15: Attendance + Monthly view (Archetype D)
- Phase 16: Settings — Appearance section + accent persistence

---

## 6. Out of Scope

- Backend API changes (service queue uses existing `/appointments/walkins/active`).
- Light mode toggle (dark only for now).
- Animations / transitions beyond simple CSS `transition-colors`.
- New pages or features not currently in the app.

---

## 7. Page Inventory

All 23 pages and their archetype:

| Page | Path | Archetype |
|---|---|---|
| Dashboard | `/dashboard` | Custom (§3.2) |
| POS | `/dashboard/pos` | Custom (§3.3) |
| Bills | `/dashboard/bills` | A — List |
| Customers | `/dashboard/customers` | A — List |
| Inventory | `/dashboard/inventory` | A — List |
| Inventory Transfers | `/dashboard/inventory/transfers` | A — List |
| Expenses | `/dashboard/expenses` | A — List |
| Purchase Invoices | `/dashboard/purchases/invoices` | A — List |
| Purchase Invoice Detail | `/dashboard/purchases/invoices/[id]` | A — List |
| Purchase Invoice New | `/dashboard/purchases/invoices/new` | E — Operations form |
| Purchase Payment New | `/dashboard/purchases/payments/new` | E — Operations form |
| Staff Dashboard | `/dashboard/staff` | B — Queue |
| My Services | `/dashboard/my-services` | B — Queue |
| Reports Hub | `/dashboard/reports` | C — Reports |
| Profit & Loss | `/dashboard/reports/profit-loss` | C — Reports |
| Reconciliation | `/dashboard/reconciliation` | C — Reports |
| Cash Drawer | `/dashboard/cash-drawer` | E — Operations |
| Purchases Suppliers | `/dashboard/purchases/suppliers` | E — Operations |
| Users & Staff | `/dashboard/users` | D — Management |
| Services / Catalog | `/dashboard/services` | D — Management |
| Attendance | `/dashboard/attendance` | D — Management |
| Attendance Monthly | `/dashboard/attendance/monthly` | D — Management |
| Settings | `/dashboard/settings` | Custom (§3.4) |

## 8. Reference Files

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
| `frontend/src/app/dashboard/customers/page.tsx` | Customers list |
| `frontend/src/app/dashboard/services/page.tsx` | Services/Catalog |
| `frontend/src/app/dashboard/users/page.tsx` | Users & Staff (tabbed) |
| `frontend/src/app/dashboard/attendance/page.tsx` | Attendance |
| `frontend/src/app/dashboard/attendance/monthly/page.tsx` | Monthly calendar view |
| `frontend/src/app/dashboard/cash-drawer/page.tsx` | Cash Drawer |
| `frontend/src/app/dashboard/my-services/page.tsx` | My Services (staff) |
| `frontend/src/app/dashboard/staff/page.tsx` | Staff Dashboard |
| `frontend/src/app/dashboard/reports/page.tsx` | Reports Hub |
| `frontend/src/app/dashboard/reports/profit-loss/page.tsx` | P&L Report |
| `frontend/src/app/dashboard/reconciliation/page.tsx` | Reconciliation |
| `frontend/src/app/dashboard/expenses/page.tsx` | Expenses |
| `frontend/src/app/dashboard/inventory/page.tsx` | Inventory |
| `frontend/src/app/dashboard/purchases/invoices/page.tsx` | Purchase Invoices |
| `frontend/src/app/dashboard/purchases/suppliers/page.tsx` | Suppliers |
| `docs/audits/01-mobile-responsiveness-audit.md` | 65+ mobile fixes catalogue |
