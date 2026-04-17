# SalonOS UI/UX Enhancement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign the entire SalonOS frontend with a Premium Dark theme, 4 swappable accent palettes, a Service Queue dashboard widget, revenue privacy toggle, and all 65+ mobile responsiveness fixes.

**Architecture:** CSS variable token system defined in `globals.css` (Tailwind v4 `@theme` block) drives all surface/accent colours; a `data-accent` attribute on `<html>` swaps palettes; each component is rebuilt in-place following the new token system without changing business logic.

**Tech Stack:** Next.js 16 App Router, React 19, TypeScript, Tailwind CSS v4 (`@theme` block), shadcn/ui, Zustand, Lucide React, Recharts.

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `frontend/src/app/globals.css` | Modify | Add surface/accent CSS tokens, body dark base |
| `frontend/src/lib/theme.ts` | Create | `getAccent()`, `setAccent()`, `initAccent()` helpers |
| `frontend/src/app/layout.tsx` | Modify | Call `initAccent()` on mount |
| `frontend/src/app/dashboard/layout.tsx` | Modify | Dark header, remove light bg |
| `frontend/src/components/app-sidebar.tsx` | Modify | Dark sidebar, active accent state, accent ring dots |
| `frontend/src/components/nav-bottom.tsx` | Create | Mobile bottom nav (4 items + More sheet) |
| `frontend/src/app/dashboard/page.tsx` | Modify | Revenue hiding, service queue data derivation |
| `frontend/src/components/dashboard/stat-card.tsx` | Create | Reusable dark stat card with eye-toggle support |
| `frontend/src/components/dashboard/service-queue.tsx` | Create | Per-staff lane widget |
| `frontend/src/components/dashboard/active-customer-card.tsx` | Modify | Dark tiles, status dots, dimmed checkout |
| `frontend/src/app/dashboard/pos/page.tsx` | Modify | Dark POS, FAB for mobile cart |
| `frontend/src/components/pos/cart-sidebar.tsx` | Modify | Dark cart sidebar styling |
| `frontend/src/app/dashboard/bills/page.tsx` | Modify | Table-to-card pattern |
| `frontend/src/app/dashboard/customers/page.tsx` | Modify | Table-to-card pattern |
| `frontend/src/app/dashboard/inventory/page.tsx` | Modify | Table-to-card pattern |
| `frontend/src/app/dashboard/purchases/invoices/page.tsx` | Modify | Table-to-card pattern |
| `frontend/src/app/dashboard/expenses/page.tsx` | Modify | Table-to-card pattern |
| `frontend/src/app/dashboard/settings/page.tsx` | Modify | Add Appearance section with accent switcher |

---

## Phase 1 — CSS Token System

### Task 1: Add dark surface + accent tokens to globals.css

**Files:**
- Modify: `frontend/src/app/globals.css`

- [ ] **Step 1: Open globals.css and locate the `@theme` block (line 7)**

Current `@theme` ends around line 47. We will append tokens after it.

- [ ] **Step 2: Add surface tokens and accent palette to globals.css**

Add this block immediately after the closing `}` of `@theme` (after line 47):

```css
/* ─── Dark surface tokens ───────────────────────────────── */
:root {
  --surface-page: #111111;
  --surface-card: #161616;
  --surface-row: #1a1a1a;
  --surface-hover: #202020;
  --surface-sidebar: #0a0a0a;
  --border-subtle: #2a2a2a;
  --text-primary: #f5f5f5;
  --text-secondary: #a3a3a3;
  --text-muted: #525252;

  /* Accent: Violet (default) */
  --accent: #7c3aed;
  --accent-hover: #6d28d9;
  --accent-bg: #160d2b;
  --accent-fg: #ffffff;
}

[data-accent="rose"] {
  --accent: #e11d48;
  --accent-hover: #be123c;
  --accent-bg: #2b0d14;
}

[data-accent="amber"] {
  --accent: #d97706;
  --accent-hover: #b45309;
  --accent-bg: #2b1a00;
}

[data-accent="teal"] {
  --accent: #0d9488;
  --accent-hover: #0f766e;
  --accent-bg: #00211f;
}

/* ─── Make tokens available as Tailwind utilities ────────── */
@theme inline {
  --color-surface-page: var(--surface-page);
  --color-surface-card: var(--surface-card);
  --color-surface-row: var(--surface-row);
  --color-surface-hover: var(--surface-hover);
  --color-surface-sidebar: var(--surface-sidebar);
  --color-border-subtle: var(--border-subtle);
  --color-text-primary: var(--text-primary);
  --color-text-secondary: var(--text-secondary);
  --color-text-muted: var(--text-muted);
  --color-accent: var(--accent);
  --color-accent-hover: var(--accent-hover);
  --color-accent-bg: var(--accent-bg);
}
```

- [ ] **Step 3: Replace the body base styles (around line 49-54)**

Find:
```css
body {
  font-family: var(--font-sans);
  background-color: var(--color-gray-50);
  color: var(--color-gray-900);
}
```

Replace with:
```css
body {
  font-family: var(--font-sans);
  background-color: var(--surface-page);
  color: var(--text-primary);
}
```

- [ ] **Step 4: Verify the dev server compiles without errors**

```bash
cd frontend && npm run dev
```

Expected: no CSS compilation errors in terminal.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/app/globals.css
git commit -m "feat(ui): add dark surface and accent CSS token system"
```

---

### Task 2: Create theme helper and wire accent init to app layout

**Files:**
- Create: `frontend/src/lib/theme.ts`
- Modify: `frontend/src/app/layout.tsx`

- [ ] **Step 1: Create frontend/src/lib/theme.ts**

```typescript
export type AccentName = 'violet' | 'rose' | 'amber' | 'teal';

const STORAGE_KEY = 'salon-accent';
const VALID_ACCENTS: AccentName[] = ['violet', 'rose', 'amber', 'teal'];

export function getAccent(): AccentName {
  if (typeof window === 'undefined') return 'violet';
  const stored = localStorage.getItem(STORAGE_KEY) as AccentName | null;
  return stored && VALID_ACCENTS.includes(stored) ? stored : 'violet';
}

export function setAccent(accent: AccentName): void {
  localStorage.setItem(STORAGE_KEY, accent);
  applyAccent(accent);
}

export function applyAccent(accent: AccentName): void {
  const html = document.documentElement;
  if (accent === 'violet') {
    html.removeAttribute('data-accent');
  } else {
    html.setAttribute('data-accent', accent);
  }
}

export function initAccent(): void {
  applyAccent(getAccent());
}
```

- [ ] **Step 2: Read frontend/src/app/layout.tsx to see current content**

```bash
cat frontend/src/app/layout.tsx
```

- [ ] **Step 3: Add accent init to layout.tsx**

Add a `'use client'` ThemeInit component that calls `initAccent()` on mount. Add it inside the existing layout's `<body>` before `{children}`:

```tsx
// Add near the top of layout.tsx (before the default export):
'use client';
import { useEffect } from 'react';
import { initAccent } from '@/lib/theme';

function ThemeInit() {
  useEffect(() => {
    initAccent();
  }, []);
  return null;
}
```

Then inside the layout's `<body>` add `<ThemeInit />` as the first child.

Note: `layout.tsx` is a Server Component by default. Add `ThemeInit` as a separate client component in the same file using the pattern above, and render it inside the server layout's `<body>`.

- [ ] **Step 4: Verify accent switching works in browser console**

Open browser console and run:
```javascript
document.documentElement.setAttribute('data-accent', 'rose')
```

Expected: accent colour changes to rose (`#e11d48`).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/theme.ts frontend/src/app/layout.tsx
git commit -m "feat(ui): add accent init helper and wire to app layout"
```

---

## Phase 2 — Sidebar + Bottom Nav

### Task 3: Restyle the dashboard layout header

**Files:**
- Modify: `frontend/src/app/dashboard/layout.tsx`

- [ ] **Step 1: Read the current layout.tsx**

The file is at `frontend/src/app/dashboard/layout.tsx`. Current content (already has `min-h-dvh` and responsive padding from a prior update):

```tsx
<main className="w-full min-h-dvh overflow-hidden flex flex-col bg-slate-50">
  <header className="h-12 md:h-14 border-b bg-white px-4 flex items-center justify-between shrink-0 z-10 sticky top-0">
```

- [ ] **Step 2: Apply dark styling to layout**

Replace the `<main>` and `<header>` class strings:

Find:
```tsx
<main className="w-full min-h-dvh overflow-hidden flex flex-col bg-slate-50">
  <header className="h-12 md:h-14 border-b bg-white px-4 flex items-center justify-between shrink-0 z-10 sticky top-0">
    <div className="flex items-center gap-2">
      <SidebarTrigger />
      <div className="h-4 w-px bg-slate-200 mx-2 hidden sm:block" />
      <h1 className="text-sm font-medium text-slate-600 hidden sm:block">Dashboard</h1>
    </div>
```

Replace with:
```tsx
<main className="w-full min-h-dvh overflow-hidden flex flex-col bg-surface-page">
  <header className="h-12 md:h-14 border-b border-border-subtle bg-surface-sidebar px-4 flex items-center justify-between shrink-0 z-10 sticky top-0">
    <div className="flex items-center gap-2">
      <SidebarTrigger className="text-text-secondary hover:text-text-primary" />
      <div className="h-4 w-px bg-border-subtle mx-2 hidden sm:block" />
      <h1 className="text-sm font-medium text-text-secondary hidden sm:block">Dashboard</h1>
    </div>
```

- [ ] **Step 3: Add bottom nav placeholder to layout (mobile only)**

After the closing `</main>` (but still inside `<SidebarProvider>`), add:

```tsx
{/* Bottom nav is rendered per-page via NavBottom component - see Task 4 */}
```

This is just a comment placeholder — the actual NavBottom is added in Task 4.

- [ ] **Step 4: Verify layout renders dark on all dashboard pages**

Visit `/dashboard` in the browser. Expected: dark header + dark page background, no white flash.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/app/dashboard/layout.tsx
git commit -m "feat(ui): apply dark tokens to dashboard layout header"
```

---

### Task 4: Restyle the app sidebar

**Files:**
- Modify: `frontend/src/components/app-sidebar.tsx`

- [ ] **Step 1: Read the current sidebar (already done above)**

Key classes to change:
- `<Sidebar>` wrapper: needs dark bg override
- Active item: needs accent left-border + accent-bg fill  
- Footer user button: needs dark hover state

- [ ] **Step 2: Update Sidebar wrapper and active item styles**

Find:
```tsx
<Sidebar collapsible="icon" {...props} className="border-r border-sidebar-border bg-sidebar">
```

Replace with:
```tsx
<Sidebar collapsible="icon" {...props} className="border-r border-border-subtle bg-surface-sidebar">
```

- [ ] **Step 3: Update nav item active + hover styling**

Find:
```tsx
<SidebarMenuButton 
  asChild 
  isActive={pathname === item.url}
  tooltip={item.title}
  className="hover:bg-sidebar-accent hover:text-sidebar-accent-foreground transition-colors"
  size="default"
>
```

Replace with:
```tsx
<SidebarMenuButton 
  asChild 
  isActive={pathname === item.url || pathname.startsWith(item.url + '/')}
  tooltip={item.title}
  className={`
    transition-colors hover:bg-surface-hover hover:text-text-primary
    ${(pathname === item.url || pathname.startsWith(item.url + '/'))
      ? 'bg-accent-bg text-text-primary border-l-[3px] border-accent rounded-l-none'
      : 'text-text-secondary border-l-[3px] border-transparent'
    }
  `}
  size="default"
>
```

- [ ] **Step 4: Update footer user button dark styling**

Find:
```tsx
<SidebarMenuButton
  size="lg"
  className="data-[state=open]:bg-sidebar-accent data-[state=open]:text-sidebar-accent-foreground"
>
```

Replace with:
```tsx
<SidebarMenuButton
  size="lg"
  className="data-[state=open]:bg-surface-hover text-text-secondary hover:text-text-primary hover:bg-surface-hover"
>
```

- [ ] **Step 5: Update sidebar header text colors**

Find:
```tsx
<div className="grid flex-1 text-left text-sm leading-tight">
  <span className="truncate font-semibold">
    {settings?.salon_name || 'Salon'}
  </span>
  <span className="truncate text-xs">
    {settings?.salon_tagline || 'Management'}
  </span>
</div>
```

Replace with:
```tsx
<div className="grid flex-1 text-left text-sm leading-tight">
  <span className="truncate font-semibold text-text-primary">
    {settings?.salon_name || 'Salon'}
  </span>
  <span className="truncate text-xs text-text-secondary">
    {settings?.salon_tagline || 'Management'}
  </span>
</div>
```

- [ ] **Step 6: Verify sidebar renders correctly**

Visit `/dashboard`. Expected: dark sidebar with violet left-border on the active item, light text on dark background.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/components/app-sidebar.tsx
git commit -m "feat(ui): apply dark theme to app sidebar with accent active state"
```

---

### Task 5: Create mobile bottom nav

**Files:**
- Create: `frontend/src/components/nav-bottom.tsx`
- Modify: `frontend/src/app/dashboard/layout.tsx`

- [ ] **Step 1: Create frontend/src/components/nav-bottom.tsx**

```tsx
'use client';

import { usePathname, useRouter } from 'next/navigation';
import { LayoutDashboard, CreditCard, Receipt, MoreHorizontal } from 'lucide-react';
import { useState } from 'react';
import { Sheet, SheetContent, SheetHeader, SheetTitle } from '@/components/ui/sheet';
import { useAuthStore } from '@/stores/auth-store';

const PRIMARY_NAV = [
  { title: 'Home', url: '/dashboard', icon: LayoutDashboard, roles: ['owner', 'receptionist'] },
  { title: 'POS', url: '/dashboard/pos', icon: CreditCard, roles: ['owner', 'receptionist', 'staff'] },
  { title: 'Bills', url: '/dashboard/bills', icon: Receipt, roles: ['owner', 'receptionist'] },
];

const MORE_NAV = [
  { title: 'Customers', url: '/dashboard/customers' },
  { title: 'Inventory', url: '/dashboard/inventory' },
  { title: 'Purchases', url: '/dashboard/purchases/invoices' },
  { title: 'Expenses', url: '/dashboard/expenses' },
  { title: 'Reports', url: '/dashboard/reports' },
  { title: 'Settings', url: '/dashboard/settings' },
];

export function NavBottom() {
  const pathname = usePathname();
  const router = useRouter();
  const { user } = useAuthStore();
  const [moreOpen, setMoreOpen] = useState(false);

  const visibleNav = PRIMARY_NAV.filter(item => item.roles.includes(user?.role || ''));

  const isActive = (url: string) => pathname === url || pathname.startsWith(url + '/');

  return (
    <>
      <nav className="fixed bottom-0 left-0 right-0 z-50 flex md:hidden border-t border-border-subtle bg-surface-sidebar">
        {visibleNav.map((item) => (
          <button
            key={item.url}
            onClick={() => router.push(item.url)}
            className={`flex flex-col items-center justify-center flex-1 py-2 gap-1 text-[10px] transition-colors ${
              isActive(item.url)
                ? 'text-accent'
                : 'text-text-muted hover:text-text-secondary'
            }`}
          >
            {isActive(item.url) && (
              <span className="absolute top-0 w-8 h-0.5 bg-accent rounded-full" />
            )}
            <item.icon className="h-5 w-5" />
            <span>{item.title}</span>
          </button>
        ))}
        <button
          onClick={() => setMoreOpen(true)}
          className="flex flex-col items-center justify-center flex-1 py-2 gap-1 text-[10px] text-text-muted hover:text-text-secondary transition-colors"
        >
          <MoreHorizontal className="h-5 w-5" />
          <span>More</span>
        </button>
      </nav>

      <Sheet open={moreOpen} onOpenChange={setMoreOpen}>
        <SheetContent side="bottom" className="bg-surface-card border-border-subtle rounded-t-xl pb-safe">
          <SheetHeader className="mb-4">
            <SheetTitle className="text-text-primary">More</SheetTitle>
          </SheetHeader>
          <div className="grid grid-cols-3 gap-3 pb-6">
            {MORE_NAV.map((item) => (
              <button
                key={item.url}
                onClick={() => { router.push(item.url); setMoreOpen(false); }}
                className="flex items-center justify-center py-3 px-2 rounded-lg bg-surface-row text-text-secondary hover:bg-surface-hover hover:text-text-primary text-sm transition-colors"
              >
                {item.title}
              </button>
            ))}
          </div>
        </SheetContent>
      </Sheet>
    </>
  );
}
```

- [ ] **Step 2: Add NavBottom to dashboard layout**

In `frontend/src/app/dashboard/layout.tsx`, add the import and render `<NavBottom />` inside the `<main>` block, after `<div className="flex-1 overflow-auto ...">`:

Add import at top:
```tsx
import { NavBottom } from '@/components/nav-bottom';
```

Add before the closing `</main>`:
```tsx
<NavBottom />
```

Also add bottom padding on mobile so content isn't hidden behind the nav bar. Change the content div:

Find:
```tsx
<div className="flex-1 overflow-auto p-3 sm:p-4 md:p-6 relative">
```

Replace:
```tsx
<div className="flex-1 overflow-auto p-3 sm:p-4 md:p-6 pb-20 md:pb-6 relative">
```

- [ ] **Step 3: Verify bottom nav on mobile viewport**

In browser DevTools, switch to a 390px wide viewport (iPhone 14). Expected: bottom nav appears with Home, POS, Bills, More. Tapping More opens a sheet.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/nav-bottom.tsx frontend/src/app/dashboard/layout.tsx
git commit -m "feat(ui): add mobile bottom navigation with More sheet"
```

---

## Phase 3 — Dashboard Redesign

### Task 6: Create reusable dark StatCard component

**Files:**
- Create: `frontend/src/components/dashboard/stat-card.tsx`

- [ ] **Step 1: Create frontend/src/components/dashboard/stat-card.tsx**

```tsx
'use client';

import { useState, useEffect } from 'react';
import { Eye, EyeOff } from 'lucide-react';
import { useAuthStore } from '@/stores/auth-store';

interface StatCardProps {
  title: string;
  value: string;
  subValue?: string;
  /** If true, this card is hidden by default and has an eye toggle */
  sensitive?: boolean;
  /** localStorage key to persist visibility per user */
  visibilityKey?: string;
  trend?: React.ReactNode;
  icon?: React.ReactNode;
}

export function StatCard({
  title,
  value,
  subValue,
  sensitive = false,
  visibilityKey,
  trend,
  icon,
}: StatCardProps) {
  const { user } = useAuthStore();
  const storageKey = visibilityKey ? `${visibilityKey}-${user?.id}` : null;

  const [visible, setVisible] = useState(() => {
    if (!sensitive) return true;
    if (typeof window === 'undefined' || !storageKey) return false;
    return localStorage.getItem(storageKey) === 'true';
  });

  // Staff never see sensitive cards
  if (sensitive && user?.role === 'staff') return null;

  const toggle = () => {
    const next = !visible;
    setVisible(next);
    if (storageKey) localStorage.setItem(storageKey, String(next));
  };

  return (
    <div className="rounded-xl bg-surface-card border border-border-subtle p-4 flex flex-col gap-2">
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium text-text-secondary uppercase tracking-wide">
          {title}
        </span>
        <div className="flex items-center gap-2">
          {icon && <span className="text-text-muted">{icon}</span>}
          {sensitive && (
            <button
              onClick={toggle}
              className="text-text-muted hover:text-text-secondary transition-colors"
              aria-label={visible ? 'Hide value' : 'Show value'}
            >
              {visible ? <EyeOff className="h-3.5 w-3.5" /> : <Eye className="h-3.5 w-3.5" />}
            </button>
          )}
        </div>
      </div>

      <div className="flex items-end justify-between gap-2">
        <span className="text-xl md:text-2xl font-bold text-text-primary tabular-nums">
          {sensitive && !visible ? '••••' : value}
        </span>
        {trend && <span className="shrink-0">{trend}</span>}
      </div>

      {subValue && (
        <span className="text-xs text-text-muted">
          {sensitive && !visible ? '—' : subValue}
        </span>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit
```

Expected: no errors in `stat-card.tsx`.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/dashboard/stat-card.tsx
git commit -m "feat(ui): add dark StatCard component with revenue eye-toggle"
```

---

### Task 7: Create Service Queue widget

**Files:**
- Create: `frontend/src/components/dashboard/service-queue.tsx`

- [ ] **Step 1: Create frontend/src/components/dashboard/service-queue.tsx**

The component receives `sessions` (the existing `CustomerSession[]` from `/appointments/walkins/active`) and derives per-staff lanes:

```tsx
'use client';

import { Clock } from 'lucide-react';

interface Service {
  id: string;
  name: string;
}

interface Staff {
  id: string;
  display_name: string;
}

interface WalkIn {
  id: string;
  service: Service;
  assigned_staff: Staff;
  status: string;
  checked_in_at: string | null;
}

interface CustomerSession {
  session_id: string;
  customer_name: string;
  walkins: WalkIn[];
}

interface StaffLane {
  staff: Staff;
  items: Array<{
    walkinId: string;
    serviceName: string;
    customerName: string;
    checkedInAt: Date;
    status: string;
  }>;
}

function buildLanes(sessions: CustomerSession[]): StaffLane[] {
  const laneMap = new Map<string, StaffLane>();

  for (const session of sessions) {
    for (const walkin of session.walkins) {
      if (walkin.status === 'completed') continue;
      const staffId = walkin.assigned_staff.id;

      if (!laneMap.has(staffId)) {
        laneMap.set(staffId, { staff: walkin.assigned_staff, items: [] });
      }

      laneMap.get(staffId)!.items.push({
        walkinId: walkin.id,
        serviceName: walkin.service.name,
        customerName: session.customer_name,
        checkedInAt: walkin.checked_in_at ? new Date(walkin.checked_in_at) : new Date(),
        status: walkin.status,
      });
    }
  }

  // Sort each lane by check-in time ascending
  for (const lane of laneMap.values()) {
    lane.items.sort((a, b) => a.checkedInAt.getTime() - b.checkedInAt.getTime());
  }

  return Array.from(laneMap.values());
}

function elapsedMinutes(date: Date): number {
  return Math.floor((Date.now() - date.getTime()) / 60000);
}

const STATUS_DOT: Record<string, string> = {
  checked_in: 'bg-blue-500',
  in_progress: 'bg-amber-400',
};

interface ServiceQueueProps {
  sessions: CustomerSession[];
}

export function ServiceQueue({ sessions }: ServiceQueueProps) {
  const lanes = buildLanes(sessions);

  if (lanes.length === 0) {
    return (
      <div className="rounded-xl bg-surface-card border border-border-subtle p-6 text-center">
        <p className="text-sm text-text-muted">No active services</p>
      </div>
    );
  }

  return (
    <div className="rounded-xl bg-surface-card border border-border-subtle p-4">
      <h3 className="text-xs font-medium text-text-secondary uppercase tracking-wide mb-3">
        Service Queue
      </h3>
      <div className="grid gap-3" style={{ gridTemplateColumns: `repeat(${Math.min(lanes.length, 3)}, 1fr)` }}>
        {lanes.map((lane) => (
          <div key={lane.staff.id} className="flex flex-col gap-2">
            <div className="text-xs font-semibold text-text-primary truncate pb-1 border-b border-border-subtle">
              {lane.staff.display_name}
            </div>
            {lane.items.map((item, i) => (
              <div
                key={item.walkinId}
                className="flex items-start gap-2 rounded-lg bg-surface-row p-2"
              >
                <span className="mt-1 shrink-0">
                  <span className={`block h-2 w-2 rounded-full ${STATUS_DOT[item.status] ?? 'bg-text-muted'}`} />
                </span>
                <div className="min-w-0 flex-1">
                  <p className="text-xs font-medium text-text-primary truncate">{item.serviceName}</p>
                  <p className="text-[10px] text-text-secondary truncate">{item.customerName}</p>
                </div>
                <span className="shrink-0 flex items-center gap-0.5 text-[10px] text-text-muted">
                  <Clock className="h-3 w-3" />
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

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit
```

Expected: no errors in `service-queue.tsx`.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/dashboard/service-queue.tsx
git commit -m "feat(ui): add ServiceQueue widget with per-staff lanes"
```

---

### Task 8: Restyle active customer card with dark tokens + status dots

**Files:**
- Modify: `frontend/src/components/dashboard/active-customer-card.tsx`

- [ ] **Step 1: Replace the Card wrapper and header classes**

Find:
```tsx
<Card className="hover:shadow-md transition-shadow">
  <CardHeader className="p-4 pb-2">
```

Replace with:
```tsx
<div className="rounded-xl bg-surface-card border border-border-subtle hover:border-accent/30 transition-colors">
  <div className="p-4 pb-2">
```

- [ ] **Step 2: Replace the customer name + time badge**

Find:
```tsx
<h3 className="font-semibold text-base truncate leading-none">
  {titleCase(session.customer_name)}
</h3>
<Badge variant="secondary" className="h-5 px-1.5 text-[10px] font-normal">
  <Clock className="h-3 w-3 mr-1" />
  {session.time_since_checkin}m
</Badge>
```

Replace with:
```tsx
<h3 className="font-semibold text-base truncate leading-none text-text-primary">
  {titleCase(session.customer_name)}
</h3>
<span className="inline-flex items-center gap-1 text-[10px] text-text-muted bg-surface-row px-2 py-0.5 rounded-full">
  <Clock className="h-3 w-3" />
  {session.time_since_checkin}m
</span>
```

- [ ] **Step 3: Replace the per-service status icons with coloured dots**

Replace the `getStatusIcon` function:

Find:
```tsx
const getStatusIcon = (status: string) => {
  switch (status) {
    case 'checked_in':
      return <Circle className="h-3 w-3 text-blue-500" />;
    case 'in_progress':
      return <Loader className="h-3 w-3 text-amber-500 animate-spin" />;
    case 'completed':
      return <CheckCircle className="h-3 w-3 text-green-500" />;
    default:
      return <Circle className="h-3 w-3 text-gray-400" />;
  }
};
```

Replace with:
```tsx
const STATUS_COLORS: Record<string, string> = {
  checked_in: 'bg-blue-500',
  in_progress: 'bg-amber-400 animate-pulse',
  completed: 'bg-green-500',
};

const getStatusDot = (status: string) => (
  <span className={`block h-2 w-2 rounded-full shrink-0 ${STATUS_COLORS[status] ?? 'bg-text-muted'}`} />
);
```

Then update the JSX that uses `getStatusIcon` — find:
```tsx
{getStatusIcon(walkin.status)}
```

Replace with:
```tsx
{getStatusDot(walkin.status)}
```

- [ ] **Step 4: Update service row container and per-walkin row styling**

Find:
```tsx
<CardContent className="p-4 py-2">
  <div className="space-y-2">
    {session.walkins.map((walkin) => (
      <div
        key={walkin.id}
        className="flex items-center justify-between text-sm gap-2"
      >
```

Replace with:
```tsx
<div className="px-4 py-2">
  <div className="space-y-1.5">
    {session.walkins.map((walkin) => (
      <div
        key={walkin.id}
        className="flex items-center justify-between text-sm gap-2 rounded-lg bg-surface-row px-3 py-2"
      >
```

- [ ] **Step 5: Update action buttons styling**

Find:
```tsx
{walkin.status === 'checked_in' && (
  <Button
    variant="ghost"
    size="sm"
    className="h-6 w-6 p-0"
    onClick={() => handleStartService(walkin.id)}
    title="Start service"
  >
    <Play className="h-3 w-3" />
  </Button>
)}
{walkin.status === 'in_progress' && (
  <Button
    variant="ghost"
    size="sm"
    className="h-6 w-6 p-0"
    onClick={() => handleCompleteService(walkin.id)}
    title="Complete service"
  >
    <Check className="h-3 w-3" />
  </Button>
)}
```

Replace with:
```tsx
{walkin.status === 'checked_in' && (
  <Button
    variant="ghost"
    size="sm"
    className="h-6 w-6 p-0 text-blue-400 hover:text-blue-300 hover:bg-blue-500/10"
    onClick={() => handleStartService(walkin.id)}
    title="Start service"
  >
    <Play className="h-3 w-3" />
  </Button>
)}
{walkin.status === 'in_progress' && (
  <Button
    variant="ghost"
    size="sm"
    className="h-6 w-6 p-0 text-green-400 hover:text-green-300 hover:bg-green-500/10"
    onClick={() => handleCompleteService(walkin.id)}
    title="Complete service"
  >
    <Check className="h-3 w-3" />
  </Button>
)}
```

- [ ] **Step 6: Update footer total row and close the div tags**

Find:
```tsx
<div className="mt-3 pt-2 border-t flex justify-between items-center">
  <span className="text-xs text-muted-foreground">Total Amount</span>
  <span className="font-semibold text-sm">
    {formatPrice(session.total_amount)}
  </span>
</div>
</CardContent>

<CardFooter className="p-4 pt-1">
  <Button
    className="w-full h-8 text-xs"
    size="sm"
    onClick={() => onCheckout(session.session_id)}
  >
    {session.all_completed ? 'Checkout' : 'Go to Checkout'}
  </Button>
</CardFooter>
</Card>
```

Replace with:
```tsx
<div className="mt-3 pt-2 border-t border-border-subtle flex justify-between items-center">
  <span className="text-xs text-text-secondary">Total Amount</span>
  <span className="font-semibold text-sm text-text-primary">
    {formatPrice(session.total_amount)}
  </span>
</div>
</div>

<div className="px-4 pb-4 pt-1">
  <Button
    className="w-full h-8 text-xs"
    size="sm"
    disabled={!session.all_completed}
    style={!session.all_completed ? { opacity: 0.4, cursor: 'not-allowed' } : {}}
    onClick={() => session.all_completed && onCheckout(session.session_id)}
  >
    Checkout
  </Button>
</div>
</div>
```

- [ ] **Step 7: Remove unused imports**

Remove `Card, CardContent, CardFooter, CardHeader` from imports. Remove `Circle, Loader, CheckCircle` from imports (replaced by dots).

- [ ] **Step 8: Verify component renders correctly**

Check the dashboard with active sessions. Expected: dark tiles, coloured dots, dimmed Checkout when services incomplete.

- [ ] **Step 9: Commit**

```bash
git add frontend/src/components/dashboard/active-customer-card.tsx
git commit -m "feat(ui): restyle active customer card with dark tokens and status dots"
```

---

### Task 9: Wire StatCard and ServiceQueue into dashboard page

**Files:**
- Modify: `frontend/src/app/dashboard/page.tsx`

- [ ] **Step 1: Add imports for new components at top of dashboard/page.tsx**

Add these imports:
```tsx
import { StatCard } from '@/components/dashboard/stat-card';
import { ServiceQueue } from '@/components/dashboard/service-queue';
```

- [ ] **Step 2: Replace the stat cards section in the JSX**

Find the section that renders 4 stat cards (it uses `<Card>` components showing revenue, services, customers, etc.). Replace the entire stat grid with:

```tsx
<div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-6">
  <StatCard
    title="Today's Revenue"
    value={formatPrice(stats.today_revenue)}
    subValue={`${Math.round((stats.today_revenue / (settings.daily_revenue_target_paise || 1)) * 100)}% of daily goal`}
    sensitive
    visibilityKey="revenue-visible"
    trend={comparison && <TrendIndicator value={comparison.revenue_percent_change} />}
  />
  <StatCard
    title="Services"
    value={String(stats.today_services)}
    subValue={`of ${settings.daily_services_target} target`}
    trend={comparison && <TrendIndicator value={comparison.services_percent_change} />}
  />
  <StatCard
    title="Customers"
    value={String(stats.today_customers)}
    trend={comparison && <TrendIndicator value={comparison.customers_percent_change} />}
  />
  <StatCard
    title="Active Now"
    value={String(stats.active_services)}
    subValue={stats.pending_bills ? `${stats.pending_bills} pending bills` : undefined}
  />
</div>
```

- [ ] **Step 3: Replace Quick Actions with ServiceQueue in the right column**

Find the right column section (it will contain Quick Actions or a similar widget). Replace it with:

```tsx
<ServiceQueue sessions={activeSessions} />
```

- [ ] **Step 4: Verify dashboard renders correctly with dark stat cards and service queue**

Visit `/dashboard`. Expected: 4 dark stat cards with revenue hidden by default, service queue in right column.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/app/dashboard/page.tsx
git commit -m "feat(ui): integrate StatCard and ServiceQueue into dashboard page"
```

---

## Phase 4 — POS Page

### Task 10: Apply dark theme to POS page and add mobile FAB

**Files:**
- Modify: `frontend/src/app/dashboard/pos/page.tsx`
- Modify: `frontend/src/components/pos/cart-sidebar.tsx`

- [ ] **Step 1: Read the current POS page structure**

```bash
head -80 frontend/src/app/dashboard/pos/page.tsx
```

- [ ] **Step 2: Update POS page container and search bar styling**

Find the main container class (typically `flex h-full gap-4` or similar). Update to use dark tokens:

Find any `bg-white`, `bg-gray-50`, `bg-slate-*` in the POS page and replace with dark equivalents:
- `bg-white` → `bg-surface-card`
- `bg-gray-50` or `bg-slate-50` → `bg-surface-page`
- `border-gray-*` or `border-slate-*` → `border-border-subtle`
- `text-gray-*` secondary text → `text-text-secondary`
- `text-gray-900` primary text → `text-text-primary`

- [ ] **Step 3: Add mobile FAB for cart**

Find the section where `CartSidebar` is rendered (it will be `hidden md:block` or similar). After it, add a FAB button for mobile:

```tsx
{/* Mobile cart FAB */}
{cartItemCount > 0 && (
  <button
    className="fixed bottom-20 right-4 z-40 flex md:hidden items-center justify-center h-14 w-14 rounded-full bg-accent text-white shadow-lg shadow-accent/30 transition-transform active:scale-95"
    onClick={() => setCartSheetOpen(true)}
    aria-label="Open cart"
  >
    <ShoppingCart className="h-6 w-6" />
    <span className="absolute -top-1 -right-1 flex h-5 w-5 items-center justify-center rounded-full bg-white text-accent text-[10px] font-bold">
      {cartItemCount}
    </span>
  </button>
)}
```

Note: `cartItemCount` should come from `useCartStore()`. Add `const cartItems = useCartStore(state => state.items)` and `const cartItemCount = cartItems.length` if not already present. Add a `cartSheetOpen` state and a `Sheet` component wrapping `CartSidebar` for mobile.

- [ ] **Step 4: Update cart-sidebar.tsx dark styling**

In `frontend/src/components/pos/cart-sidebar.tsx`, replace light background/border classes:

```tsx
// Find the root container (usually a div with bg-white or bg-gray-50 + border-l)
// Change to:
className="... bg-surface-card border-l border-border-subtle ..."

// Line item rows - change bg-gray-50/slate to:
className="... bg-surface-row rounded-lg ..."

// Totals section separator:
className="... border-t border-border-subtle ..."

// Secondary text:
className="... text-text-secondary ..."

// Checkout button (already accent-colored in most shadcn configs, but verify):
className="... bg-accent hover:bg-accent-hover text-white ..."
```

- [ ] **Step 5: Verify POS dark styling and mobile FAB**

Visit `/dashboard/pos` on both desktop (1280px) and mobile (390px) viewport.

Expected:
- Desktop: dark two-panel layout, dark service cards
- Mobile: service grid visible, FAB appears when cart has items, tapping opens Sheet

- [ ] **Step 6: Commit**

```bash
git add frontend/src/app/dashboard/pos/page.tsx frontend/src/components/pos/cart-sidebar.tsx
git commit -m "feat(ui): apply dark theme to POS page with mobile cart FAB"
```

---

## Phase 5 — Table-to-Card Pattern

### Task 11: Bills page — table-to-card

**Files:**
- Modify: `frontend/src/app/dashboard/bills/page.tsx`

- [ ] **Step 1: Read the bills page table markup**

```bash
grep -n "table\|thead\|tbody\|tr\|td\|th" frontend/src/app/dashboard/bills/page.tsx | head -30
```

- [ ] **Step 2: Wrap the existing table in `hidden md:block`**

Find the root table element (will be a `<table>` or a shadcn `<Table>`). Wrap it:

```tsx
{/* Desktop table */}
<div className="hidden md:block">
  {/* ... existing table JSX ... */}
</div>
```

- [ ] **Step 3: Add mobile card list using `md:hidden`**

After the desktop table wrapper, add:

```tsx
{/* Mobile cards */}
<div className="md:hidden space-y-2">
  {bills.map((bill) => (
    <div
      key={bill.id}
      className="rounded-xl bg-surface-card border border-border-subtle p-4 space-y-2"
    >
      <div className="flex items-center justify-between">
        <span className="font-mono text-xs text-text-muted">
          {bill.invoice_number ?? '—'}
        </span>
        <span className="text-xs text-text-muted">
          {new Date(bill.posted_at ?? bill.created_at).toLocaleTimeString('en-IN', {
            hour: '2-digit',
            minute: '2-digit',
          })}
        </span>
      </div>
      <div className="flex items-center justify-between">
        <span className="font-semibold text-text-primary text-sm">
          {titleCase(bill.customer_name ?? 'Walk-in')}
        </span>
        <span className="font-semibold text-accent text-sm">
          ₹{(bill.rounded_total / 100).toLocaleString('en-IN')}
        </span>
      </div>
      <div className="flex items-center justify-between gap-2">
        <span className={`text-xs px-2 py-0.5 rounded-full ${
          bill.status === 'paid' ? 'bg-green-500/15 text-green-400' :
          bill.status === 'pending' ? 'bg-amber-500/15 text-amber-400' :
          'bg-surface-row text-text-muted'
        }`}>
          {bill.status}
        </span>
        <Button
          variant="ghost"
          size="sm"
          className="h-7 text-xs text-text-secondary hover:text-text-primary"
          onClick={() => { setSelectedBillId(bill.id); setShowBillDetails(true); }}
        >
          View
        </Button>
      </div>
    </div>
  ))}
</div>
```

- [ ] **Step 4: Apply dark styling to the desktop table headers and rows**

In the existing table, replace light header/row classes:
- `bg-gray-50` / `bg-slate-50` headers → `bg-surface-row`
- `border-gray-200` / `border-slate-200` → `border-border-subtle`
- `text-gray-500` → `text-text-secondary`
- `text-gray-900` → `text-text-primary`

- [ ] **Step 5: Verify on mobile and desktop viewports**

Expected: mobile shows cards, desktop shows table. Both dark.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/app/dashboard/bills/page.tsx
git commit -m "feat(ui): bills page — dark theme + table-to-card for mobile"
```

---

### Task 12: Customers page — table-to-card

**Files:**
- Modify: `frontend/src/app/dashboard/customers/page.tsx`

- [ ] **Step 1: Wrap existing table in `hidden md:block`**

Same pattern as Task 11, Step 2.

- [ ] **Step 2: Add mobile card list**

```tsx
<div className="md:hidden space-y-2">
  {customers.map((customer) => (
    <div
      key={customer.id}
      className="rounded-xl bg-surface-card border border-border-subtle p-4 space-y-2"
    >
      <div className="flex items-center justify-between">
        <span className="font-semibold text-text-primary text-sm">
          {titleCase(customer.full_name)}
        </span>
        {customer.gender && (
          <span className="text-[10px] px-2 py-0.5 rounded-full bg-surface-row text-text-muted">
            {customer.gender}
          </span>
        )}
      </div>
      <div className="flex items-center justify-between text-xs text-text-secondary">
        <span>{customer.phone}</span>
        <span>{customer.total_visits ?? 0} visits</span>
      </div>
      {customer.pending_amount > 0 && (
        <div className="flex items-center justify-between text-xs">
          <span className="text-text-muted">Pending</span>
          <span className="text-amber-400 font-medium">
            ₹{(customer.pending_amount / 100).toLocaleString('en-IN')}
          </span>
        </div>
      )}
    </div>
  ))}
</div>
```

Note: field names (`full_name`, `phone`, `total_visits`, `pending_amount`) must match the actual API response shape in `customers/page.tsx`. Read the file's `interface Customer` before writing the card to verify field names.

- [ ] **Step 3: Apply dark classes to desktop table (same method as Task 11, Step 4)**

- [ ] **Step 4: Verify and commit**

```bash
git add frontend/src/app/dashboard/customers/page.tsx
git commit -m "feat(ui): customers page — dark theme + table-to-card for mobile"
```

---

### Task 13: Inventory, Purchases, Expenses pages — table-to-card

**Files:**
- Modify: `frontend/src/app/dashboard/inventory/page.tsx`
- Modify: `frontend/src/app/dashboard/purchases/invoices/page.tsx`
- Modify: `frontend/src/app/dashboard/expenses/page.tsx`

Apply the same table-to-card pattern from Task 11 to each page. For each:

- [ ] **Step 1: Read the page to confirm interface field names**

```bash
grep -n "interface\|\.tsx\|\.map(" frontend/src/app/dashboard/inventory/page.tsx | head -20
```

- [ ] **Step 2: Wrap existing table in `hidden md:block`**

- [ ] **Step 3: Add `md:hidden` mobile card list for Inventory**

```tsx
<div className="md:hidden space-y-2">
  {products.map((product) => (
    <div key={product.id} className="rounded-xl bg-surface-card border border-border-subtle p-4 space-y-2">
      <div className="flex items-center justify-between">
        <span className="font-mono text-xs text-text-muted">{product.sku_code}</span>
        <span className="text-[10px] px-2 py-0.5 rounded-full bg-surface-row text-text-muted">
          {product.category}
        </span>
      </div>
      <div className="flex items-center justify-between">
        <span className="font-semibold text-text-primary text-sm">{product.name}</span>
        <span className={`text-xs font-medium ${product.stock_quantity <= (product.low_stock_threshold ?? 5) ? 'text-red-400' : 'text-text-secondary'}`}>
          {product.stock_quantity} {product.unit}
        </span>
      </div>
    </div>
  ))}
</div>
```

- [ ] **Step 4: Add `md:hidden` mobile card list for Purchases Invoices**

```tsx
<div className="md:hidden space-y-2">
  {invoices.map((invoice) => (
    <div key={invoice.id} className="rounded-xl bg-surface-card border border-border-subtle p-4 space-y-2">
      <div className="flex items-center justify-between">
        <span className="font-mono text-xs text-text-muted">{invoice.invoice_ref ?? '—'}</span>
        <span className="text-xs text-text-muted">
          {new Date(invoice.invoice_date).toLocaleDateString('en-IN')}
        </span>
      </div>
      <div className="flex items-center justify-between">
        <span className="font-semibold text-text-primary text-sm truncate max-w-[60%]">
          {invoice.supplier_name}
        </span>
        <span className={`text-[10px] px-2 py-0.5 rounded-full ${
          invoice.status === 'received' ? 'bg-green-500/15 text-green-400' :
          invoice.status === 'draft' ? 'bg-surface-row text-text-muted' :
          'bg-amber-500/15 text-amber-400'
        }`}>
          {invoice.status}
        </span>
      </div>
      <div className="flex justify-between text-xs text-text-secondary">
        <span>Total: ₹{(invoice.total_amount / 100).toLocaleString('en-IN')}</span>
      </div>
    </div>
  ))}
</div>
```

- [ ] **Step 5: Add `md:hidden` mobile card list for Expenses**

```tsx
<div className="md:hidden space-y-2">
  {expenses.map((expense) => (
    <div key={expense.id} className="rounded-xl bg-surface-card border border-border-subtle p-4 space-y-2">
      <div className="flex items-center justify-between">
        <span className="text-xs text-text-muted">
          {new Date(expense.date).toLocaleDateString('en-IN')}
        </span>
        <span className="text-[10px] px-2 py-0.5 rounded-full bg-surface-row text-text-muted">
          {expense.category}
        </span>
      </div>
      <div className="flex items-center justify-between">
        <span className="font-semibold text-text-primary text-sm truncate max-w-[60%]">
          {expense.description}
        </span>
        <span className="font-semibold text-accent text-sm">
          ₹{(expense.amount / 100).toLocaleString('en-IN')}
        </span>
      </div>
      <span className="text-xs text-text-muted">{expense.payment_method}</span>
    </div>
  ))}
</div>
```

- [ ] **Step 6: Apply dark classes to all three desktop tables**

- [ ] **Step 7: Commit**

```bash
git add frontend/src/app/dashboard/inventory/page.tsx \
        frontend/src/app/dashboard/purchases/invoices/page.tsx \
        frontend/src/app/dashboard/expenses/page.tsx
git commit -m "feat(ui): inventory, purchases, expenses — dark + table-to-card mobile"
```

---

## Phase 6 — Settings Accent Switcher

### Task 14: Add Appearance section to Settings page

**Files:**
- Modify: `frontend/src/app/dashboard/settings/page.tsx`

- [ ] **Step 1: Add accent switcher state to settings page**

Add these imports:
```tsx
import { getAccent, setAccent, type AccentName } from '@/lib/theme';
```

Add state inside the component:
```tsx
const [accent, setAccentState] = useState<AccentName>(() => getAccent());
```

Add handler:
```tsx
const handleAccentChange = (name: AccentName) => {
  setAccentState(name);
  setAccent(name); // writes to localStorage + updates data-accent on <html>
};
```

- [ ] **Step 2: Add Appearance section JSX before the existing Save button section**

Find where the last settings `<Card>` section ends, and add:

```tsx
{/* Appearance */}
<Card className="bg-surface-card border-border-subtle">
  <CardHeader>
    <CardTitle className="flex items-center gap-2 text-text-primary">
      <Palette className="h-5 w-5" />
      Appearance
    </CardTitle>
    <CardDescription className="text-text-secondary">
      Choose an accent colour for the app.
    </CardDescription>
  </CardHeader>
  <CardContent>
    <div className="flex gap-3 flex-wrap">
      {(
        [
          { name: 'violet', color: '#7c3aed', label: 'Violet' },
          { name: 'rose',   color: '#e11d48', label: 'Rose' },
          { name: 'amber',  color: '#d97706', label: 'Amber' },
          { name: 'teal',   color: '#0d9488', label: 'Teal' },
        ] as { name: AccentName; color: string; label: string }[]
      ).map(({ name, color, label }) => (
        <button
          key={name}
          onClick={() => handleAccentChange(name)}
          className={`flex flex-col items-center gap-1.5 p-3 rounded-xl border-2 transition-all ${
            accent === name
              ? 'border-current shadow-lg shadow-current/20'
              : 'border-border-subtle hover:border-text-muted'
          }`}
          style={{ color }}
          aria-label={`${label} accent`}
        >
          <span
            className="h-8 w-8 rounded-full"
            style={{ backgroundColor: color }}
          />
          <span className="text-xs text-text-secondary">{label}</span>
        </button>
      ))}
    </div>
  </CardContent>
</Card>
```

- [ ] **Step 3: Verify accent switching from Settings page**

Visit `/dashboard/settings`. Expected: 4 colour swatches, clicking one changes the accent throughout the app immediately (sidebar active item, buttons, etc.).

- [ ] **Step 4: Verify accent persists on page refresh**

Click "Rose", refresh the page. Expected: Rose accent is still active.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/app/dashboard/settings/page.tsx
git commit -m "feat(ui): add accent colour switcher to Settings page"
```

---

## Phase 7 — Polish & Reconciliation

### Task 15: Apply dark theme to remaining pages

**Files:**
- Modify: `frontend/src/app/dashboard/reconciliation/page.tsx`
- Modify: `frontend/src/app/dashboard/reports/page.tsx`
- Modify: `frontend/src/app/dashboard/cash-drawer/page.tsx`

For each page, find and replace light background/text/border classes with dark token equivalents using the same substitution pattern from Task 11, Step 4:

| Old class | New class |
|---|---|
| `bg-white` | `bg-surface-card` |
| `bg-gray-50`, `bg-slate-50` | `bg-surface-page` |
| `bg-gray-100`, `bg-slate-100` | `bg-surface-row` |
| `border-gray-200`, `border-slate-200` | `border-border-subtle` |
| `text-gray-500`, `text-slate-500` | `text-text-secondary` |
| `text-gray-900`, `text-slate-900` | `text-text-primary` |
| `text-gray-400`, `text-slate-400` | `text-text-muted` |

- [ ] **Step 1: Apply substitutions to reconciliation page**

- [ ] **Step 2: Apply substitutions to reports page**

- [ ] **Step 3: Apply substitutions to cash-drawer page**

- [ ] **Step 4: Commit**

```bash
git add frontend/src/app/dashboard/reconciliation/page.tsx \
        frontend/src/app/dashboard/reports/page.tsx \
        frontend/src/app/dashboard/cash-drawer/page.tsx
git commit -m "feat(ui): apply dark tokens to reconciliation, reports, cash-drawer pages"
```

---

### Task 16: Final QA pass

- [ ] **Step 1: Run TypeScript check across frontend**

```bash
cd frontend && npx tsc --noEmit
```

Expected: 0 errors.

- [ ] **Step 2: Test all major flows at desktop viewport (1280px)**

1. Login → lands on dashboard ✓ dark
2. Sidebar nav — active item shows accent left-border ✓
3. Accent switcher in Settings — all 4 palettes change app-wide ✓
4. Revenue card hidden by default, eye toggle reveals it ✓
5. Staff login — revenue card never visible ✓
6. Dashboard service queue shows per-staff lanes ✓
7. POS — service grid dark, cart sidebar dark ✓
8. Bills / Customers / Inventory / Purchases / Expenses — desktop tables dark ✓

- [ ] **Step 3: Test all major flows at mobile viewport (390px)**

1. Sidebar hidden — bottom nav visible ✓
2. POS — FAB visible when cart has items, opens Sheet ✓
3. Bills / Customers / Inventory — card layout visible ✓
4. More sheet from bottom nav opens remaining nav items ✓

- [ ] **Step 4: Commit final clean-up**

```bash
git add -p  # stage any final tweaks
git commit -m "feat(ui): final dark theme polish and QA fixes"
```

---

## Summary

| Phase | Tasks | Files |
|---|---|---|
| 1 — CSS Tokens | 1–2 | `globals.css`, `lib/theme.ts`, `app/layout.tsx` |
| 2 — Sidebar + Nav | 3–5 | `dashboard/layout.tsx`, `app-sidebar.tsx`, `nav-bottom.tsx` |
| 3 — Dashboard | 6–9 | `stat-card.tsx`, `service-queue.tsx`, `active-customer-card.tsx`, `dashboard/page.tsx` |
| 4 — POS | 10 | `pos/page.tsx`, `cart-sidebar.tsx` |
| 5 — Table-to-Card | 11–13 | `bills`, `customers`, `inventory`, `purchases`, `expenses` |
| 6 — Settings | 14 | `settings/page.tsx` |
| 7 — Polish | 15–16 | `reconciliation`, `reports`, `cash-drawer` |
