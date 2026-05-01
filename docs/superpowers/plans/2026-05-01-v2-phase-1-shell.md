# V2 Phase 1 — Shell Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wrap every existing dashboard route in the new V2 shell — labelled sidebar (collapsible to icon rail), real route-derived breadcrumb top bar, ⌘K command palette, mobile bottom-tab nav, and the `@modal` parallel slot for entity detail routes — without touching any V1 page body.

**Architecture:** Introduce a Next.js App Router route group `app/(shell)/` that owns the new layout. Move every existing `app/dashboard/*` route into the group (keeping URLs unchanged). The new layout composes `SidebarV2` (192 px) + `SidebarRail` (56 px collapsed, persisted in localStorage and toggled by `⌘\`) + `TopBar` (Breadcrumb + ⌘K trigger + user menu) + `BottomTabNav` (mobile only). The `@modal` parallel slot renders intercepted entity-detail routes as the V2 Dialog primitive when launched from a list page; the canonical `[id]` route is a full page when accessed via cold URL or palette. Bills is the proof entity — its list page sheds its local `selectedBillId` useState and wires to the new pattern.

**Tech Stack:** Next.js 16 App Router (parallel slots + intercepting routes), React 19, cmdk@1.1.x (already installed for Combobox primitive in T10), Tailwind 4 + V2 design tokens (Phase 0), TypeScript 5+, lucide-react icons. No new runtime deps.

---

## File structure (responsibilities)

**New files:**
- `frontend/src/app/(shell)/layout.tsx` — root shell layout. Owns sidebar + topbar + content grid + `@modal` slot.
- `frontend/src/app/(shell)/@modal/default.tsx` — parallel-slot default (renders nothing when no modal route is active).
- `frontend/src/app/(shell)/@modal/(.)bills/[id]/page.tsx` — intercepted route: renders `BillDetail` inside a Dialog.
- `frontend/src/app/(shell)/bills/[id]/page.tsx` — canonical route: renders `BillDetail` as a full page.
- `frontend/src/components/shell/sidebar-v2.tsx` — labelled 192px sidebar with grouped sections.
- `frontend/src/components/shell/sidebar-rail.tsx` — collapsed 56px icon rail variant.
- `frontend/src/components/shell/sidebar-state.tsx` — `useSidebarState` hook (localStorage + ⌘\ keybind).
- `frontend/src/components/shell/topbar.tsx` — breadcrumb + ⌘K trigger button + user menu placeholder.
- `frontend/src/components/shell/breadcrumb.tsx` — route-derived breadcrumb (uses `usePathname`).
- `frontend/src/components/shell/bottom-tab-nav.tsx` — 4-item mobile nav (Today / POS / Bills / More).
- `frontend/src/components/shell/more-sheet.tsx` — overflow nav opened by "More" tab.
- `frontend/src/components/shell/section-config.ts` — single source of truth for the sidebar sections (used by sidebar + bottom-nav).
- `frontend/src/components/command-palette/command-palette.tsx` — root cmdk dialog opened on ⌘K / Ctrl+K.
- `frontend/src/components/command-palette/use-palette.tsx` — open/close state context (provides imperative `open()` for TopBar).
- `frontend/src/components/command-palette/providers/navigation.ts` — static nav-action provider.
- `frontend/src/components/command-palette/providers/customers.ts` — async customer-search provider.
- `frontend/src/components/command-palette/providers/bills.ts` — async bill-search provider.
- `frontend/src/components/command-palette/providers/skus.ts` — async SKU-search provider.
- `frontend/src/components/command-palette/providers/actions.ts` — global actions (new bill, open drawer, toggle theme).
- `frontend/src/components/command-palette/history.ts` — localStorage history of executed commands.
- `frontend/src/components/bills/bill-detail.tsx` — shared body used by both the canonical and intercepted bill detail routes.
- Tests under `frontend/src/components/shell/__tests__/` and `frontend/src/components/command-palette/__tests__/`.

**Modified files:**
- `frontend/src/app/dashboard/*` — every subroute moves into `frontend/src/app/(shell)/dashboard/*`. URLs unchanged because route groups don't affect URL.
- `frontend/src/app/dashboard/layout.tsx` — deleted; the new `(shell)/layout.tsx` replaces it.
- `frontend/src/app/dashboard/bills/page.tsx` → `frontend/src/app/(shell)/dashboard/bills/page.tsx` and is edited in T15 to drop `useState<string|null>(null)` for the selected bill.
- `docs/design_system.md` — append §7.5 implementation note (T14) and a Phase 1 changelog row (T21).

**Pre-existing files referenced (do NOT modify here):**
- `frontend/src/components/ui/dialog.tsx` (Phase 0 T11) — used by intercepted modal route.
- `frontend/src/components/ui/combobox.tsx` (Phase 0 T10) — uses cmdk; the palette imports cmdk directly, not via the Combobox primitive.
- `frontend/src/lib/utils.ts` — `cn()` helper.

---

## Pre-flight (run once before Task 1)

- [ ] Confirm branch state

```bash
cd /Users/angelxlakra/dev/efs-salon/efs-salon-os && git status && git log --oneline -3
```

Expected: clean working tree, HEAD at the last Phase 0 commit (`3c8864c` or later if hot-fixed).

- [ ] Create or check out the Phase 1 branch

```bash
cd /Users/angelxlakra/dev/efs-salon/efs-salon-os && git checkout -b feature/v2-phase-1
```

Or if returning to existing branch: `git checkout feature/v2-phase-1`.

- [ ] Capture baseline counts (used by every "Verify" step in this plan)

```bash
cd /Users/angelxlakra/dev/efs-salon/efs-salon-os/frontend && PATH="/Users/angelxlakra/.nvm/versions/node/v22.20.0/bin:$PATH" npx tsc --noEmit 2>&1 | grep -c "error TS"
```

Expected: 162 (pre-existing baseline carried over from Phase 0).

```bash
cd /Users/angelxlakra/dev/efs-salon/efs-salon-os/frontend && PATH="/Users/angelxlakra/.nvm/versions/node/v22.20.0/bin:$PATH" npm test -- --run 2>&1 | tail -3
```

Expected: 106 tests pass across 18 files.

> **nvm sandbox quirk:** every `npm`/`npx`/`node` command in this plan must inline-prepend `PATH="/Users/angelxlakra/.nvm/versions/node/v22.20.0/bin:$PATH"`. `nvm use` does not persist across separate Bash invocations.

---

## Workstream A — Layout shell foundation (T1–T6)

### Task 1: Create `(shell)` route group with skeleton layout

**Files:**
- Create: `frontend/src/app/(shell)/layout.tsx`
- Create: `frontend/src/app/(shell)/@modal/default.tsx`
- Create: `frontend/src/components/shell/section-config.ts`

**Why:** The route group `(shell)` wraps every Phase-1+ route in the new chrome without changing URLs. Creating it with a skeleton first means every subsequent task has a parent to mount into. The `@modal` slot ships as a default-empty parallel route now so layout typechecks before T12 wires real intercepted routes.

- [ ] **Step 1: Create the section config**

`frontend/src/components/shell/section-config.ts`:

```ts
import {
  Calendar,
  CreditCard,
  FileText,
  Home,
  Package,
  Receipt,
  Settings as SettingsIcon,
  ShoppingCart,
  TrendingUp,
  UserCog,
  Users,
  Wallet,
  type LucideIcon,
} from "lucide-react";

export type ShellNavItem = {
  label: string;
  href: string;
  icon: LucideIcon;
};

export type ShellSection = {
  id: "today" | "ledger" | "insight" | "admin";
  label: string;
  items: ShellNavItem[];
};

/** Sidebar groupings per design_system.md §6.3. Single source of truth — sidebar + bottom-nav both read from here. */
export const SHELL_SECTIONS: ShellSection[] = [
  {
    id: "today",
    label: "Today's work",
    items: [
      { label: "Today", href: "/dashboard", icon: Home },
      { label: "POS", href: "/dashboard/pos", icon: ShoppingCart },
      { label: "Bills", href: "/dashboard/bills", icon: Receipt },
      { label: "Appointments", href: "/dashboard/appointments", icon: Calendar },
    ],
  },
  {
    id: "ledger",
    label: "Ledger",
    items: [
      { label: "Customers", href: "/dashboard/customers", icon: Users },
      { label: "Inventory", href: "/dashboard/inventory", icon: Package },
      { label: "Purchases", href: "/dashboard/purchases", icon: FileText },
      { label: "Expenses", href: "/dashboard/expenses", icon: Wallet },
      { label: "Cash Drawer", href: "/dashboard/cash-drawer", icon: CreditCard },
      { label: "Reconciliation", href: "/dashboard/reconciliation", icon: TrendingUp },
    ],
  },
  {
    id: "insight",
    label: "Insight",
    items: [
      { label: "Reports", href: "/dashboard/reports", icon: TrendingUp },
      { label: "Attendance", href: "/dashboard/attendance", icon: Calendar },
    ],
  },
  {
    id: "admin",
    label: "Admin",
    items: [
      { label: "Users & Staff", href: "/dashboard/users", icon: UserCog },
      { label: "Services", href: "/dashboard/services", icon: SettingsIcon },
      { label: "Settings", href: "/dashboard/settings", icon: SettingsIcon },
    ],
  },
];

/** Mobile bottom nav — 4 items per spec §3.3, "More" opens overflow sheet. */
export const MOBILE_TABS: ShellNavItem[] = [
  { label: "Today", href: "/dashboard", icon: Home },
  { label: "POS", href: "/dashboard/pos", icon: ShoppingCart },
  { label: "Bills", href: "/dashboard/bills", icon: Receipt },
  // The "More" tab is rendered specially in BottomTabNav — it opens MoreSheet, not a route.
];
```

- [ ] **Step 2: Create the @modal default**

`frontend/src/app/(shell)/@modal/default.tsx`:

```tsx
// Parallel slot default. When no @modal route matches, render nothing.
// (Required by Next.js: a parallel slot must always have a `default.tsx` so
// route changes outside the slot don't unmount it.)
export default function ModalDefault() {
  return null;
}
```

- [ ] **Step 3: Create the shell layout skeleton**

`frontend/src/app/(shell)/layout.tsx`:

```tsx
import * as React from "react";

export default function ShellLayout({
  children,
  modal,
}: {
  children: React.ReactNode;
  modal: React.ReactNode;
}) {
  // T2-T6 will replace this skeleton with sidebar + topbar + bottom-nav grid.
  // For now we just verify the route group compiles and the @modal slot is wired.
  return (
    <div className="min-h-dvh bg-surface-page text-text-primary">
      <main>{children}</main>
      {modal}
    </div>
  );
}
```

- [ ] **Step 4: Verify build**

```bash
cd /Users/angelxlakra/dev/efs-salon/efs-salon-os/frontend && PATH="/Users/angelxlakra/.nvm/versions/node/v22.20.0/bin:$PATH" npx tsc --noEmit 2>&1 | grep -c "error TS"
```

Expected: 162 (no new errors). The new layout doesn't bind to any existing route yet.

- [ ] **Step 5: Commit**

```bash
cd /Users/angelxlakra/dev/efs-salon/efs-salon-os && git add frontend/src/app/\(shell\)/ frontend/src/components/shell/section-config.ts && git commit -m "feat(shell): scaffold (shell) route group + section config"
```

---

### Task 2: SidebarV2 component (192px labelled)

**Files:**
- Create: `frontend/src/components/shell/sidebar-v2.tsx`
- Create: `frontend/src/components/shell/__tests__/sidebar-v2.test.tsx`

**Why:** The labelled sidebar is the navigation primary. Per spec §3.3 it groups routes into 4 sections (Today / Ledger / Insight / Admin), reads its items from `section-config.ts` (T1), and reuses the `NavItem` primitive (Phase 0 T18) for each row.

- [ ] **Step 1: Write failing tests**

`frontend/src/components/shell/__tests__/sidebar-v2.test.tsx`:

```tsx
import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { SidebarV2 } from "@/components/shell/sidebar-v2";

vi.mock("next/navigation", () => ({
  usePathname: () => "/dashboard/bills",
}));

describe("SidebarV2", () => {
  it("renders all 4 section labels", () => {
    render(<SidebarV2 />);
    expect(screen.getByText("Today's work")).toBeInTheDocument();
    expect(screen.getByText("Ledger")).toBeInTheDocument();
    expect(screen.getByText("Insight")).toBeInTheDocument();
    expect(screen.getByText("Admin")).toBeInTheDocument();
  });

  it("renders the active route with data-active=true", () => {
    render(<SidebarV2 />);
    // /dashboard/bills is the active route
    const billsLink = screen.getByRole("link", { name: /Bills/i });
    expect(billsLink).toHaveAttribute("data-active", "true");
  });

  it("renders Today (root /dashboard) without data-active when on a sub-route", () => {
    render(<SidebarV2 />);
    const todayLink = screen.getByRole("link", { name: /Today/i });
    expect(todayLink).not.toHaveAttribute("data-active");
  });

  it("uses the surface-sidebar token on the wrapper", () => {
    const { container } = render(<SidebarV2 />);
    expect(container.firstChild).toHaveClass("bg-surface-sidebar");
  });
});
```

- [ ] **Step 2: Run tests, verify FAIL**

```bash
cd /Users/angelxlakra/dev/efs-salon/efs-salon-os/frontend && PATH="/Users/angelxlakra/.nvm/versions/node/v22.20.0/bin:$PATH" npm test -- sidebar-v2 --run
```

Expected: failure (component doesn't exist).

- [ ] **Step 3: Implement SidebarV2**

`frontend/src/components/shell/sidebar-v2.tsx`:

```tsx
"use client";

import * as React from "react";
import { usePathname } from "next/navigation";
import { NavItem } from "@/components/ui/nav-item";
import { SHELL_SECTIONS } from "@/components/shell/section-config";
import { cn } from "@/lib/utils";

/**
 * Labelled 192px sidebar. Reads structure from `section-config.ts`.
 * Active route detection: exact match for /dashboard, prefix match for sub-routes.
 */
function isActive(itemHref: string, pathname: string): boolean {
  if (itemHref === "/dashboard") return pathname === "/dashboard";
  return pathname === itemHref || pathname.startsWith(itemHref + "/");
}

export function SidebarV2({ className }: { className?: string }) {
  const pathname = usePathname() ?? "/";
  return (
    <aside
      className={cn(
        "w-48 shrink-0 bg-surface-sidebar border-r border-border-subtle h-dvh sticky top-0 flex flex-col",
        className,
      )}
    >
      <div className="px-4 py-3 border-b border-border-subtle">
        <span className="font-display text-display-sm text-text-primary">SalonOS</span>
      </div>
      <nav className="flex-1 overflow-y-auto p-2 flex flex-col gap-4">
        {SHELL_SECTIONS.map((section) => (
          <div key={section.id} className="flex flex-col gap-1">
            <div className="px-3 pt-2 pb-1 text-overline text-text-muted">{section.label}</div>
            {section.items.map((item) => {
              const Icon = item.icon;
              return (
                <NavItem
                  key={item.href}
                  label={item.label}
                  href={item.href}
                  icon={<Icon />}
                  active={isActive(item.href, pathname)}
                />
              );
            })}
          </div>
        ))}
      </nav>
    </aside>
  );
}
```

- [ ] **Step 4: Run tests, verify PASS**

```bash
cd /Users/angelxlakra/dev/efs-salon/efs-salon-os/frontend && PATH="/Users/angelxlakra/.nvm/versions/node/v22.20.0/bin:$PATH" npm test -- sidebar-v2 --run
```

Expected: 4 tests pass.

- [ ] **Step 5: Commit**

```bash
cd /Users/angelxlakra/dev/efs-salon/efs-salon-os && git add frontend/src/components/shell/sidebar-v2.tsx frontend/src/components/shell/__tests__/sidebar-v2.test.tsx && git commit -m "feat(shell): SidebarV2 (192px labelled, 4 sections from section-config)"
```

---

### Task 3: SidebarRail component (56px collapsed)

**Files:**
- Create: `frontend/src/components/shell/sidebar-rail.tsx`
- Create: `frontend/src/components/shell/__tests__/sidebar-rail.test.tsx`

**Why:** Power-user collapsed variant. Same data source (`section-config.ts`), icon-only rendering with NavItem's `variant="rail"` (Phase 0 T18). Sized to 56 px per spec §3.3.

- [ ] **Step 1: Write failing tests**

`frontend/src/components/shell/__tests__/sidebar-rail.test.tsx`:

```tsx
import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { SidebarRail } from "@/components/shell/sidebar-rail";

vi.mock("next/navigation", () => ({
  usePathname: () => "/dashboard/customers",
}));

describe("SidebarRail", () => {
  it("renders icon-only items (no label text inline, but accessible)", () => {
    render(<SidebarRail />);
    // The label is rendered (for screen readers + tooltip on hover) but not as the dominant element.
    // We assert by role + name (combines aria-label + visible text).
    expect(screen.getAllByRole("link").length).toBeGreaterThan(0);
  });

  it("uses the surface-sidebar token", () => {
    const { container } = render(<SidebarRail />);
    expect(container.firstChild).toHaveClass("bg-surface-sidebar");
  });

  it("marks the active route", () => {
    render(<SidebarRail />);
    const customersLink = screen.getByRole("link", { name: /Customers/i });
    expect(customersLink).toHaveAttribute("data-active", "true");
  });

  it("is exactly 56px wide (w-14)", () => {
    const { container } = render(<SidebarRail />);
    expect(container.firstChild).toHaveClass("w-14");
  });
});
```

- [ ] **Step 2: Run tests, verify FAIL**

```bash
cd /Users/angelxlakra/dev/efs-salon/efs-salon-os/frontend && PATH="/Users/angelxlakra/.nvm/versions/node/v22.20.0/bin:$PATH" npm test -- sidebar-rail --run
```

Expected: failure.

- [ ] **Step 3: Implement SidebarRail**

`frontend/src/components/shell/sidebar-rail.tsx`:

```tsx
"use client";

import * as React from "react";
import { usePathname } from "next/navigation";
import { NavItem } from "@/components/ui/nav-item";
import { SHELL_SECTIONS } from "@/components/shell/section-config";
import { cn } from "@/lib/utils";

function isActive(itemHref: string, pathname: string): boolean {
  if (itemHref === "/dashboard") return pathname === "/dashboard";
  return pathname === itemHref || pathname.startsWith(itemHref + "/");
}

export function SidebarRail({ className }: { className?: string }) {
  const pathname = usePathname() ?? "/";
  return (
    <aside
      className={cn(
        "w-14 shrink-0 bg-surface-sidebar border-r border-border-subtle h-dvh sticky top-0 flex flex-col items-center",
        className,
      )}
    >
      <div className="h-12 flex items-center justify-center border-b border-border-subtle w-full">
        <span className="font-display text-display-sm text-accent">S</span>
      </div>
      <nav className="flex-1 overflow-y-auto py-2 flex flex-col gap-1 w-full items-center">
        {SHELL_SECTIONS.flatMap((section) => section.items).map((item) => {
          const Icon = item.icon;
          return (
            <NavItem
              key={item.href}
              label={item.label}
              href={item.href}
              icon={<Icon />}
              active={isActive(item.href, pathname)}
              variant="rail"
            />
          );
        })}
      </nav>
    </aside>
  );
}
```

- [ ] **Step 4: Run tests, verify PASS**

Expected: 4 tests pass.

- [ ] **Step 5: Commit**

```bash
cd /Users/angelxlakra/dev/efs-salon/efs-salon-os && git add frontend/src/components/shell/sidebar-rail.tsx frontend/src/components/shell/__tests__/sidebar-rail.test.tsx && git commit -m "feat(shell): SidebarRail (56px icon-only collapsed variant)"
```

---

### Task 4: Sidebar collapse state hook (⌘\ + localStorage)

**Files:**
- Create: `frontend/src/components/shell/sidebar-state.tsx`
- Create: `frontend/src/components/shell/__tests__/sidebar-state.test.tsx`

**Why:** The sidebar's collapsed/expanded state must persist across reloads (so a power user's choice stays) and toggle with the `⌘\` (Mac) / `Ctrl+\` (Win) keybind per spec §3.3. Encapsulating that into a single hook + provider keeps the layout dumb and the state owner explicit.

- [ ] **Step 1: Write failing tests**

`frontend/src/components/shell/__tests__/sidebar-state.test.tsx`:

```tsx
import { describe, expect, it, beforeEach, afterEach, vi } from "vitest";
import { render, screen, act } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import {
  SidebarStateProvider,
  useSidebarState,
} from "@/components/shell/sidebar-state";

function Probe() {
  const { collapsed, toggle, setCollapsed } = useSidebarState();
  return (
    <div>
      <span data-testid="state">{collapsed ? "collapsed" : "expanded"}</span>
      <button onClick={toggle}>toggle</button>
      <button onClick={() => setCollapsed(true)}>collapse</button>
    </div>
  );
}

describe("SidebarStateProvider", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  afterEach(() => {
    window.localStorage.clear();
  });

  it("defaults to expanded when no localStorage value", () => {
    render(
      <SidebarStateProvider>
        <Probe />
      </SidebarStateProvider>,
    );
    expect(screen.getByTestId("state")).toHaveTextContent("expanded");
  });

  it("hydrates from localStorage on mount", () => {
    window.localStorage.setItem("salon.sidebar.collapsed", "true");
    render(
      <SidebarStateProvider>
        <Probe />
      </SidebarStateProvider>,
    );
    expect(screen.getByTestId("state")).toHaveTextContent("collapsed");
  });

  it("toggle flips state and persists to localStorage", async () => {
    const user = userEvent.setup();
    render(
      <SidebarStateProvider>
        <Probe />
      </SidebarStateProvider>,
    );
    await user.click(screen.getByText("toggle"));
    expect(screen.getByTestId("state")).toHaveTextContent("collapsed");
    expect(window.localStorage.getItem("salon.sidebar.collapsed")).toBe("true");
  });

  it("⌘\\ (Meta+Backslash) toggles collapse via keyboard", async () => {
    const user = userEvent.setup();
    render(
      <SidebarStateProvider>
        <Probe />
      </SidebarStateProvider>,
    );
    expect(screen.getByTestId("state")).toHaveTextContent("expanded");
    await user.keyboard("{Meta>}\\{/Meta}");
    expect(screen.getByTestId("state")).toHaveTextContent("collapsed");
  });
});
```

- [ ] **Step 2: Run tests, verify FAIL**

```bash
cd /Users/angelxlakra/dev/efs-salon/efs-salon-os/frontend && PATH="/Users/angelxlakra/.nvm/versions/node/v22.20.0/bin:$PATH" npm test -- sidebar-state --run
```

Expected: failure.

- [ ] **Step 3: Implement the provider + hook**

`frontend/src/components/shell/sidebar-state.tsx`:

```tsx
"use client";

import * as React from "react";

const STORAGE_KEY = "salon.sidebar.collapsed";

type SidebarStateValue = {
  collapsed: boolean;
  toggle: () => void;
  setCollapsed: (next: boolean) => void;
};

const SidebarStateContext = React.createContext<SidebarStateValue | null>(null);

export function SidebarStateProvider({ children }: { children: React.ReactNode }) {
  // SSR-safe: start expanded, hydrate from localStorage in effect.
  const [collapsed, setCollapsedState] = React.useState(false);

  React.useEffect(() => {
    if (typeof window === "undefined") return;
    const stored = window.localStorage.getItem(STORAGE_KEY);
    if (stored === "true") setCollapsedState(true);
  }, []);

  const setCollapsed = React.useCallback((next: boolean) => {
    setCollapsedState(next);
    if (typeof window !== "undefined") {
      window.localStorage.setItem(STORAGE_KEY, String(next));
    }
  }, []);

  const toggle = React.useCallback(() => {
    setCollapsedState((prev) => {
      const next = !prev;
      if (typeof window !== "undefined") {
        window.localStorage.setItem(STORAGE_KEY, String(next));
      }
      return next;
    });
  }, []);

  // Keyboard binding: ⌘\ on Mac, Ctrl+\ on Win/Linux.
  React.useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "\\") {
        e.preventDefault();
        toggle();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [toggle]);

  const value = React.useMemo<SidebarStateValue>(
    () => ({ collapsed, toggle, setCollapsed }),
    [collapsed, toggle, setCollapsed],
  );

  return <SidebarStateContext.Provider value={value}>{children}</SidebarStateContext.Provider>;
}

export function useSidebarState(): SidebarStateValue {
  const ctx = React.useContext(SidebarStateContext);
  if (!ctx) throw new Error("useSidebarState must be used inside <SidebarStateProvider>");
  return ctx;
}
```

- [ ] **Step 4: Run tests, verify PASS**

Expected: 4 tests pass. The keyboard test depends on `userEvent.keyboard("{Meta>}\\{/Meta}")` actually firing a Meta+Backslash event in jsdom — verify this works; if not, fall back to dispatching a synthetic `KeyboardEvent` directly:

```tsx
act(() => {
  window.dispatchEvent(new KeyboardEvent("keydown", { key: "\\", metaKey: true }));
});
```

- [ ] **Step 5: Commit**

```bash
cd /Users/angelxlakra/dev/efs-salon/efs-salon-os && git add frontend/src/components/shell/sidebar-state.tsx frontend/src/components/shell/__tests__/sidebar-state.test.tsx && git commit -m "feat(shell): sidebar collapse state (Cmd+\\ + localStorage)"
```

---

### Task 5: TopBar component (breadcrumb + ⌘K trigger + user menu)

**Files:**
- Create: `frontend/src/components/shell/topbar.tsx`
- Create: `frontend/src/components/shell/__tests__/topbar.test.tsx`

**Why:** Sticky top bar per spec §3.3. Three regions: real route-derived breadcrumb (left), ⌘K palette trigger (center-right), user menu placeholder (right). The Breadcrumb component itself is split out into T6 — TopBar just renders it.

- [ ] **Step 1: Write failing tests**

`frontend/src/components/shell/__tests__/topbar.test.tsx`:

```tsx
import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { TopBar } from "@/components/shell/topbar";
import { PaletteProvider } from "@/components/command-palette/use-palette";

vi.mock("next/navigation", () => ({
  usePathname: () => "/dashboard/bills",
}));

describe("TopBar", () => {
  it("renders breadcrumb (Today / Bills) for /dashboard/bills", () => {
    render(
      <PaletteProvider>
        <TopBar />
      </PaletteProvider>,
    );
    expect(screen.getByText("Today")).toBeInTheDocument();
    expect(screen.getByText("Bills")).toBeInTheDocument();
  });

  it("renders the ⌘K palette trigger button", () => {
    render(
      <PaletteProvider>
        <TopBar />
      </PaletteProvider>,
    );
    const trigger = screen.getByRole("button", { name: /search|palette/i });
    expect(trigger).toBeInTheDocument();
  });

  it("renders a user menu placeholder", () => {
    render(
      <PaletteProvider>
        <TopBar />
      </PaletteProvider>,
    );
    expect(screen.getByLabelText(/user menu/i)).toBeInTheDocument();
  });

  it("uses sticky positioning + surface-card background", () => {
    const { container } = render(
      <PaletteProvider>
        <TopBar />
      </PaletteProvider>,
    );
    expect(container.firstChild).toHaveClass("sticky");
    expect(container.firstChild).toHaveClass("bg-surface-card");
  });
});
```

- [ ] **Step 2: Run tests, verify FAIL**

```bash
cd /Users/angelxlakra/dev/efs-salon/efs-salon-os/frontend && PATH="/Users/angelxlakra/.nvm/versions/node/v22.20.0/bin:$PATH" npm test -- topbar --run
```

Expected: failure (TopBar + PaletteProvider don't exist yet — PaletteProvider lands in T7 but we need a stub here).

- [ ] **Step 3: Create a temporary stub for PaletteProvider so TopBar can import it**

`frontend/src/components/command-palette/use-palette.tsx` (will be replaced in T7):

```tsx
"use client";

import * as React from "react";

type PaletteValue = {
  open: () => void;
  close: () => void;
  isOpen: boolean;
};

const PaletteContext = React.createContext<PaletteValue | null>(null);

export function PaletteProvider({ children }: { children: React.ReactNode }) {
  const [isOpen, setIsOpen] = React.useState(false);
  const value = React.useMemo<PaletteValue>(
    () => ({
      open: () => setIsOpen(true),
      close: () => setIsOpen(false),
      isOpen,
    }),
    [isOpen],
  );
  return <PaletteContext.Provider value={value}>{children}</PaletteContext.Provider>;
}

export function usePalette(): PaletteValue {
  const ctx = React.useContext(PaletteContext);
  if (!ctx) throw new Error("usePalette must be used inside <PaletteProvider>");
  return ctx;
}
```

- [ ] **Step 4: Implement TopBar**

`frontend/src/components/shell/topbar.tsx`:

```tsx
"use client";

import * as React from "react";
import { Search, User } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Kbd } from "@/components/ui/kbd";
import { Breadcrumb } from "@/components/shell/breadcrumb";
import { usePalette } from "@/components/command-palette/use-palette";
import { cn } from "@/lib/utils";

export function TopBar({ className }: { className?: string }) {
  const { open } = usePalette();
  return (
    <header
      className={cn(
        "sticky top-0 z-30 flex items-center gap-3 px-4 h-12 bg-surface-card border-b border-border-subtle",
        className,
      )}
    >
      <Breadcrumb className="flex-1 min-w-0" />
      <button
        type="button"
        onClick={open}
        aria-label="Open search palette"
        className="hidden sm:inline-flex items-center gap-2 h-8 px-3 rounded-md bg-surface-row text-text-secondary border border-border-subtle hover:bg-surface-row-hover text-body-sm"
      >
        <Search className="size-4" />
        <span className="hidden md:inline">Search…</span>
        <Kbd keys={["⌘", "K"]} />
      </button>
      <Button
        type="button"
        variant="ghost"
        size="sm"
        aria-label="User menu"
        className="size-8 p-0"
      >
        <User className="size-4" />
      </Button>
    </header>
  );
}
```

- [ ] **Step 5: Run tests, verify PASS**

Expected: 4 tests pass. (The Breadcrumb component lands in T6 but the test only asserts text content "Today" / "Bills" — that text appears via Breadcrumb. If T5 runs before T6, write a stub Breadcrumb at `frontend/src/components/shell/breadcrumb.tsx` that returns `<div>Today / Bills</div>` for now and replace it in T6.)

If running T5 before T6, also create:

`frontend/src/components/shell/breadcrumb.tsx` (placeholder, replaced in T6):

```tsx
"use client";
export function Breadcrumb({ className }: { className?: string }) {
  return <div className={className}>Today / Bills</div>;
}
```

- [ ] **Step 6: Commit**

```bash
cd /Users/angelxlakra/dev/efs-salon/efs-salon-os && git add frontend/src/components/shell/topbar.tsx frontend/src/components/shell/__tests__/topbar.test.tsx frontend/src/components/shell/breadcrumb.tsx frontend/src/components/command-palette/use-palette.tsx && git commit -m "feat(shell): TopBar (breadcrumb + Cmd+K trigger + user menu)"
```

---

### Task 6: Breadcrumb (route-derived)

**Files:**
- Modify: `frontend/src/components/shell/breadcrumb.tsx` (replace stub from T5)
- Create: `frontend/src/components/shell/__tests__/breadcrumb.test.tsx`

**Why:** Per spec §3.3 — "Breadcrumb is real (`Today / Bills / Invoice SAL-25-0171`), not decorative." Drives off `usePathname()` and the `SHELL_SECTIONS` config. Each segment is a link except the last (current page).

- [ ] **Step 1: Write failing tests**

`frontend/src/components/shell/__tests__/breadcrumb.test.tsx`:

```tsx
import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { Breadcrumb } from "@/components/shell/breadcrumb";

const mockPath = vi.hoisted(() => ({ value: "/dashboard" }));
vi.mock("next/navigation", () => ({
  usePathname: () => mockPath.value,
}));

describe("Breadcrumb", () => {
  it("renders 'Today' alone for /dashboard", () => {
    mockPath.value = "/dashboard";
    render(<Breadcrumb />);
    expect(screen.getByText("Today")).toBeInTheDocument();
    // No separator chevron because it's the only segment.
    expect(screen.queryByText("/")).toBeNull();
  });

  it("renders 'Today / Bills' for /dashboard/bills", () => {
    mockPath.value = "/dashboard/bills";
    render(<Breadcrumb />);
    expect(screen.getByText("Today")).toBeInTheDocument();
    expect(screen.getByText("Bills")).toBeInTheDocument();
  });

  it("renders the leaf as plain text (not a link), parents as links", () => {
    mockPath.value = "/dashboard/bills";
    render(<Breadcrumb />);
    expect(screen.getByRole("link", { name: "Today" })).toBeInTheDocument();
    // "Bills" is the leaf — no link role
    expect(screen.queryByRole("link", { name: "Bills" })).toBeNull();
  });

  it("falls back to capitalised segment when no section-config match", () => {
    mockPath.value = "/dashboard/bills/SAL-25-0171";
    render(<Breadcrumb />);
    // "SAL-25-0171" is unknown to section-config; shown verbatim.
    expect(screen.getByText("SAL-25-0171")).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run tests, verify FAIL**

```bash
cd /Users/angelxlakra/dev/efs-salon/efs-salon-os/frontend && PATH="/Users/angelxlakra/.nvm/versions/node/v22.20.0/bin:$PATH" npm test -- breadcrumb --run
```

Expected: failure (only the placeholder from T5 exists).

- [ ] **Step 3: Implement Breadcrumb**

Replace `frontend/src/components/shell/breadcrumb.tsx` with:

```tsx
"use client";

import * as React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { ChevronRight } from "lucide-react";
import { SHELL_SECTIONS } from "@/components/shell/section-config";
import { cn } from "@/lib/utils";

/** Build a label-lookup table from the section config so /dashboard/bills → "Bills". */
const HREF_TO_LABEL = (() => {
  const map = new Map<string, string>();
  for (const section of SHELL_SECTIONS) {
    for (const item of section.items) {
      map.set(item.href, item.label);
    }
  }
  return map;
})();

type Crumb = { href: string; label: string };

function buildCrumbs(pathname: string): Crumb[] {
  // Always begin with Today (the dashboard root).
  const crumbs: Crumb[] = [{ href: "/dashboard", label: "Today" }];
  if (pathname === "/dashboard" || !pathname.startsWith("/dashboard")) return crumbs;

  // Walk the path segment-by-segment, building accumulated hrefs.
  const segments = pathname.replace(/^\/dashboard\//, "").split("/").filter(Boolean);
  let acc = "/dashboard";
  for (const seg of segments) {
    acc = `${acc}/${seg}`;
    const labelFromConfig = HREF_TO_LABEL.get(acc);
    crumbs.push({
      href: acc,
      label: labelFromConfig ?? seg, // unknown segments (IDs) shown verbatim
    });
  }
  return crumbs;
}

export function Breadcrumb({ className }: { className?: string }) {
  const pathname = usePathname() ?? "/dashboard";
  const crumbs = buildCrumbs(pathname);
  return (
    <nav className={cn("flex items-center gap-1 text-body-sm text-text-secondary truncate", className)} aria-label="Breadcrumb">
      {crumbs.map((crumb, i) => {
        const isLast = i === crumbs.length - 1;
        return (
          <React.Fragment key={crumb.href}>
            {i > 0 && <ChevronRight className="size-3 text-text-muted shrink-0" aria-hidden />}
            {isLast ? (
              <span className="text-text-primary font-medium truncate" aria-current="page">{crumb.label}</span>
            ) : (
              <Link href={crumb.href} className="hover:text-text-primary truncate">{crumb.label}</Link>
            )}
          </React.Fragment>
        );
      })}
    </nav>
  );
}
```

- [ ] **Step 4: Run tests, verify PASS**

Expected: 4 tests pass.

- [ ] **Step 5: Commit**

```bash
cd /Users/angelxlakra/dev/efs-salon/efs-salon-os && git add frontend/src/components/shell/breadcrumb.tsx frontend/src/components/shell/__tests__/breadcrumb.test.tsx && git commit -m "feat(shell): route-derived Breadcrumb"
```

---

## Workstream B — ⌘K command palette (T7–T11)

### Task 7: CommandPalette modal scaffolding

**Files:**
- Modify: `frontend/src/components/command-palette/use-palette.tsx` (replace stub from T5)
- Create: `frontend/src/components/command-palette/command-palette.tsx`
- Create: `frontend/src/components/command-palette/__tests__/command-palette.test.tsx`

**Why:** Wires ⌘K / Ctrl+K globally so any component can call `usePalette().open()`. Builds the cmdk shell with Dialog (Phase 0 T11). T8–T10 plug providers into this shell; T11 adds history.

- [ ] **Step 1: Write failing tests**

`frontend/src/components/command-palette/__tests__/command-palette.test.tsx`:

```tsx
import { describe, expect, it } from "vitest";
import { render, screen, act } from "@testing-library/react";
import { CommandPalette } from "@/components/command-palette/command-palette";
import { PaletteProvider } from "@/components/command-palette/use-palette";

describe("CommandPalette", () => {
  it("is closed by default (no input visible)", () => {
    render(
      <PaletteProvider>
        <CommandPalette />
      </PaletteProvider>,
    );
    expect(screen.queryByPlaceholderText(/Type a command/i)).toBeNull();
  });

  it("opens on Cmd+K keyboard shortcut", () => {
    render(
      <PaletteProvider>
        <CommandPalette />
      </PaletteProvider>,
    );
    act(() => {
      window.dispatchEvent(new KeyboardEvent("keydown", { key: "k", metaKey: true }));
    });
    expect(screen.getByPlaceholderText(/Type a command/i)).toBeInTheDocument();
  });

  it("opens on Ctrl+K (Win/Linux)", () => {
    render(
      <PaletteProvider>
        <CommandPalette />
      </PaletteProvider>,
    );
    act(() => {
      window.dispatchEvent(new KeyboardEvent("keydown", { key: "k", ctrlKey: true }));
    });
    expect(screen.getByPlaceholderText(/Type a command/i)).toBeInTheDocument();
  });

  it("closes on Escape", async () => {
    render(
      <PaletteProvider>
        <CommandPalette />
      </PaletteProvider>,
    );
    act(() => {
      window.dispatchEvent(new KeyboardEvent("keydown", { key: "k", metaKey: true }));
    });
    expect(screen.getByPlaceholderText(/Type a command/i)).toBeInTheDocument();
    act(() => {
      window.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape" }));
    });
    expect(screen.queryByPlaceholderText(/Type a command/i)).toBeNull();
  });
});
```

- [ ] **Step 2: Run tests, verify FAIL**

```bash
cd /Users/angelxlakra/dev/efs-salon/efs-salon-os/frontend && PATH="/Users/angelxlakra/.nvm/versions/node/v22.20.0/bin:$PATH" npm test -- command-palette --run
```

Expected: failure.

- [ ] **Step 3: Replace the use-palette stub with the production version**

`frontend/src/components/command-palette/use-palette.tsx`:

```tsx
"use client";

import * as React from "react";

type PaletteValue = {
  open: () => void;
  close: () => void;
  toggle: () => void;
  isOpen: boolean;
};

const PaletteContext = React.createContext<PaletteValue | null>(null);

export function PaletteProvider({ children }: { children: React.ReactNode }) {
  const [isOpen, setIsOpen] = React.useState(false);

  const open = React.useCallback(() => setIsOpen(true), []);
  const close = React.useCallback(() => setIsOpen(false), []);
  const toggle = React.useCallback(() => setIsOpen((prev) => !prev), []);

  // Global keyboard binding: ⌘K (Mac) or Ctrl+K (Win/Linux).
  React.useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        toggle();
      } else if (e.key === "Escape" && isOpen) {
        e.preventDefault();
        close();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [toggle, close, isOpen]);

  const value = React.useMemo<PaletteValue>(
    () => ({ open, close, toggle, isOpen }),
    [open, close, toggle, isOpen],
  );

  return <PaletteContext.Provider value={value}>{children}</PaletteContext.Provider>;
}

export function usePalette(): PaletteValue {
  const ctx = React.useContext(PaletteContext);
  if (!ctx) throw new Error("usePalette must be used inside <PaletteProvider>");
  return ctx;
}
```

- [ ] **Step 4: Implement CommandPalette**

`frontend/src/components/command-palette/command-palette.tsx`:

```tsx
"use client";

import * as React from "react";
import { Command } from "cmdk";
import {
  Dialog,
  DialogContent,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { usePalette } from "@/components/command-palette/use-palette";

/**
 * Root command palette. T8–T10 will mount providers (navigation actions,
 * customer/bill/SKU search, global actions) inside the cmdk Command element.
 * T11 wires persisted history.
 */
export function CommandPalette() {
  const { isOpen, close } = usePalette();
  const [query, setQuery] = React.useState("");

  // Reset query each time the palette closes so the next open starts fresh.
  React.useEffect(() => {
    if (!isOpen) setQuery("");
  }, [isOpen]);

  return (
    <Dialog open={isOpen} onOpenChange={(o) => (o ? null : close())}>
      <DialogContent size="md" hideClose className="p-0 overflow-hidden">
        <DialogTitle className="sr-only">Command palette</DialogTitle>
        <DialogDescription className="sr-only">
          Type to search customers, bills, SKUs, or run an action.
        </DialogDescription>
        <Command label="Command palette" className="flex flex-col">
          <Command.Input
            value={query}
            onValueChange={setQuery}
            placeholder="Type a command or search…"
            className="px-4 h-12 text-body bg-transparent border-b border-border-subtle outline-none"
          />
          <Command.List className="max-h-[60dvh] overflow-y-auto p-2">
            <Command.Empty className="px-3 py-6 text-center text-text-muted text-body-sm">
              No results.
            </Command.Empty>
            {/* Provider groups slot in here — T8/T9/T10/T11. */}
          </Command.List>
        </Command>
      </DialogContent>
    </Dialog>
  );
}
```

- [ ] **Step 5: Run tests, verify PASS**

Expected: 4 tests pass.

> **JSDOM polyfill note** (T10 Combobox lesson): cmdk relies on `Element.prototype.scrollIntoView` and `ResizeObserver` which jsdom doesn't ship. If the test crashes on those, add to the top of the test file:
>
> ```ts
> if (typeof Element !== "undefined") {
>   Element.prototype.scrollIntoView = vi.fn();
> }
> if (typeof window !== "undefined" && !window.ResizeObserver) {
>   window.ResizeObserver = class {
>     observe() {}
>     unobserve() {}
>     disconnect() {}
>   } as unknown as typeof ResizeObserver;
> }
> ```

- [ ] **Step 6: Commit**

```bash
cd /Users/angelxlakra/dev/efs-salon/efs-salon-os && git add frontend/src/components/command-palette/use-palette.tsx frontend/src/components/command-palette/command-palette.tsx frontend/src/components/command-palette/__tests__/command-palette.test.tsx && git commit -m "feat(palette): CommandPalette scaffolding (Cmd+K opens cmdk in V2 Dialog)"
```

---

### Task 8: Navigation actions provider

**Files:**
- Create: `frontend/src/components/command-palette/providers/navigation.tsx`
- Modify: `frontend/src/components/command-palette/command-palette.tsx`
- Create: `frontend/src/components/command-palette/__tests__/navigation.test.tsx`

**Why:** First palette content. Lets the user type "bills" → press Enter → router.push("/dashboard/bills"). Reads from `SHELL_SECTIONS` (T1) so adding a new sidebar entry automatically becomes a palette command — DRY.

- [ ] **Step 1: Write failing tests**

`frontend/src/components/command-palette/__tests__/navigation.test.tsx`:

```tsx
import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, act } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { CommandPalette } from "@/components/command-palette/command-palette";
import { PaletteProvider } from "@/components/command-palette/use-palette";

const push = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push }),
}));

beforeEach(() => {
  push.mockReset();
  if (typeof Element !== "undefined") {
    Element.prototype.scrollIntoView = vi.fn();
  }
  if (typeof window !== "undefined" && !window.ResizeObserver) {
    (window as unknown as { ResizeObserver: typeof ResizeObserver }).ResizeObserver = class {
      observe() {}
      unobserve() {}
      disconnect() {}
    } as unknown as typeof ResizeObserver;
  }
});

function openPalette() {
  act(() => {
    window.dispatchEvent(new KeyboardEvent("keydown", { key: "k", metaKey: true }));
  });
}

describe("CommandPalette navigation provider", () => {
  it("lists navigation entries from section-config", async () => {
    render(
      <PaletteProvider>
        <CommandPalette />
      </PaletteProvider>,
    );
    openPalette();
    expect(await screen.findByText("Today")).toBeInTheDocument();
    expect(screen.getByText("Bills")).toBeInTheDocument();
    expect(screen.getByText("Customers")).toBeInTheDocument();
  });

  it("navigates on Enter and closes the palette", async () => {
    const user = userEvent.setup();
    render(
      <PaletteProvider>
        <CommandPalette />
      </PaletteProvider>,
    );
    openPalette();
    await user.type(screen.getByPlaceholderText(/Type a command/i), "bills");
    await user.keyboard("{Enter}");
    expect(push).toHaveBeenCalledWith("/dashboard/bills");
    expect(screen.queryByPlaceholderText(/Type a command/i)).toBeNull();
  });
});
```

- [ ] **Step 2: Run tests, verify FAIL**

```bash
cd /Users/angelxlakra/dev/efs-salon/efs-salon-os/frontend && PATH="/Users/angelxlakra/.nvm/versions/node/v22.20.0/bin:$PATH" npm test -- navigation --run
```

Expected: failure.

- [ ] **Step 3: Implement the navigation provider**

`frontend/src/components/command-palette/providers/navigation.tsx`:

```tsx
"use client";

import * as React from "react";
import { Command } from "cmdk";
import { useRouter } from "next/navigation";
import { SHELL_SECTIONS } from "@/components/shell/section-config";
import { usePalette } from "@/components/command-palette/use-palette";

export function NavigationProvider() {
  const router = useRouter();
  const { close } = usePalette();
  return (
    <Command.Group heading="Go to" className="text-overline text-text-muted px-2 py-1">
      {SHELL_SECTIONS.flatMap((section) => section.items).map((item) => {
        const Icon = item.icon;
        return (
          <Command.Item
            key={item.href}
            value={`go-${item.label.toLowerCase()}`}
            onSelect={() => {
              router.push(item.href);
              close();
            }}
            className="flex items-center gap-2 px-3 h-9 rounded-md text-body-sm text-text-primary cursor-pointer aria-selected:bg-surface-row-hover"
          >
            <Icon className="size-4 text-text-muted" />
            <span>{item.label}</span>
          </Command.Item>
        );
      })}
    </Command.Group>
  );
}
```

- [ ] **Step 4: Mount the provider in CommandPalette**

Edit `frontend/src/components/command-palette/command-palette.tsx`. Inside `<Command.List>`, after `<Command.Empty>`, add:

```tsx
<NavigationProvider />
```

And import it at the top:

```tsx
import { NavigationProvider } from "@/components/command-palette/providers/navigation";
```

- [ ] **Step 5: Run tests, verify PASS**

Expected: 2 tests pass plus the existing 4 from T7 still pass.

- [ ] **Step 6: Commit**

```bash
cd /Users/angelxlakra/dev/efs-salon/efs-salon-os && git add frontend/src/components/command-palette/providers/navigation.tsx frontend/src/components/command-palette/command-palette.tsx frontend/src/components/command-palette/__tests__/navigation.test.tsx && git commit -m "feat(palette): navigation provider (sidebar entries as Go-to commands)"
```

---

### Task 9: Quick-search providers (customers / bills / SKUs)

**Files:**
- Create: `frontend/src/components/command-palette/providers/customers.tsx`
- Create: `frontend/src/components/command-palette/providers/bills.tsx`
- Create: `frontend/src/components/command-palette/providers/skus.tsx`
- Modify: `frontend/src/components/command-palette/command-palette.tsx`
- Create: `frontend/src/components/command-palette/__tests__/search-providers.test.tsx`

**Why:** Quick-search is the palette's #1 daily use case. Backend search endpoints already exist (audit confirmed: `customers?search=`, `inventory?search=`, `pos?search=`). Each provider debounces input, fires the query, and renders results as `Command.Item` rows that route to the entity detail.

- [ ] **Step 1: Write failing tests**

`frontend/src/components/command-palette/__tests__/search-providers.test.tsx`:

```tsx
import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, act, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { CommandPalette } from "@/components/command-palette/command-palette";
import { PaletteProvider } from "@/components/command-palette/use-palette";

const push = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push }),
}));

const fetchMock = vi.fn();
beforeEach(() => {
  push.mockReset();
  fetchMock.mockReset();
  global.fetch = fetchMock as unknown as typeof fetch;
  if (typeof Element !== "undefined") {
    Element.prototype.scrollIntoView = vi.fn();
  }
  if (typeof window !== "undefined" && !window.ResizeObserver) {
    (window as unknown as { ResizeObserver: typeof ResizeObserver }).ResizeObserver = class {
      observe() {}
      unobserve() {}
      disconnect() {}
    } as unknown as typeof ResizeObserver;
  }
});

function openPalette() {
  act(() => {
    window.dispatchEvent(new KeyboardEvent("keydown", { key: "k", metaKey: true }));
  });
}

describe("CommandPalette search providers", () => {
  it("queries customers when input is non-empty and renders matches", async () => {
    fetchMock.mockResolvedValueOnce({
      ok: true,
      json: async () => [
        { id: "c1", first_name: "Priya", last_name: "Sharma", phone: "9000000001" },
      ],
    });
    fetchMock.mockResolvedValueOnce({ ok: true, json: async () => [] }); // bills
    fetchMock.mockResolvedValueOnce({ ok: true, json: async () => [] }); // skus

    const user = userEvent.setup();
    render(
      <PaletteProvider>
        <CommandPalette />
      </PaletteProvider>,
    );
    openPalette();
    await user.type(screen.getByPlaceholderText(/Type a command/i), "priya");
    await waitFor(() => {
      expect(screen.getByText(/Priya Sharma/)).toBeInTheDocument();
    });
  });

  it("does NOT call fetch when query is empty (avoids hitting search endpoints on open)", async () => {
    render(
      <PaletteProvider>
        <CommandPalette />
      </PaletteProvider>,
    );
    openPalette();
    // Allow an effect tick.
    await new Promise((r) => setTimeout(r, 50));
    expect(fetchMock).not.toHaveBeenCalled();
  });
});
```

- [ ] **Step 2: Run tests, verify FAIL**

```bash
cd /Users/angelxlakra/dev/efs-salon/efs-salon-os/frontend && PATH="/Users/angelxlakra/.nvm/versions/node/v22.20.0/bin:$PATH" npm test -- search-providers --run
```

Expected: failure.

- [ ] **Step 3: Implement the customers provider**

`frontend/src/components/command-palette/providers/customers.tsx`:

```tsx
"use client";

import * as React from "react";
import { Command } from "cmdk";
import { useRouter } from "next/navigation";
import { Users } from "lucide-react";
import { usePalette } from "@/components/command-palette/use-palette";

type Customer = { id: string; first_name: string; last_name: string; phone: string };

function useDebounced<T>(value: T, delayMs: number): T {
  const [debounced, setDebounced] = React.useState(value);
  React.useEffect(() => {
    const handle = setTimeout(() => setDebounced(value), delayMs);
    return () => clearTimeout(handle);
  }, [value, delayMs]);
  return debounced;
}

export function CustomersProvider({ query }: { query: string }) {
  const debouncedQuery = useDebounced(query.trim(), 200);
  const [results, setResults] = React.useState<Customer[]>([]);
  const router = useRouter();
  const { close } = usePalette();

  React.useEffect(() => {
    if (!debouncedQuery) {
      setResults([]);
      return;
    }
    let cancelled = false;
    fetch(`/api/customers/autocomplete?q=${encodeURIComponent(debouncedQuery)}`)
      .then((r) => (r.ok ? r.json() : []))
      .then((data: Customer[]) => {
        if (!cancelled) setResults(Array.isArray(data) ? data.slice(0, 5) : []);
      })
      .catch(() => {
        if (!cancelled) setResults([]);
      });
    return () => {
      cancelled = true;
    };
  }, [debouncedQuery]);

  if (!debouncedQuery || results.length === 0) return null;

  return (
    <Command.Group heading="Customers" className="text-overline text-text-muted px-2 py-1">
      {results.map((c) => (
        <Command.Item
          key={c.id}
          value={`customer-${c.id}`}
          onSelect={() => {
            router.push(`/dashboard/customers/${c.id}`);
            close();
          }}
          className="flex items-center gap-2 px-3 h-9 rounded-md text-body-sm text-text-primary cursor-pointer aria-selected:bg-surface-row-hover"
        >
          <Users className="size-4 text-text-muted" />
          <span>{c.first_name} {c.last_name}</span>
          <span className="ml-auto text-text-muted tabular text-caption">{c.phone}</span>
        </Command.Item>
      ))}
    </Command.Group>
  );
}
```

- [ ] **Step 4: Implement the bills provider**

`frontend/src/components/command-palette/providers/bills.tsx`:

```tsx
"use client";

import * as React from "react";
import { Command } from "cmdk";
import { useRouter } from "next/navigation";
import { Receipt } from "lucide-react";
import { usePalette } from "@/components/command-palette/use-palette";

type Bill = { id: string; invoice_number: string; total_paise: number; customer_name?: string };

function useDebounced<T>(value: T, delayMs: number): T {
  const [debounced, setDebounced] = React.useState(value);
  React.useEffect(() => {
    const handle = setTimeout(() => setDebounced(value), delayMs);
    return () => clearTimeout(handle);
  }, [value, delayMs]);
  return debounced;
}

export function BillsProvider({ query }: { query: string }) {
  const debouncedQuery = useDebounced(query.trim(), 200);
  const [results, setResults] = React.useState<Bill[]>([]);
  const router = useRouter();
  const { close } = usePalette();

  React.useEffect(() => {
    if (!debouncedQuery) {
      setResults([]);
      return;
    }
    let cancelled = false;
    fetch(`/api/pos/bills?search=${encodeURIComponent(debouncedQuery)}&limit=5`)
      .then((r) => (r.ok ? r.json() : []))
      .then((data) => {
        if (cancelled) return;
        const arr: Bill[] = Array.isArray(data) ? data : (data?.items ?? []);
        setResults(arr.slice(0, 5));
      })
      .catch(() => {
        if (!cancelled) setResults([]);
      });
    return () => {
      cancelled = true;
    };
  }, [debouncedQuery]);

  if (!debouncedQuery || results.length === 0) return null;

  return (
    <Command.Group heading="Bills" className="text-overline text-text-muted px-2 py-1">
      {results.map((b) => (
        <Command.Item
          key={b.id}
          value={`bill-${b.id}`}
          onSelect={() => {
            router.push(`/dashboard/bills/${b.id}`);
            close();
          }}
          className="flex items-center gap-2 px-3 h-9 rounded-md text-body-sm text-text-primary cursor-pointer aria-selected:bg-surface-row-hover"
        >
          <Receipt className="size-4 text-text-muted" />
          <span>{b.invoice_number}</span>
          {b.customer_name && <span className="text-text-muted">— {b.customer_name}</span>}
          <span className="ml-auto text-text-muted tabular text-caption">
            ₹{(b.total_paise / 100).toFixed(2)}
          </span>
        </Command.Item>
      ))}
    </Command.Group>
  );
}
```

- [ ] **Step 5: Implement the SKUs provider**

`frontend/src/components/command-palette/providers/skus.tsx`:

```tsx
"use client";

import * as React from "react";
import { Command } from "cmdk";
import { useRouter } from "next/navigation";
import { Package } from "lucide-react";
import { usePalette } from "@/components/command-palette/use-palette";

type SKU = { id: string; name: string; sku_code: string };

function useDebounced<T>(value: T, delayMs: number): T {
  const [debounced, setDebounced] = React.useState(value);
  React.useEffect(() => {
    const handle = setTimeout(() => setDebounced(value), delayMs);
    return () => clearTimeout(handle);
  }, [value, delayMs]);
  return debounced;
}

export function SkusProvider({ query }: { query: string }) {
  const debouncedQuery = useDebounced(query.trim(), 200);
  const [results, setResults] = React.useState<SKU[]>([]);
  const router = useRouter();
  const { close } = usePalette();

  React.useEffect(() => {
    if (!debouncedQuery) {
      setResults([]);
      return;
    }
    let cancelled = false;
    fetch(`/api/inventory?search=${encodeURIComponent(debouncedQuery)}&limit=5`)
      .then((r) => (r.ok ? r.json() : []))
      .then((data) => {
        if (cancelled) return;
        const arr: SKU[] = Array.isArray(data) ? data : (data?.items ?? []);
        setResults(arr.slice(0, 5));
      })
      .catch(() => {
        if (!cancelled) setResults([]);
      });
    return () => {
      cancelled = true;
    };
  }, [debouncedQuery]);

  if (!debouncedQuery || results.length === 0) return null;

  return (
    <Command.Group heading="Inventory" className="text-overline text-text-muted px-2 py-1">
      {results.map((s) => (
        <Command.Item
          key={s.id}
          value={`sku-${s.id}`}
          onSelect={() => {
            router.push(`/dashboard/inventory/${s.id}`);
            close();
          }}
          className="flex items-center gap-2 px-3 h-9 rounded-md text-body-sm text-text-primary cursor-pointer aria-selected:bg-surface-row-hover"
        >
          <Package className="size-4 text-text-muted" />
          <span>{s.name}</span>
          <span className="ml-auto text-text-muted text-caption">{s.sku_code}</span>
        </Command.Item>
      ))}
    </Command.Group>
  );
}
```

- [ ] **Step 6: Mount providers in CommandPalette**

Edit `frontend/src/components/command-palette/command-palette.tsx` so `<Command.List>` reads:

```tsx
<Command.List className="max-h-[60dvh] overflow-y-auto p-2">
  <Command.Empty className="px-3 py-6 text-center text-text-muted text-body-sm">
    No results.
  </Command.Empty>
  <NavigationProvider />
  <CustomersProvider query={query} />
  <BillsProvider query={query} />
  <SkusProvider query={query} />
</Command.List>
```

And add the imports at the top:

```tsx
import { CustomersProvider } from "@/components/command-palette/providers/customers";
import { BillsProvider } from "@/components/command-palette/providers/bills";
import { SkusProvider } from "@/components/command-palette/providers/skus";
```

- [ ] **Step 7: Run tests, verify PASS**

Expected: 2 new tests pass plus existing T7/T8 tests still green.

- [ ] **Step 8: Commit**

```bash
cd /Users/angelxlakra/dev/efs-salon/efs-salon-os && git add frontend/src/components/command-palette/providers/customers.tsx frontend/src/components/command-palette/providers/bills.tsx frontend/src/components/command-palette/providers/skus.tsx frontend/src/components/command-palette/command-palette.tsx frontend/src/components/command-palette/__tests__/search-providers.test.tsx && git commit -m "feat(palette): customer/bill/SKU search providers (debounced, top 5)"
```

---

### Task 10: Action commands (new bill, open drawer, toggle theme)

**Files:**
- Create: `frontend/src/components/command-palette/providers/actions.tsx`
- Modify: `frontend/src/components/command-palette/command-palette.tsx`
- Create: `frontend/src/components/command-palette/__tests__/actions.test.tsx`

**Why:** Per spec §3.4 the palette must expose imperative actions, not just navigation. Theme toggle is the only action that mutates app state directly here (flips `data-theme` on `<html>`); the others are navigation shortcuts (new bill → POS) or side-effects (open cash drawer).

- [ ] **Step 1: Write failing tests**

`frontend/src/components/command-palette/__tests__/actions.test.tsx`:

```tsx
import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, act } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { CommandPalette } from "@/components/command-palette/command-palette";
import { PaletteProvider } from "@/components/command-palette/use-palette";

const push = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push }),
}));

beforeEach(() => {
  push.mockReset();
  document.documentElement.setAttribute("data-theme", "light");
  if (typeof Element !== "undefined") {
    Element.prototype.scrollIntoView = vi.fn();
  }
  if (typeof window !== "undefined" && !window.ResizeObserver) {
    (window as unknown as { ResizeObserver: typeof ResizeObserver }).ResizeObserver = class {
      observe() {}
      unobserve() {}
      disconnect() {}
    } as unknown as typeof ResizeObserver;
  }
});

function openPalette() {
  act(() => {
    window.dispatchEvent(new KeyboardEvent("keydown", { key: "k", metaKey: true }));
  });
}

describe("CommandPalette actions provider", () => {
  it("lists action commands when palette opens", () => {
    render(
      <PaletteProvider>
        <CommandPalette />
      </PaletteProvider>,
    );
    openPalette();
    expect(screen.getByText(/New bill/i)).toBeInTheDocument();
    expect(screen.getByText(/Open cash drawer/i)).toBeInTheDocument();
    expect(screen.getByText(/Toggle theme/i)).toBeInTheDocument();
  });

  it("New bill navigates to /dashboard/pos", async () => {
    const user = userEvent.setup();
    render(
      <PaletteProvider>
        <CommandPalette />
      </PaletteProvider>,
    );
    openPalette();
    await user.click(screen.getByText(/New bill/i));
    expect(push).toHaveBeenCalledWith("/dashboard/pos");
  });

  it("Toggle theme flips data-theme on html element", async () => {
    const user = userEvent.setup();
    render(
      <PaletteProvider>
        <CommandPalette />
      </PaletteProvider>,
    );
    openPalette();
    expect(document.documentElement.getAttribute("data-theme")).toBe("light");
    await user.click(screen.getByText(/Toggle theme/i));
    expect(document.documentElement.getAttribute("data-theme")).toBe("dark");
  });
});
```

- [ ] **Step 2: Run tests, verify FAIL**

```bash
cd /Users/angelxlakra/dev/efs-salon/efs-salon-os/frontend && PATH="/Users/angelxlakra/.nvm/versions/node/v22.20.0/bin:$PATH" npm test -- actions --run
```

Expected: failure.

- [ ] **Step 3: Implement the actions provider**

`frontend/src/components/command-palette/providers/actions.tsx`:

```tsx
"use client";

import * as React from "react";
import { Command } from "cmdk";
import { useRouter } from "next/navigation";
import { Plus, CreditCard, Sun } from "lucide-react";
import { usePalette } from "@/components/command-palette/use-palette";

function toggleTheme() {
  if (typeof document === "undefined") return;
  const current = document.documentElement.getAttribute("data-theme");
  const next = current === "dark" ? "light" : "dark";
  document.documentElement.setAttribute("data-theme", next);
  try {
    window.localStorage.setItem("salon.theme", next);
  } catch {
    // storage may be unavailable in private mode — fail silent.
  }
}

export function ActionsProvider() {
  const router = useRouter();
  const { close } = usePalette();

  const items: { id: string; label: string; icon: typeof Plus; run: () => void }[] = [
    {
      id: "new-bill",
      label: "New bill",
      icon: Plus,
      run: () => {
        router.push("/dashboard/pos");
        close();
      },
    },
    {
      id: "open-cash-drawer",
      label: "Open cash drawer",
      icon: CreditCard,
      run: () => {
        router.push("/dashboard/cash-drawer");
        close();
      },
    },
    {
      id: "toggle-theme",
      label: "Toggle theme",
      icon: Sun,
      run: () => {
        toggleTheme();
        close();
      },
    },
  ];

  return (
    <Command.Group heading="Actions" className="text-overline text-text-muted px-2 py-1">
      {items.map((it) => {
        const Icon = it.icon;
        return (
          <Command.Item
            key={it.id}
            value={`action-${it.id}`}
            onSelect={it.run}
            className="flex items-center gap-2 px-3 h-9 rounded-md text-body-sm text-text-primary cursor-pointer aria-selected:bg-surface-row-hover"
          >
            <Icon className="size-4 text-text-muted" />
            <span>{it.label}</span>
          </Command.Item>
        );
      })}
    </Command.Group>
  );
}
```

- [ ] **Step 4: Mount in CommandPalette**

Edit `frontend/src/components/command-palette/command-palette.tsx`. Inside `<Command.List>`, add `<ActionsProvider />` AFTER `<NavigationProvider />` (so navigation surfaces first when the palette opens with empty query).

```tsx
<NavigationProvider />
<ActionsProvider />
<CustomersProvider query={query} />
<BillsProvider query={query} />
<SkusProvider query={query} />
```

Add the import:

```tsx
import { ActionsProvider } from "@/components/command-palette/providers/actions";
```

- [ ] **Step 5: Run tests, verify PASS**

Expected: 3 new tests pass; navigation + search-provider tests still green.

- [ ] **Step 6: Commit**

```bash
cd /Users/angelxlakra/dev/efs-salon/efs-salon-os && git add frontend/src/components/command-palette/providers/actions.tsx frontend/src/components/command-palette/command-palette.tsx frontend/src/components/command-palette/__tests__/actions.test.tsx && git commit -m "feat(palette): action commands (new bill, open drawer, toggle theme)"
```

---

### Task 11: Persisted command history

**Files:**
- Create: `frontend/src/components/command-palette/history.ts`
- Modify: `frontend/src/components/command-palette/command-palette.tsx`
- Create: `frontend/src/components/command-palette/__tests__/history.test.ts`

**Why:** Per spec §3.4 the palette persists history. Practically: when the user opens the palette with an empty query, surface the 5 most-recently executed commands at the top so muscle-memory pays off. Stored in localStorage, capped at 10 entries.

- [ ] **Step 1: Write failing tests**

`frontend/src/components/command-palette/__tests__/history.test.ts`:

```ts
import { describe, expect, it, beforeEach } from "vitest";
import { recordCommand, readHistory, clearHistory } from "@/components/command-palette/history";

describe("palette history", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it("readHistory returns empty array when nothing stored", () => {
    expect(readHistory()).toEqual([]);
  });

  it("recordCommand appends and persists", () => {
    recordCommand({ id: "go-bills", label: "Bills", href: "/dashboard/bills" });
    expect(readHistory()).toHaveLength(1);
    expect(readHistory()[0].id).toBe("go-bills");
  });

  it("recordCommand deduplicates — same id moves to front, not duplicated", () => {
    recordCommand({ id: "go-bills", label: "Bills", href: "/dashboard/bills" });
    recordCommand({ id: "go-customers", label: "Customers", href: "/dashboard/customers" });
    recordCommand({ id: "go-bills", label: "Bills", href: "/dashboard/bills" });
    const h = readHistory();
    expect(h).toHaveLength(2);
    expect(h[0].id).toBe("go-bills");
    expect(h[1].id).toBe("go-customers");
  });

  it("recordCommand caps history at 10 entries", () => {
    for (let i = 0; i < 15; i++) {
      recordCommand({ id: `cmd-${i}`, label: `Cmd ${i}`, href: `/x/${i}` });
    }
    expect(readHistory()).toHaveLength(10);
    // Most recent first.
    expect(readHistory()[0].id).toBe("cmd-14");
  });

  it("clearHistory empties storage", () => {
    recordCommand({ id: "x", label: "X", href: "/x" });
    clearHistory();
    expect(readHistory()).toEqual([]);
  });
});
```

- [ ] **Step 2: Run tests, verify FAIL**

```bash
cd /Users/angelxlakra/dev/efs-salon/efs-salon-os/frontend && PATH="/Users/angelxlakra/.nvm/versions/node/v22.20.0/bin:$PATH" npm test -- history --run
```

Expected: failure.

- [ ] **Step 3: Implement history**

`frontend/src/components/command-palette/history.ts`:

```ts
const STORAGE_KEY = "salon.palette.history";
const MAX_ENTRIES = 10;

export type HistoryEntry = {
  id: string;
  label: string;
  href: string;
};

export function readHistory(): HistoryEntry[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export function recordCommand(entry: HistoryEntry): void {
  if (typeof window === "undefined") return;
  const current = readHistory();
  const filtered = current.filter((e) => e.id !== entry.id);
  const next = [entry, ...filtered].slice(0, MAX_ENTRIES);
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
  } catch {
    // storage unavailable — fail silent.
  }
}

export function clearHistory(): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.removeItem(STORAGE_KEY);
  } catch {
    // ignore
  }
}
```

- [ ] **Step 4: Wire history into NavigationProvider**

Edit `frontend/src/components/command-palette/providers/navigation.tsx`. Inside the `onSelect` callback, record before navigating:

```tsx
import { recordCommand } from "@/components/command-palette/history";

// Inside Command.Item onSelect:
onSelect={() => {
  recordCommand({ id: `go-${item.label.toLowerCase()}`, label: item.label, href: item.href });
  router.push(item.href);
  close();
}}
```

Apply the same pattern to `customers.tsx`, `bills.tsx`, `skus.tsx`, and `actions.tsx` (skip `actions.tsx` for `toggle-theme` since it has no href — but you may record the navigation actions like new-bill).

- [ ] **Step 5: Add a "Recent" group to the palette**

Edit `frontend/src/components/command-palette/command-palette.tsx`:

```tsx
import { Command } from "cmdk";
import { useRouter } from "next/navigation";
import { Clock } from "lucide-react";
import { readHistory } from "@/components/command-palette/history";
// ...other imports unchanged

// Inside the component, BEFORE the render:
const router = useRouter();
const [history, setHistory] = React.useState<ReturnType<typeof readHistory>>([]);
React.useEffect(() => {
  if (isOpen) setHistory(readHistory().slice(0, 5));
}, [isOpen]);
const showHistory = !query && history.length > 0;
```

Add a Recent group before the NavigationProvider:

```tsx
<Command.List className="max-h-[60dvh] overflow-y-auto p-2">
  <Command.Empty className="px-3 py-6 text-center text-text-muted text-body-sm">
    No results.
  </Command.Empty>
  {showHistory && (
    <Command.Group heading="Recent" className="text-overline text-text-muted px-2 py-1">
      {history.map((h) => (
        <Command.Item
          key={`recent-${h.id}`}
          value={`recent-${h.id}`}
          onSelect={() => {
            router.push(h.href);
            close();
          }}
          className="flex items-center gap-2 px-3 h-9 rounded-md text-body-sm text-text-primary cursor-pointer aria-selected:bg-surface-row-hover"
        >
          <Clock className="size-4 text-text-muted" />
          <span>{h.label}</span>
        </Command.Item>
      ))}
    </Command.Group>
  )}
  <NavigationProvider />
  <ActionsProvider />
  <CustomersProvider query={query} />
  <BillsProvider query={query} />
  <SkusProvider query={query} />
</Command.List>
```

- [ ] **Step 6: Run tests, verify PASS**

Expected: all 5 history tests pass; existing palette tests still pass.

- [ ] **Step 7: Commit**

```bash
cd /Users/angelxlakra/dev/efs-salon/efs-salon-os && git add frontend/src/components/command-palette/history.ts frontend/src/components/command-palette/providers/ frontend/src/components/command-palette/command-palette.tsx frontend/src/components/command-palette/__tests__/history.test.ts && git commit -m "feat(palette): persisted history (top 5 recent surface on empty query)"
```

---

## Workstream C — `@modal` parallel slot (T12–T15)

### Task 12: Add `@modal` slot to (shell) layout

**Files:**
- Modify: `frontend/src/app/(shell)/layout.tsx`

**Why:** The skeleton from T1 already accepts a `modal` prop. Now we wire the shell's full chrome (sidebar + topbar + bottom-nav) and the SidebarStateProvider/PaletteProvider. The `{modal}` slot renders alongside `{children}` so intercepted routes stack on top.

- [ ] **Step 1: Replace `frontend/src/app/(shell)/layout.tsx`**

```tsx
import * as React from "react";
import { SidebarV2 } from "@/components/shell/sidebar-v2";
import { SidebarRail } from "@/components/shell/sidebar-rail";
import { TopBar } from "@/components/shell/topbar";
import { BottomTabNav } from "@/components/shell/bottom-tab-nav";
import { SidebarStateProvider, useSidebarState } from "@/components/shell/sidebar-state";
import { PaletteProvider } from "@/components/command-palette/use-palette";
import { CommandPalette } from "@/components/command-palette/command-palette";

function ShellChrome({ children, modal }: { children: React.ReactNode; modal: React.ReactNode }) {
  const { collapsed } = useSidebarState();
  return (
    <div className="min-h-dvh bg-surface-page text-text-primary flex">
      {/* Desktop sidebar — collapses to rail. */}
      <div className="hidden md:block">
        {collapsed ? <SidebarRail /> : <SidebarV2 />}
      </div>
      <div className="flex-1 flex flex-col min-w-0">
        <TopBar />
        {/* pb-16 reserves space for BottomTabNav on mobile (T18). */}
        <main className="flex-1 pb-16 md:pb-0">{children}</main>
      </div>
      {/* Mobile bottom nav. */}
      <BottomTabNav />
      {/* Parallel modal slot. */}
      {modal}
      {/* Global command palette. */}
      <CommandPalette />
    </div>
  );
}

export default function ShellLayout({
  children,
  modal,
}: {
  children: React.ReactNode;
  modal: React.ReactNode;
}) {
  return (
    <SidebarStateProvider>
      <PaletteProvider>
        <ShellChrome modal={modal}>{children}</ShellChrome>
      </PaletteProvider>
    </SidebarStateProvider>
  );
}
```

- [ ] **Step 2: Verify build (no behavior tests; integration ships in T19)**

```bash
cd /Users/angelxlakra/dev/efs-salon/efs-salon-os/frontend && PATH="/Users/angelxlakra/.nvm/versions/node/v22.20.0/bin:$PATH" npx tsc --noEmit 2>&1 | grep -c "error TS"
```

Expected: 162 (no new errors). If TS complains about `BottomTabNav` not existing yet, this task depends on T16 — reorder so T16 ships first, OR add a placeholder `BottomTabNav.tsx` that returns `null`:

```tsx
// frontend/src/components/shell/bottom-tab-nav.tsx (placeholder for T12 — replaced by T16)
export function BottomTabNav() {
  return null;
}
```

- [ ] **Step 3: Commit**

```bash
cd /Users/angelxlakra/dev/efs-salon/efs-salon-os && git add frontend/src/app/\(shell\)/layout.tsx frontend/src/components/shell/bottom-tab-nav.tsx && git commit -m "feat(shell): wire SidebarV2/Rail + TopBar + @modal slot + PaletteProvider"
```

---

### Task 13: Wire bills entity (canonical [id] + intercepted route)

**Files:**
- Create: `frontend/src/components/bills/bill-detail.tsx`
- Create: `frontend/src/app/(shell)/bills/[id]/page.tsx`
- Create: `frontend/src/app/(shell)/@modal/(.)bills/[id]/page.tsx`

**Why:** Demonstrates the canonical-vs-intercepted route pattern with one entity (bills). Same body component (`BillDetail`) renders inside a Dialog when launched from `/dashboard/bills` (intercepted) and as a full page when accessed from a cold URL or the palette (canonical).

> **Path note:** the route group `(shell)` does NOT appear in the URL. So `/bills/[id]` here resolves to `/bills/[id]` in the browser — but we want `/dashboard/bills/[id]` to keep V1 URLs unchanged. Therefore the canonical route file lives at `frontend/src/app/(shell)/dashboard/bills/[id]/page.tsx` and the intercepted slot lives at `frontend/src/app/(shell)/@modal/(.)dashboard/bills/[id]/page.tsx`. Adjust paths below accordingly.

**Corrected file paths:**
- Create: `frontend/src/app/(shell)/dashboard/bills/[id]/page.tsx` — canonical
- Create: `frontend/src/app/(shell)/@modal/(.)dashboard/bills/[id]/page.tsx` — intercepted

- [ ] **Step 1: Implement BillDetail (shared body)**

`frontend/src/components/bills/bill-detail.tsx`:

```tsx
"use client";

import * as React from "react";
import { Skeleton } from "@/components/ui/skeleton";

type Bill = {
  id: string;
  invoice_number: string;
  total_paise: number;
  customer_name?: string;
  status: string;
};

export function BillDetail({ id }: { id: string }) {
  const [bill, setBill] = React.useState<Bill | null>(null);
  const [error, setError] = React.useState<string | null>(null);

  React.useEffect(() => {
    let cancelled = false;
    fetch(`/api/pos/bills/${id}`)
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`))))
      .then((data: Bill) => {
        if (!cancelled) setBill(data);
      })
      .catch((e) => {
        if (!cancelled) setError(e instanceof Error ? e.message : "Failed to load");
      });
    return () => {
      cancelled = true;
    };
  }, [id]);

  if (error) return <div className="p-6 text-danger-fg">{error}</div>;
  if (!bill) {
    return (
      <div className="p-6 flex flex-col gap-3">
        <Skeleton shape="text" width="60%" />
        <Skeleton shape="text" width="40%" />
        <Skeleton shape="row" />
        <Skeleton shape="row" />
      </div>
    );
  }

  return (
    <div className="p-6 flex flex-col gap-2">
      <h2 className="text-heading-md text-text-primary">{bill.invoice_number}</h2>
      {bill.customer_name && (
        <p className="text-body-sm text-text-secondary">{bill.customer_name}</p>
      )}
      <p className="text-money-lg text-text-primary tabular">
        ₹{(bill.total_paise / 100).toFixed(2)}
      </p>
      <p className="text-body-sm text-text-secondary capitalize">{bill.status}</p>
    </div>
  );
}
```

- [ ] **Step 2: Implement the canonical full-page route**

`frontend/src/app/(shell)/dashboard/bills/[id]/page.tsx`:

```tsx
import { BillDetail } from "@/components/bills/bill-detail";

export default async function BillCanonicalPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return (
    <div className="container mx-auto max-w-4xl">
      <BillDetail id={id} />
    </div>
  );
}
```

- [ ] **Step 3: Implement the intercepted modal route**

`frontend/src/app/(shell)/@modal/(.)dashboard/bills/[id]/page.tsx`:

```tsx
"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import {
  Dialog,
  DialogContent,
  DialogTitle,
} from "@/components/ui/dialog";
import { BillDetail } from "@/components/bills/bill-detail";

export default function BillInterceptedPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = React.use(params);
  const router = useRouter();
  return (
    <Dialog open onOpenChange={(open) => (open ? null : router.back())}>
      <DialogContent size="md">
        <DialogTitle className="sr-only">Bill detail</DialogTitle>
        <BillDetail id={id} />
      </DialogContent>
    </Dialog>
  );
}
```

- [ ] **Step 4: Verify both routes resolve at build time**

```bash
cd /Users/angelxlakra/dev/efs-salon/efs-salon-os/frontend && PATH="/Users/angelxlakra/.nvm/versions/node/v22.20.0/bin:$PATH" npx tsc --noEmit 2>&1 | grep -c "error TS"
```

Expected: 162 (unchanged).

> **Manual verification (post-T19):** after T19 lands, visiting `http://localhost:3000/dashboard/bills/<some-id>` directly renders the canonical full page, while clicking a row from `/dashboard/bills` (after T15 wires it) opens the same body in a Dialog without leaving the list URL.

- [ ] **Step 5: Commit**

```bash
cd /Users/angelxlakra/dev/efs-salon/efs-salon-os && git add frontend/src/components/bills/bill-detail.tsx frontend/src/app/\(shell\)/dashboard/bills/\[id\]/page.tsx 'frontend/src/app/(shell)/@modal/(.)dashboard/bills/[id]/page.tsx' && git commit -m "feat(shell): bills entity wired via @modal slot (canonical + intercepted)"
```

> If the shell prefers the literal-quoted path: `git add 'frontend/src/app/(shell)/@modal/(.)dashboard/bills/[id]/page.tsx'` (single quotes preserve the parens and `(.)` segment).

---

### Task 14: Document `@modal` pattern in design_system.md

**Files:**
- Modify: `docs/design_system.md`

**Why:** Future entity retrofits (Phase 3+) will copy the bills pattern verbatim — customers, invoices, SKUs, purchases, expenses all need it. Documenting the exact file layout + the canonical-vs-intercepted distinction prevents drift.

- [ ] **Step 1: Find §7.5 in `docs/design_system.md`**

Look for the heading `## §7.5` or "entity detail routing". From Phase 0's prior work, this section was added with intent text but no implementation example.

- [ ] **Step 2: Append the implementation template**

Add the following subsection at the end of §7.5:

```md
### §7.5.1 — Implementation template (Phase 1)

Every entity detail surface uses two route files plus one shared body component.

**File layout (use bills as canonical example):**

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

**Lint enforcement (Phase 0 T25):** `salon/no-list-owned-detail-state` flags any list page that imports a `*DetailDialog` AND holds a `selected*Id` in `useState`. List pages must instead push to the entity URL (`router.push(\`/dashboard/<entity>/\${id}\`)`) and let the @modal slot handle rendering.

**Reference implementation:** see `frontend/src/app/(shell)/dashboard/bills/[id]/page.tsx`, `frontend/src/app/(shell)/@modal/(.)dashboard/bills/[id]/page.tsx`, and `frontend/src/components/bills/bill-detail.tsx` (Phase 1 T13).
```

- [ ] **Step 3: Commit**

```bash
cd /Users/angelxlakra/dev/efs-salon/efs-salon-os && git add docs/design_system.md && git commit -m "docs(design-system): add §7.5.1 @modal implementation template"
```

---

### Task 15: Proof retrofit — remove `bills/page.tsx` local useState

**Files:**
- Modify: `frontend/src/app/(shell)/dashboard/bills/page.tsx` (after T19 moves it from `app/dashboard/bills/page.tsx`)

**Why:** This task closes the salon/no-list-owned-detail-state lint warning that has been firing on `bills/page.tsx` since Phase 0 T25. It's the proof point that the @modal pattern works end-to-end.

> **Sequencing note:** T15 modifies a file that lives at `app/dashboard/bills/page.tsx` today and moves to `app/(shell)/dashboard/bills/page.tsx` at T19. Run T15 AFTER T19 unless you handle the move yourself here. The instructions below assume T19 has already moved the file.

- [ ] **Step 1: Open the moved file**

`frontend/src/app/(shell)/dashboard/bills/page.tsx`

- [ ] **Step 2: Identify the offending pattern**

Search for `const [selectedBillId, setSelectedBillId] = useState<string | null>(null)` (or similar). The current file pattern is roughly:

```tsx
const [selectedBillId, setSelectedBillId] = useState<string | null>(null);
// ...
<BillDetailsDialog billId={selectedBillId} onClose={() => setSelectedBillId(null)} />
```

- [ ] **Step 3: Remove the state + dialog import + dialog render**

Delete:
- The `useState<string | null>` line.
- The `import { BillDetailsDialog } from "@/components/bills/bill-details-dialog"` line.
- The `<BillDetailsDialog billId={...} ... />` JSX.

- [ ] **Step 4: Replace the row click handler with navigation**

Wherever a row click currently sets `selectedBillId(row.id)`, replace with:

```tsx
import { useRouter } from "next/navigation";
// inside the component:
const router = useRouter();
// row click handler:
onRowClick={(bill) => router.push(`/dashboard/bills/${bill.id}`)}
```

The @modal slot intercepts that navigation and renders `BillDetail` in a Dialog (T13). The list URL stays `/dashboard/bills`.

- [ ] **Step 5: Verify lint warning is gone**

```bash
cd /Users/angelxlakra/dev/efs-salon/efs-salon-os/frontend && PATH="/Users/angelxlakra/.nvm/versions/node/v22.20.0/bin:$PATH" npm run lint 2>&1 | grep "no-list-owned-detail-state"
```

Expected: 0 matches (was 1 in Phase 0).

- [ ] **Step 6: Verify tsc unchanged + tests still pass**

```bash
cd /Users/angelxlakra/dev/efs-salon/efs-salon-os/frontend && PATH="/Users/angelxlakra/.nvm/versions/node/v22.20.0/bin:$PATH" npx tsc --noEmit 2>&1 | grep -c "error TS"
```

Expected: 162 (or possibly 161 if removing a typing leak fixed something — accept any decrease).

- [ ] **Step 7: Commit**

```bash
cd /Users/angelxlakra/dev/efs-salon/efs-salon-os && git add frontend/src/app/\(shell\)/dashboard/bills/page.tsx && git commit -m "refactor(bills): remove list-owned detail state (use @modal route)"
```

---

## Workstream D — Mobile shell (T16–T18)

### Task 16: BottomTabNav (4 items: Today / POS / Bills / More)

**Files:**
- Modify: `frontend/src/components/shell/bottom-tab-nav.tsx` (replace placeholder from T12)
- Create: `frontend/src/components/shell/__tests__/bottom-tab-nav.test.tsx`

**Why:** Mobile primary nav per spec §3.3. 4 fixed items: 3 routes (`MOBILE_TABS` from T1) + 1 "More" tab that opens the overflow sheet (T17). Visible only at `<md` breakpoint; hidden on desktop.

- [ ] **Step 1: Write failing tests**

`frontend/src/components/shell/__tests__/bottom-tab-nav.test.tsx`:

```tsx
import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { BottomTabNav } from "@/components/shell/bottom-tab-nav";

vi.mock("next/navigation", () => ({
  usePathname: () => "/dashboard",
}));

describe("BottomTabNav", () => {
  it("renders the 3 fixed tabs + a More button", () => {
    render(<BottomTabNav />);
    expect(screen.getByRole("link", { name: /Today/ })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /POS/ })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Bills/ })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /More/i })).toBeInTheDocument();
  });

  it("hides on desktop (md and up)", () => {
    const { container } = render(<BottomTabNav />);
    expect(container.firstChild).toHaveClass("md:hidden");
  });

  it("opens the More sheet on click", async () => {
    const user = userEvent.setup();
    render(<BottomTabNav />);
    await user.click(screen.getByRole("button", { name: /More/i }));
    // Sheet content (T17) renders the secondary nav items.
    expect(screen.getByRole("link", { name: /Customers/i })).toBeInTheDocument();
  });

  it("marks the active tab", () => {
    render(<BottomTabNav />);
    const today = screen.getByRole("link", { name: /Today/ });
    expect(today).toHaveAttribute("data-active", "true");
  });
});
```

- [ ] **Step 2: Run tests, verify FAIL**

```bash
cd /Users/angelxlakra/dev/efs-salon/efs-salon-os/frontend && PATH="/Users/angelxlakra/.nvm/versions/node/v22.20.0/bin:$PATH" npm test -- bottom-tab-nav --run
```

Expected: failure (placeholder returns null).

- [ ] **Step 3: Implement BottomTabNav**

`frontend/src/components/shell/bottom-tab-nav.tsx` (replace placeholder):

```tsx
"use client";

import * as React from "react";
import { usePathname } from "next/navigation";
import { MoreHorizontal } from "lucide-react";
import { NavItem } from "@/components/ui/nav-item";
import { MOBILE_TABS } from "@/components/shell/section-config";
import { MoreSheet } from "@/components/shell/more-sheet";
import { cn } from "@/lib/utils";

function isActive(itemHref: string, pathname: string): boolean {
  if (itemHref === "/dashboard") return pathname === "/dashboard";
  return pathname === itemHref || pathname.startsWith(itemHref + "/");
}

export function BottomTabNav({ className }: { className?: string }) {
  const pathname = usePathname() ?? "/";
  const [moreOpen, setMoreOpen] = React.useState(false);

  return (
    <>
      <nav
        className={cn(
          "md:hidden fixed bottom-0 inset-x-0 z-30 h-14 bg-surface-card border-t border-border-subtle flex items-stretch",
          className,
        )}
        aria-label="Primary mobile navigation"
      >
        {MOBILE_TABS.map((tab) => {
          const Icon = tab.icon;
          return (
            <NavItem
              key={tab.href}
              variant="bottom"
              label={tab.label}
              href={tab.href}
              icon={<Icon />}
              active={isActive(tab.href, pathname)}
            />
          );
        })}
        <button
          type="button"
          onClick={() => setMoreOpen(true)}
          className="flex-1 flex flex-col items-center justify-center gap-0.5 text-[11px] text-text-secondary hover:text-text-primary"
          aria-label="More navigation"
        >
          <MoreHorizontal className="size-5" />
          <span>More</span>
        </button>
      </nav>
      <MoreSheet open={moreOpen} onOpenChange={setMoreOpen} />
    </>
  );
}
```

- [ ] **Step 4: Create a placeholder MoreSheet (replaced by T17)**

`frontend/src/components/shell/more-sheet.tsx`:

```tsx
"use client";

import * as React from "react";
import Link from "next/link";

// Placeholder — T17 replaces with full Sheet UI.
export function MoreSheet({ open, onOpenChange }: { open: boolean; onOpenChange: (next: boolean) => void }) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-40 bg-surface-overlay" onClick={() => onOpenChange(false)}>
      <div className="absolute bottom-0 inset-x-0 bg-surface-card p-4 rounded-t-lg" onClick={(e) => e.stopPropagation()}>
        <Link href="/dashboard/customers">Customers</Link>
        <Link href="/dashboard/inventory" className="ml-2">Inventory</Link>
      </div>
    </div>
  );
}
```

- [ ] **Step 5: Run tests, verify PASS**

Expected: 4 tests pass.

- [ ] **Step 6: Commit**

```bash
cd /Users/angelxlakra/dev/efs-salon/efs-salon-os && git add frontend/src/components/shell/bottom-tab-nav.tsx frontend/src/components/shell/more-sheet.tsx frontend/src/components/shell/__tests__/bottom-tab-nav.test.tsx && git commit -m "feat(shell): BottomTabNav (Today/POS/Bills/More) with overflow sheet"
```

---

### Task 17: Mobile More sheet (overflow nav)

**Files:**
- Modify: `frontend/src/components/shell/more-sheet.tsx` (replace placeholder from T16)
- Create: `frontend/src/components/shell/__tests__/more-sheet.test.tsx`

**Why:** Houses everything that didn't fit in the 4 bottom tabs — all sections beyond Today / POS / Bills. Renders inside the V2 Dialog primitive (Phase 0 T11) sized as `full` for a sheet-style takeover on mobile.

- [ ] **Step 1: Write failing tests**

`frontend/src/components/shell/__tests__/more-sheet.test.tsx`:

```tsx
import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MoreSheet } from "@/components/shell/more-sheet";

vi.mock("next/navigation", () => ({
  usePathname: () => "/dashboard",
}));

describe("MoreSheet", () => {
  it("does not render when closed", () => {
    render(<MoreSheet open={false} onOpenChange={() => {}} />);
    expect(screen.queryByText("Customers")).toBeNull();
  });

  it("renders all overflow sections when open", () => {
    render(<MoreSheet open={true} onOpenChange={() => {}} />);
    // Items NOT in MOBILE_TABS should appear here.
    expect(screen.getByText("Customers")).toBeInTheDocument();
    expect(screen.getByText("Inventory")).toBeInTheDocument();
    expect(screen.getByText("Settings")).toBeInTheDocument();
  });

  it("calls onOpenChange(false) when a link is clicked", async () => {
    const user = userEvent.setup();
    const onOpenChange = vi.fn();
    render(<MoreSheet open={true} onOpenChange={onOpenChange} />);
    await user.click(screen.getByRole("link", { name: /Customers/i }));
    expect(onOpenChange).toHaveBeenCalledWith(false);
  });
});
```

- [ ] **Step 2: Run tests, verify FAIL**

```bash
cd /Users/angelxlakra/dev/efs-salon/efs-salon-os/frontend && PATH="/Users/angelxlakra/.nvm/versions/node/v22.20.0/bin:$PATH" npm test -- more-sheet --run
```

Expected: failure (placeholder doesn't render section headings or closing behavior).

- [ ] **Step 3: Replace MoreSheet with the full implementation**

`frontend/src/components/shell/more-sheet.tsx`:

```tsx
"use client";

import * as React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogBody,
} from "@/components/ui/dialog";
import { SHELL_SECTIONS, MOBILE_TABS } from "@/components/shell/section-config";
import { cn } from "@/lib/utils";

function isActive(itemHref: string, pathname: string): boolean {
  if (itemHref === "/dashboard") return pathname === "/dashboard";
  return pathname === itemHref || pathname.startsWith(itemHref + "/");
}

export function MoreSheet({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (next: boolean) => void;
}) {
  const pathname = usePathname() ?? "/";

  // Items already in the bottom tabs — exclude from overflow.
  const tabHrefs = new Set(MOBILE_TABS.map((t) => t.href));

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent size="full" className="md:hidden">
        <DialogHeader>
          <DialogTitle>More</DialogTitle>
        </DialogHeader>
        <DialogBody>
          <div className="flex flex-col gap-4">
            {SHELL_SECTIONS.map((section) => {
              const overflowItems = section.items.filter((it) => !tabHrefs.has(it.href));
              if (overflowItems.length === 0) return null;
              return (
                <div key={section.id} className="flex flex-col gap-1">
                  <div className="px-3 pt-2 pb-1 text-overline text-text-muted">{section.label}</div>
                  {overflowItems.map((item) => {
                    const Icon = item.icon;
                    const active = isActive(item.href, pathname);
                    return (
                      <Link
                        key={item.href}
                        href={item.href}
                        onClick={() => onOpenChange(false)}
                        className={cn(
                          "flex items-center gap-3 px-3 h-10 rounded-md text-body text-text-primary",
                          "hover:bg-surface-row-hover",
                          active && "bg-accent-bg-soft text-accent font-semibold",
                        )}
                        data-active={active || undefined}
                      >
                        <Icon className="size-4 text-text-muted" />
                        <span>{item.label}</span>
                      </Link>
                    );
                  })}
                </div>
              );
            })}
          </div>
        </DialogBody>
      </DialogContent>
    </Dialog>
  );
}
```

- [ ] **Step 4: Run tests, verify PASS**

Expected: 3 tests pass; T16's BottomTabNav tests still pass.

- [ ] **Step 5: Commit**

```bash
cd /Users/angelxlakra/dev/efs-salon/efs-salon-os && git add frontend/src/components/shell/more-sheet.tsx frontend/src/components/shell/__tests__/more-sheet.test.tsx && git commit -m "feat(shell): MoreSheet (mobile overflow nav for hidden sections)"
```

---

### Task 18: Reserve bottom-nav height in mobile content

**Files:**
- Modify: `frontend/src/app/(shell)/layout.tsx`

**Why:** Per spec §5 ("Bottom nav overlaps mobile dashboard donut charts" — V1 failure mode), the layout must reserve `h-14` (56px) of padding at the bottom of `<main>` on mobile so content doesn't slide under the BottomTabNav. Already present in T12 as `pb-16` — confirm it's correct (16 = 64px, slightly more than nav height for safe area), and additionally honor `env(safe-area-inset-bottom)` for iOS notch devices.

- [ ] **Step 1: Verify the current layout has the padding rule**

```bash
grep -n "pb-16\|pb-14\|safe-area" frontend/src/app/\(shell\)/layout.tsx
```

If it shows `pb-16 md:pb-0`, that's already correct.

- [ ] **Step 2: Add safe-area inset for iOS notch devices**

Edit `frontend/src/app/(shell)/layout.tsx`. Find the `<main>` line:

```tsx
<main className="flex-1 pb-16 md:pb-0">{children}</main>
```

Replace with:

```tsx
<main className="flex-1 pb-[calc(theme(spacing.16)+env(safe-area-inset-bottom))] md:pb-0">
  {children}
</main>
```

> **Tailwind 4 note:** `theme(spacing.16)` resolves to `4rem` (64px). `env(safe-area-inset-bottom)` is 0 on browsers without notch.

- [ ] **Step 3: Add safe-area inset to the BottomTabNav itself**

Edit `frontend/src/components/shell/bottom-tab-nav.tsx`. The `<nav>` element currently has `h-14 fixed bottom-0`. Update to:

```tsx
className={cn(
  "md:hidden fixed bottom-0 inset-x-0 z-30 bg-surface-card border-t border-border-subtle flex items-stretch",
  "h-[calc(theme(spacing.14)+env(safe-area-inset-bottom))] pb-[env(safe-area-inset-bottom)]",
  className,
)}
```

So the visible nav stays 56px tall, with extra padding pushing the touch targets up off the home-indicator zone on iOS.

- [ ] **Step 4: Verify**

```bash
cd /Users/angelxlakra/dev/efs-salon/efs-salon-os/frontend && PATH="/Users/angelxlakra/.nvm/versions/node/v22.20.0/bin:$PATH" npx tsc --noEmit 2>&1 | grep -c "error TS"
```

Expected: 162.

```bash
cd /Users/angelxlakra/dev/efs-salon/efs-salon-os/frontend && PATH="/Users/angelxlakra/.nvm/versions/node/v22.20.0/bin:$PATH" npm test -- shell --run 2>&1 | tail -5
```

Expected: shell tests still pass.

- [ ] **Step 5: Commit**

```bash
cd /Users/angelxlakra/dev/efs-salon/efs-salon-os && git add frontend/src/app/\(shell\)/layout.tsx frontend/src/components/shell/bottom-tab-nav.tsx && git commit -m "feat(shell): reserve bottom-nav height + iOS safe-area inset"
```

---

## Workstream E — Wire-up + close (T19–T21)

### Task 19: Move existing routes into `(shell)` group

**Files:**
- Move: `frontend/src/app/dashboard/**` → `frontend/src/app/(shell)/dashboard/**`
- Delete: `frontend/src/app/dashboard/layout.tsx` (V1 layout — superseded by `(shell)/layout.tsx`)
- Modify: any imports inside the moved files that reference layout-relative paths (unlikely; most use `@/` aliases).

**Why:** Activates the new shell for every existing dashboard route. Route groups don't change URLs, so `/dashboard/bills` keeps resolving — just through the new layout. The V1 `dashboard/layout.tsx` is deleted because the new `(shell)/layout.tsx` is now the dashboard route's parent.

> **Critical:** test on a fresh branch. If anything breaks, revert THIS commit and audit imports. The move is mechanical but Next's caching can mask issues — run `rm -rf .next` once before starting.

- [ ] **Step 1: Inventory the existing dashboard tree**

```bash
ls frontend/src/app/dashboard/
```

Expected output (from Phase 0 baseline): `attendance bills cash-drawer customers expenses inventory layout.tsx my-services page.tsx pos purchases reconciliation reports services settings staff users`

- [ ] **Step 2: Move every subdirectory + `page.tsx` into the `(shell)/dashboard/` directory**

```bash
mkdir -p frontend/src/app/\(shell\)/dashboard
git mv frontend/src/app/dashboard/page.tsx frontend/src/app/\(shell\)/dashboard/page.tsx
for d in attendance bills cash-drawer customers expenses inventory my-services pos purchases reconciliation reports services settings staff users; do
  git mv "frontend/src/app/dashboard/$d" "frontend/src/app/(shell)/dashboard/$d"
done
```

- [ ] **Step 3: Delete the V1 layout**

```bash
git rm frontend/src/app/dashboard/layout.tsx
```

- [ ] **Step 4: Confirm `frontend/src/app/dashboard/` is now empty and remove the empty dir**

```bash
ls frontend/src/app/dashboard/ 2>&1
rmdir frontend/src/app/dashboard
```

If `ls` still shows files, find what's left and decide whether to move it.

- [ ] **Step 5: Clear Next cache + re-typecheck**

```bash
rm -rf frontend/.next
cd /Users/angelxlakra/dev/efs-salon/efs-salon-os/frontend && PATH="/Users/angelxlakra/.nvm/versions/node/v22.20.0/bin:$PATH" npx tsc --noEmit 2>&1 | grep -c "error TS"
```

Expected: 162 (or whatever the carrying baseline is — should NOT increase).

- [ ] **Step 6: Boot dev server and click through every section**

```bash
cd /Users/angelxlakra/dev/efs-salon/efs-salon-os/frontend && PATH="/Users/angelxlakra/.nvm/versions/node/v22.20.0/bin:$PATH" npm run dev
```

Open `http://localhost:3000/dashboard` — sidebar visible, breadcrumb shows "Today". Click each sidebar entry; URL stays at `/dashboard/<entity>`, content renders inside the new shell. Open ⌘K — palette appears. Select Customers — navigates correctly. On mobile width (DevTools), the BottomTabNav appears, sidebar hides, More opens the sheet.

If anything 404s, the move missed a file. Audit and re-`git mv`.

- [ ] **Step 7: Stop dev server and commit**

```bash
cd /Users/angelxlakra/dev/efs-salon/efs-salon-os && git add -A && git commit -m "feat(shell): activate (shell) layout for all dashboard routes"
```

---

### Task 20: Final verification (baselines + lint + tests + build)

**Files:** none modified. Verification only.

**Why:** Phase 1 is structurally done after T19. T20 confirms baselines are intact before T21 (changelog) closes the phase.

- [ ] **Step 1: Tests**

```bash
cd /Users/angelxlakra/dev/efs-salon/efs-salon-os/frontend && PATH="/Users/angelxlakra/.nvm/versions/node/v22.20.0/bin:$PATH" npm test -- --run 2>&1 | tail -3
```

Expected: 106 (Phase 0 baseline) + ~30 new Phase 1 tests = ~136 tests, all passing.

- [ ] **Step 2: tsc**

```bash
cd /Users/angelxlakra/dev/efs-salon/efs-salon-os/frontend && PATH="/Users/angelxlakra/.nvm/versions/node/v22.20.0/bin:$PATH" npx tsc --noEmit 2>&1 | grep -c "error TS"
```

Expected: 162 (Phase 0 baseline). Should NOT have grown.

- [ ] **Step 3: Lint**

```bash
cd /Users/angelxlakra/dev/efs-salon/efs-salon-os/frontend && PATH="/Users/angelxlakra/.nvm/versions/node/v22.20.0/bin:$PATH" npm run lint 2>&1 | tail -3
```

Expected: 38 errors (Phase 0 baseline carried), warnings may rise as new shell components add `salon/no-raw-grays` hits — investigate any net-new errors.

The `salon/no-list-owned-detail-state` warning on `bills/page.tsx` should be GONE (T15).

- [ ] **Step 4: Plugin tests**

```bash
cd /Users/angelxlakra/dev/efs-salon/efs-salon-os/frontend/eslint-plugin-salon && for f in tests/*.test.js; do PATH="/Users/angelxlakra/.nvm/versions/node/v22.20.0/bin:$PATH" node "$f" 2>&1 | tail -1; done
```

Expected: all 4 PASS.

- [ ] **Step 5: Storybook builds**

```bash
cd /Users/angelxlakra/dev/efs-salon/efs-salon-os/frontend && PATH="/Users/angelxlakra/.nvm/versions/node/v22.20.0/bin:$PATH" timeout 180 npm run build-storybook 2>&1 | tail -5
```

Expected: success, 13 stories indexed (no Phase 1 stories yet — they belong to a follow-up).

- [ ] **Step 6: Contrast (smoke check, tokens unchanged in Phase 1)**

```bash
cd /Users/angelxlakra/dev/efs-salon/efs-salon-os/frontend && PATH="/Users/angelxlakra/.nvm/versions/node/v22.20.0/bin:$PATH" npm run check:contrast 2>&1 | tail -3
```

Expected: "All contrast checks passed."

- [ ] **Step 7: Manual dev-server walk-through (5 minutes)**

```bash
cd /Users/angelxlakra/dev/efs-salon/efs-salon-os/frontend && PATH="/Users/angelxlakra/.nvm/versions/node/v22.20.0/bin:$PATH" npm run dev
```

Verify in the browser:
- `/dashboard` renders inside the new shell (sidebar + topbar visible).
- Breadcrumb is correct on every route.
- ⌘K opens palette; navigation actions route correctly; toggle theme flips dark/light.
- ⌘\\ collapses sidebar to rail; persists on reload.
- Visit `/dashboard/bills`, click a row → modal opens with bill detail; URL stays at `/dashboard/bills`.
- Open `/dashboard/bills/<id>` directly in a new tab → renders as full page (canonical).
- Resize to 390px width → sidebar hides, BottomTabNav appears at bottom, More opens overflow sheet, content respects `pb-16` so it doesn't slide under the nav.

- [ ] **Step 8: No commit (verification only)**

If any step fails, fix-and-commit per task. If all green, proceed to T21.

---

### Task 21: Phase 1 changelog entry + close

**Files:**
- Modify: `docs/design_system.md` (changelog row)

**Why:** Closes the phase officially. Mirror Phase 0's changelog row format from §13.

- [ ] **Step 1: Append a row to the §13 changelog table**

Find the changelog table in `docs/design_system.md` §13. Add after the most recent row:

```md
| 2026-05-?? | Phase 1 landed: (shell) route group with new SidebarV2 (192px labelled) + SidebarRail (56px collapsed via ⌘\\ + localStorage), real route-derived TopBar + Breadcrumb, ⌘K command palette (cmdk) with navigation/customers/bills/SKUs/actions/recent providers, mobile BottomTabNav + MoreSheet with iOS safe-area inset, @modal parallel slot wired with bills as canonical entity (proof retrofit removed list-owned detail useState). All V1 dashboard routes moved into (shell) group with URLs unchanged. tsc/lint baselines unchanged from Phase 0; new tests added for sidebar/topbar/breadcrumb/palette/bottom-nav. | Angel + Claude |
```

Replace `2026-05-??` with the actual date the task lands.

- [ ] **Step 2: Commit**

```bash
cd /Users/angelxlakra/dev/efs-salon/efs-salon-os && git add docs/design_system.md && git commit -m "docs(design-system): mark Phase 1 complete"
```

---

## Verification checklist (run before Phase 2)

After all tasks commit, on a clean checkout:

- [ ] `cd frontend && npm install` completes without errors
- [ ] `npm run dev` boots the app; ⌘K opens the palette; ⌘\\ collapses the sidebar
- [ ] `npm test -- --run` — all primitive + shell + palette tests pass
- [ ] `npm run lint` — error count unchanged from Phase 0 (38); `no-list-owned-detail-state` no longer fires on `bills/page.tsx`
- [ ] `cd eslint-plugin-salon && for f in tests/*.test.js; do node "$f"; done` — all 4 PASS
- [ ] `npm run build-storybook` — succeeds (no Phase 1 stories yet, but no regressions)
- [ ] `/dashboard/bills` → click row → bill detail modal opens; URL stays at list
- [ ] `/dashboard/bills/<id>` (cold URL) → bill detail full page
- [ ] Mobile (390px viewport) → BottomTabNav visible, sidebar hidden, More sheet works

If any item fails, fix before declaring Phase 1 done.

---

## Next phase

Phase 2 ships the **Appointments** page natively in V2 — calendar/time-grid/staff-swimlane primitive that Attendance and Staff Queue will reuse later. Hardest visual pattern in the app; proves the system under realistic pressure. Brainstorm + spec + plan via `superpowers:writing-plans` once Phase 1 is approved.


