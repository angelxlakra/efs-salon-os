# SalonOS Design System

**Status:** Living document — keep in sync with `frontend/src/styles/tokens.css` and the primitives library.
**Owner:** Frontend team
**Last updated:** 2026-04-23 (V2 initial draft)

> The strategic "why" lives in `docs/superpowers/specs/2026-04-23-v2-redesign-design.md`.
> This document is the "how" — concrete tokens, primitives, patterns, and rules.
> If you're building a new page, everything you need is here.

---

## 1. Principles

1. **Tokens carry meaning, utilities do not.** Never reach for a raw Tailwind gray (`text-gray-500`, `bg-zinc-900`) in app code. Use semantic tokens (`text-muted`, `bg-surface-card`). Raw scales exist only inside the token file.
2. **Density first, whitespace second.** Data is the hero; whitespace serves legibility, not decoration. Rhythm matters more than room.
3. **One primitive per job.** No page ships a bespoke input, button, or dialog. If a primitive is missing, extend the library — don't one-off it.
4. **Light is authoritative.** Dark tokens are tuned to match *perceived* contrast of light tokens, not to mirror values numerically.
5. **Motion earns muscle memory, never decorates.** Sub-200ms, respects `prefers-reduced-motion`, never loops.
6. **Copy is part of the system.** "Today" not "Dashboard". "Customers" everywhere (no "Guests" split — use the word staff already say). Empty states guide the next action, not announce absence.

---

## 2. Colour tokens

All tokens are defined in `frontend/src/styles/tokens.css` and mapped to Tailwind utilities via `@theme`.

### 2.1 Semantic model

| Family | Tokens | Usage |
|---|---|---|
| `surface` | `page`, `card`, `row`, `row-hover`, `sidebar`, `overlay` | Container backgrounds |
| `border` | `subtle`, `default`, `strong`, `focus` | Dividers, outlines, focus rings |
| `text` | `primary`, `secondary`, `muted`, `disabled`, `inverse` | All text |
| `accent` | `default`, `hover`, `active`, `bg-soft`, `fg-on-accent` | Primary actions, active nav, selection, focus |
| `semantic.success` | `fg`, `bg-soft`, `border` | Paid, completed, healthy |
| `semantic.warning` | `fg`, `bg-soft`, `border` | Low stock, overdue soon, caution |
| `semantic.danger` | `fg`, `bg-soft`, `border` | Failed, destructive, overdue |
| `semantic.info` | `fg`, `bg-soft`, `border` | Neutral status, in-progress |
| `data-viz` | `series-1` through `series-6` | Charts only — colourblind-safe, never used in UI chrome |

### 2.2 Values (light — authoritative)

```css
:root {
  /* Surface */
  --surface-page:       #fafaf9;   /* warm white, not pure white */
  --surface-card:       #ffffff;
  --surface-row:        #ffffff;
  --surface-row-hover:  #f5f5f4;
  --surface-sidebar:    #f8f7f5;
  --surface-overlay:    rgba(20, 14, 10, 0.48);

  /* Border */
  --border-subtle:      #eeece9;
  --border-default:     #e3e0db;
  --border-strong:      #cfcac3;
  --border-focus:       var(--accent-default);

  /* Text */
  --text-primary:       #1c1917;   /* 14.6:1 on surface-page */
  --text-secondary:     #44403c;   /* 8.9:1  */
  --text-muted:         #78716c;   /* 4.9:1  — WCAG AA compliant on card */
  --text-disabled:      #a8a29e;
  --text-inverse:       #ffffff;

  /* Accent — Copper */
  --accent-default:     #b0561f;
  --accent-hover:       #954919;
  --accent-active:      #7d3d15;
  --accent-bg-soft:     #fbe9dd;
  --accent-fg-on-accent:#ffffff;

  /* Semantic */
  --success-fg:         #166534;
  --success-bg-soft:    #dcfce7;
  --success-border:     #bbf7d0;

  --warning-fg:         #92400e;
  --warning-bg-soft:    #fef3c7;
  --warning-border:     #fde68a;

  --danger-fg:          #991b1b;
  --danger-bg-soft:     #fee2e2;
  --danger-border:      #fecaca;

  --info-fg:            #1e40af;
  --info-bg-soft:       #dbeafe;
  --info-border:        #bfdbfe;

  /* Data viz — colourblind-safe ordered palette */
  --data-series-1:      #b0561f;   /* copper */
  --data-series-2:      #1e40af;   /* indigo */
  --data-series-3:      #166534;   /* green */
  --data-series-4:      #92400e;   /* amber */
  --data-series-5:      #6b21a8;   /* purple */
  --data-series-6:      #0e7490;   /* cyan */
}
```

### 2.3 Values (dark — perceptually matched)

```css
[data-theme="dark"] {
  --surface-page:       #14120f;   /* warm near-black, not pure black */
  --surface-card:       #1c1a17;
  --surface-row:        #1f1d1a;
  --surface-row-hover:  #26231f;
  --surface-sidebar:    #0f0e0c;
  --surface-overlay:    rgba(0, 0, 0, 0.6);

  --border-subtle:      #2a2723;
  --border-default:     #3a3631;
  --border-strong:      #504a42;
  --border-focus:       var(--accent-default);

  --text-primary:       #f5f2ee;   /* 14.1:1 on surface-card */
  --text-secondary:     #c9c2b8;   /* 8.7:1  */
  --text-muted:         #948b7e;   /* 4.8:1  */
  --text-disabled:      #5a5249;
  --text-inverse:       #1c1917;

  /* Copper brightened for dark surface — preserves perceived saturation */
  --accent-default:     #d97847;
  --accent-hover:       #e38f65;
  --accent-active:      #f0a684;
  --accent-bg-soft:     #3a1d0c;
  --accent-fg-on-accent:#1c1917;

  --success-fg:         #86efac;
  --success-bg-soft:    #14321f;
  --success-border:     #1f4a2d;

  --warning-fg:         #fcd34d;
  --warning-bg-soft:    #3b2a10;
  --warning-border:     #5a4018;

  --danger-fg:          #fca5a5;
  --danger-bg-soft:     #3b1616;
  --danger-border:      #5a2020;

  --info-fg:            #93c5fd;
  --info-bg-soft:       #1e2a4a;
  --info-border:        #2a3d6e;

  --data-series-1:      #d97847;
  --data-series-2:      #7aa0e8;
  --data-series-3:      #86efac;
  --data-series-4:      #fcd34d;
  --data-series-5:      #c084fc;
  --data-series-6:      #5eead4;
}
```

### 2.4 Contrast commitments

| Element | Minimum ratio | Covered tokens |
|---|---|---|
| Body text (< 18px, < 14px bold) | **4.5:1** | `text-primary`, `text-secondary`, `text-muted` |
| Large text (≥ 18px or ≥ 14px bold) | **3:1** | Page titles, card titles |
| Non-text UI (focus rings, icons carrying info) | **3:1** | `border-focus`, `accent-default`, semantic borders |
| Disabled text | Exempt, but ≥ 2:1 | `text-disabled` |

All values above satisfy these ratios. Any new token must be verified before landing.

---

## 3. Typography

### 3.1 Font stack

```css
--font-display: "Instrument Serif", "EB Garamond", Georgia, serif;
--font-body:    "Inter", ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
--font-mono:    ui-monospace, "SF Mono", "JetBrains Mono", Menlo, Consolas, monospace;
```

Fonts are self-hosted (see `frontend/public/fonts/`) — no Google Fonts runtime fetch.

### 3.2 Usage rules

- **Display (Instrument Serif)** — used sparingly. Allowed on:
  - Page titles (`h1`) on dashboards, landing screens
  - Empty-state headlines
  - Login / auth screen headline
  - **Not on printed receipts** — the print template is unchanged in V2.
- **Body (Inter)** — every other text surface.
- **Mono** — SKU codes, invoice numbers, keyboard shortcuts.
- **Tabular numerals** (`font-variant-numeric: tabular-nums`) — required on every surface that displays money, counts, or time. Applied via utility `.tabular`.

### 3.3 Scale

| Token | Size / line-height | Weight | Casing | Usage |
|---|---|---|---|---|
| `.text-display-xl` | 32px / 1.1 | 400 serif | — | Auth screen headline, marketing surfaces |
| `.text-display-lg` | 28px / 1.15 | 400 serif | — | Page title (serif pages) |
| `.text-display-md` | 24px / 1.2 | 400 serif | — | Empty-state headline |
| `.text-heading-lg` | 20px / 1.25 | 600 | — | Page title (standard) |
| `.text-heading-md` | 16px / 1.35 | 600 | — | Card title, section header |
| `.text-heading-sm` | 14px / 1.4 | 600 | — | Sub-section, table group header |
| `.text-body-lg` | 16px / 1.5 | 400 | — | Reading text (rare in this app) |
| `.text-body` | 14px / 1.5 | 400 | — | **Default body** |
| `.text-body-sm` | 13px / 1.45 | 400 | — | Table rows, secondary info |
| `.text-caption` | 12px / 1.4 | 500 | — | Metadata, counts |
| `.text-overline` | 11px / 1.3 | 600 | UPPERCASE, +6% tracking | Stat card labels, section markers |
| `.text-money-lg` | 22px / 1.2 | 700 tabular | — | KPI primary values |
| `.text-money` | 14px / 1.5 | 600 tabular | — | Table amounts, line items |

### 3.4 Font-weight map

- `400` — body text
- `500` — captions, subtle emphasis
- `600` — headings, buttons, active nav
- `700` — KPI values, money, critical emphasis

No `300`, no `800`, no `900`. Weight inflation is a smell.

---

## 4. Spacing & sizing

### 4.1 Scale

Base unit: **4px**. Preferred rhythm: **8px** (major) with **4px** (minor).

```
space-0:   0
space-1:   4px
space-2:   8px
space-3:   12px
space-4:   16px
space-5:   20px
space-6:   24px
space-8:   32px
space-10:  40px
space-12:  48px
space-16:  64px
space-20:  80px
```

### 4.2 Layout grid

- **Page gutter:** 24px desktop, 16px tablet, 12px mobile.
- **Card inner padding:** 20px default, 24px for KPI / dashboard cards.
- **Section gap (between cards):** 16px default, 24px between unlike sections.
- **Form field gap:** 16px between fields, 4px between label and input, 4px between input and help text.
- **Table row height:** 36px default. Dense variant 32px. Comfort variant 44px (used only in Appointments staff swimlanes).
- **Button height:** sm 28px, md 36px, lg 44px. Touch targets on mobile always ≥ 44px (enforced by primitive).

### 4.3 Radius

```
radius-sm:  4px   (inputs, pills, small buttons)
radius-md:  6px   (buttons, badges)
radius-lg:  10px  (cards, dialogs, surfaces)
radius-xl:  14px  (large surfaces, feature cards)
radius-full: 9999px (avatars, circular chips)
```

### 4.4 Shadows

Minimal. Shadow is an affordance signal, not decoration.

```
shadow-none:    — (default — flat)
shadow-xs:      0 1px 2px rgba(20, 14, 10, 0.06)       — cards that raise on hover
shadow-sm:      0 2px 4px rgba(20, 14, 10, 0.06), 0 1px 2px rgba(20, 14, 10, 0.04)       — popovers, dropdowns
shadow-md:      0 8px 20px rgba(20, 14, 10, 0.10), 0 2px 6px rgba(20, 14, 10, 0.06)      — dialogs, drawers
shadow-focus:   0 0 0 3px rgba(176, 86, 31, 0.18)       — focus ring (accent-tinted)
```

Dark-mode shadows use `rgba(0, 0, 0, …)` with slightly higher alpha.

---

## 5. Motion

### 5.1 Tokens

```
motion-instant:   0ms
motion-fast:      80ms
motion-default:   120ms
motion-slow:      180ms
motion-spring:    cubic-bezier(0.22, 1.2, 0.36, 1)   — gentle overshoot
motion-ease-out:  cubic-bezier(0.2, 0.8, 0.2, 1)     — UI default
motion-linear:    linear                              — progress only
```

### 5.2 Rules

- Page transitions — 120ms opacity fade. No slide.
- State (hover, focus, press) — 80ms.
- Modal / drawer open — 180ms with `motion-spring` on transform.
- Modal / drawer close — 120ms `motion-ease-out`.
- Tables, lists, charts — **no animation on data change**. Only on user-initiated sort/filter. Prevents "dashboard vibrating" with polling.
- `prefers-reduced-motion` — all motion collapses to opacity-only; `motion-instant` for transforms.

---

## 6. Primitives

Each primitive lives under `frontend/src/components/ui/` (existing path) and has a TypeScript interface below.

### 6.1 Button

```tsx
<Button
  variant="primary" | "secondary" | "ghost" | "danger" | "icon"
  size="sm" | "md" | "lg"
  loading={boolean}
  leadingIcon={ReactNode}
  trailingIcon={ReactNode}
  fullWidth={boolean}
>
  Label
</Button>
```

- `primary` uses `accent` tokens.
- `danger` uses `semantic.danger`.
- Icon buttons must pass `aria-label`.
- Loading state swaps label for a spinner + preserves width.

### 6.2 Input / Currency / Select

```tsx
<Input
  label="Amount"
  hint="In rupees"
  error={string | undefined}
  required={boolean}
  leadingAddon={ReactNode}
  trailingAddon={ReactNode}
  size="sm" | "md" | "lg"
  {...inputProps}
/>

<CurrencyInput value={paise} onChange={(paise) => ...} />   // handles paise↔rupee conversion

<Select options={...} value={...} onChange={...} />         // restyled Radix Select
<Combobox options={...} value={...} onSearch={...} />       // cmdk under the hood
```

- Currency always displays with `₹` prefix and tabular figures.
- Validation errors render in `semantic.danger` and slide under the input; no toast-only errors.

### 6.3 Dialog / Drawer / Sheet

```tsx
<Dialog
  size="sm" | "md" | "lg" | "xl" | "full"
  title="..."
  description="..."
  closeOnOverlay={boolean}
>
  ...
</Dialog>
```

- Default: `max-w: min(calc(100vw - 2rem), <size>)`, `max-h: 90dvh`, body `overflow-y-auto`.
- Sizes: sm=400, md=560, lg=720, xl=960, full=responsive with 24px gutter.
- Mobile < 640px: Dialog renders as a bottom sheet; Drawer unchanged.
- Destructive confirmation dialogs use `variant="destructive"` — primary button is `danger`, subject name required to be typed for irreversible actions (e.g. "Delete customer").

### 6.4 Table shell

```tsx
<Table
  data={rows}
  columns={[
    { id: "name",   header: "Name",   priority: "high",   accessor: (r) => r.name },
    { id: "phone",  header: "Phone",  priority: "medium", accessor: (r) => r.phone },
    { id: "spent",  header: "Total",  priority: "high",   accessor: (r) => r.spent, align: "right", format: "money" },
    { id: "visits", header: "Visits", priority: "low",    accessor: (r) => r.visits, align: "right" },
  ]}
  sort={{ column: "spent", direction: "desc" }}
  onSortChange={...}
  totals={{ spent: sumPaise }}
  density="default" | "dense" | "comfort"
  mobileCard={(row) => <CustomerCard row={row} />}   // optional override; otherwise auto-card from high-priority columns
  rowAction={(row) => <RowActionMenu row={row} />}   // destructive actions live here, never in the row
  emptyState={<EmptyState ... />}
  loading={boolean}
  onRowClick={(row) => ...}
/>
```

- Mobile behaviour: columns with `priority: "low"` are hidden; the primitive auto-generates a card view from `priority: "high" | "medium"` columns unless `mobileCard` overrides.
- `totals` renders a sticky footer row when provided.
- No hardcoded column widths in page code; primitive handles sizing based on content and priority.

### 6.5 Card

```tsx
<Card density="sm" | "md" | "lg" padding="none" | "default" | "lg">
  <Card.Header title="..." description="..." action={...} />
  <Card.Body>...</Card.Body>
  <Card.Footer>...</Card.Footer>
</Card>
```

- Default density is `md` (20px padding). `lg` for KPI/feature cards. `sm` for list items.
- Optional `hover` prop raises `shadow-none` → `shadow-xs`.

### 6.6 Badge

```tsx
<Badge tone="neutral" | "success" | "warning" | "danger" | "info" | "accent" size="sm" | "md">
  Paid
</Badge>
```

- Uses semantic `bg-soft` + `fg` + `border`. No hand-rolled colours.

### 6.7 EmptyState

```tsx
<EmptyState
  icon={<CalendarIcon />}
  title="No bookings yet today"          // Instrument Serif
  body="First appointment at 10:00. Add a walk-in to start earlier."
  primaryAction={<Button>New walk-in</Button>}
  secondaryAction={<Button variant="ghost">View yesterday</Button>}
/>
```

- `title` is required and uses the display serif.
- `body` is one sentence and guides the next action. "No data" / "No results" are not acceptable copy.

### 6.8 Skeleton

```tsx
<Skeleton shape="text" | "row" | "card" | "kpi" width={...} />
```

- Always render skeleton during load, never blank or spinner-only. Skeleton widths should mirror typical content (e.g., 60% for name rows).

### 6.9 FilterBar

```tsx
<FilterBar>
  <FilterBar.Search placeholder="Search bills…" onChange={...} />
  <FilterBar.Pills value={...} onChange={...} options={[{ value: "all", label: "All", count: 171 }, ...]} />
  <FilterBar.DateRange value={...} onChange={...} />
  <FilterBar.Actions>
    <Button variant="secondary">Export</Button>
  </FilterBar.Actions>
</FilterBar>
```

- Reused on Bills, Inventory, Customers, Purchases, Expenses, Appointments.
- Pills support count suffix (`"Paid · 142"`) — counts are live from server.

### 6.10 Toast

- Sonner, restyled. Position: bottom-right desktop, top on mobile.
- **Success** toasts auto-dismiss at 4s.
- **Warning/Danger** toasts are persistent until dismissed.
- **Never** rely on a toast to report an input validation error — use the inline error on the field.

---

## 7. Layout shell

### 7.1 Shape

```
┌─────────────────────────────────────────────────────────────┐
│ Topbar (48px) — breadcrumb · ⌘K trigger · user menu         │
├─────────┬───────────────────────────────────────────────────┤
│         │                                                   │
│ Sidebar │  Page content                                     │
│ (192px) │  · 24px page gutter (desktop)                     │
│         │  · min-h-dvh                                      │
│         │                                                   │
└─────────┴───────────────────────────────────────────────────┘
```

Sidebar collapses to **56px icon rail** via `⌘\`. State persisted per user in local storage.

Mobile (< 768px): sidebar becomes a sheet; bottom-tab nav replaces it.

### 7.2 Sidebar groups

Non-collapsible labelled groups (in order):

1. **Today's work** — Dashboard · POS · Bills · Appointments
2. **Ledger** — Customers · Inventory · Purchases · Expenses · Cash Drawer · EOD Reconciliation
3. **Insight** — Reports · Profit & Loss · Attendance
4. **Admin** — Users & Staff · Services · Settings

Each nav item is a primitive:

```tsx
<NavItem
  icon={<HomeIcon />}
  label="Today"
  href="/dashboard"
  active={pathname === "/dashboard"}
  badge={<Badge tone="accent" size="sm">3</Badge>}  // optional, e.g. pending bills
/>
```

### 7.3 Topbar

- **Breadcrumb** shows real navigation — `Today › Bills › SAL-25-0171`. Clickable crumbs.
- **Global search** trigger (⌘K) sits in the topbar as a quick affordance, even though the shortcut works anywhere.
- **User menu** holds theme toggle, role switcher, sign out.

### 7.4 Command palette

```tsx
<CommandPalette
  groups={[
    { title: "Navigate", commands: [...routes] },
    { title: "Create", commands: ["New bill", "New walk-in", "New appointment", "Add customer", "Adjust stock"] },
    { title: "Find", commands: [...recentCustomers, ...recentBills, ...recentSKUs] },
    { title: "System", commands: ["Toggle theme", "Collapse sidebar", "Sign out"] },
  ]}
/>
```

Opens on `⌘K` / `Ctrl+K`. Escapes to close. Command history persisted.

**"Find" results navigate via `router.push()` to the entity's canonical URL** (see §7.5). The palette does not open dialogs directly — it routes. Whether the destination renders as a dialog or a full page is determined by the intercepting-route pattern, not the palette.

### 7.5 Entity detail routing (`@modal` + intercepting routes)

Every entity with a detail view has a **canonical URL**. Detail state is never owned by a list page's local `useState`.

#### Route shape

```
frontend/src/app/dashboard/
├── @modal/
│   ├── default.tsx                 // returns null
│   └── (.)bills/[id]/page.tsx      // intercepting — renders BillDetail in <Dialog>
│   └── (.)customers/[id]/page.tsx
│   └── (.)invoices/[id]/page.tsx
│   └── (.)inventory/[id]/page.tsx
│   └── (.)purchases/[id]/page.tsx
│   └── (.)appointments/[id]/page.tsx
├── bills/
│   ├── page.tsx                    // list
│   └── [id]/page.tsx               // full-page detail (cold URL, palette, deep link)
├── customers/
│   ├── page.tsx
│   └── [id]/page.tsx
└── layout.tsx                      // renders {children} and {modal}
```

The layout wires the parallel slot:

```tsx
export default function DashboardLayout({ children, modal }: {
  children: ReactNode;
  modal: ReactNode;
}) {
  return (
    <Shell>
      {children}
      {modal}            {/* renders intercepting dialog when matched, else null */}
    </Shell>
  );
}
```

#### Behaviour matrix

| Entry point | What renders |
|---|---|
| Click a row on `/dashboard/bills` | URL becomes `/dashboard/bills/:id`, intercepting route renders `BillDetail` inside `<Dialog>` over the list. Close dismisses to `/dashboard/bills`. |
| Enter a bill from ⌘K `Find` | `router.push('/dashboard/bills/:id')` — not intercepted, renders as a full page. |
| Visit `/dashboard/bills/:id` directly (deep link, refresh, shared URL) | Full page. |
| Hit browser back from the dialog | Returns to the list — the dialog unmounts because the URL changed. |

#### One component, two shells

```tsx
// frontend/src/components/bills/bill-detail.tsx
export function BillDetail({ billId }: { billId: string }) {
  // The detail content itself. Knows nothing about dialog vs page.
  return <DetailHeader ... /> + <BillLineItems ... /> + <BillSummary ... />;
}

// app/dashboard/bills/[id]/page.tsx — full page
export default function BillPage({ params }) {
  return <PageContainer><BillDetail billId={params.id} /></PageContainer>;
}

// app/dashboard/@modal/(.)bills/[id]/page.tsx — intercepted dialog
export default function BillModal({ params }) {
  const router = useRouter();
  return (
    <Dialog open onOpenChange={() => router.back()} size="xl">
      <BillDetail billId={params.id} />
    </Dialog>
  );
}
```

The detail component is shared. Only the shell differs.

#### Rules

1. **No list page ever owns detail state.** `useState<string | null>(selectedBillId)` in a list page is a lint error. The canonical route owns the state.
2. **Actions inside the detail use `router.push` / `router.back`** — never a local `onClose`. This keeps the dialog and page shell interchangeable.
3. **Destructive actions behave the same in both shells** — typed-confirmation dialog layered over the detail. The detail dismisses on success via `router.back()` in dialog mode, `router.push('/bills')` in page mode.
4. **Loading & error states live in the detail component**, not the shell. Both shells render the same skeleton.
5. **Which entities qualify:** anything searchable from the palette or linkable from other surfaces. Current list: `bills`, `customers`, `invoices`, `inventory` (SKUs), `purchases`, `appointments`. `users`, `services`, `expenses`, `cash-drawer-sessions` can follow as they mature — no entity is locked out, but none should ship without its canonical route.

#### §7.5.1 — Implementation template (Phase 1)

Phase 1 ships the route group `(shell)` that owns the parallel `@modal` slot. The actual file layout used in production:

```
frontend/src/app/(shell)/dashboard/<entity>/[id]/page.tsx        — canonical full page
frontend/src/app/(shell)/@modal/(.)dashboard/<entity>/[id]/page.tsx — intercepted modal
frontend/src/components/<entity>/<entity>-detail.tsx              — shared body
```

**Behaviour:**

- Cold URL or palette navigation → renders the canonical page.
- Click from a list row inside `/dashboard/<entity>` → Next intercepts, slots the body into `@modal`, list URL stays.
- Browser back → closes the modal (because `router.back()` unwinds the URL).
- Deep link (WhatsApp, copy URL) → renders the canonical page (no list context to intercept).

**Detail body contract:**

- Single component named `<Entity>Detail` (`BillDetail`, `CustomerDetail`, etc.).
- Accepts `{ id }` only. Fetches its own data with cleanup-aware `useEffect`.
- Renders Skeleton (Phase 0 T15) while loading; danger token text on error.
- No URL knowledge — same body works in modal and full-page.

**Lint enforcement (Phase 0 T25):** `salon/no-list-owned-detail-state` flags any list page that imports a `*DetailDialog` AND holds a `selected*Id` in `useState`. List pages must instead push to the entity URL (`router.push(\`/dashboard/<entity>/\${id}\`)`) and let the `@modal` slot handle rendering.

**Reference implementation:** see `frontend/src/app/(shell)/dashboard/bills/[id]/page.tsx`, `frontend/src/app/(shell)/@modal/(.)dashboard/bills/[id]/page.tsx`, and `frontend/src/components/bills/bill-detail.tsx` (Phase 1 T13).

---

## 8. Page patterns

### 8.1 List page (Bills / Customers / Inventory / Purchases / Expenses)

```
┌─────────────────────────────────────────────────────────────┐
│ PageHeader                                                  │
│   · text-heading-lg title                                   │
│   · text-body-sm description                                │
│   · Primary action (e.g. "New bill") top-right              │
├─────────────────────────────────────────────────────────────┤
│ KpiRow (optional — 3-5 cards)                               │
├─────────────────────────────────────────────────────────────┤
│ FilterBar                                                   │
├─────────────────────────────────────────────────────────────┤
│ Table (with totals row + pagination)                        │
└─────────────────────────────────────────────────────────────┘
```

- KPI row is the "at-a-glance summary" — `Total`, `This month`, `Pending`, etc.
- Filter state persisted in URL query params.
- Pagination via URL (`?page=3`), never client-only.

### 8.2 Detail page (Bill / Customer / Invoice / SKU)

Renders in two shells (see §7.5): full page at `/[entity]/[id]`, intercepting dialog at `@modal/(.)[entity]/[id]`. Same component, different wrapper.

```
┌─────────────────────────────────────────────────────────────┐
│ DetailHeader                                                │
│   · Back link (← uses router.back())                        │
│   · text-heading-lg title + ID                              │
│   · Status badge + key metadata                             │
│   · Action buttons (right-aligned; destructive in menu)     │
├─────────────────────────────────────────────────────────────┤
│ 2-column layout on desktop, stacked on mobile               │
│  ┌─────────────────────────┬─────────────────────────┐     │
│  │ Primary content         │ Summary sidebar         │     │
│  │ (line items, timeline)  │ (totals, meta)          │     │
│  └─────────────────────────┴─────────────────────────┘     │
└─────────────────────────────────────────────────────────────┘
```

- Destructive actions never live in the top bar. They live under a "More actions" menu, and always require a confirmation dialog with typed subject.
- The detail component takes `{ id }` as its only external input. No `onClose`, no `isOpen`, no knowledge of its shell. That's what lets the same component render in the dialog *and* the full page.

### 8.3 Form page (New Bill / New Invoice / Customer Edit)

- Two-column on ≥ 1024px — main form left, summary/totals sticky right.
- One-column on mobile — summary becomes a sticky bottom bar.
- Submit buttons are **always visible** (sticky footer on mobile). Never scroll-to-find-submit.
- Validation errors are inline; submit is disabled with a tooltip explaining why, not silently.

### 8.4 Dashboard / Today

- KPI row at top (Revenue, Services, Customers, Active now).
- "What needs attention" panel — pending payments, low stock, no-shows — replaces empty charts.
- Service queue card.
- Hourly trend.
- Zero-state Today is informative: "Drawer not opened yet. Opening float?" not "₹0 revenue."

---

## 9. Accessibility

- **All interactive elements are keyboard-reachable.** No hover-only affordances.
- **Focus is always visible** — the focus ring uses `shadow-focus` (copper tint) and `outline-offset: 2px`.
- **Minimum touch target:** 44×44px on mobile (primitive enforced).
- **Form fields have associated labels** — never placeholder-as-label.
- **Colour alone is never the only signal.** Status uses colour + icon + text.
- **Heading hierarchy** is linear — no skipping levels.
- **`aria-live="polite"`** on key status regions (queue updates, stock changes). This is a P2 — ship basic WCAG AA first.

---

## 10. Enforcement

Mechanisms that prevent V1's drift from returning.

### 10.1 Lint (ESLint custom rule)

Rejects in `frontend/src/{app,components}/**/*.{ts,tsx}`:

- Raw Tailwind grays: `text-gray-*`, `bg-gray-*`, `border-gray-*` (and `zinc`, `slate`, `stone`, `neutral` variants).
- Hex literals in `className`: `bg-[#fff]`, `text-[#111]`.
- Arbitrary fixed widths on table columns: `w-[200px]` in a `<td>`.
- `h-screen` in page shells (use `min-h-dvh`).
- Detail state owned by a list page: `useState<string | null>(null)` paired with a `*DetailsDialog` / `*DetailDrawer` import inside a `*/page.tsx` under `app/dashboard/<entity>/`. Entity detail must go through its canonical route (§7.5).

Allowlisted only inside `frontend/src/styles/tokens.css`.

### 10.2 Visual regression

- Storybook stories for every primitive, with light + dark snapshots.
- Chromatic / Percy on PRs touching `components/ui/` or `styles/tokens.css`.
- Contrast test: automated script parses token CSS and asserts WCAG AA ratios before CI passes.

### 10.3 Code review checklist

Reviewers block merge if a PR:

- Adds a component that could be built from an existing primitive.
- Uses `font-family: "Outfit"` or references any retired token.
- Adds a loading state without a skeleton.
- Adds an empty state without Instrument Serif title + guiding body.
- Adds a destructive action in a toolbar (must be in a menu).
- Adds a dialog without responsive `max-w` / `max-h: 90dvh`.
- Opens an entity detail from anywhere without a canonical route (no `/dashboard/<entity>/[id]` full page + matching `@modal/(.)<entity>/[id]` intercept).

---

## 11. Do / Don't

| Don't | Do |
|---|---|
| `className="text-gray-500"` | `className="text-muted"` |
| `className="bg-[#fff]"` | `className="bg-surface-card"` |
| `<div role="button">` with custom styling | `<Button>` primitive |
| Spinner-only loading state | `<Skeleton>` matching the shape of real content |
| "No data available" | EmptyState with headline + guiding body + CTA |
| Delete icon always in table row | Destructive action inside row action menu |
| Multi-column grid inside a dialog on mobile (`grid-cols-2`) | `grid-cols-1 sm:grid-cols-2` |
| `max-w-4xl` dialog on mobile | Dialog primitive with responsive sizing |
| Amount shown in accent colour | Tabular number in `text-primary` + semantic badge for state |
| Red border on a non-destructive filter pill | Accent border for active filter; red reserved for destructive |
| Two different list patterns on two pages | One `<Table>` primitive with mobile card variant |
| `const [selectedBillId, setSelectedBillId] = useState(null)` in a list page | `router.push('/dashboard/bills/:id')` — the route owns the state, dialog is an intercepting route |

---

## 12. Open decisions (tracked, not blocking)

- **Tremor theme layer** — confirm it can be themed via our CSS vars without a fork.
- **Dark copper shade** — `#d97847` is our first calibration. Review against real charts, cards, and focus rings before locking.
- **Animation of number changes** (e.g. dashboard revenue ticking up during a bill payment) — currently disallowed; reconsider if there's strong user feedback.

---

## 13. Changelog

| Date | Change | Author |
|---|---|---|
| 2026-04-23 | Initial V2 draft: tokens (light + dark), typography scale, spacing, primitive inventory, layout shell, enforcement plan | Angel + Claude |
| 2026-04-23 | Locked "Customers" as the single term (no "Guests" split). Receipt print template out of scope for V2 (display serif is in-app only). | Angel |
| 2026-04-23 | Added §7.5 — entity detail routing via `@modal` parallel slot + intercepting routes. List pages must not own detail state. Enforced by lint + review checklist. | Angel |
| 2026-05-01 | Phase 0 landed: tokens.css (light + dark), typography stack self-hosted (Inter + Instrument Serif), 14 V2 primitives restyled (Button, Input, CurrencyInput, Combobox, Dialog, Card, Badge, EmptyState, Skeleton, DataTable, FilterBar, NavItem, Kbd, Toast), ESLint 9 flat config + `eslint-plugin-salon` with 4 rules (`no-raw-grays`, `no-hex-literals-in-classname`, `no-h-screen`, `no-list-owned-detail-state`) all in `warn` mode, Storybook 9 (Vite framework) with stories for every primitive, contrast CI script (26/26 pairs PASS), consolidated `npm run check` script. 162 tsc errors and 38 lint errors carried over from V1 — Phase 1 retrofit closes the gap. | Angel + Claude |
| 2026-05-02 | Phase 1 landed: `(shell)` route group with new SidebarV2 (192px labelled) + SidebarRail (56px collapsed via `Cmd+\` + localStorage), real route-derived TopBar + Breadcrumb, ⌘K command palette (cmdk) with navigation/customers/bills/SKUs/actions/recent providers, mobile BottomTabNav + MoreSheet with iOS safe-area inset, `@modal` parallel slot wired with bills as canonical entity (proof retrofit removed list-owned detail useState — `salon/no-list-owned-detail-state` warning eliminated). All V1 dashboard routes moved into `(shell)` group with URLs unchanged. tsc baseline 162, lint baseline 38 errors — both unchanged from Phase 0. Test count 106 → 149 (+43 across new shell + palette modules). | Angel + Claude |
