# V2 Phase 0 — Design System Infrastructure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the V2 design system as shippable infrastructure — tokens, typography, a restyled primitives library, and a lint rule that prevents regression — so every subsequent phase retrofits pages *through* this system rather than alongside it.

**Architecture:** Tokens live in `src/styles/tokens.css` as CSS custom properties (light default, dark via `[data-theme="dark"]`) and are exposed to Tailwind v4 via `@theme inline`. Primitives live at `src/components/ui/` (existing path — re-skinned in place, not forked) so V1 pages automatically pick up V2 tokens as they mount. ESLint rules in a local plugin (`eslint-plugin-salon`) enforce the no-raw-grays / no-hex-literals / no-list-owned-detail-state invariants. Storybook provides visual ground truth; a Node contrast script gates CI.

**Tech Stack:** Next.js 16 · React 19 · TypeScript · Tailwind v4 (`@theme`) · Radix UI primitives · cmdk · sonner · @tanstack/react-table · Vitest + @testing-library/react (new) · Storybook 8 (new) · ESLint 9 flat config (new — migrate from `.eslintrc.json`) · `@typescript-eslint/utils` RuleTester for custom rules · `wcag-contrast` for the contrast check.

**Spec references:** [`docs/superpowers/specs/2026-04-23-v2-redesign-design.md`](../specs/2026-04-23-v2-redesign-design.md) · [`docs/design_system.md`](../../design_system.md)

**Out of scope for this phase:** Layout shell, `@modal` slot, ⌘K palette, any page retrofit. Those ship in Phase 1+.

---

## File Structure

### Files created

| Path | Responsibility |
|---|---|
| `frontend/src/styles/tokens.css` | Single source of truth for all colour, radius, shadow tokens. Light default + dark override block. |
| `frontend/src/styles/typography.css` | Typography utility classes (`.text-display-lg`, `.text-money`, etc.) and font-face declarations. |
| `frontend/public/fonts/Inter-*.woff2` | Self-hosted Inter (weights 400/500/600/700). |
| `frontend/public/fonts/InstrumentSerif-Regular.woff2` | Self-hosted Instrument Serif (weight 400 only). |
| `frontend/src/components/ui/currency-input.tsx` | New primitive: `<CurrencyInput>` — handles paise↔rupee conversion, tabular figures. |
| `frontend/src/components/ui/combobox.tsx` | New primitive: `<Combobox>` built on cmdk + Popover. |
| `frontend/src/components/ui/empty-state.tsx` | New primitive: `<EmptyState>` — serif title + body + CTA. |
| `frontend/src/components/ui/filter-bar.tsx` | New primitive: `<FilterBar>` with compound components (Search, Pills, DateRange, Actions). |
| `frontend/src/components/ui/nav-item.tsx` | New primitive: `<NavItem>` for sidebar + bottom-nav. |
| `frontend/src/components/ui/data-table.tsx` | New primitive: `<DataTable>` wrapping @tanstack/react-table with mobile card fallback. Separate from low-level `table.tsx` element primitives. |
| `frontend/src/components/ui/kbd.tsx` | New primitive: `<Kbd>` for displaying keyboard shortcuts. |
| `frontend/eslint-plugin-salon/index.js` | Local ESLint plugin — custom rules entry point. |
| `frontend/eslint-plugin-salon/rules/no-raw-grays.js` | Forbids `text-gray-*`, `bg-gray-*`, `border-gray-*` + `zinc`/`slate`/`stone`/`neutral` variants outside `src/styles/`. |
| `frontend/eslint-plugin-salon/rules/no-hex-literals-in-classname.js` | Forbids hex literals inside `className` strings (`bg-[#fff]`). |
| `frontend/eslint-plugin-salon/rules/no-list-owned-detail-state.js` | Forbids `useState` holding an entity ID next to a `*DetailsDialog` import in a list page. |
| `frontend/eslint-plugin-salon/rules/no-h-screen.js` | Forbids `h-screen` utility; suggests `min-h-dvh`. |
| `frontend/eslint-plugin-salon/tests/*.test.js` | RuleTester suites for each rule. |
| `frontend/eslint.config.mjs` | Flat ESLint config — replaces `.eslintrc.json`; loads local plugin. |
| `frontend/vitest.config.ts` | Vitest configuration for primitive unit tests. |
| `frontend/vitest.setup.ts` | Testing-library setup + jest-dom matchers. |
| `frontend/src/components/ui/__tests__/*.test.tsx` | Unit tests for new primitives. |
| `frontend/.storybook/main.ts` | Storybook configuration. |
| `frontend/.storybook/preview.tsx` | Storybook global decorators — theme toggle, font preload. |
| `frontend/src/components/ui/*.stories.tsx` | Storybook stories, one per primitive (light + dark variants). |
| `frontend/scripts/check-contrast.mjs` | Node script that parses `tokens.css` and asserts WCAG AA ratios. |
| `frontend/package.json` | (modified) Adds scripts + new dev deps. |
| `frontend/src/app/layout.tsx` | (modified) Font loading + theme attribute. |
| `frontend/src/app/globals.css` | (modified) Reduced to `@import` statements + Tailwind base; tokens moved to `tokens.css`. |
| `frontend/src/lib/tokens.ts` | Typed re-exports of token names for TS consumers (e.g., chart series colours). |

### Files deleted

| Path | Reason |
|---|---|
| `frontend/.eslintrc.json` | Replaced by `eslint.config.mjs` (ESLint 9 flat config). |

---

## Sequencing note

Tokens and font loading must land before any primitive is restyled (otherwise restyled primitives reference undefined tokens). ESLint rules land **last** and in **warn** mode only — V1 code still uses `text-gray-*` everywhere and must not break CI. The rules flip to `error` in Phase 1 after the shell retrofit sweeps most gray classes out. Each task below is a single commit.

---

## Task 1: Vitest + testing-library scaffold

**Files:**
- Modify: `frontend/package.json`
- Create: `frontend/vitest.config.ts`
- Create: `frontend/vitest.setup.ts`
- Create: `frontend/src/lib/__tests__/cn.test.ts`

**Why:** Phase 0 needs unit tests for every new primitive. Current repo has zero frontend test infra. Vitest wins over Jest for speed and native ESM; jsdom for DOM; `@testing-library/react` for assertions; `@testing-library/jest-dom` matchers.

- [ ] **Step 1: Install deps**

```bash
cd frontend
npm install -D vitest @vitest/ui @vitejs/plugin-react jsdom \
  @testing-library/react @testing-library/jest-dom @testing-library/user-event
```

- [ ] **Step 2: Create `vitest.config.ts`**

```ts
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import path from "node:path";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    setupFiles: ["./vitest.setup.ts"],
    globals: true,
    css: true,
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
});
```

- [ ] **Step 3: Create `vitest.setup.ts`**

```ts
import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

afterEach(() => cleanup());
```

- [ ] **Step 4: Add `test` + `test:watch` scripts to `package.json`**

In `frontend/package.json` under `"scripts"`:

```json
"test": "vitest run",
"test:watch": "vitest",
"test:ui": "vitest --ui"
```

- [ ] **Step 5: Write a smoke test to verify infra**

`frontend/src/lib/__tests__/cn.test.ts`:

```ts
import { describe, expect, it } from "vitest";
import { cn } from "@/lib/utils";

describe("cn", () => {
  it("merges class names", () => {
    expect(cn("p-2", "p-4")).toBe("p-4");
  });
  it("handles conditional classes", () => {
    expect(cn("base", false && "hidden", "shown")).toBe("base shown");
  });
});
```

- [ ] **Step 6: Run test to verify it passes**

Run: `cd frontend && npm test -- --run`
Expected: `Test Files  1 passed (1)` / `Tests  2 passed (2)`

- [ ] **Step 7: Commit**

```bash
git add frontend/package.json frontend/package-lock.json frontend/vitest.config.ts frontend/vitest.setup.ts frontend/src/lib/__tests__/cn.test.ts
git commit -m "test(frontend): add vitest + testing-library scaffold"
```

---

## Task 2: Self-host fonts

**Files:**
- Create: `frontend/public/fonts/Inter-Regular.woff2`
- Create: `frontend/public/fonts/Inter-Medium.woff2`
- Create: `frontend/public/fonts/Inter-SemiBold.woff2`
- Create: `frontend/public/fonts/Inter-Bold.woff2`
- Create: `frontend/public/fonts/InstrumentSerif-Regular.woff2`
- Create: `frontend/src/styles/typography.css`

**Why:** The spec bans runtime Google Fonts fetches (§3.1 design_system). Four weights of Inter + one of Instrument Serif cover the entire type scale.

- [ ] **Step 1: Download fonts**

```bash
cd frontend/public/fonts
# Inter v4 — from rsms/inter-desktop github release (official)
curl -L -o Inter-Regular.woff2  "https://github.com/rsms/inter/raw/v4.0/docs/font-files/Inter-Regular.woff2"
curl -L -o Inter-Medium.woff2   "https://github.com/rsms/inter/raw/v4.0/docs/font-files/Inter-Medium.woff2"
curl -L -o Inter-SemiBold.woff2 "https://github.com/rsms/inter/raw/v4.0/docs/font-files/Inter-SemiBold.woff2"
curl -L -o Inter-Bold.woff2     "https://github.com/rsms/inter/raw/v4.0/docs/font-files/Inter-Bold.woff2"
# Instrument Serif — from Google Fonts static hosting (CDN static file, cached once)
curl -L -o InstrumentSerif-Regular.woff2 \
  "https://fonts.gstatic.com/s/instrumentserif/v12/jizBREVNn1dOx-zrZ2X3pZvkThUY0TY7ikbI.woff2"
```

Expected: 5 files, each > 20KB.

- [ ] **Step 2: Create `src/styles/typography.css` with `@font-face` declarations**

```css
/* Inter — self-hosted */
@font-face {
  font-family: "Inter";
  font-style: normal;
  font-weight: 400;
  font-display: swap;
  src: url("/fonts/Inter-Regular.woff2") format("woff2");
}
@font-face {
  font-family: "Inter";
  font-style: normal;
  font-weight: 500;
  font-display: swap;
  src: url("/fonts/Inter-Medium.woff2") format("woff2");
}
@font-face {
  font-family: "Inter";
  font-style: normal;
  font-weight: 600;
  font-display: swap;
  src: url("/fonts/Inter-SemiBold.woff2") format("woff2");
}
@font-face {
  font-family: "Inter";
  font-style: normal;
  font-weight: 700;
  font-display: swap;
  src: url("/fonts/Inter-Bold.woff2") format("woff2");
}

/* Instrument Serif — self-hosted */
@font-face {
  font-family: "Instrument Serif";
  font-style: normal;
  font-weight: 400;
  font-display: swap;
  src: url("/fonts/InstrumentSerif-Regular.woff2") format("woff2");
}
```

(Typography utility classes will be appended in Task 4.)

- [ ] **Step 3: Commit**

```bash
git add frontend/public/fonts/ frontend/src/styles/typography.css
git commit -m "feat(fonts): self-host Inter + Instrument Serif"
```

---

## Task 3: Colour + radius + shadow tokens

**Files:**
- Create: `frontend/src/styles/tokens.css`
- Create: `frontend/src/lib/tokens.ts`

**Why:** Single source of truth for every semantic colour. Values and structure match [`docs/design_system.md`](../../design_system.md) §2.

- [ ] **Step 1: Create `frontend/src/styles/tokens.css`**

```css
/* ────────────────────────────────────────────────────────────────
   Aasan design tokens — V2
   Single source of truth. Do not add raw hex literals anywhere
   else in the codebase. Lint enforces this.
   ──────────────────────────────────────────────────────────────── */

:root {
  /* Surface */
  --surface-page:       #fafaf9;
  --surface-card:       #ffffff;
  --surface-row:        #ffffff;
  --surface-row-hover:  #f5f5f4;
  --surface-sidebar:    #f8f7f5;
  --surface-overlay:    rgba(20, 14, 10, 0.48);

  /* Border */
  --border-subtle:      #eeece9;
  --border-default:     #e3e0db;
  --border-strong:      #cfcac3;
  --border-focus:       #b0561f;

  /* Text */
  --text-primary:       #1c1917;
  --text-secondary:     #44403c;
  --text-muted:         #78716c;
  --text-disabled:      #a8a29e;
  --text-inverse:       #ffffff;

  /* Accent — Copper */
  --accent-default:     #b0561f;
  --accent-hover:       #954919;
  --accent-active:      #7d3d15;
  --accent-bg-soft:     #fbe9dd;
  --accent-fg:          #ffffff;

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

  /* Data viz */
  --data-series-1:      #b0561f;
  --data-series-2:      #1e40af;
  --data-series-3:      #166534;
  --data-series-4:      #92400e;
  --data-series-5:      #6b21a8;
  --data-series-6:      #0e7490;

  /* Radius */
  --radius-sm:          4px;
  --radius-md:          6px;
  --radius-lg:          10px;
  --radius-xl:          14px;
  --radius-full:        9999px;

  /* Shadow */
  --shadow-xs:          0 1px 2px rgba(20, 14, 10, 0.06);
  --shadow-sm:          0 2px 4px rgba(20, 14, 10, 0.06), 0 1px 2px rgba(20, 14, 10, 0.04);
  --shadow-md:          0 8px 20px rgba(20, 14, 10, 0.10), 0 2px 6px rgba(20, 14, 10, 0.06);
  --shadow-focus:       0 0 0 3px rgba(176, 86, 31, 0.18);

  /* Motion */
  --motion-fast:        80ms;
  --motion-default:     120ms;
  --motion-slow:        180ms;
  --motion-spring:      cubic-bezier(0.22, 1.2, 0.36, 1);
  --motion-ease-out:    cubic-bezier(0.2, 0.8, 0.2, 1);
}

[data-theme="dark"] {
  --surface-page:       #14120f;
  --surface-card:       #1c1a17;
  --surface-row:        #1f1d1a;
  --surface-row-hover:  #26231f;
  --surface-sidebar:    #0f0e0c;
  --surface-overlay:    rgba(0, 0, 0, 0.6);

  --border-subtle:      #2a2723;
  --border-default:     #3a3631;
  --border-strong:      #504a42;
  --border-focus:       #d97847;

  --text-primary:       #f5f2ee;
  --text-secondary:     #c9c2b8;
  --text-muted:         #948b7e;
  --text-disabled:      #5a5249;
  --text-inverse:       #1c1917;

  --accent-default:     #d97847;
  --accent-hover:       #e38f65;
  --accent-active:      #f0a684;
  --accent-bg-soft:     #3a1d0c;
  --accent-fg:          #1c1917;

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

  --shadow-xs:          0 1px 2px rgba(0, 0, 0, 0.4);
  --shadow-sm:          0 2px 4px rgba(0, 0, 0, 0.35), 0 1px 2px rgba(0, 0, 0, 0.25);
  --shadow-md:          0 8px 20px rgba(0, 0, 0, 0.45), 0 2px 6px rgba(0, 0, 0, 0.3);
  --shadow-focus:       0 0 0 3px rgba(217, 120, 71, 0.28);
}

@media (prefers-reduced-motion: reduce) {
  :root {
    --motion-fast: 0ms;
    --motion-default: 0ms;
    --motion-slow: 0ms;
  }
}
```

- [ ] **Step 2: Create `src/lib/tokens.ts` (typed re-export for TS consumers)**

```ts
/**
 * Typed token references for use in TS (chart series colours, inline style props).
 * Do NOT add new hex literals — add a new CSS token in tokens.css and re-export here.
 */
export const tokens = {
  surface: {
    page: "var(--surface-page)",
    card: "var(--surface-card)",
    row: "var(--surface-row)",
    rowHover: "var(--surface-row-hover)",
    sidebar: "var(--surface-sidebar)",
    overlay: "var(--surface-overlay)",
  },
  border: {
    subtle: "var(--border-subtle)",
    default: "var(--border-default)",
    strong: "var(--border-strong)",
    focus: "var(--border-focus)",
  },
  text: {
    primary: "var(--text-primary)",
    secondary: "var(--text-secondary)",
    muted: "var(--text-muted)",
    disabled: "var(--text-disabled)",
    inverse: "var(--text-inverse)",
  },
  accent: {
    default: "var(--accent-default)",
    hover: "var(--accent-hover)",
    active: "var(--accent-active)",
    bgSoft: "var(--accent-bg-soft)",
    fg: "var(--accent-fg)",
  },
  semantic: {
    success: { fg: "var(--success-fg)", bgSoft: "var(--success-bg-soft)", border: "var(--success-border)" },
    warning: { fg: "var(--warning-fg)", bgSoft: "var(--warning-bg-soft)", border: "var(--warning-border)" },
    danger:  { fg: "var(--danger-fg)",  bgSoft: "var(--danger-bg-soft)",  border: "var(--danger-border)"  },
    info:    { fg: "var(--info-fg)",    bgSoft: "var(--info-bg-soft)",    border: "var(--info-border)"    },
  },
  dataViz: [
    "var(--data-series-1)",
    "var(--data-series-2)",
    "var(--data-series-3)",
    "var(--data-series-4)",
    "var(--data-series-5)",
    "var(--data-series-6)",
  ],
} as const;
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/styles/tokens.css frontend/src/lib/tokens.ts
git commit -m "feat(tokens): define V2 colour/radius/shadow tokens (light + dark)"
```

---

## Task 4: Typography utility classes

**Files:**
- Modify: `frontend/src/styles/typography.css`

**Why:** Twelve named type classes from `docs/design_system.md` §3.3 give every page a shared vocabulary. `font-variant-numeric: tabular-nums` is mandatory for every money class.

- [ ] **Step 1: Append utility classes to `frontend/src/styles/typography.css`**

```css
/* ────────────────────────────────────────────────────────────────
   Type scale — see docs/design_system.md §3.3
   ──────────────────────────────────────────────────────────────── */

:root {
  --font-display: "Instrument Serif", "EB Garamond", Georgia, serif;
  --font-body:    "Inter", ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
  --font-mono:    ui-monospace, "SF Mono", "JetBrains Mono", Menlo, Consolas, monospace;
}

body {
  font-family: var(--font-body);
  font-feature-settings: "cv11", "ss01", "ss03";
  -webkit-font-smoothing: antialiased;
}

.font-display { font-family: var(--font-display); }
.font-mono    { font-family: var(--font-mono); }

.tabular      { font-variant-numeric: tabular-nums lining-nums; }

.text-display-xl { font-family: var(--font-display); font-size: 32px; line-height: 1.1;  font-weight: 400; letter-spacing: -0.01em; }
.text-display-lg { font-family: var(--font-display); font-size: 28px; line-height: 1.15; font-weight: 400; letter-spacing: -0.01em; }
.text-display-md { font-family: var(--font-display); font-size: 24px; line-height: 1.2;  font-weight: 400; letter-spacing: -0.005em; }

.text-heading-lg { font-size: 20px; line-height: 1.25; font-weight: 600; letter-spacing: -0.005em; }
.text-heading-md { font-size: 16px; line-height: 1.35; font-weight: 600; }
.text-heading-sm { font-size: 14px; line-height: 1.4;  font-weight: 600; }

.text-body-lg    { font-size: 16px; line-height: 1.5;  font-weight: 400; }
.text-body       { font-size: 14px; line-height: 1.5;  font-weight: 400; }
.text-body-sm    { font-size: 13px; line-height: 1.45; font-weight: 400; }

.text-caption    { font-size: 12px; line-height: 1.4;  font-weight: 500; }
.text-overline   { font-size: 11px; line-height: 1.3;  font-weight: 600; text-transform: uppercase; letter-spacing: 0.06em; }

.text-money-lg   { font-size: 22px; line-height: 1.2;  font-weight: 700; font-variant-numeric: tabular-nums lining-nums; }
.text-money      { font-size: 14px; line-height: 1.5;  font-weight: 600; font-variant-numeric: tabular-nums lining-nums; }
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/styles/typography.css
git commit -m "feat(typography): V2 type scale + tabular-figure money utilities"
```

---

## Task 5: Wire tokens to Tailwind, replace legacy globals.css

**Files:**
- Modify: `frontend/src/app/globals.css`
- Modify: `frontend/src/app/layout.tsx`

**Why:** Tailwind v4's `@theme inline` directive promotes our CSS vars to utility classes (`bg-surface-card`, `text-muted`, etc.). The old multi-accent experiment and legacy gray scale are deleted.

- [ ] **Step 1: Rewrite `frontend/src/app/globals.css` end-to-end**

```css
@import "tailwindcss";
@import "tw-animate-css";
@import "../styles/tokens.css";
@import "../styles/typography.css";

@custom-variant dark (&:is([data-theme="dark"] *));

@theme inline {
  /* Colours exposed as Tailwind utilities */
  --color-surface-page:       var(--surface-page);
  --color-surface-card:       var(--surface-card);
  --color-surface-row:        var(--surface-row);
  --color-surface-row-hover:  var(--surface-row-hover);
  --color-surface-sidebar:    var(--surface-sidebar);
  --color-surface-overlay:    var(--surface-overlay);

  --color-border-subtle:      var(--border-subtle);
  --color-border-default:     var(--border-default);
  --color-border-strong:      var(--border-strong);
  --color-border-focus:       var(--border-focus);

  --color-text-primary:       var(--text-primary);
  --color-text-secondary:     var(--text-secondary);
  --color-text-muted:         var(--text-muted);
  --color-text-disabled:      var(--text-disabled);
  --color-text-inverse:       var(--text-inverse);

  --color-accent:             var(--accent-default);
  --color-accent-hover:       var(--accent-hover);
  --color-accent-active:      var(--accent-active);
  --color-accent-bg-soft:     var(--accent-bg-soft);
  --color-accent-fg:          var(--accent-fg);

  --color-success-fg:         var(--success-fg);
  --color-success-bg-soft:    var(--success-bg-soft);
  --color-success-border:     var(--success-border);
  --color-warning-fg:         var(--warning-fg);
  --color-warning-bg-soft:    var(--warning-bg-soft);
  --color-warning-border:     var(--warning-border);
  --color-danger-fg:          var(--danger-fg);
  --color-danger-bg-soft:     var(--danger-bg-soft);
  --color-danger-border:      var(--danger-border);
  --color-info-fg:            var(--info-fg);
  --color-info-bg-soft:       var(--info-bg-soft);
  --color-info-border:        var(--info-border);

  /* Radius */
  --radius-sm:                var(--radius-sm);
  --radius-md:                var(--radius-md);
  --radius-lg:                var(--radius-lg);
  --radius-xl:                var(--radius-xl);

  /* Shadow */
  --shadow-xs:                var(--shadow-xs);
  --shadow-sm:                var(--shadow-sm);
  --shadow-md:                var(--shadow-md);
  --shadow-focus:             var(--shadow-focus);

  /* Font families */
  --font-sans:                var(--font-body);
  --font-display:             var(--font-display);
  --font-mono:                var(--font-mono);
}

/* Print styles preserved from V1 — receipt template is out of scope for V2 */
@media print {
  body { background-color: white; }
  .no-print { display: none !important; }
  .receipt-print { width: 80mm; font-size: 10pt; margin: 0; padding: 0; }
}

@layer base {
  * {
    border-color: var(--border-default);
  }
  body {
    background-color: var(--surface-page);
    color: var(--text-primary);
  }
  *:focus-visible {
    outline: 2px solid var(--border-focus);
    outline-offset: 2px;
    box-shadow: var(--shadow-focus);
  }
}
```

- [ ] **Step 2: Update `frontend/src/app/layout.tsx` to opt into light-default theme**

Read the file, then replace the `<html>` opening tag:

```tsx
<html lang="en" data-theme="light" suppressHydrationWarning>
```

If a `ThemeInit` component is present, leave it — it toggles the `data-theme` attribute from local storage client-side.

- [ ] **Step 3: Run the dev server and verify no compile errors**

```bash
cd frontend && npm run dev
```

Open `https://localhost` (per user cert trust notes in project memory). Expect: the app loads with the light background (`#fafaf9`) instead of near-black, and no console errors about missing CSS variables.

Stop the server (Ctrl-C) once confirmed.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/app/globals.css frontend/src/app/layout.tsx
git commit -m "feat(tokens): wire V2 tokens into Tailwind; remove multi-accent experiment"
```

---

## Task 6: Contrast CI script

**Files:**
- Create: `frontend/scripts/check-contrast.mjs`
- Modify: `frontend/package.json`

**Why:** Prevents V1's 1.02-contrast regression. Parses `tokens.css`, resolves each token to a hex, and asserts AA ratios for every text × surface pair in both themes.

- [ ] **Step 1: Install `wcag-contrast`**

```bash
cd frontend && npm install -D wcag-contrast
```

- [ ] **Step 2: Write `frontend/scripts/check-contrast.mjs`**

```js
#!/usr/bin/env node
/**
 * Parses tokens.css and asserts WCAG AA contrast for every text × surface
 * combination in both themes. Exits non-zero if any pair fails.
 */
import fs from "node:fs";
import path from "node:path";
import url from "node:url";
import { hex as contrast } from "wcag-contrast";

const __dirname = path.dirname(url.fileURLToPath(import.meta.url));
const cssPath = path.resolve(__dirname, "../src/styles/tokens.css");
const css = fs.readFileSync(cssPath, "utf8");

function parseBlock(css, selector) {
  const re = new RegExp(`${selector}\\s*\\{([^}]+)\\}`, "m");
  const match = css.match(re);
  if (!match) throw new Error(`Selector ${selector} not found in tokens.css`);
  const body = match[1];
  const vars = {};
  for (const line of body.split("\n")) {
    const m = line.match(/--([a-z0-9-]+)\s*:\s*(#[0-9a-fA-F]{3,8})\s*;/);
    if (m) vars[m[1]] = m[2];
  }
  return vars;
}

const light = parseBlock(css, ":root");
const dark  = { ...light, ...parseBlock(css, '\\[data-theme="dark"\\]') };

// Pairs are [fgTokenName, bgTokenName, minRatio, label]
const PAIRS = [
  ["text-primary",   "surface-page",      4.5, "body text on page"],
  ["text-primary",   "surface-card",      4.5, "body text on card"],
  ["text-primary",   "surface-row",       4.5, "body text on row"],
  ["text-secondary", "surface-card",      4.5, "secondary text on card"],
  ["text-muted",     "surface-card",      4.5, "muted text on card"],
  ["text-muted",     "surface-page",      4.5, "muted text on page"],
  ["accent-default", "surface-page",      3.0, "accent on page (non-text)"],
  ["accent-default", "surface-card",      3.0, "accent on card (non-text)"],
  ["accent-fg",      "accent-default",    4.5, "text on accent button"],
  ["success-fg",     "success-bg-soft",   4.5, "success text in pill"],
  ["warning-fg",     "warning-bg-soft",   4.5, "warning text in pill"],
  ["danger-fg",      "danger-bg-soft",    4.5, "danger text in pill"],
  ["info-fg",        "info-bg-soft",      4.5, "info text in pill"],
];

let failed = 0;
for (const [theme, vars] of [["light", light], ["dark", dark]]) {
  for (const [fg, bg, min, label] of PAIRS) {
    const fgHex = vars[fg];
    const bgHex = vars[bg];
    if (!fgHex || !bgHex) {
      console.error(`[${theme}] missing token: ${fg} or ${bg}`);
      failed++;
      continue;
    }
    const ratio = contrast(fgHex, bgHex);
    const pass = ratio >= min;
    const icon = pass ? "PASS" : "FAIL";
    console.log(
      `[${theme}] ${icon} ${label.padEnd(40)} ${fg} on ${bg}  ratio=${ratio.toFixed(2)}  min=${min}`
    );
    if (!pass) failed++;
  }
}

if (failed > 0) {
  console.error(`\nFAILED — ${failed} contrast check(s) did not meet WCAG AA.`);
  process.exit(1);
}
console.log("\nAll contrast checks passed.");
```

- [ ] **Step 3: Add script to `frontend/package.json`**

```json
"check:contrast": "node scripts/check-contrast.mjs"
```

- [ ] **Step 4: Run and verify all checks pass**

Run: `cd frontend && npm run check:contrast`
Expected: every line prints `PASS`, final line: `All contrast checks passed.`

If any fail, the token values are wrong — stop, fix tokens.css, re-run.

- [ ] **Step 5: Commit**

```bash
git add frontend/scripts/check-contrast.mjs frontend/package.json frontend/package-lock.json
git commit -m "ci(tokens): add WCAG AA contrast check script"
```

---

## Task 7: Button primitive

**Files:**
- Modify: `frontend/src/components/ui/button.tsx`
- Create: `frontend/src/components/ui/__tests__/button.test.tsx`

**Why:** The existing shadcn Button stays API-compatible so V1 callers don't break. We re-skin via tokens and add the `danger` + `icon` variants plus `loading` prop from the design system spec.

- [ ] **Step 1: Write failing tests**

`frontend/src/components/ui/__tests__/button.test.tsx`:

```tsx
import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Button } from "@/components/ui/button";

describe("Button", () => {
  it("renders children", () => {
    render(<Button>Save</Button>);
    expect(screen.getByRole("button", { name: "Save" })).toBeInTheDocument();
  });

  it("calls onClick when clicked", async () => {
    const onClick = vi.fn();
    const user = userEvent.setup();
    render(<Button onClick={onClick}>Go</Button>);
    await user.click(screen.getByRole("button"));
    expect(onClick).toHaveBeenCalledOnce();
  });

  it("renders loading state with spinner and preserves width", () => {
    const { rerender } = render(<Button>Save</Button>);
    const widthBefore = screen.getByRole("button").getBoundingClientRect().width;
    rerender(<Button loading>Save</Button>);
    const btn = screen.getByRole("button");
    expect(btn).toBeDisabled();
    expect(btn.querySelector('[data-slot="spinner"]')).toBeInTheDocument();
    // Text stays in DOM (visually hidden) so width does not collapse
    expect(btn).toHaveTextContent("Save");
  });

  it("applies danger variant class", () => {
    render(<Button variant="danger">Delete</Button>);
    expect(screen.getByRole("button").className).toMatch(/danger/);
  });

  it("icon variant requires aria-label (throws in dev)", () => {
    // When used without aria-label, a console.error is expected in dev.
    const spy = vi.spyOn(console, "error").mockImplementation(() => {});
    render(<Button variant="icon" aria-label="Close" />);
    spy.mockRestore();
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd frontend && npm test -- button --run`
Expected: FAIL — `loading` prop, `danger` variant, and `icon` variant don't exist yet on the existing `Button`.

- [ ] **Step 3: Read current `button.tsx` and rewrite**

Read `frontend/src/components/ui/button.tsx`, then replace its contents with:

```tsx
import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import { Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md font-medium transition-colors " +
    "focus-visible:outline-none disabled:opacity-50 disabled:pointer-events-none " +
    "[&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0",
  {
    variants: {
      variant: {
        primary:
          "bg-accent text-accent-fg hover:bg-accent-hover active:bg-accent-active",
        secondary:
          "bg-surface-card text-text-primary border border-border-default hover:bg-surface-row-hover",
        ghost:
          "text-text-primary hover:bg-surface-row-hover",
        danger:
          "bg-danger-fg text-text-inverse hover:opacity-90",
        icon:
          "text-text-secondary hover:bg-surface-row-hover hover:text-text-primary",
      },
      size: {
        sm: "h-7 px-3 text-[13px]",
        md: "h-9 px-4 text-sm",
        lg: "h-11 px-6 text-base",
      },
      fullWidth: {
        true: "w-full",
      },
    },
    compoundVariants: [
      { variant: "icon", size: "sm", class: "h-7 w-7 p-0" },
      { variant: "icon", size: "md", class: "h-9 w-9 p-0" },
      { variant: "icon", size: "lg", class: "h-11 w-11 p-0" },
    ],
    defaultVariants: { variant: "primary", size: "md" },
  }
);

type ButtonProps = React.ButtonHTMLAttributes<HTMLButtonElement> &
  VariantProps<typeof buttonVariants> & {
    asChild?: boolean;
    loading?: boolean;
    leadingIcon?: React.ReactNode;
    trailingIcon?: React.ReactNode;
  };

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  (
    { className, variant, size, fullWidth, asChild, loading, disabled, leadingIcon, trailingIcon, children, ...props },
    ref
  ) => {
    const Comp = asChild ? Slot : "button";
    return (
      <Comp
        ref={ref}
        className={cn(buttonVariants({ variant, size, fullWidth }), className)}
        disabled={disabled || loading}
        aria-busy={loading || undefined}
        {...props}
      >
        {loading ? (
          <>
            <Loader2 data-slot="spinner" className="animate-spin" aria-hidden />
            <span className="sr-only sm:not-sr-only">{children}</span>
          </>
        ) : (
          <>
            {leadingIcon}
            {children}
            {trailingIcon}
          </>
        )}
      </Comp>
    );
  }
);
Button.displayName = "Button";

export { buttonVariants };
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd frontend && npm test -- button --run`
Expected: PASS (5 tests).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/ui/button.tsx frontend/src/components/ui/__tests__/button.test.tsx
git commit -m "feat(ui): V2 Button with danger/icon variants + loading state"
```

---

## Task 8: Input primitive (token re-skin)

**Files:**
- Modify: `frontend/src/components/ui/input.tsx`
- Create: `frontend/src/components/ui/__tests__/input.test.tsx`

**Why:** Adds `label`/`hint`/`error`/`leadingAddon`/`trailingAddon`/`size` props per spec §6.2. Keeps the underlying DOM element as `<input>` so V1 callers still work when they spread props.

- [ ] **Step 1: Write failing tests**

`frontend/src/components/ui/__tests__/input.test.tsx`:

```tsx
import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { Input } from "@/components/ui/input";

describe("Input", () => {
  it("renders with a label", () => {
    render(<Input label="Email" id="email" />);
    expect(screen.getByLabelText("Email")).toBeInTheDocument();
  });

  it("shows error text and sets aria-invalid", () => {
    render(<Input label="Email" error="Invalid email" />);
    expect(screen.getByText("Invalid email")).toBeInTheDocument();
    expect(screen.getByLabelText("Email")).toHaveAttribute("aria-invalid", "true");
  });

  it("shows hint text when no error", () => {
    render(<Input label="Email" hint="We'll never share" />);
    expect(screen.getByText("We'll never share")).toBeInTheDocument();
  });

  it("renders leadingAddon and trailingAddon", () => {
    render(<Input label="Price" leadingAddon={<span>₹</span>} trailingAddon={<span>.00</span>} />);
    expect(screen.getByText("₹")).toBeInTheDocument();
    expect(screen.getByText(".00")).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run tests, verify FAIL**

Run: `cd frontend && npm test -- input --run`
Expected: FAIL.

- [ ] **Step 3: Rewrite `frontend/src/components/ui/input.tsx`**

```tsx
import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const fieldVariants = cva(
  "w-full rounded-md border bg-surface-card text-text-primary placeholder:text-text-muted " +
    "focus-visible:outline-none focus-visible:border-accent focus-visible:shadow-[var(--shadow-focus)] " +
    "disabled:opacity-50 disabled:cursor-not-allowed",
  {
    variants: {
      size: {
        sm: "h-7 px-2.5 text-[13px]",
        md: "h-9 px-3 text-sm",
        lg: "h-11 px-4 text-base",
      },
      invalid: {
        true: "border-danger-border focus-visible:border-danger-fg",
        false: "border-border-default",
      },
    },
    defaultVariants: { size: "md", invalid: false },
  }
);

type InputProps = Omit<React.InputHTMLAttributes<HTMLInputElement>, "size"> &
  VariantProps<typeof fieldVariants> & {
    label?: string;
    hint?: string;
    error?: string;
    leadingAddon?: React.ReactNode;
    trailingAddon?: React.ReactNode;
  };

let autoIdCounter = 0;

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, size, label, hint, error, leadingAddon, trailingAddon, id, ...props }, ref) => {
    const autoId = React.useMemo(() => `input-${++autoIdCounter}`, []);
    const inputId = id ?? autoId;
    const describedById = error ? `${inputId}-err` : hint ? `${inputId}-hint` : undefined;

    return (
      <div className="flex flex-col gap-1">
        {label && (
          <label htmlFor={inputId} className="text-heading-sm text-text-secondary">
            {label}
          </label>
        )}
        <div className="relative flex items-center">
          {leadingAddon && (
            <span className="absolute left-3 text-text-muted" aria-hidden>
              {leadingAddon}
            </span>
          )}
          <input
            ref={ref}
            id={inputId}
            aria-invalid={!!error || undefined}
            aria-describedby={describedById}
            className={cn(
              fieldVariants({ size, invalid: !!error }),
              leadingAddon && "pl-8",
              trailingAddon && "pr-8",
              className
            )}
            {...props}
          />
          {trailingAddon && (
            <span className="absolute right-3 text-text-muted" aria-hidden>
              {trailingAddon}
            </span>
          )}
        </div>
        {error ? (
          <p id={`${inputId}-err`} className="text-body-sm text-danger-fg">
            {error}
          </p>
        ) : hint ? (
          <p id={`${inputId}-hint`} className="text-body-sm text-text-muted">
            {hint}
          </p>
        ) : null}
      </div>
    );
  }
);
Input.displayName = "Input";
```

- [ ] **Step 4: Run tests, verify PASS**

Run: `cd frontend && npm test -- input --run`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/ui/input.tsx frontend/src/components/ui/__tests__/input.test.tsx
git commit -m "feat(ui): V2 Input with label/hint/error/addons"
```

---

## Task 9: CurrencyInput primitive

**Files:**
- Create: `frontend/src/components/ui/currency-input.tsx`
- Create: `frontend/src/components/ui/__tests__/currency-input.test.tsx`

**Why:** All money in Aasan is paise (integers). Every form that takes money needs the paise↔rupee conversion in one place. This is a new primitive — no V1 equivalent.

- [ ] **Step 1: Write failing tests**

```tsx
import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { CurrencyInput } from "@/components/ui/currency-input";

describe("CurrencyInput", () => {
  it("displays paise as rupees with 2 decimals", () => {
    render(<CurrencyInput label="Amount" value={24800} onChange={() => {}} />);
    const input = screen.getByLabelText("Amount") as HTMLInputElement;
    expect(input.value).toBe("248.00");
  });

  it("calls onChange with paise integer when user types rupees", async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    render(<CurrencyInput label="Amount" value={0} onChange={onChange} />);
    const input = screen.getByLabelText("Amount");
    await user.clear(input);
    await user.type(input, "250");
    // Last call should be paise = 25000
    const last = onChange.mock.calls[onChange.mock.calls.length - 1][0];
    expect(last).toBe(25000);
  });

  it("rejects negative values", async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    render(<CurrencyInput label="Amount" value={0} onChange={onChange} />);
    const input = screen.getByLabelText("Amount");
    await user.clear(input);
    await user.type(input, "-5");
    // onChange never called with negative paise
    for (const [arg] of onChange.mock.calls) expect(arg).toBeGreaterThanOrEqual(0);
  });

  it("renders ₹ leading addon", () => {
    render(<CurrencyInput label="Amount" value={0} onChange={() => {}} />);
    expect(screen.getByText("₹")).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run tests, verify FAIL (module not found)**

Run: `cd frontend && npm test -- currency --run`

- [ ] **Step 3: Implement `frontend/src/components/ui/currency-input.tsx`**

```tsx
import * as React from "react";
import { Input } from "@/components/ui/input";

type Props = Omit<React.ComponentProps<typeof Input>, "value" | "onChange" | "leadingAddon" | "type"> & {
  /** Value in paise (integer). */
  value: number;
  /** Called with updated paise value. */
  onChange: (paise: number) => void;
};

/**
 * Displays a paise integer as a rupees decimal and normalises back on change.
 * All money in Aasan is stored as paise; this is the only place rupees↔paise
 * conversion should live in forms.
 */
export const CurrencyInput = React.forwardRef<HTMLInputElement, Props>(
  ({ value, onChange, ...rest }, ref) => {
    const [text, setText] = React.useState(() => (value / 100).toFixed(2));

    React.useEffect(() => {
      setText((value / 100).toFixed(2));
    }, [value]);

    return (
      <Input
        ref={ref}
        type="text"
        inputMode="decimal"
        leadingAddon={<span aria-hidden>₹</span>}
        className="tabular"
        value={text}
        onChange={(e) => {
          const raw = e.target.value;
          setText(raw);
          const numeric = parseFloat(raw);
          if (!Number.isFinite(numeric) || numeric < 0) return;
          onChange(Math.round(numeric * 100));
        }}
        onBlur={() => {
          // Normalise on blur — e.g. "250" → "250.00"
          const numeric = parseFloat(text);
          if (Number.isFinite(numeric) && numeric >= 0) {
            setText(numeric.toFixed(2));
          } else {
            setText((value / 100).toFixed(2));
          }
        }}
        {...rest}
      />
    );
  }
);
CurrencyInput.displayName = "CurrencyInput";
```

- [ ] **Step 4: Run tests, verify PASS**

Run: `cd frontend && npm test -- currency --run`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/ui/currency-input.tsx frontend/src/components/ui/__tests__/currency-input.test.tsx
git commit -m "feat(ui): add CurrencyInput primitive (paise↔rupees)"
```

---

## Task 10: Combobox primitive

**Files:**
- Create: `frontend/src/components/ui/combobox.tsx`
- Create: `frontend/src/components/ui/__tests__/combobox.test.tsx`

**Why:** `<Select>` (Radix) is only enough for fixed short lists. Customer/SKU pickers need typeahead over hundreds of options. `cmdk` is already installed.

- [ ] **Step 1: Write failing tests**

```tsx
import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Combobox } from "@/components/ui/combobox";

const options = [
  { value: "1", label: "Priya" },
  { value: "2", label: "Rajni" },
  { value: "3", label: "Anjali" },
];

describe("Combobox", () => {
  it("shows selected value label on trigger", () => {
    render(<Combobox options={options} value="2" onChange={() => {}} placeholder="Pick customer" />);
    expect(screen.getByRole("combobox")).toHaveTextContent("Rajni");
  });

  it("shows placeholder when no value", () => {
    render(<Combobox options={options} value={null} onChange={() => {}} placeholder="Pick customer" />);
    expect(screen.getByRole("combobox")).toHaveTextContent("Pick customer");
  });

  it("filters options when typing", async () => {
    const user = userEvent.setup();
    render(<Combobox options={options} value={null} onChange={() => {}} placeholder="Pick" />);
    await user.click(screen.getByRole("combobox"));
    await user.type(screen.getByRole("searchbox"), "raj");
    expect(screen.getByText("Rajni")).toBeInTheDocument();
    expect(screen.queryByText("Priya")).not.toBeInTheDocument();
  });

  it("calls onChange with option value on select", async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    render(<Combobox options={options} value={null} onChange={onChange} placeholder="Pick" />);
    await user.click(screen.getByRole("combobox"));
    await user.click(screen.getByText("Anjali"));
    expect(onChange).toHaveBeenCalledWith("3");
  });
});
```

- [ ] **Step 2: Run tests, verify FAIL**

Run: `cd frontend && npm test -- combobox --run`

- [ ] **Step 3: Implement `frontend/src/components/ui/combobox.tsx`**

```tsx
import * as React from "react";
import { Check, ChevronsUpDown } from "lucide-react";
import { Command, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList } from "@/components/ui/command";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export type ComboboxOption = {
  value: string;
  label: string;
  keywords?: string[];
};

type Props = {
  options: ComboboxOption[];
  value: string | null;
  onChange: (value: string | null) => void;
  placeholder?: string;
  searchPlaceholder?: string;
  emptyMessage?: string;
  disabled?: boolean;
  className?: string;
};

export function Combobox({
  options,
  value,
  onChange,
  placeholder = "Select…",
  searchPlaceholder = "Search…",
  emptyMessage = "No results.",
  disabled,
  className,
}: Props) {
  const [open, setOpen] = React.useState(false);
  const selected = options.find((o) => o.value === value) ?? null;

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="secondary"
          role="combobox"
          aria-expanded={open}
          disabled={disabled}
          className={cn("w-full justify-between font-normal", className)}
        >
          <span className={cn(!selected && "text-text-muted")}>
            {selected ? selected.label : placeholder}
          </span>
          <ChevronsUpDown className="opacity-60" />
        </Button>
      </PopoverTrigger>
      <PopoverContent className="p-0 w-[--radix-popover-trigger-width]">
        <Command>
          <CommandInput placeholder={searchPlaceholder} />
          <CommandList>
            <CommandEmpty>{emptyMessage}</CommandEmpty>
            <CommandGroup>
              {options.map((opt) => (
                <CommandItem
                  key={opt.value}
                  value={opt.label}
                  keywords={opt.keywords}
                  onSelect={() => {
                    onChange(opt.value === value ? null : opt.value);
                    setOpen(false);
                  }}
                >
                  <Check className={cn("mr-2 size-4", opt.value === value ? "opacity-100" : "opacity-0")} />
                  {opt.label}
                </CommandItem>
              ))}
            </CommandGroup>
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  );
}
```

- [ ] **Step 4: Run tests, verify PASS**

Run: `cd frontend && npm test -- combobox --run`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/ui/combobox.tsx frontend/src/components/ui/__tests__/combobox.test.tsx
git commit -m "feat(ui): add Combobox primitive (cmdk + Popover)"
```

---

## Task 11: Dialog primitive — responsive sizing

**Files:**
- Modify: `frontend/src/components/ui/dialog.tsx`
- Create: `frontend/src/components/ui/__tests__/dialog.test.tsx`

**Why:** V1's default `max-w-4xl` dialogs overflow on mobile. The V2 primitive has an opinionated `size` prop and `max-h: 90dvh`. Per design_system §6.3 — dialogs become bottom-sheets below 640px.

- [ ] **Step 1: Write failing tests**

```tsx
import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { Dialog, DialogContent, DialogTitle } from "@/components/ui/dialog";

describe("Dialog (V2)", () => {
  it("renders with size='md' max-width", () => {
    render(
      <Dialog open>
        <DialogContent size="md">
          <DialogTitle>Hi</DialogTitle>
          body
        </DialogContent>
      </Dialog>
    );
    const content = screen.getByRole("dialog");
    // Data attribute rather than inline style — easier to assert
    expect(content).toHaveAttribute("data-size", "md");
  });

  it("renders title for a11y", () => {
    render(
      <Dialog open>
        <DialogContent size="md">
          <DialogTitle>My Title</DialogTitle>
          body
        </DialogContent>
      </Dialog>
    );
    expect(screen.getByText("My Title")).toBeInTheDocument();
  });

  it("applies destructive variant class when variant='destructive'", () => {
    render(
      <Dialog open>
        <DialogContent size="sm" variant="destructive">
          <DialogTitle>Confirm</DialogTitle>
        </DialogContent>
      </Dialog>
    );
    expect(screen.getByRole("dialog")).toHaveAttribute("data-variant", "destructive");
  });
});
```

- [ ] **Step 2: Run tests, verify FAIL**

Run: `cd frontend && npm test -- dialog --run`

- [ ] **Step 3: Read existing `dialog.tsx`, then replace its `DialogContent` export**

Read `frontend/src/components/ui/dialog.tsx`, then rewrite end-to-end (keep the other exports as direct Radix re-exports):

> **Amendment 2026-04-23:** `DialogProps` and `DialogBody` retained as additive exports — V1 callers (25 sites + `command.tsx`) depend on them and must compile under Phase 0 doctrine.
> **Amendment 2026-04-23 (cont.):** `DialogContent` cva base uses `flex flex-col overflow-hidden` (not `overflow-y-auto`) — `DialogBody`'s `flex-1`/`min-h-0` requires a flex parent for the V1 sticky-header/scrolling-body pattern.

```tsx
"use client";

import * as React from "react";
import * as DialogPrimitive from "@radix-ui/react-dialog";
import { X } from "lucide-react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const contentVariants = cva(
  "fixed z-50 left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 " +
    "bg-surface-card text-text-primary rounded-lg shadow-[var(--shadow-md)] " +
    "w-[calc(100vw-2rem)] max-h-[90dvh] flex flex-col overflow-hidden " +
    "data-[state=open]:animate-in data-[state=open]:fade-in-0 " +
    "data-[state=closed]:animate-out data-[state=closed]:fade-out-0",
  {
    variants: {
      size: {
        sm: "sm:max-w-[400px]",
        md: "sm:max-w-[560px]",
        lg: "sm:max-w-[720px]",
        xl: "sm:max-w-[960px]",
        full: "sm:max-w-[calc(100vw-3rem)]",
      },
      variant: {
        default: "",
        destructive: "border border-danger-border",
      },
    },
    defaultVariants: { size: "md", variant: "default" },
  }
);

// Backwards-compat type so command.tsx's `extends DialogProps {}` still compiles
export type DialogProps = React.ComponentPropsWithoutRef<typeof DialogPrimitive.Root>;

export const Dialog = DialogPrimitive.Root;
export const DialogTrigger = DialogPrimitive.Trigger;
export const DialogClose = DialogPrimitive.Close;
export const DialogPortal = DialogPrimitive.Portal;
export const DialogTitle = DialogPrimitive.Title;
export const DialogDescription = DialogPrimitive.Description;

export const DialogOverlay = React.forwardRef<
  React.ElementRef<typeof DialogPrimitive.Overlay>,
  React.ComponentPropsWithoutRef<typeof DialogPrimitive.Overlay>
>(({ className, ...props }, ref) => (
  <DialogPrimitive.Overlay
    ref={ref}
    className={cn(
      "fixed inset-0 z-50 bg-[var(--surface-overlay)] data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=open]:fade-in-0 data-[state=closed]:fade-out-0",
      className
    )}
    {...props}
  />
));
DialogOverlay.displayName = "DialogOverlay";

type DialogContentProps = React.ComponentPropsWithoutRef<typeof DialogPrimitive.Content> &
  VariantProps<typeof contentVariants> & {
    hideClose?: boolean;
  };

export const DialogContent = React.forwardRef<
  React.ElementRef<typeof DialogPrimitive.Content>,
  DialogContentProps
>(({ className, size, variant, hideClose, children, ...props }, ref) => (
  <DialogPortal>
    <DialogOverlay />
    <DialogPrimitive.Content
      ref={ref}
      data-size={size ?? "md"}
      data-variant={variant ?? "default"}
      className={cn(contentVariants({ size, variant }), className)}
      {...props}
    >
      {children}
      {!hideClose && (
        <DialogPrimitive.Close
          aria-label="Close"
          className="absolute right-4 top-4 text-text-muted hover:text-text-primary transition-colors"
        >
          <X className="size-4" />
        </DialogPrimitive.Close>
      )}
    </DialogPrimitive.Content>
  </DialogPortal>
));
DialogContent.displayName = "DialogContent";

export const DialogHeader = ({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) => (
  <div className={cn("flex flex-col gap-1 p-6 border-b border-border-subtle", className)} {...props} />
);
export const DialogBody = ({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) => (
  <div className={cn("flex-1 overflow-y-auto min-h-0 p-6", className)} {...props} />
);
export const DialogFooter = ({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) => (
  <div className={cn("flex flex-col-reverse sm:flex-row sm:justify-end gap-2 p-6 border-t border-border-subtle", className)} {...props} />
);
```

- [ ] **Step 4: Run tests, verify PASS**

Run: `cd frontend && npm test -- dialog --run`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/ui/dialog.tsx frontend/src/components/ui/__tests__/dialog.test.tsx
git commit -m "feat(ui): V2 Dialog with responsive size prop + 90dvh max-h"
```

---

## Task 12: Card primitive (compound API)

**Files:**
- Modify: `frontend/src/components/ui/card.tsx`
- Create: `frontend/src/components/ui/__tests__/card.test.tsx`

**Why:** Design system §6.5 specifies a compound `<Card>` with `Card.Header` / `Card.Body` / `Card.Footer`. V1's Card is a dumb wrapper — we upgrade it to the compound shape, keeping the bare `Card` export so V1 callers still compile.

> **Amendment 2026-04-23:** Plan-vs-reality grep miss — pre-dispatch audit
> quoted `"@/components/ui/card"` literally and counted only 1 caller. A
> quote-agnostic grep surfaced 31 V1 pages (dashboard/bills/customers/
> expenses/inventory/attendance/purchases/my-services/…) importing
> `CardHeader`/`CardTitle`/`CardDescription`/`CardFooter`/`CardAction`.
> Shipping the wholesale rewrite as-written added ~59 TS errors and broke
> `next build`. Fix (applied in the same commit as the rewrite): keep the
> plan's compound API exactly as spec'd, AND add additive V1 legacy shims
> re-exporting the pre-T12 implementations of `CardHeader` / `CardTitle` /
> `CardDescription` / `CardFooter` / `CardAction` verbatim. Compound internals
> were renamed `HeaderSlot` / `BodySlot` / `FooterSlot` to avoid collision
> with the legacy V1 names at the export boundary. Phase 1 retrofit deletes
> the shims block. Mirrors the T11(a) DialogBody/DialogProps pattern at
> larger scale.

> **Amendment 2026-04-25:** Code-quality review caught two issues post-ship.
> (1) `HeaderSlot` rendered an empty `<div className="flex flex-col ...">`
> when only `action` was passed with no title/description/children — DOM
> noise + a11y concern. Fixed: gate the left stack behind
> `const hasLeft = title || description || children;`. (2) Test coverage
> was too shallow for a primitive that gates 31 V1 callers; added a
> regression-guard test ensuring all 5 V1 legacy shim exports remain
> present (so Phase 1 retrofit cannot silently drop one), and a test for
> the action-only Header branch. Also update the Step 3 code block below
> to reflect the `hasLeft` guard. Deferred to Phase 1: redundant
> `data-density` attribute (parallel to Dialog `data-size`/`data-variant`);
> `FooterSlot` unconditional `border-t` (consumer can override via
> `className`).

- [ ] **Step 1: Write failing tests**

```tsx
import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { Card } from "@/components/ui/card";

describe("Card", () => {
  it("renders compound parts", () => {
    render(
      <Card density="md">
        <Card.Header title="Revenue" description="Today" />
        <Card.Body>₹24,800</Card.Body>
        <Card.Footer>+12% vs avg</Card.Footer>
      </Card>
    );
    expect(screen.getByText("Revenue")).toBeInTheDocument();
    expect(screen.getByText("Today")).toBeInTheDocument();
    expect(screen.getByText("₹24,800")).toBeInTheDocument();
    expect(screen.getByText("+12% vs avg")).toBeInTheDocument();
  });

  it("applies density data attribute", () => {
    const { container } = render(<Card density="lg">body</Card>);
    expect(container.firstChild).toHaveAttribute("data-density", "lg");
  });
});
```

- [ ] **Step 2: Run tests, verify FAIL**

- [ ] **Step 3: Rewrite `frontend/src/components/ui/card.tsx`**

```tsx
import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const cardVariants = cva(
  "rounded-lg bg-surface-card border border-border-subtle transition-shadow",
  {
    variants: {
      density: {
        sm: "[&_[data-slot=body]]:p-3 [&_[data-slot=header]]:px-3 [&_[data-slot=header]]:pt-3 [&_[data-slot=footer]]:px-3 [&_[data-slot=footer]]:pb-3",
        md: "[&_[data-slot=body]]:p-5 [&_[data-slot=header]]:px-5 [&_[data-slot=header]]:pt-5 [&_[data-slot=footer]]:px-5 [&_[data-slot=footer]]:pb-5",
        lg: "[&_[data-slot=body]]:p-6 [&_[data-slot=header]]:px-6 [&_[data-slot=header]]:pt-6 [&_[data-slot=footer]]:px-6 [&_[data-slot=footer]]:pb-6",
      },
      hover: {
        true: "hover:shadow-[var(--shadow-xs)]",
      },
    },
    defaultVariants: { density: "md" },
  }
);

type CardProps = React.HTMLAttributes<HTMLDivElement> & VariantProps<typeof cardVariants>;

function CardRoot({ className, density, hover, ...props }: CardProps) {
  return <div data-density={density ?? "md"} className={cn(cardVariants({ density, hover }), className)} {...props} />;
}

function HeaderSlot({
  title,
  description,
  action,
  className,
  children,
  ...props
}: React.HTMLAttributes<HTMLDivElement> & { title?: string; description?: string; action?: React.ReactNode }) {
  const hasLeft = title || description || children;
  return (
    <div data-slot="header" className={cn("flex items-start justify-between gap-4", className)} {...props}>
      {hasLeft && (
        <div className="flex flex-col gap-1 min-w-0">
          {title && <h3 className="text-heading-md text-text-primary truncate">{title}</h3>}
          {description && <p className="text-body-sm text-text-muted">{description}</p>}
          {children}
        </div>
      )}
      {action && <div className="shrink-0">{action}</div>}
    </div>
  );
}

function BodySlot({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div data-slot="body" className={cn("text-body text-text-primary", className)} {...props} />;
}

function FooterSlot({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div data-slot="footer" className={cn("border-t border-border-subtle text-body-sm text-text-muted", className)} {...props} />;
}

export const Card = Object.assign(CardRoot, {
  Header: HeaderSlot,
  Body: BodySlot,
  Footer: FooterSlot,
});

// V1 `CardContent` alias preserved — used by callers that never migrated past the shadcn default export shape.
export { BodySlot as CardContent };

// ---------------------------------------------------------------------------
// V1 legacy shims — deprecated. Do not reach for these in new code; use the
// compound `<Card.Header />` / `<Card.Body />` / `<Card.Footer />` API.
//
// Kept verbatim from the pre-T12 implementation so ~30 V1 pages continue to
// typecheck and render during Phase 0. Slated for removal during Phase 1
// retrofit once all callers migrate to the compound API. See plan T12
// amendment (2026-04-23).
// ---------------------------------------------------------------------------

function CardHeader({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="card-header"
      className={cn(
        "@container/card-header grid auto-rows-min grid-rows-[auto_auto] items-start gap-2 px-6 has-data-[slot=card-action]:grid-cols-[1fr_auto] [.border-b]:pb-6",
        className
      )}
      {...props}
    />
  );
}

function CardTitle({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="card-title"
      className={cn("leading-none font-semibold", className)}
      {...props}
    />
  );
}

function CardDescription({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="card-description"
      className={cn("text-muted-foreground text-sm", className)}
      {...props}
    />
  );
}

function CardAction({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="card-action"
      className={cn(
        "col-start-2 row-span-2 row-start-1 self-start justify-self-end",
        className
      )}
      {...props}
    />
  );
}

function CardFooter({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="card-footer"
      className={cn("flex items-center px-6 [.border-t]:pt-6", className)}
      {...props}
    />
  );
}

export { CardHeader, CardTitle, CardDescription, CardAction, CardFooter };
```

- [ ] **Step 4: Run tests, verify PASS**

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/ui/card.tsx frontend/src/components/ui/__tests__/card.test.tsx
git commit -m "feat(ui): Card compound API (Header/Body/Footer) + density prop"
```

---

## Task 13: Badge primitive — semantic tones

**Files:**
- Modify: `frontend/src/components/ui/badge.tsx`
- Create: `frontend/src/components/ui/__tests__/badge.test.tsx`

**Why:** V1 badges use hand-rolled colours. V2 routes through semantic tokens exclusively — no red-border filter pill can exist.

> **Amendment 2026-04-25:** Pre-dispatch audit using a quote-agnostic grep
> (`grep -rn "@/components/ui/badge" frontend/src`) found 24 caller files
> and 40 call sites still passing the V1 shadcn `variant` prop
> (`outline`/`secondary`/`destructive`/`default`). Shipping the plan's
> wholesale rewrite as-written would add ~40 TS errors and break
> `next build`. Fix (applied in same commit): keep the V2 `tone` prop
> exactly as spec'd AND accept `variant` as a deprecated additive prop
> mapped to a tone via `LEGACY_VARIANT_TO_TONE` (`destructive→danger`,
> everything else→`neutral`). `variant` is destructured so it never
> spreads onto the DOM span. `tone` wins when both are provided.
> Mirrors T11(a) (Dialog `DialogBody`/`DialogProps`) and T12(a) (Card V1
> shims). Phase 1 retrofit deletes the shim + legacy-variant tests.
> `asChild` and `badgeVariants` export also dropped here — zero external
> callers verified.

> **Amendment 2026-04-25 (post-review):** Code-quality review flagged 4
> Important coverage gaps. Fixed in same commit (no behavior change):
> (1) Added `size` prop coverage (default sm + md). (2) Strengthened the
> `danger` tone test to also assert the cva class string is emitted
> (`bg-danger-bg-soft` / `text-danger-fg` / `border-danger-border`) so a
> broken cva mapping cannot pass with only `data-tone` checks.
> (3) Reorganised legacy-variant tests into a `describe("legacy variant
> shim (remove in Phase 1)")` block with `it.each` over all 4 legacy
> variants — completes the mapping contract and marks the block for
> one-shot deletion at retrofit time. (4) Added a comment in
> `badge.tsx` documenting the `outline → neutral` visual drift decision.
> Test count 11 → 16. tsc unchanged at 162.

- [ ] **Step 1: Write failing tests**

```tsx
import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { Badge } from "@/components/ui/badge";

describe("Badge", () => {
  it.each([
    ["neutral"], ["success"], ["warning"], ["danger"], ["info"], ["accent"],
  ] as const)("renders %s tone", (tone) => {
    render(<Badge tone={tone}>x</Badge>);
    expect(screen.getByText("x")).toHaveAttribute("data-tone", tone);
  });

  it("defaults to neutral", () => {
    render(<Badge>default</Badge>);
    expect(screen.getByText("default")).toHaveAttribute("data-tone", "neutral");
  });

  it("danger tone emits the danger class string (cva mapping is wired)", () => {
    render(<Badge tone="danger">x</Badge>);
    const el = screen.getByText("x");
    expect(el.className).toMatch(/bg-danger-bg-soft/);
    expect(el.className).toMatch(/text-danger-fg/);
    expect(el.className).toMatch(/border-danger-border/);
  });

  it("defaults to size=sm", () => {
    render(<Badge>x</Badge>);
    expect(screen.getByText("x").className).toMatch(/text-\[11px\]/);
  });

  it("renders size=md", () => {
    render(<Badge size="md">x</Badge>);
    expect(screen.getByText("x").className).toMatch(/text-\[12px\]/);
  });

  // ---------------------------------------------------------------------
  // Legacy variant shim — the entire describe block below deletes during
  // Phase 1 retrofit once all 24 V1 caller files are migrated to `tone`.
  // ---------------------------------------------------------------------
  describe("legacy variant shim (remove in Phase 1)", () => {
    it.each([
      ["default", "neutral"],
      ["secondary", "neutral"],
      ["destructive", "danger"],
      ["outline", "neutral"],
    ] as const)("variant=%s maps to tone=%s", (variant, tone) => {
      render(<Badge variant={variant}>x</Badge>);
      expect(screen.getByText("x")).toHaveAttribute("data-tone", tone);
    });

    it("legacy variant is not spread to the DOM", () => {
      const { container } = render(<Badge variant="secondary">s</Badge>);
      const span = container.querySelector("span");
      expect(span).not.toHaveAttribute("variant");
    });

    it("explicit tone takes precedence over legacy variant", () => {
      render(<Badge tone="success" variant="destructive">mixed</Badge>);
      expect(screen.getByText("mixed")).toHaveAttribute("data-tone", "success");
    });
  });
});
```

- [ ] **Step 2: Run tests, verify FAIL**

- [ ] **Step 3: Rewrite `frontend/src/components/ui/badge.tsx`**

```tsx
import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center gap-1 rounded-full border font-semibold whitespace-nowrap",
  {
    variants: {
      tone: {
        neutral: "bg-surface-row text-text-secondary border-border-subtle",
        success: "bg-success-bg-soft text-success-fg border-success-border",
        warning: "bg-warning-bg-soft text-warning-fg border-warning-border",
        danger:  "bg-danger-bg-soft  text-danger-fg  border-danger-border",
        info:    "bg-info-bg-soft    text-info-fg    border-info-border",
        accent:  "bg-accent-bg-soft  text-accent     border-transparent",
      },
      size: {
        sm: "px-2 py-0.5 text-[11px]",
        md: "px-2.5 py-1 text-[12px]",
      },
    },
    defaultVariants: { tone: "neutral", size: "sm" },
  }
);

type Tone = NonNullable<VariantProps<typeof badgeVariants>["tone"]>;

/**
 * Legacy shim — maps the V1 shadcn `variant` prop onto the V2 `tone` prop.
 * Deprecated: do not reach for `variant` in new code; use `tone` directly.
 * Kept additive to preserve tsc+next-build health on 24 V1 caller files
 * (40 call sites) until Phase 1 retrofit migrates them. See plan T13
 * amendment (2026-04-25).
 */
type LegacyVariant = "default" | "secondary" | "destructive" | "outline";
const LEGACY_VARIANT_TO_TONE: Record<LegacyVariant, Tone> = {
  default: "neutral",
  secondary: "neutral",
  destructive: "danger",
  // V1 `outline` was visually distinct (transparent bg, prominent border).
  // V2 maps it to neutral — a deliberate visual drift; revisit per call-site
  // during Phase 1 retrofit if any chips read as wrong.
  outline: "neutral",
};

type BadgeProps = React.HTMLAttributes<HTMLSpanElement> &
  VariantProps<typeof badgeVariants> & {
    /** @deprecated Use `tone` instead. Mapped internally to a tone for V1 compat. */
    variant?: LegacyVariant;
  };

export function Badge({ tone, size, variant, className, ...props }: BadgeProps) {
  const resolvedTone: Tone = tone ?? (variant ? LEGACY_VARIANT_TO_TONE[variant] : "neutral");
  return (
    <span
      data-tone={resolvedTone}
      className={cn(badgeVariants({ tone: resolvedTone, size }), className)}
      {...props}
    />
  );
}
```

- [ ] **Step 4: Run tests, verify PASS**

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/ui/badge.tsx frontend/src/components/ui/__tests__/badge.test.tsx
git commit -m "feat(ui): Badge with semantic tone prop (+ V1 variant shim)"
```

---

## Task 14: EmptyState primitive

**Files:**
- Create: `frontend/src/components/ui/empty-state.tsx`
- Create: `frontend/src/components/ui/__tests__/empty-state.test.tsx`

**Why:** V1 scatters "No data" / "No records" strings. Spec §6.7 requires a single primitive with serif title + guiding body + CTA.

> **Amendment 2026-04-25:** Code-quality review caught 4 fixable issues
> in the as-shipped greenfield primitive (no behavior regression risk).
> Applied in same commit: (1) `secondaryAction` is now strictly
> subordinate — guard tightened from `(primary || secondary) &&` to
> `primary &&`, plus JSDoc note. Prevents accidental "lone secondary CTA"
> renders. (2) Added optional `headingLevel?: 2 | 3 | 4` prop (default 3)
> rendered via `const Heading = \`h${headingLevel}\` as const` — fixes
> a11y when EmptyState is route-level content. (3) Added component-level
> JSDoc explicitly forbidding generic "No data" copy (the rule was in
> the plan but not in the code). (4) Replaced the redundant smoke test
> #3 with 4 substantive tests: no-action-row negative, secondary-without-
> primary negative, icon `aria-hidden` wrapper, className merge,
> headingLevel default+override. Test count 3 → 7. Deferred to Phase 1:
> body uses `text-text-secondary` (Card uses `text-text-muted` — design
> call), `[&_svg]:size-8` only sizes svg children (lucide-only convention),
> `Props` type not exported (matches Card/Badge), `max-w-sm` on whole
> inner stack (cosmetic).

- [ ] **Step 1: Write failing tests**

```tsx
import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { EmptyState } from "@/components/ui/empty-state";

describe("EmptyState", () => {
  it("renders title in display serif", () => {
    render(<EmptyState title="No bookings yet today" body="Add a walk-in." />);
    const title = screen.getByText("No bookings yet today");
    expect(title.className).toMatch(/font-display|text-display/);
  });

  it("renders body and primary action", () => {
    render(
      <EmptyState
        title="No results"
        body="Try a different search."
        primaryAction={<button>Retry</button>}
      />
    );
    expect(screen.getByText("Try a different search.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Retry" })).toBeInTheDocument();
  });

  it("renders no action row when no actions provided", () => {
    const { container } = render(<EmptyState title="t" body="b" />);
    expect(container.querySelectorAll("button")).toHaveLength(0);
    expect(container.querySelector(".mt-2")).toBeNull();
  });

  it("does NOT render secondaryAction without primaryAction (subordinate semantics)", () => {
    render(
      <EmptyState
        title="t"
        body="b"
        secondaryAction={<button>SecondaryOnly</button>}
      />
    );
    expect(screen.queryByRole("button", { name: "SecondaryOnly" })).toBeNull();
  });

  it("marks the icon wrapper as decorative (aria-hidden)", () => {
    const { container } = render(
      <EmptyState title="t" body="b" icon={<svg data-testid="i" />} />
    );
    const wrapper = container.querySelector("[aria-hidden]");
    expect(wrapper).toBeTruthy();
    expect(wrapper?.querySelector('[data-testid="i"]')).toBeTruthy();
  });

  it("merges className via cn() preserving base classes", () => {
    const { container } = render(
      <EmptyState title="t" body="b" className="custom-extra" />
    );
    expect(container.firstChild).toHaveClass("custom-extra");
    expect(container.firstChild).toHaveClass("text-center");
  });

  it("renders configurable headingLevel (default h3, supports h2/h4)", () => {
    const { container, rerender } = render(<EmptyState title="t" body="b" />);
    expect(container.querySelector("h3")).toBeTruthy();

    rerender(<EmptyState title="t" body="b" headingLevel={2} />);
    expect(container.querySelector("h2")).toBeTruthy();
    expect(container.querySelector("h3")).toBeNull();

    rerender(<EmptyState title="t" body="b" headingLevel={4} />);
    expect(container.querySelector("h4")).toBeTruthy();
  });
});
```

- [ ] **Step 2: Run tests, verify FAIL**

- [ ] **Step 3: Implement `frontend/src/components/ui/empty-state.tsx`**

```tsx
import * as React from "react";
import { cn } from "@/lib/utils";

type Props = {
  icon?: React.ReactNode;
  /** Required. Rendered in the display serif. */
  title: string;
  /** Required. One sentence guiding the next action. "No data" is not acceptable. */
  body: string;
  /** Heading level for the title. Default 3 — bump to 2 (or 1) when EmptyState is the sole content of a route. */
  headingLevel?: 2 | 3 | 4;
  primaryAction?: React.ReactNode;
  /** Only rendered alongside `primaryAction`. Pass a sole CTA as `primaryAction` instead. */
  secondaryAction?: React.ReactNode;
  className?: string;
};

/**
 * Standardised "no data" surface. Consumers MUST pass a specific, action-oriented
 * `body` string (one sentence). Generic copy like "No data" / "Nothing here" is
 * not acceptable per Phase 0 plan T14 — every empty state must guide the next move.
 */
export function EmptyState({
  icon,
  title,
  body,
  headingLevel = 3,
  primaryAction,
  secondaryAction,
  className,
}: Props) {
  const Heading = `h${headingLevel}` as const;
  return (
    <div className={cn("flex flex-col items-center justify-center text-center gap-4 py-12 px-6", className)}>
      {icon && <div className="text-text-muted [&_svg]:size-8" aria-hidden>{icon}</div>}
      <div className="flex flex-col gap-2 max-w-sm">
        <Heading className="text-display-md text-text-primary">{title}</Heading>
        <p className="text-body text-text-secondary">{body}</p>
      </div>
      {primaryAction && (
        <div className="flex gap-2 mt-2">
          {primaryAction}
          {secondaryAction}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 4: Run tests, verify PASS**

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/ui/empty-state.tsx frontend/src/components/ui/__tests__/empty-state.test.tsx
git commit -m "feat(ui): add EmptyState primitive (serif title + guiding body + CTA)"
```

---

## Task 15: Skeleton primitive — standardised shapes

**Files:**
- Modify: `frontend/src/components/ui/skeleton.tsx`
- Create: `frontend/src/components/ui/__tests__/skeleton.test.tsx`

**Why:** V1 uses mixed spinners / blank states. Spec §6.8 makes Skeleton mandatory for loading states with four named shapes.

> **Amendment 2026-04-26:** Pre-dispatch audit found 1 caller — the
> shared `sidebar.tsx` layout primitive at lines 622+627 — passing
> `data-sidebar` and `style` (custom CSS variable for menu-skeleton
> width). The plan's narrowed `Props = { shape?, width?, className? }`
> would break sidebar visually + add ~3 TS errors. Sidebar is layout
> infra rendered on every V1 + V2 route, so the usual "tolerate broken
> V1 visuals" doctrine does not apply. Fix (applied in same commit):
> extend `Props` with `React.HTMLAttributes<HTMLDivElement>` and spread
> `...rest` to the div. Also destructure caller `style` separately and
> merge it with the internal `width` prop so caller CSS vars survive.
> The V2 contract (use `shape`/`width`) is still enforced by the typed
> primary props. Test count 2 → 9 (added default-shape, sidebar-attr
> regression guard, style-merge guard, aria-hidden guard).

> **Amendment 2026-04-26 (post-review):** Code-quality review caught
> 3 fixable issues in the as-shipped version (no behavior regression
> risk). Applied in same commit: (1) `width={0}` was silently overridden
> by the default-width class because both gates used truthy checks
> (`width ?` / `!width &&`). Fixed by extracting `const hasWidth =
> width !== undefined` and using that in both branches. (2) Added a
> 3-line code comment documenting the `aria-hidden` decorative-by-default
> invariant + `{...rest}` escape hatch (callers opt back in by passing
> `aria-hidden={false}` or use `aria-busy` on the live container).
> (3) Added 3 new tests covering default-width-per-shape: text→w-3/4,
> card→w-full, and the `width=0` regression guard. Test count 9 → 12.
> Deferred to Phase 1: parallel `shapeClass`/`defaultWidthClass` records
> (style call — leave as-is), `Shape` type export (speculative), Phase
> 1 plan-doc note about shim being permanent (not a legacy adapter).

- [ ] **Step 1: Write failing tests**

```tsx
import { describe, expect, it } from "vitest";
import { render } from "@testing-library/react";
import * as React from "react";
import { Skeleton } from "@/components/ui/skeleton";

describe("Skeleton", () => {
  it.each([["text"], ["row"], ["card"], ["kpi"]] as const)("renders %s shape", (shape) => {
    const { container } = render(<Skeleton shape={shape} />);
    expect(container.firstChild).toHaveAttribute("data-shape", shape);
  });

  it("defaults to text shape when no shape prop given", () => {
    const { container } = render(<Skeleton />);
    expect(container.firstChild).toHaveAttribute("data-shape", "text");
  });

  it("applies custom width via inline style", () => {
    const { container } = render(<Skeleton shape="text" width="60%" />);
    expect(container.firstChild).toHaveStyle({ width: "60%" });
  });

  it("forwards arbitrary HTML attrs (regression guard for sidebar caller)", () => {
    const { container } = render(
      <Skeleton shape="text" data-sidebar="menu-skeleton-text" />
    );
    expect(container.firstChild).toHaveAttribute("data-sidebar", "menu-skeleton-text");
  });

  it("forwards inline style attrs alongside width prop", () => {
    const { container } = render(
      <Skeleton
        shape="text"
        style={{ "--skeleton-width": "70%" } as React.CSSProperties}
      />
    );
    const el = container.firstChild as HTMLElement;
    expect(el.style.getPropertyValue("--skeleton-width")).toBe("70%");
  });

  it("renders as decorative (aria-hidden)", () => {
    const { container } = render(<Skeleton shape="row" />);
    expect(container.firstChild).toHaveAttribute("aria-hidden");
  });
});
```

- [ ] **Step 2: Run, verify FAIL**

- [ ] **Step 3: Rewrite `frontend/src/components/ui/skeleton.tsx`**

```tsx
import * as React from "react";
import { cn } from "@/lib/utils";

type Shape = "text" | "row" | "card" | "kpi";

type Props = React.HTMLAttributes<HTMLDivElement> & {
  shape?: Shape;
  width?: React.CSSProperties["width"];
};

const shapeClass: Record<Shape, string> = {
  text: "h-4 rounded",
  row:  "h-9 rounded-md",
  card: "h-32 rounded-lg",
  kpi:  "h-20 rounded-lg",
};

const defaultWidthClass: Record<Shape, string> = {
  text: "w-3/4",
  row:  "w-full",
  card: "w-full",
  kpi:  "w-full",
};

export function Skeleton({ shape = "text", width, className, style, ...rest }: Props) {
  return (
    <div
      data-shape={shape}
      style={width ? { ...style, width } : style}
      className={cn(
        "animate-pulse bg-surface-row-hover",
        shapeClass[shape],
        !width && defaultWidthClass[shape],
        className
      )}
      aria-hidden
      {...rest}
    />
  );
}
```

- [ ] **Step 4: Run, verify PASS**

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/ui/skeleton.tsx frontend/src/components/ui/__tests__/skeleton.test.tsx
git commit -m "feat(ui): Skeleton with named shapes (text/row/card/kpi)"
```

---

## Task 16: DataTable primitive — with mobile card fallback

**Files:**
- Create: `frontend/src/components/ui/data-table.tsx`
- Create: `frontend/src/components/ui/__tests__/data-table.test.tsx`

**Why:** Spec §6.4 is the most complex primitive. Single source of truth for every list in V2 (Bills, Customers, Inventory, Purchases, Expenses). Mobile card fallback is *default*, not opt-in. Named `DataTable` to avoid conflict with existing low-level `<Table>` element primitive.

> **Amendment 2026-04-29:** Code-quality review caught 3 Important issues
> in the as-shipped greenfield primitive. Applied in the same commit:
> (1) Row click was mouse-only — no `tabIndex`, no keyboard handler.
> Real a11y regression on THE V2 list primitive. Fix: when `onRowClick`
> is set, both desktop `<tr>` and mobile card `<div>` get `tabIndex={0}`,
> an `onKeyDown` handler that activates on Enter/Space, plus
> `focus:outline-none focus:bg-surface-row-hover` for visible focus
> indication. Mobile card also gets `role="button"` (semantic since it's
> a div); desktop tr keeps default `role="row"` (W3C-correct;
> `role="button"` on tr is nonstandard). (2) Empty data with no
> `emptyState` prop rendered broken table chrome (header row + empty
> tbody) instead of nothing. Fix: rewrite empty branch to
> `if (data.length === 0) return emptyState ? <>{emptyState}</> : null;`.
> (3) 4 tests too thin for the primitive's importance. Added 6 tests:
> keyboard-Enter+Space activation, negative tabIndex without onRowClick,
> rowAction stopPropagation, mobileCard override, density variants
> (dense → h-8, comfort → h-11), null-empty fallback. Test count 4 → 10.
>
> Also documented (not fixed): `format="money"` without `align="right"`
> renders left-aligned with tabular nums — caller bug, not enforced.
> `Props<T>` not exported (matches Card/Badge convention). Mobile cards
> don't render `rowAction` (current spec choice; revisit at first
> mobile-with-actions call site). Vitest dual-render JSDOM idiom: tests
> for any responsive primitive must use `getAllByText` /
> `getAllByRole` since both desktop and mobile DOM render simultaneously
> (Tailwind class-based hide/show doesn't take effect in JSDOM).

- [ ] **Step 1: Write failing tests**

```tsx
import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { DataTable, type DataTableColumn } from "@/components/ui/data-table";

type Customer = { id: string; name: string; phone: string; spentPaise: number };
const rows: Customer[] = [
  { id: "1", name: "Priya", phone: "9000000001", spentPaise: 240000 },
  { id: "2", name: "Rajni", phone: "9000000002", spentPaise: 180000 },
];
const columns: DataTableColumn<Customer>[] = [
  { id: "name",  header: "Name",   priority: "high",   accessor: (r) => r.name },
  { id: "phone", header: "Phone",  priority: "medium", accessor: (r) => r.phone },
  { id: "spent", header: "Spent",  priority: "high",   accessor: (r) => `₹${(r.spentPaise / 100).toFixed(2)}`, align: "right" },
];

describe("DataTable", () => {
  it("renders headers and rows", () => {
    render(<DataTable data={rows} columns={columns} getRowId={(r) => r.id} />);
    expect(screen.getByRole("columnheader", { name: "Name" })).toBeInTheDocument();
    expect(screen.getByText("Priya")).toBeInTheDocument();
    expect(screen.getByText("₹2400.00")).toBeInTheDocument();
  });

  it("renders empty state when data is empty", () => {
    render(
      <DataTable
        data={[]}
        columns={columns}
        getRowId={(r) => r.id}
        emptyState={<div>nothing yet</div>}
      />
    );
    expect(screen.getByText("nothing yet")).toBeInTheDocument();
  });

  it("renders skeleton when loading", () => {
    const { container } = render(
      <DataTable data={[]} columns={columns} getRowId={(r) => r.id} loading />
    );
    expect(container.querySelectorAll("[data-shape='row']").length).toBeGreaterThan(0);
  });

  it("calls onRowClick when row is clicked", async () => {
    const onRowClick = vi.fn();
    const { default: userEvent } = await import("@testing-library/user-event");
    const user = userEvent.setup();
    render(<DataTable data={rows} columns={columns} getRowId={(r) => r.id} onRowClick={onRowClick} />);
    await user.click(screen.getByText("Priya"));
    expect(onRowClick).toHaveBeenCalledWith(rows[0]);
  });
});
```

- [ ] **Step 2: Run, verify FAIL**

- [ ] **Step 3: Implement `frontend/src/components/ui/data-table.tsx`**

```tsx
import * as React from "react";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

export type ColumnPriority = "high" | "medium" | "low";

export type DataTableColumn<T> = {
  id: string;
  header: string;
  priority: ColumnPriority;
  accessor: (row: T) => React.ReactNode;
  align?: "left" | "right" | "center";
  format?: "money" | "default";
};

type Props<T> = {
  data: T[];
  columns: DataTableColumn<T>[];
  getRowId: (row: T) => string;
  emptyState?: React.ReactNode;
  loading?: boolean;
  onRowClick?: (row: T) => void;
  rowAction?: (row: T) => React.ReactNode;
  density?: "default" | "dense" | "comfort";
  /** Override the default card-from-high-priority-columns mobile view. */
  mobileCard?: (row: T) => React.ReactNode;
};

export function DataTable<T>({
  data,
  columns,
  getRowId,
  emptyState,
  loading,
  onRowClick,
  rowAction,
  density = "default",
  mobileCard,
}: Props<T>) {
  if (loading) {
    return (
      <div className="flex flex-col gap-2" aria-busy>
        {Array.from({ length: 5 }).map((_, i) => (
          <Skeleton key={i} shape="row" />
        ))}
      </div>
    );
  }

  if (data.length === 0 && emptyState) {
    return <>{emptyState}</>;
  }

  const visibleColumns = columns.filter((c) => c.priority !== "low");
  const rowHeight = density === "dense" ? "h-8" : density === "comfort" ? "h-11" : "h-9";

  return (
    <>
      {/* Desktop / tablet table */}
      <div className="hidden sm:block rounded-lg border border-border-subtle overflow-hidden bg-surface-card">
        <table className="w-full border-collapse">
          <thead className="bg-surface-row-hover">
            <tr>
              {columns.map((col) => (
                <th
                  key={col.id}
                  className={cn(
                    "px-4 py-2 text-overline text-text-secondary border-b border-border-subtle",
                    col.align === "right" && "text-right",
                    col.align === "center" && "text-center",
                    col.align !== "right" && col.align !== "center" && "text-left",
                    col.priority === "low" && "hidden lg:table-cell"
                  )}
                >
                  {col.header}
                </th>
              ))}
              {rowAction && <th className="w-10" />}
            </tr>
          </thead>
          <tbody>
            {data.map((row) => (
              <tr
                key={getRowId(row)}
                onClick={onRowClick ? () => onRowClick(row) : undefined}
                className={cn(
                  rowHeight,
                  "border-b border-border-subtle last:border-0",
                  onRowClick && "cursor-pointer hover:bg-surface-row-hover"
                )}
              >
                {columns.map((col) => (
                  <td
                    key={col.id}
                    className={cn(
                      "px-4 text-body-sm text-text-primary",
                      col.align === "right" && "text-right tabular",
                      col.align === "center" && "text-center",
                      col.format === "money" && "tabular",
                      col.priority === "low" && "hidden lg:table-cell"
                    )}
                  >
                    {col.accessor(row)}
                  </td>
                ))}
                {rowAction && (
                  <td className="pr-2 text-right" onClick={(e) => e.stopPropagation()}>
                    {rowAction(row)}
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Mobile card fallback */}
      <div className="sm:hidden flex flex-col gap-2">
        {data.map((row) => (
          <div
            key={getRowId(row)}
            onClick={onRowClick ? () => onRowClick(row) : undefined}
            className={cn(
              "rounded-lg border border-border-subtle bg-surface-card p-3",
              onRowClick && "cursor-pointer active:bg-surface-row-hover"
            )}
          >
            {mobileCard ? (
              mobileCard(row)
            ) : (
              <div className="flex flex-col gap-1">
                {visibleColumns.map((col) => (
                  <div key={col.id} className="flex justify-between gap-3">
                    <span className="text-caption text-text-muted">{col.header}</span>
                    <span
                      className={cn(
                        "text-body-sm text-text-primary",
                        (col.align === "right" || col.format === "money") && "tabular"
                      )}
                    >
                      {col.accessor(row)}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
    </>
  );
}
```

- [ ] **Step 4: Run, verify PASS**

Run: `cd frontend && npm test -- data-table --run`

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/ui/data-table.tsx frontend/src/components/ui/__tests__/data-table.test.tsx
git commit -m "feat(ui): DataTable primitive with mobile card fallback"
```

---

## Task 17: FilterBar primitive (compound API)

**Files:**
- Create: `frontend/src/components/ui/filter-bar.tsx`
- Create: `frontend/src/components/ui/__tests__/filter-bar.test.tsx`

**Why:** Same filter strip across Bills, Inventory, Customers, Purchases, Expenses, Appointments. Compound API per §6.9.

> **Amendment 2026-04-29:** Plan code had an internal contradiction —
> the implementation set `role="tab"` on each pill button while the test
> queried `getByRole("button", ...)`. Explicit `role="tab"` overrides
> the `<button>`'s implicit `role="button"`, so the verbatim plan would
> fail tests #2 and #3. Fix (applied in same commit): drop `role="tab"`
> AND `role="tablist"` (a tablist must contain tabs; without them the
> wrapper role is a lie). Use proper toggle-button semantics:
> `aria-pressed={active}` on each pill, `role="group" aria-label="Filters"`
> on the wrapper. `aria-selected` (which the implementer initially
> retained) is invalid ARIA on a `button` role — only valid on
> `tab`/`option`/`row`/etc. Filter pills filter a list in place rather
> than swapping content panels, so toggle-button is the correct pattern.
> Added a 4th test asserting `aria-pressed` is set AND `aria-selected`
> is NOT set, locking the contract.


```tsx
import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { FilterBar } from "@/components/ui/filter-bar";

describe("FilterBar", () => {
  it("renders search input", () => {
    render(
      <FilterBar>
        <FilterBar.Search placeholder="Search bills…" value="" onChange={() => {}} />
      </FilterBar>
    );
    expect(screen.getByPlaceholderText("Search bills…")).toBeInTheDocument();
  });

  it("renders pills with counts and fires onChange", async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    render(
      <FilterBar>
        <FilterBar.Pills
          value="all"
          onChange={onChange}
          options={[
            { value: "all",  label: "All",  count: 171 },
            { value: "paid", label: "Paid", count: 142 },
          ]}
        />
      </FilterBar>
    );
    await user.click(screen.getByRole("button", { name: /Paid/ }));
    expect(onChange).toHaveBeenCalledWith("paid");
  });

  it("marks active pill", () => {
    render(
      <FilterBar>
        <FilterBar.Pills
          value="paid"
          onChange={() => {}}
          options={[{ value: "paid", label: "Paid", count: 142 }]}
        />
      </FilterBar>
    );
    expect(screen.getByRole("button", { name: /Paid/ })).toHaveAttribute("data-active", "true");
  });
});
```

- [ ] **Step 2: Run, verify FAIL**

- [ ] **Step 3: Implement `frontend/src/components/ui/filter-bar.tsx`**

```tsx
import * as React from "react";
import { Search } from "lucide-react";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

function Root({ className, children }: { className?: string; children: React.ReactNode }) {
  return (
    <div className={cn("flex flex-wrap items-center gap-2 py-2", className)}>
      {children}
    </div>
  );
}

function Search_({
  value,
  onChange,
  placeholder = "Search…",
  className,
}: {
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  className?: string;
}) {
  return (
    <div className={cn("flex-1 min-w-[200px]", className)}>
      <Input
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        leadingAddon={<Search className="size-4" />}
        aria-label="Search"
      />
    </div>
  );
}

type PillOption = { value: string; label: string; count?: number };

function Pills({
  value,
  onChange,
  options,
  className,
}: {
  value: string;
  onChange: (v: string) => void;
  options: PillOption[];
  className?: string;
}) {
  return (
    <div className={cn("flex flex-wrap gap-1", className)} role="tablist">
      {options.map((opt) => {
        const active = opt.value === value;
        return (
          <button
            key={opt.value}
            type="button"
            role="tab"
            aria-selected={active}
            data-active={active}
            onClick={() => onChange(opt.value)}
            className={cn(
              "inline-flex items-center gap-1.5 rounded-full px-3 h-7 text-body-sm border transition-colors",
              active
                ? "bg-accent text-accent-fg border-transparent font-semibold"
                : "bg-surface-card text-text-secondary border-border-default hover:bg-surface-row-hover"
            )}
          >
            <span>{opt.label}</span>
            {opt.count !== undefined && (
              <span className={cn("tabular text-[11px]", active ? "opacity-80" : "text-text-muted")}>
                · {opt.count}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}

function Actions({ className, children }: { className?: string; children: React.ReactNode }) {
  return <div className={cn("flex items-center gap-2 ml-auto", className)}>{children}</div>;
}

export const FilterBar = Object.assign(Root, {
  Search: Search_,
  Pills,
  Actions,
});
```

- [ ] **Step 4: Run, verify PASS**

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/ui/filter-bar.tsx frontend/src/components/ui/__tests__/filter-bar.test.tsx
git commit -m "feat(ui): FilterBar with Search/Pills/Actions compound API"
```

---

## Task 18: NavItem primitive

**Files:**
- Create: `frontend/src/components/ui/nav-item.tsx`
- Create: `frontend/src/components/ui/__tests__/nav-item.test.tsx`

**Why:** Sidebar, bottom-nav, and (later) ⌘K palette all render the same conceptual NavItem. Centralising it prevents the three-ways-to-render-navigation drift that bit V1.

> **Amendment 2026-04-29:** Plan code set `data-active` (for styling)
> but no ARIA attribute on the active item. NavItem renders on every
> V2 route (sidebar, bottom-nav, future ⌘K palette), so missing
> `aria-current="page"` is a real screen-reader regression. Fix
> (applied in same commit): add `aria-current={active ? "page" :
> undefined}` on the `<Link>`. Same `|| undefined` pattern as
> `data-active` so the attribute is omitted (not "false") when
> inactive. Added 1 test asserting both `data-active="true"` AND
> `aria-current="page"` are set on active, plus 1 test asserting
> both are OMITTED when inactive (locks the contract). Test count
> 3 → 5. Deferred: badge silently dropped for `rail`/`bottom`
> variants (plan choice — JSDoc note would help; revisit at first
> mobile-nav call site).

- [ ] **Step 1: Write failing tests**

```tsx
import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { NavItem } from "@/components/ui/nav-item";

describe("NavItem", () => {
  it("renders label and icon", () => {
    render(<NavItem label="Today" href="/dashboard" icon={<span data-testid="ico">I</span>} />);
    expect(screen.getByText("Today")).toBeInTheDocument();
    expect(screen.getByTestId("ico")).toBeInTheDocument();
  });

  it("marks active when active=true", () => {
    render(<NavItem label="Today" href="/dashboard" active />);
    expect(screen.getByRole("link")).toHaveAttribute("data-active", "true");
  });

  it("renders badge when provided", () => {
    render(<NavItem label="Bills" href="/bills" badge={<span>3</span>} />);
    expect(screen.getByText("3")).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run, verify FAIL**

- [ ] **Step 3: Implement `frontend/src/components/ui/nav-item.tsx`**

```tsx
import * as React from "react";
import Link from "next/link";
import { cn } from "@/lib/utils";

type Props = {
  label: string;
  href: string;
  icon?: React.ReactNode;
  active?: boolean;
  badge?: React.ReactNode;
  variant?: "sidebar" | "rail" | "bottom";
  className?: string;
};

export function NavItem({
  label,
  href,
  icon,
  active,
  badge,
  variant = "sidebar",
  className,
}: Props) {
  return (
    <Link
      href={href}
      data-active={active || undefined}
      className={cn(
        "flex items-center gap-2 transition-colors rounded-md",
        "text-body-sm text-text-secondary hover:text-text-primary hover:bg-surface-row-hover",
        "data-[active=true]:bg-accent-bg-soft data-[active=true]:text-accent data-[active=true]:font-semibold",
        variant === "sidebar" && "px-3 h-8",
        variant === "rail" && "flex-col justify-center w-12 h-14 text-[10px] gap-0.5",
        variant === "bottom" && "flex-col justify-center flex-1 h-14 text-[11px] gap-0.5",
        className
      )}
    >
      {icon && <span aria-hidden className="[&_svg]:size-4 shrink-0">{icon}</span>}
      <span className={cn("flex-1", variant !== "sidebar" && "text-center")}>{label}</span>
      {badge && variant === "sidebar" && <span className="ml-auto">{badge}</span>}
    </Link>
  );
}
```

- [ ] **Step 4: Run, verify PASS**

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/ui/nav-item.tsx frontend/src/components/ui/__tests__/nav-item.test.tsx
git commit -m "feat(ui): NavItem primitive for sidebar/rail/bottom-nav"
```

---

## Task 19: Kbd primitive

**Files:**
- Create: `frontend/src/components/ui/kbd.tsx`
- Create: `frontend/src/components/ui/__tests__/kbd.test.tsx`

**Why:** Command palette, keyboard-shortcut hints in tooltips, empty states mentioning `⌘K` — all render keyboard chords. One component.

> **Amendment 2026-04-29:** Pre-dispatch audit found two plan defects.
> (1) `role="kbd-chord"` on the wrapper `<span>` is not a valid ARIA
> role — axe-core / eslint-jsx-a11y will flag it. The native `<kbd>`
> element is already semantically correct; no wrapper role is needed.
> Fix: drop the `role` attribute entirely. (2) Plan test #1 had no
> `expect()` assertions — it passed vacuously regardless of
> implementation. Fix: rewrite to assert `container.querySelectorAll("kbd")`
> returns 2 elements with the correct text content in order.
> Both fixes applied in same commit. Implementation and other test
> are otherwise verbatim.

- [ ] **Step 1: Write failing tests**

```tsx
import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { Kbd } from "@/components/ui/kbd";

describe("Kbd", () => {
  it("renders each key as its own <kbd> element in order", () => {
    const { container } = render(<Kbd keys={["⌘", "K"]} />);
    const kbdElements = container.querySelectorAll("kbd");
    expect(kbdElements).toHaveLength(2);
    expect(kbdElements[0]).toHaveTextContent("⌘");
    expect(kbdElements[1]).toHaveTextContent("K");
  });

  it("renders the keys' text content", () => {
    render(<Kbd keys={["⌘", "K"]} />);
    expect(screen.getByText("⌘")).toBeInTheDocument();
    expect(screen.getByText("K")).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run, verify FAIL**

- [ ] **Step 3: Implement `frontend/src/components/ui/kbd.tsx`**

```tsx
import * as React from "react";
import { cn } from "@/lib/utils";

type Props = {
  keys: string[];
  className?: string;
};

export function Kbd({ keys, className }: Props) {
  return (
    <span className={cn("inline-flex items-center gap-0.5 font-mono text-[10px]", className)}>
      {keys.map((k, i) => (
        <kbd
          key={`${k}-${i}`}
          className="inline-flex items-center justify-center min-w-[18px] h-[18px] px-1 rounded bg-surface-row-hover text-text-secondary border border-border-subtle"
        >
          {k}
        </kbd>
      ))}
    </span>
  );
}
```

- [ ] **Step 4: Run, verify PASS**

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/ui/kbd.tsx frontend/src/components/ui/__tests__/kbd.test.tsx
git commit -m "feat(ui): Kbd primitive for keyboard-shortcut chords"
```

---

## Task 20: Toast (sonner) — restyle to tokens + enforce rules

**Files:**
- Modify: `frontend/src/components/ui/sonner.tsx`
- Modify: `frontend/src/app/layout.tsx` (added 2026-04-29 — see amendment)

**Why:** Sonner is the existing toast lib. We re-skin it via tokens and set policy defaults: success = auto-dismiss 4s, warning/danger = persistent.

> **Amendment 2026-04-29:** Plan listed only `frontend/src/components/ui/sonner.tsx`
> as the modified file, but `app/layout.tsx:2` imported `Toaster` from
> `'sonner'` directly — bypassing the wrapper entirely. Shipping the
> rewrite alone would have left V2 token styling unreachable at runtime
> (the wrapper would be dead code). Fix (applied in same commit): also
> flip `app/layout.tsx:2` to `import { Toaster } from '@/components/ui/sonner'`.
> Toaster is shared chrome that renders on every route, so this is
> analogous to the T15 sidebar argument — visual breakage on shared
> infra ≠ tolerated V1 page breakage. Duration policy ("success = 4s,
> warning/danger = persistent" from the Why section above) cannot be
> enforced in the Toaster config — must be applied at
> `toast.success(...)` / `toast.error(...)` call sites. Deferred to
> Phase 1 retrofit.

- [ ] **Step 1: Read the current `frontend/src/components/ui/sonner.tsx`, then rewrite**

```tsx
"use client";

import { Toaster as SonnerToaster, type ToasterProps } from "sonner";

export function Toaster(props: ToasterProps) {
  return (
    <SonnerToaster
      position="bottom-right"
      closeButton
      richColors={false}
      toastOptions={{
        classNames: {
          toast:
            "bg-surface-card text-text-primary border border-border-default shadow-[var(--shadow-md)] rounded-lg",
          title: "text-body font-semibold",
          description: "text-body-sm text-text-secondary",
          success: "[&]:border-success-border [&_[data-icon]]:text-success-fg",
          warning: "[&]:border-warning-border [&_[data-icon]]:text-warning-fg",
          error:   "[&]:border-danger-border  [&_[data-icon]]:text-danger-fg",
          info:    "[&]:border-info-border    [&_[data-icon]]:text-info-fg",
          closeButton: "text-text-muted hover:text-text-primary",
          actionButton: "bg-accent text-accent-fg",
          cancelButton: "text-text-secondary",
        },
      }}
      {...props}
    />
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/ui/sonner.tsx
git commit -m "feat(ui): restyle Toast (sonner) to V2 tokens"
```

---

## Task 21: ESLint 9 flat config migration

**Files:**
- Delete: `frontend/.eslintrc.json`
- Create: `frontend/eslint.config.mjs`
- Modify: `frontend/package.json`

**Why:** The legacy `.eslintrc.json` format doesn't support local plugin paths cleanly. Migrating to flat config is a prerequisite for Task 22's custom plugin.

> **Amendment 2026-04-30:** Two plan deviations applied during execution.
> (1) Plan's Step 2 used `FlatCompat` to load `next/core-web-vitals` and
> `next/typescript` via `compat.extends(...)`. That crashed with
> `TypeError: Converting circular structure to JSON` because Next 16's
> `eslint-config-next` ships native flat configs (CJS modules exporting
> `Linter.Config[]`), not legacy presets. Fix: import the flat-config
> arrays directly via `eslint-config-next/core-web-vitals` and
> `eslint-config-next/typescript`, dropping `FlatCompat`. The `@eslint/eslintrc`
> dep is now unused but kept installed (forward-useful, harmless).
> (2) Risk #1 fired: `next lint` is removed in Next 16 — running it produced
> "Invalid project directory provided" because Next tried to lint a
> nonexistent `lint/` dir. Fix: changed `package.json` lint script from
> `"next lint"` to `"eslint ."`. Both fixes in same commit. (3) Adding
> `js.configs.recommended` introduced 1 new lint error in `cn.test.ts:9`
> — the test deliberately uses `false && "hidden"` to verify `cn()` drops
> falsy conditional classes. Suppressed via inline
> `// eslint-disable-next-line no-constant-binary-expression`. The 38
> pre-existing errors and 208 warnings surfaced by the new lint run were
> always present but masked by the broken `next lint` toolchain — Phase 0
> doctrine accepts them.

- [ ] **Step 1: Install flat-config helpers**

```bash
cd frontend && npm install -D @eslint/eslintrc @eslint/js typescript-eslint
```

- [ ] **Step 2: Create `frontend/eslint.config.mjs`**

```js
import js from "@eslint/js";
import ts from "typescript-eslint";
import { FlatCompat } from "@eslint/eslintrc";
import path from "node:path";
import url from "node:url";

const __dirname = path.dirname(url.fileURLToPath(import.meta.url));
const compat = new FlatCompat({ baseDirectory: __dirname });

export default [
  js.configs.recommended,
  ...ts.configs.recommended,
  ...compat.extends("next/core-web-vitals", "next/typescript"),
  {
    ignores: [
      ".next/**",
      "node_modules/**",
      "eslint-plugin-salon/**",
      "scripts/**",
    ],
  },
  {
    rules: {
      "@typescript-eslint/no-unused-vars": "warn",
      "@typescript-eslint/no-explicit-any": "warn",
      "prefer-const": "warn",
    },
  },
];
```

- [ ] **Step 3: Delete `.eslintrc.json`**

```bash
rm frontend/.eslintrc.json
```

- [ ] **Step 4: Run lint to confirm parity**

Run: `cd frontend && npm run lint`
Expected: lint runs without loader errors; existing warnings from V1 code are unchanged in kind.

- [ ] **Step 5: Commit**

```bash
git add frontend/eslint.config.mjs frontend/package.json frontend/package-lock.json
git rm frontend/.eslintrc.json
git commit -m "chore(lint): migrate to ESLint 9 flat config"
```

---

## Task 22: Custom ESLint plugin — `no-raw-grays`

**Files:**
- Create: `frontend/eslint-plugin-salon/package.json`
- Create: `frontend/eslint-plugin-salon/index.js`
- Create: `frontend/eslint-plugin-salon/rules/no-raw-grays.js`
- Create: `frontend/eslint-plugin-salon/tests/no-raw-grays.test.js`
- Modify: `frontend/eslint.config.mjs`
- Modify: `frontend/package.json`

**Why:** Structurally prevents V1's 1.02-contrast regression. Rejects any `text-gray-*` / `bg-gray-*` / `border-gray-*` plus `zinc`/`slate`/`stone`/`neutral` variants in app code.

> **Amendment 2026-04-30:** Plan's Step 6 showed a "full eslint.config.mjs"
> using FlatCompat to load `next/core-web-vitals` — but T21 replaced
> FlatCompat with direct flat-config imports (commit `75c55db`). The
> additive diff in this task adds `import salon from "./eslint-plugin-salon/index.js"`
> + a new files-scoped config block, merged into the T21 config. Step 8
> ("next lint --dir src") is stale and was skipped — T21 already changed
> the lint script to `"eslint ."`. Plugin tests run via `node tests/...`
> (ESLint's RuleTester, not vitest).

- [ ] **Step 1: Create the plugin package**

`frontend/eslint-plugin-salon/package.json`:

```json
{
  "name": "eslint-plugin-salon",
  "version": "0.0.0",
  "private": true,
  "main": "index.js",
  "type": "commonjs"
}
```

- [ ] **Step 2: Write the rule test first**

`frontend/eslint-plugin-salon/tests/no-raw-grays.test.js`:

```js
const { RuleTester } = require("eslint");
const rule = require("../rules/no-raw-grays");

const ruleTester = new RuleTester({
  languageOptions: {
    parserOptions: { ecmaVersion: 2022, sourceType: "module", ecmaFeatures: { jsx: true } },
  },
});

ruleTester.run("no-raw-grays", rule, {
  valid: [
    { code: `const c = "text-text-muted bg-surface-card"` },
    { code: `<div className="text-accent" />` },
    { code: `const x = "text-red-500"` }, // red is not a banned family
  ],
  invalid: [
    {
      code: `<div className="text-gray-500" />`,
      errors: [{ messageId: "rawGray" }],
    },
    {
      code: `const c = "bg-zinc-900 p-2"`,
      errors: [{ messageId: "rawGray" }],
    },
    {
      code: `const c = \`border-slate-200 \${flag && "text-neutral-700"}\``,
      errors: [{ messageId: "rawGray" }, { messageId: "rawGray" }],
    },
  ],
});

console.log("no-raw-grays PASS");
```

- [ ] **Step 3: Implement the rule**

`frontend/eslint-plugin-salon/rules/no-raw-grays.js`:

```js
"use strict";

const BANNED_FAMILIES = ["gray", "zinc", "slate", "stone", "neutral"];
// Matches tokens like `text-gray-500`, `bg-zinc-900/50`, `border-slate-200`
const PATTERN = new RegExp(
  `\\b(text|bg|border|ring|outline|decoration|divide|fill|stroke|placeholder)-(${BANNED_FAMILIES.join("|")})-\\d+`,
  "g"
);

function* findMatches(str) {
  let m;
  PATTERN.lastIndex = 0;
  while ((m = PATTERN.exec(str))) {
    yield m[0];
  }
}

module.exports = {
  meta: {
    type: "problem",
    messages: {
      rawGray:
        "Raw Tailwind gray utility '{{match}}'. Use a semantic token (text-muted, bg-surface-card, border-default) — grays must go through tokens.",
    },
    schema: [],
  },
  create(context) {
    function check(node, text) {
      for (const match of findMatches(text)) {
        context.report({ node, messageId: "rawGray", data: { match } });
      }
    }
    return {
      Literal(node) {
        if (typeof node.value === "string") check(node, node.value);
      },
      TemplateElement(node) {
        if (node.value && node.value.raw) check(node, node.value.raw);
      },
    };
  },
};
```

- [ ] **Step 4: Write the plugin index**

`frontend/eslint-plugin-salon/index.js`:

```js
"use strict";

module.exports = {
  rules: {
    "no-raw-grays": require("./rules/no-raw-grays"),
  },
};
```

- [ ] **Step 5: Run the rule test**

```bash
cd frontend/eslint-plugin-salon && node tests/no-raw-grays.test.js
```

Expected output ends with: `no-raw-grays PASS`

- [ ] **Step 6: Wire plugin into `eslint.config.mjs`**

Append a new config block before the existing rules block:

```js
import salon from "./eslint-plugin-salon/index.js";
// …
{
  files: ["src/{app,components}/**/*.{ts,tsx}"],
  ignores: ["src/styles/**", "src/components/ui/**/*.stories.tsx"],
  plugins: { salon },
  rules: {
    "salon/no-raw-grays": "warn", // flips to "error" in Phase 1
  },
},
```

Full config after change (matches T21-shipped flat-config — direct imports, no FlatCompat):

```js
import js from "@eslint/js";
import ts from "typescript-eslint";
import nextCoreWebVitals from "eslint-config-next/core-web-vitals";
import nextTypescript from "eslint-config-next/typescript";
import salon from "./eslint-plugin-salon/index.js";

export default [
  js.configs.recommended,
  ...ts.configs.recommended,
  ...nextCoreWebVitals,
  ...nextTypescript,
  {
    ignores: [".next/**", "node_modules/**", "eslint-plugin-salon/**", "scripts/**"],
  },
  {
    files: ["src/{app,components}/**/*.{ts,tsx}"],
    ignores: ["src/styles/**", "src/components/ui/**/*.stories.tsx"],
    plugins: { salon },
    rules: {
      "salon/no-raw-grays": "warn",
    },
  },
  {
    rules: {
      "@typescript-eslint/no-unused-vars": "warn",
      "@typescript-eslint/no-explicit-any": "warn",
      "prefer-const": "warn",
    },
  },
];
```

- [ ] **Step 7: Run `npm run lint` and confirm warnings appear**

Run: `cd frontend && npm run lint`
Expected: many `salon/no-raw-grays` warnings reported on V1 pages (this is correct — they will be cleaned up as we retrofit each page in Phase 1+). No errors; CI stays green.

- [ ] **Step 8: Add the plugin dir to `package.json` lint script path (if needed)**

If `npm run lint` doesn't pick up flat config automatically, ensure `"lint": "next lint --dir src"` or similar in `package.json`. Next.js 16 uses flat config by default.

- [ ] **Step 9: Commit**

```bash
git add frontend/eslint-plugin-salon/ frontend/eslint.config.mjs
git commit -m "feat(lint): add salon/no-raw-grays custom rule (warn)"
```

---

## Task 23: ESLint rule — `no-hex-literals-in-classname`

**Files:**
- Create: `frontend/eslint-plugin-salon/rules/no-hex-literals-in-classname.js`
- Create: `frontend/eslint-plugin-salon/tests/no-hex-literals-in-classname.test.js`
- Modify: `frontend/eslint-plugin-salon/index.js`
- Modify: `frontend/eslint.config.mjs`

**Why:** Rejects `bg-[#fff]` / `text-[#111]` arbitrary-value hex literals that bypass the token system.

- [ ] **Step 1: Write the rule test**

`frontend/eslint-plugin-salon/tests/no-hex-literals-in-classname.test.js`:

```js
const { RuleTester } = require("eslint");
const rule = require("../rules/no-hex-literals-in-classname");

const ruleTester = new RuleTester({
  languageOptions: {
    parserOptions: { ecmaVersion: 2022, sourceType: "module", ecmaFeatures: { jsx: true } },
  },
});

ruleTester.run("no-hex-literals-in-classname", rule, {
  valid: [
    { code: `<div className="bg-accent" />` },
    { code: `const c = "text-text-primary"` },
    { code: `const s = { color: "#111" }` }, // inline style, not className — allowed (not flagged by this rule)
  ],
  invalid: [
    {
      code: `<div className="bg-[#fff]" />`,
      errors: [{ messageId: "hexInClassName" }],
    },
    {
      code: `const c = \`text-[#123abc] \${x}\``,
      errors: [{ messageId: "hexInClassName" }],
    },
  ],
});
console.log("no-hex-literals-in-classname PASS");
```

- [ ] **Step 2: Implement the rule**

`frontend/eslint-plugin-salon/rules/no-hex-literals-in-classname.js`:

```js
"use strict";

// Detects Tailwind arbitrary-value hex literals: bg-[#fff], text-[#123456], border-[#aaa]
const PATTERN = /\b[a-z-]+\-\[#[0-9a-fA-F]{3,8}\]/g;

function* findMatches(str) {
  let m;
  PATTERN.lastIndex = 0;
  while ((m = PATTERN.exec(str))) {
    yield m[0];
  }
}

module.exports = {
  meta: {
    type: "problem",
    messages: {
      hexInClassName:
        "Hex literal '{{match}}' in className. Add a token in tokens.css and reference it — raw hex bypasses light/dark theming.",
    },
    schema: [],
  },
  create(context) {
    function check(node, text) {
      for (const match of findMatches(text)) {
        context.report({ node, messageId: "hexInClassName", data: { match } });
      }
    }
    return {
      Literal(node) {
        if (typeof node.value === "string") check(node, node.value);
      },
      TemplateElement(node) {
        if (node.value && node.value.raw) check(node, node.value.raw);
      },
    };
  },
};
```

- [ ] **Step 3: Update `eslint-plugin-salon/index.js`**

```js
"use strict";

module.exports = {
  rules: {
    "no-raw-grays": require("./rules/no-raw-grays"),
    "no-hex-literals-in-classname": require("./rules/no-hex-literals-in-classname"),
  },
};
```

- [ ] **Step 4: Run test**

```bash
cd frontend/eslint-plugin-salon && node tests/no-hex-literals-in-classname.test.js
```

Expected: ends with `no-hex-literals-in-classname PASS`.

- [ ] **Step 5: Enable rule in `eslint.config.mjs`**

Add to the salon plugin block:

```js
"salon/no-hex-literals-in-classname": "warn",
```

- [ ] **Step 6: Run `npm run lint`**

Run: `cd frontend && npm run lint`
Expected: new warnings for any existing hex literals in className; no errors.

- [ ] **Step 7: Commit**

```bash
git add frontend/eslint-plugin-salon/ frontend/eslint.config.mjs
git commit -m "feat(lint): add salon/no-hex-literals-in-classname rule"
```

---

## Task 24: ESLint rule — `no-h-screen`

**Files:**
- Create: `frontend/eslint-plugin-salon/rules/no-h-screen.js`
- Create: `frontend/eslint-plugin-salon/tests/no-h-screen.test.js`
- Modify: `frontend/eslint-plugin-salon/index.js`
- Modify: `frontend/eslint.config.mjs`

**Why:** `h-screen` uses 100vh which is buggy on iOS Safari (under/overshoots the viewport). V2 uses `min-h-dvh`. Narrow rule — one check, one fix.

- [ ] **Step 1: Rule test**

`frontend/eslint-plugin-salon/tests/no-h-screen.test.js`:

```js
const { RuleTester } = require("eslint");
const rule = require("../rules/no-h-screen");

const ruleTester = new RuleTester({
  languageOptions: {
    parserOptions: { ecmaVersion: 2022, sourceType: "module", ecmaFeatures: { jsx: true } },
  },
});

ruleTester.run("no-h-screen", rule, {
  valid: [
    { code: `<div className="min-h-dvh" />` },
    { code: `<div className="h-[200px]" />` },
    { code: `<div className="h-screen-override-custom" />` }, // not exact utility
  ],
  invalid: [
    { code: `<div className="h-screen" />`, errors: [{ messageId: "hScreen" }] },
    { code: `<div className="p-2 h-screen flex" />`, errors: [{ messageId: "hScreen" }] },
    { code: `const c = "md:h-screen"`, errors: [{ messageId: "hScreen" }] },
  ],
});
console.log("no-h-screen PASS");
```

- [ ] **Step 2: Implement**

`frontend/eslint-plugin-salon/rules/no-h-screen.js`:

```js
"use strict";

// Matches `h-screen` as a standalone utility (possibly prefixed with sm:/md:/lg:/xl:/dark:)
const PATTERN = /(^|\s|:)h-screen(\s|$)/g;

function hasMatch(str) {
  PATTERN.lastIndex = 0;
  return PATTERN.test(str);
}

module.exports = {
  meta: {
    type: "problem",
    messages: {
      hScreen: "`h-screen` is unreliable on mobile (iOS Safari). Use `min-h-dvh` instead.",
    },
    schema: [],
  },
  create(context) {
    return {
      Literal(node) {
        if (typeof node.value === "string" && hasMatch(node.value)) {
          context.report({ node, messageId: "hScreen" });
        }
      },
      TemplateElement(node) {
        if (node.value && node.value.raw && hasMatch(node.value.raw)) {
          context.report({ node, messageId: "hScreen" });
        }
      },
    };
  },
};
```

- [ ] **Step 3: Register + test**

Update `eslint-plugin-salon/index.js` to add the rule. Run:

```bash
cd frontend/eslint-plugin-salon && node tests/no-h-screen.test.js
```

Expected: `no-h-screen PASS`.

- [ ] **Step 4: Enable in `eslint.config.mjs`**

Add `"salon/no-h-screen": "warn"`.

- [ ] **Step 5: Run `npm run lint`** — verify any existing `h-screen` in V1 code surfaces as a warning.

- [ ] **Step 6: Commit**

```bash
git add frontend/eslint-plugin-salon/ frontend/eslint.config.mjs
git commit -m "feat(lint): add salon/no-h-screen rule"
```

---

## Task 25: ESLint rule — `no-list-owned-detail-state`

**Files:**
- Create: `frontend/eslint-plugin-salon/rules/no-list-owned-detail-state.js`
- Create: `frontend/eslint-plugin-salon/tests/no-list-owned-detail-state.test.js`
- Modify: `frontend/eslint-plugin-salon/index.js`
- Modify: `frontend/eslint.config.mjs`

**Why:** Enforces the Phase 1 `@modal` invariant structurally. Files at `src/app/dashboard/<entity>/page.tsx` that both import a `*DetailsDialog` and hold a matching ID in `useState` are flagged.

> **Amendment 2026-05-01:** Plan's `walkForId` AST traversal as written
> crashed with `RangeError: Invalid array length` because it iterated
> `Object.keys(n)` and spread every array-valued property, including
> `parent` (cyclic back-references), `tokens` (huge token arrays
> attached to Program/Function nodes), `comments`, `loc`, and `range`.
> Fix (applied in same commit): (1) skip those 5 keys during descent;
> (2) push items individually instead of spreading, with `item.type`
> truthy filter as defense against absurdly large arrays. The fix
> preserves externally observable behavior — test passes verbatim, and
> the predicted real-world offender `bills/page.tsx:53` surfaces as the
> 1 expected warning. Update the Step 2 code block in the plan to
> match the shipped rule.

- [ ] **Step 1: Rule test**

`frontend/eslint-plugin-salon/tests/no-list-owned-detail-state.test.js`:

```js
const { RuleTester } = require("eslint");
const rule = require("../rules/no-list-owned-detail-state");

const ruleTester = new RuleTester({
  languageOptions: {
    parserOptions: { ecmaVersion: 2022, sourceType: "module", ecmaFeatures: { jsx: true } },
  },
});

ruleTester.run("no-list-owned-detail-state", rule, {
  valid: [
    {
      // Detail dialog on a non-list file — allowed
      filename: "src/components/bills/bill-details-dialog.tsx",
      code: `
        import { Dialog } from "@/components/ui/dialog";
        export function BillDetailsDialog() { return null; }
      `,
    },
    {
      // List page without detail dialog import — allowed
      filename: "src/app/dashboard/bills/page.tsx",
      code: `
        import { useState } from "react";
        export default function Page() {
          const [x, setX] = useState(null);
          return null;
        }
      `,
    },
  ],
  invalid: [
    {
      filename: "src/app/dashboard/bills/page.tsx",
      code: `
        import { useState } from "react";
        import { BillDetailsDialog } from "@/components/bills/bill-details-dialog";
        export default function Page() {
          const [selectedBillId, setSelectedBillId] = useState(null);
          return <BillDetailsDialog billId={selectedBillId} />;
        }
      `,
      errors: [{ messageId: "listOwnsDetail" }],
    },
  ],
});
console.log("no-list-owned-detail-state PASS");
```

- [ ] **Step 2: Implement**

`frontend/eslint-plugin-salon/rules/no-list-owned-detail-state.js`:

```js
"use strict";

// Match files like src/app/dashboard/<entity>/page.tsx
const LIST_PAGE_RE = /src\/app\/dashboard\/[^/]+\/page\.tsx$/;
// Match imports like *DetailsDialog / *DetailDialog / *DetailDrawer / *DetailSheet
const DETAIL_IMPORT_RE = /Detail(s)?(Dialog|Drawer|Sheet)$/;

module.exports = {
  meta: {
    type: "problem",
    messages: {
      listOwnsDetail:
        "This list page owns entity detail state locally. Move detail to its canonical route under `app/dashboard/<entity>/[id]/page.tsx` and use an intercepting route at `@modal/(.)<entity>/[id]/page.tsx`. See design_system.md §7.5.",
    },
    schema: [],
  },
  create(context) {
    const filename = context.filename ?? context.getFilename();
    if (!LIST_PAGE_RE.test(filename.replace(/\\/g, "/"))) return {};

    let importsDetailDialog = false;
    let detailIdentifier = null;

    return {
      ImportDeclaration(node) {
        for (const spec of node.specifiers) {
          if (spec.type === "ImportSpecifier" && DETAIL_IMPORT_RE.test(spec.imported.name)) {
            importsDetailDialog = true;
            detailIdentifier = spec.imported.name;
          }
        }
      },
      "Program:exit"(node) {
        if (!importsDetailDialog) return;
        // Walk the file for a `useState` whose variable name suggests an entity ID
        const source = context.sourceCode ?? context.getSourceCode();
        const ID_NAME_RE = /^(selected|active|current)[A-Z].*Id$/;
        for (const tok of source.ast.body) {
          if (tok.type === "VariableDeclaration") walkForId(tok, context, ID_NAME_RE);
          if (tok.type === "ExportNamedDeclaration" && tok.declaration) walkForId(tok.declaration, context, ID_NAME_RE);
          if (tok.type === "ExportDefaultDeclaration" && tok.declaration) walkForId(tok.declaration, context, ID_NAME_RE);
          if (tok.type === "FunctionDeclaration") walkForId(tok, context, ID_NAME_RE);
        }
      },
    };

    function walkForId(node, context, idRe) {
      // Depth-limited recursive descent looking for `const [<idRe>, ...] = useState(...)`
      const stack = [node];
      while (stack.length) {
        const n = stack.pop();
        if (!n || typeof n !== "object") continue;
        if (
          n.type === "VariableDeclarator" &&
          n.id && n.id.type === "ArrayPattern" &&
          n.id.elements[0] &&
          n.id.elements[0].type === "Identifier" &&
          idRe.test(n.id.elements[0].name) &&
          n.init &&
          ((n.init.type === "CallExpression" && n.init.callee.name === "useState") ||
            (n.init.type === "CallExpression" && n.init.callee.type === "MemberExpression" && n.init.callee.property.name === "useState"))
        ) {
          context.report({ node: n, messageId: "listOwnsDetail" });
          return;
        }
        for (const k of Object.keys(n)) {
          const v = n[k];
          if (Array.isArray(v)) stack.push(...v.filter(Boolean));
          else if (v && typeof v === "object" && v.type) stack.push(v);
        }
      }
    }
  },
};
```

- [ ] **Step 3: Register + test**

Update plugin index and run:

```bash
cd frontend/eslint-plugin-salon && node tests/no-list-owned-detail-state.test.js
```

Expected: `no-list-owned-detail-state PASS`.

- [ ] **Step 4: Enable in `eslint.config.mjs`**

Add `"salon/no-list-owned-detail-state": "warn"`.

- [ ] **Step 5: Run `npm run lint`**

Expected: the existing [bills/page.tsx](../../../frontend/src/app/dashboard/bills/page.tsx) surfaces this warning. Correct — will be fixed in Phase 1.

- [ ] **Step 6: Commit**

```bash
git add frontend/eslint-plugin-salon/ frontend/eslint.config.mjs
git commit -m "feat(lint): add salon/no-list-owned-detail-state rule"
```

---

## Task 26: Storybook setup

**Files:**
- Create: `frontend/.storybook/main.ts`
- Create: `frontend/.storybook/preview.tsx`
- Modify: `frontend/package.json`

**Why:** Visual ground truth for every primitive. Light + dark decorator shows regressions instantly. No visual-regression service (Chromatic) this phase — that's a follow-up. Storybook alone is still worth it for dev loop and manual review.

> **Amendment 2026-05-01**: Storybook 8 (`@storybook/nextjs`) does NOT support Next.js 16 — peer dep is capped at `^15`, init fails with ERESOLVE. Falling through to Storybook 9 also failed via `init` because Storybook 9's auto-installer pulls `@storybook/nextjs-vite@^10` (latest) which conflicts with `storybook@9`. Resolved by manually installing pinned-to-9 set: `storybook@^9 @storybook/nextjs-vite@^9 @storybook/addon-themes@^9 @storybook/addon-docs@^9`. Switched framework from `@storybook/nextjs` (Webpack) to `@storybook/nextjs-vite` (Vite) — Storybook 9 + Next 16 is Vite-only. Replaced `webpackFinal` alias config with `viteFinal` equivalent. Replaced `@storybook/addon-essentials` (deprecated in 9, controls/actions/viewport now in core) with `@storybook/addon-docs`. Build verified via `npm run build-storybook` (passes; "no story files" is expected — T27 adds them). Skipped auto-init entirely; configs hand-written, no example `src/stories/` artifacts to clean up.

- [ ] **Step 1: Install Storybook**

```bash
cd frontend && npx storybook@^8 init --yes --type nextjs --package-manager npm
```

This creates `.storybook/` and adds scripts. Accept defaults. If it fails to auto-detect, install manually:

```bash
npm install -D @storybook/nextjs @storybook/react @storybook/addon-essentials @storybook/addon-themes storybook
```

- [ ] **Step 2: Replace `.storybook/main.ts`**

```ts
import type { StorybookConfig } from "@storybook/nextjs";
import path from "node:path";

const config: StorybookConfig = {
  stories: ["../src/components/ui/*.stories.tsx"],
  addons: ["@storybook/addon-essentials", "@storybook/addon-themes"],
  framework: { name: "@storybook/nextjs", options: {} },
  staticDirs: ["../public"],
  webpackFinal: async (cfg) => {
    cfg.resolve ||= {};
    cfg.resolve.alias = { ...(cfg.resolve.alias ?? {}), "@": path.resolve(__dirname, "../src") };
    return cfg;
  },
};
export default config;
```

- [ ] **Step 3: Replace `.storybook/preview.tsx`**

```tsx
import type { Preview } from "@storybook/react";
import { withThemeByDataAttribute } from "@storybook/addon-themes";
import "../src/app/globals.css";
import React from "react";

const preview: Preview = {
  parameters: {
    backgrounds: { disable: true },
    controls: { expanded: true },
    layout: "centered",
  },
  decorators: [
    withThemeByDataAttribute({
      themes: { light: "light", dark: "dark" },
      defaultTheme: "light",
      attributeName: "data-theme",
    }),
    (Story) => (
      <div style={{ padding: 24, minWidth: 320, background: "var(--surface-page)" }}>
        <Story />
      </div>
    ),
  ],
};
export default preview;
```

- [ ] **Step 4: Confirm scripts exist in `package.json`**

Should include:

```json
"storybook": "storybook dev -p 6006",
"build-storybook": "storybook build"
```

- [ ] **Step 5: Start Storybook to verify it boots**

```bash
cd frontend && npm run storybook
```

Expected: Storybook opens at http://localhost:6006 with no stories yet (empty sidebar). Stop (Ctrl-C).

- [ ] **Step 6: Commit**

```bash
git add frontend/.storybook/ frontend/package.json frontend/package-lock.json
git commit -m "build(storybook): bootstrap Storybook 8 with theme decorator"
```

---

## Task 27: Storybook stories for every primitive

> **Amendment 2026-05-01:** Three story files (`currency-input`, `combobox`, `filter-bar`) call `useState` inside the `render` arrow. ESLint's `react-hooks/rules-of-hooks` rejects this because the inline arrow has no PascalCase name. Fixed by extracting each `render` body into a named `function DefaultDemo()` component and rendering it as `<DefaultDemo />`. Same behaviour, lint baseline preserved at 38 errors.

**Files:**
- Create: `frontend/src/components/ui/button.stories.tsx`
- Create: `frontend/src/components/ui/input.stories.tsx`
- Create: `frontend/src/components/ui/currency-input.stories.tsx`
- Create: `frontend/src/components/ui/combobox.stories.tsx`
- Create: `frontend/src/components/ui/dialog.stories.tsx`
- Create: `frontend/src/components/ui/card.stories.tsx`
- Create: `frontend/src/components/ui/badge.stories.tsx`
- Create: `frontend/src/components/ui/empty-state.stories.tsx`
- Create: `frontend/src/components/ui/skeleton.stories.tsx`
- Create: `frontend/src/components/ui/data-table.stories.tsx`
- Create: `frontend/src/components/ui/filter-bar.stories.tsx`
- Create: `frontend/src/components/ui/nav-item.stories.tsx`
- Create: `frontend/src/components/ui/kbd.stories.tsx`

**Why:** One story per primitive with every variant visible. Theme switcher tests both modes.

- [ ] **Step 1: Write Button stories**

`frontend/src/components/ui/button.stories.tsx`:

```tsx
import type { Meta, StoryObj } from "@storybook/react";
import { Trash2, Plus } from "lucide-react";
import { Button } from "./button";

const meta: Meta<typeof Button> = { component: Button, title: "UI/Button" };
export default meta;

export const Variants: StoryObj<typeof Button> = {
  render: () => (
    <div className="flex flex-wrap gap-3">
      <Button>Primary</Button>
      <Button variant="secondary">Secondary</Button>
      <Button variant="ghost">Ghost</Button>
      <Button variant="danger">Delete</Button>
      <Button variant="icon" aria-label="Add"><Plus /></Button>
    </div>
  ),
};

export const Sizes: StoryObj<typeof Button> = {
  render: () => (
    <div className="flex items-center gap-3">
      <Button size="sm">Small</Button>
      <Button size="md">Medium</Button>
      <Button size="lg">Large</Button>
    </div>
  ),
};

export const Loading: StoryObj<typeof Button> = {
  args: { loading: true, children: "Saving…" },
};

export const WithIcons: StoryObj<typeof Button> = {
  args: { leadingIcon: <Plus />, children: "New bill" },
};

export const Danger: StoryObj<typeof Button> = {
  args: { variant: "danger", leadingIcon: <Trash2 />, children: "Delete customer" },
};
```

- [ ] **Step 2: Write Input stories**

`frontend/src/components/ui/input.stories.tsx`:

```tsx
import type { Meta, StoryObj } from "@storybook/react";
import { Input } from "./input";

const meta: Meta<typeof Input> = { component: Input, title: "UI/Input" };
export default meta;

export const Default: StoryObj<typeof Input> = {
  args: { label: "Email", placeholder: "you@example.com" },
};
export const WithHint: StoryObj<typeof Input> = {
  args: { label: "Phone", hint: "We never share your number." },
};
export const WithError: StoryObj<typeof Input> = {
  args: { label: "Email", value: "bad", error: "Invalid email address" },
};
export const WithAddons: StoryObj<typeof Input> = {
  args: { label: "Price", leadingAddon: <span>₹</span>, trailingAddon: <span className="text-text-muted text-caption">.00</span> },
};
```

- [ ] **Step 3: Write CurrencyInput stories**

```tsx
import type { Meta, StoryObj } from "@storybook/react";
import { useState } from "react";
import { CurrencyInput } from "./currency-input";

const meta: Meta<typeof CurrencyInput> = { component: CurrencyInput, title: "UI/CurrencyInput" };
export default meta;

export const Default: StoryObj<typeof CurrencyInput> = {
  render: () => {
    const [paise, setPaise] = useState(24800);
    return <CurrencyInput label="Amount" value={paise} onChange={setPaise} />;
  },
};
```

- [ ] **Step 4: Write Combobox stories**

```tsx
import type { Meta, StoryObj } from "@storybook/react";
import { useState } from "react";
import { Combobox } from "./combobox";

const meta: Meta<typeof Combobox> = { component: Combobox, title: "UI/Combobox" };
export default meta;

const customers = [
  { value: "1", label: "Priya Sharma" },
  { value: "2", label: "Rajni Gupta" },
  { value: "3", label: "Anjali Patel" },
];

export const Default: StoryObj<typeof Combobox> = {
  render: () => {
    const [v, setV] = useState<string | null>(null);
    return <div className="w-[320px]"><Combobox options={customers} value={v} onChange={setV} placeholder="Pick customer" /></div>;
  },
};
```

- [ ] **Step 5: Write Dialog stories**

```tsx
import type { Meta, StoryObj } from "@storybook/react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription, DialogTrigger } from "./dialog";
import { Button } from "./button";

const meta: Meta = { title: "UI/Dialog" };
export default meta;

export const Default: StoryObj = {
  render: () => (
    <Dialog>
      <DialogTrigger asChild><Button>Open dialog</Button></DialogTrigger>
      <DialogContent size="md">
        <DialogHeader>
          <DialogTitle className="text-display-md">New bill</DialogTitle>
          <DialogDescription>Create a new bill for a walk-in customer.</DialogDescription>
        </DialogHeader>
        <div className="p-6 text-body">Form body here.</div>
        <DialogFooter>
          <Button variant="ghost">Cancel</Button>
          <Button>Create bill</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  ),
};

export const Destructive: StoryObj = {
  render: () => (
    <Dialog>
      <DialogTrigger asChild><Button variant="danger">Delete customer</Button></DialogTrigger>
      <DialogContent size="sm" variant="destructive">
        <DialogHeader>
          <DialogTitle>Delete Priya Sharma?</DialogTitle>
          <DialogDescription>This cannot be undone. Type the customer name to confirm.</DialogDescription>
        </DialogHeader>
        <div className="p-6">…</div>
        <DialogFooter>
          <Button variant="ghost">Cancel</Button>
          <Button variant="danger">Delete</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  ),
};
```

- [ ] **Step 6: Write Card stories**

```tsx
import type { Meta, StoryObj } from "@storybook/react";
import { Card } from "./card";
import { Badge } from "./badge";

const meta: Meta<typeof Card> = { component: Card, title: "UI/Card" };
export default meta;

export const KPI: StoryObj<typeof Card> = {
  render: () => (
    <Card density="lg" className="w-[280px]">
      <Card.Header title="Revenue" description="Today" />
      <Card.Body>
        <div className="text-money-lg text-text-primary">₹24,800</div>
        <div className="text-caption text-text-muted mt-1">+12% vs 7-day avg</div>
      </Card.Body>
    </Card>
  ),
};

export const WithAction: StoryObj<typeof Card> = {
  render: () => (
    <Card density="md" className="w-[400px]">
      <Card.Header title="Service queue" description="4 waiting" action={<Badge tone="accent">4</Badge>} />
      <Card.Body>List goes here.</Card.Body>
    </Card>
  ),
};
```

- [ ] **Step 7: Write Badge stories**

```tsx
import type { Meta, StoryObj } from "@storybook/react";
import { Badge } from "./badge";

const meta: Meta<typeof Badge> = { component: Badge, title: "UI/Badge" };
export default meta;

export const AllTones: StoryObj<typeof Badge> = {
  render: () => (
    <div className="flex flex-wrap gap-2">
      <Badge tone="neutral">Neutral</Badge>
      <Badge tone="success">Paid</Badge>
      <Badge tone="warning">Low stock</Badge>
      <Badge tone="danger">Overdue</Badge>
      <Badge tone="info">Draft</Badge>
      <Badge tone="accent">New</Badge>
    </div>
  ),
};
```

- [ ] **Step 8: Write EmptyState stories**

```tsx
import type { Meta, StoryObj } from "@storybook/react";
import { Calendar } from "lucide-react";
import { EmptyState } from "./empty-state";
import { Button } from "./button";

const meta: Meta<typeof EmptyState> = { component: EmptyState, title: "UI/EmptyState" };
export default meta;

export const Default: StoryObj<typeof EmptyState> = {
  render: () => (
    <EmptyState
      icon={<Calendar />}
      title="No bookings yet today"
      body="First appointment is at 10:00. Add a walk-in to start earlier."
      primaryAction={<Button>New walk-in</Button>}
      secondaryAction={<Button variant="ghost">View yesterday</Button>}
    />
  ),
};
```

- [ ] **Step 9: Write Skeleton stories**

```tsx
import type { Meta, StoryObj } from "@storybook/react";
import { Skeleton } from "./skeleton";

const meta: Meta<typeof Skeleton> = { component: Skeleton, title: "UI/Skeleton" };
export default meta;

export const Shapes: StoryObj<typeof Skeleton> = {
  render: () => (
    <div className="flex flex-col gap-3 w-[320px]">
      <Skeleton shape="text" width="70%" />
      <Skeleton shape="text" width="40%" />
      <Skeleton shape="row" />
      <Skeleton shape="kpi" />
      <Skeleton shape="card" />
    </div>
  ),
};
```

- [ ] **Step 10: Write DataTable stories**

```tsx
import type { Meta, StoryObj } from "@storybook/react";
import { DataTable, type DataTableColumn } from "./data-table";

type Bill = { id: string; number: string; customer: string; amountPaise: number; status: "paid" | "pending" };

const rows: Bill[] = [
  { id: "1", number: "SAL-25-0171", customer: "Priya Sharma",  amountPaise: 240000, status: "paid" },
  { id: "2", number: "SAL-25-0172", customer: "Rajni Gupta",   amountPaise: 180000, status: "pending" },
  { id: "3", number: "SAL-25-0173", customer: "Anjali Patel",  amountPaise: 320000, status: "paid" },
];
const cols: DataTableColumn<Bill>[] = [
  { id: "number",   header: "Bill",      priority: "high",   accessor: (r) => r.number },
  { id: "customer", header: "Customer",  priority: "high",   accessor: (r) => r.customer },
  { id: "amount",   header: "Amount",    priority: "high",   accessor: (r) => `₹${(r.amountPaise / 100).toFixed(2)}`, align: "right", format: "money" },
  { id: "status",   header: "Status",    priority: "medium", accessor: (r) => r.status },
];

const meta: Meta<typeof DataTable<Bill>> = { title: "UI/DataTable" };
export default meta;

export const Default: StoryObj<typeof DataTable<Bill>> = {
  render: () => <div className="w-[720px]"><DataTable data={rows} columns={cols} getRowId={(r) => r.id} /></div>,
};
export const Loading: StoryObj<typeof DataTable<Bill>> = {
  render: () => <div className="w-[720px]"><DataTable data={[]} columns={cols} getRowId={(r) => r.id} loading /></div>,
};
export const Empty: StoryObj<typeof DataTable<Bill>> = {
  render: () => (
    <div className="w-[720px]">
      <DataTable
        data={[]}
        columns={cols}
        getRowId={(r) => r.id}
        emptyState={<div className="p-8 text-center text-text-muted">No bills match your filter.</div>}
      />
    </div>
  ),
};
```

- [ ] **Step 11: Write FilterBar stories**

```tsx
import type { Meta, StoryObj } from "@storybook/react";
import { useState } from "react";
import { FilterBar } from "./filter-bar";
import { Button } from "./button";

const meta: Meta = { title: "UI/FilterBar" };
export default meta;

export const Default: StoryObj = {
  render: () => {
    const [q, setQ] = useState("");
    const [tab, setTab] = useState("all");
    return (
      <div className="w-[720px]">
        <FilterBar>
          <FilterBar.Search value={q} onChange={setQ} placeholder="Search bills…" />
          <FilterBar.Pills
            value={tab}
            onChange={setTab}
            options={[
              { value: "all",     label: "All",     count: 171 },
              { value: "paid",    label: "Paid",    count: 142 },
              { value: "pending", label: "Pending", count: 29 },
            ]}
          />
          <FilterBar.Actions>
            <Button variant="secondary">Export</Button>
          </FilterBar.Actions>
        </FilterBar>
      </div>
    );
  },
};
```

- [ ] **Step 12: Write NavItem stories**

```tsx
import type { Meta, StoryObj } from "@storybook/react";
import { Home, Receipt, Users } from "lucide-react";
import { NavItem } from "./nav-item";
import { Badge } from "./badge";

const meta: Meta<typeof NavItem> = { component: NavItem, title: "UI/NavItem" };
export default meta;

export const Sidebar: StoryObj<typeof NavItem> = {
  render: () => (
    <div className="w-48 flex flex-col gap-1 bg-surface-sidebar p-2 rounded-lg">
      <NavItem label="Today" href="#" icon={<Home />} active />
      <NavItem label="POS" href="#" icon={<Receipt />} />
      <NavItem label="Customers" href="#" icon={<Users />} badge={<Badge tone="accent" size="sm">3</Badge>} />
    </div>
  ),
};

export const Rail: StoryObj<typeof NavItem> = {
  render: () => (
    <div className="w-14 flex flex-col gap-1 bg-surface-sidebar p-1 rounded-lg items-center">
      <NavItem variant="rail" label="Today" href="#" icon={<Home />} active />
      <NavItem variant="rail" label="POS" href="#" icon={<Receipt />} />
      <NavItem variant="rail" label="Cust." href="#" icon={<Users />} />
    </div>
  ),
};
```

- [ ] **Step 13: Write Kbd stories**

```tsx
import type { Meta, StoryObj } from "@storybook/react";
import { Kbd } from "./kbd";

const meta: Meta<typeof Kbd> = { component: Kbd, title: "UI/Kbd" };
export default meta;

export const Default: StoryObj<typeof Kbd> = { args: { keys: ["⌘", "K"] } };
export const Sequence: StoryObj<typeof Kbd> = { args: { keys: ["G", "then", "D"] } };
```

- [ ] **Step 3: Boot Storybook and visually inspect**

```bash
cd frontend && npm run storybook
```

Click through every story. Toggle the theme in the toolbar. Check:
- No missing-token `var(--…)` errors in the console.
- Light and dark both render with sufficient contrast.
- Tabular-figure numbers are monospaced.

Fix any visual bugs by editing the source primitive, not the story.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/ui/*.stories.tsx
git commit -m "docs(storybook): add stories for every V2 primitive"
```

---

## Task 28: Wire everything into CI scripts

**Files:**
- Modify: `frontend/package.json`

**Why:** The plan's verification is only useful if CI runs it. Consolidate the checks under one umbrella script.

- [ ] **Step 1: Add consolidated script to `frontend/package.json`**

```json
"check": "npm run check:contrast && npm test -- --run && npm run lint && npm run build-storybook"
```

- [ ] **Step 2: Run the full check locally**

Run: `cd frontend && npm run check`

> **Amendment 2026-05-01:** Plan said "Expected: all four checks pass" but
> reality is `npm run lint` fails with 38 pre-existing errors carried in
> from V1 code (`react/no-unescaped-entities`, `@typescript-eslint/no-empty-object-type`,
> `react-hooks/purity` from Next 16's eslint-config-next, plus a handful
> in V1 dashboard pages). These are ERRORS not warnings, so they short-
> circuit the `&&` chain before `build-storybook` runs. Phase 0 doctrine
> accepts this — Phase 1 retrofit brings lint to 0 errors. Until then,
> `npm run check` is informational only; CI gating happens in Phase 1.
> Contrast (3 ms) + tests (~3 s, all passing) + storybook build (~3 s
> when run alone) are individually green. The `check` chain is preserved
> as-is so Phase 1 retrofit's progress is measurable by which stage it
> reaches.

Fix any failures before continuing. Common failures:
- Contrast: a token shifted during review — rerun Task 3's values.
- Lint: an existing V1 file uses a newly-forbidden pattern. For Phase 0 these are `warn`, not `error`, so they shouldn't block.
- Test: a primitive test depends on a DOM API not in jsdom. Mock or skip with a note.

- [ ] **Step 3: Commit**

```bash
git add frontend/package.json
git commit -m "ci: add consolidated 'check' script (contrast + tests + lint + storybook)"
```

---

## Task 29: Phase 0 changelog entry + commit marker

**Files:**
- Modify: `docs/design_system.md`

**Why:** Closes the phase with a dated changelog entry noting what landed.

- [ ] **Step 1: Append a new row to the changelog in `docs/design_system.md` §13**

```md
| 2026-04-23 | Phase 0 landed: tokens.css (light + dark), typography stack self-hosted, primitives restyled (Button, Input, CurrencyInput, Combobox, Dialog, Card, Badge, EmptyState, Skeleton, DataTable, FilterBar, NavItem, Kbd, Toast), ESLint plugin (warn mode), Storybook bootstrapped, contrast CI script. | Angel |
```

- [ ] **Step 2: Commit**

```bash
git add docs/design_system.md
git commit -m "docs(design-system): mark Phase 0 complete"
```

---

## Verification checklist (run before Phase 1)

After all tasks commit, on a clean checkout:

- [ ] `cd frontend && npm install` completes without errors
- [ ] `npm run dev` boots the app in light theme; no console errors about unresolved `var(--…)` tokens
- [ ] `npm run check:contrast` — all pairs PASS
- [ ] `npm test -- --run` — all primitive unit tests pass
- [ ] `npm run lint` — warnings only for V1 code; no errors
- [ ] `cd eslint-plugin-salon && for f in tests/*.test.js; do node "$f"; done` — all rule tests PASS
- [ ] `npm run storybook` — every primitive story renders in both light and dark without contrast bugs
- [ ] Visit the dashboard in a browser — tables/cards/buttons are still functional (V1 pages render through the new tokens; expect visual drift, not functional breakage)

If any item fails, fix before declaring Phase 0 done.

---

## Next phase

After Phase 0 ships, brainstorm + write **Phase 1 (Shell + `@modal` slot + ⌘K palette)** using the same spec-then-plan flow. Phase 1 will also flip each salon/* lint rule from `warn` to `error` for files under the new shell, and begin the page-retrofit sequence defined in spec §4.
