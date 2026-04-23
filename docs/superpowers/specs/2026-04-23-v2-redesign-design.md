# SalonOS V2 — Redesign Design Spec

**Status:** Draft — pending review
**Date:** 2026-04-23
**Author:** Brainstormed by Angel + Claude

---

## 1. Executive summary

V1 of SalonOS shipped feature-by-feature. The result is an app without an enforced design language: tables drift into card lists, a partial dark-theme migration left legacy Tailwind grays at 1.02 contrast on the dashboard, POS renders as a wall of white cards on dark chrome, and destructive delete icons live permanently in customer rows. The audit found 9 contrast-rule violations on the dashboard alone and 65+ responsive issues already documented in `docs/audits/01-mobile-responsiveness-audit.md`.

V2 is not a reskin. It is the **introduction of a strict design system** — tokens, primitives, and layout shell treated as shippable infrastructure — followed by page-by-page retrofit behind that system. The end goal is one sentence: **the staff open the app and feel fresh and productive.**

---

## 2. Design direction (the locked decisions)

Each bullet is a constraint on every page V2 ships.

| Axis | Decision | Why |
|---|---|---|
| **Primary lens** | Speed × Premium | Staff spend 8h/day in the app; the UI must be fast *and* earn pride. Neither dimension wins over the other — they compound. |
| **Theme** | Light-default, dark opt-in. Dual-mode. | Salons work in daylight + fluorescent light. Light is better for receipts, print, and non-technical staff. Dark stays first-class for owners who prefer it. |
| **Sequencing** | Shell + tokens first (as infra), then pages. | V1 drifted because the design system lived in page code. V2 ships the system *before* the pages so drift is structurally impossible. |
| **Navigation shell** | Labelled sidebar (192px) → collapsible to 56px icon rail via `⌘\`. ⌘K command palette on top. Mobile keeps bottom-tab nav. | Rotating non-technical staff need label-visible nav. Power users get the rail + palette. Scales as sections grow. |
| **Personality** | Quietly branded. | Think Linear / Vercel / Notion — restraint with a single signature accent. Not neutral-tool (too cold), not expressively-branded (risk of kitsch). |
| **Accent** | Copper `#b0561f`. Multi-accent (`violet/rose/amber/teal`) retired. | Hospitality-coded warmth. Lowest-risk way to signal "not generic SaaS." Dark variant to be calibrated. |
| **Typography** | Display: Instrument Serif (titles, empty-state headlines, auth screen). Body: Inter. Tabular lining figures everywhere money appears. Receipt print template keeps its existing font. | Serif on titles costs nothing in density (rare usage) but instantly reframes the app as hospitality product. |
| **Density** | 4px grid, 8px rhythm. Row height 36px default. Page gutter 24/16/12 (desktop/tablet/mobile). | Between "dense" and "comfy." Works on 14" laptops and on tablet/POS terminals. |
| **Motion** | Considered, sub-200ms, no decorative motion. Page 120ms, state 80ms, modal/drawer 180ms spring. Respects `prefers-reduced-motion`. | Fast muscle memory without a showy "feel." |
| **Charts** | Tremor (built on existing Recharts dep). Recharts stays for custom cases. | Consistent dashboard visual language in one place, no new dep. |
| **Entity routing** | Every entity with a detail view (bill, customer, invoice, SKU, purchase, appointment) has a canonical URL at `/<entity>/[id]`. From a list page, the route is intercepted and renders as a peek dialog; from the palette / Today / a cold URL, it renders as a full page. | Palette can send you anywhere. Deep links work (WhatsApp-shareable). Browser back button behaves. One source of truth — detail state is never owned by a list page's local `useState`. |
| **Copy voice** | Hospitality-adjacent, not cute. "Today" replaces "Dashboard" in nav. "Customers" everywhere (no "Guests" split). Empty states guide the next action. | Warm but functional. "Customers" is what staff already say — don't invent vocabulary. |

---

## 3. Design system — scope

The V2 design system is a first-class deliverable with its own phase. It is **not** a Figma library — it is code (tokens + primitives + layout shell), version-controlled, with enforcement.

### 3.1 Tokens

Single source of truth for every surface, text, and accent colour. All pages must route through tokens; no raw Tailwind gray utilities, no hex literals outside the token file.

Token families:

- `surface` — `page`, `card`, `row`, `row-hover`, `sidebar`, `overlay`
- `border` — `subtle`, `default`, `strong`, `focus`
- `text` — `primary`, `secondary`, `muted`, `disabled`, `inverse`
- `accent` — `default`, `hover`, `active`, `bg-soft`, `fg-on-accent`
- `semantic` — `success`, `warning`, `danger`, `info` (each with `fg`, `bg-soft`, `border`)
- `data-viz` — `series-1` through `series-6`, chosen for colourblind safety

Each family has a light and dark resolution. The light resolution is authoritative; dark is tuned to match perceived contrast, not to mirror values.

Contrast targets:
- Body text vs surface: **≥ 4.5:1** (WCAG AA)
- Large text (18px+ or 14px bold): **≥ 3:1**
- Non-text UI (focus rings, icons): **≥ 3:1**

A lint rule (or CI script) rejects any component that references a Tailwind gray utility directly. This is the structural mechanism that prevents V1's "legacy gray" regression.

### 3.2 Primitives

Every page composes from these. No page ships a bespoke input, button, or dialog.

- **Button** (primary, secondary, ghost, danger, icon; sm/md/lg)
- **Input** (text, number, currency — with tabular figures)
- **Select / Combobox** (shadcn `Select` retained, restyled)
- **Dialog / Drawer / Sheet** — sized responsively, `max-h: 90dvh`, mobile slides up
- **Table shell** — sort, zebra, hover row, totals row, pagination, sticky header, mobile card variant
- **Card** — surface + border + spacing token; three densities (sm/md/lg)
- **Badge** — status (using semantic tokens), count, accent
- **EmptyState** — icon + title (Instrument Serif) + guiding body + CTA
- **Skeleton** — standardized shapes: `text`, `row`, `card`, `kpi`. Always used; no blank loading states.
- **Toast** — sonner, restyled; persistent for destructive/irreversible actions
- **FilterBar** — search + pill filters + date range + export (reused across Bills, Inventory, Customers, Purchases)

### 3.3 Layout shell

- Sidebar (192px labelled) with grouped sections: **Today's work** (Dashboard / POS / Bills / Appointments) · **Ledger** (Customers / Inventory / Purchases / Expenses / Cash Drawer / EOD Reconciliation) · **Insight** (Reports / Profit & Loss / Attendance) · **Admin** (Users & Staff / Services / Settings).
- Collapsible to 56px icon rail via `⌘\`, persisted in local storage.
- Sticky top bar: breadcrumb + global search (⌘K trigger) + user menu. Breadcrumb is real (`Today / Bills / Invoice SAL-25-0171`), not decorative.
- Mobile: bottom-tab nav (4 items: Today / POS / Bills / More). More opens a sheet with the rest.
- Content viewport uses `min-h-dvh` (no `100vh`).

### 3.4 Command palette (⌘K)

Global, keyboard-driven. Actions: navigate, quick-search customers / bills / SKUs, start new bill, open cash drawer, toggle theme. Opens on `⌘K` (Mac) / `Ctrl+K` (Win). Persisted history.

---

## 4. Page retrofit sequence

| Phase | Ships | Why this order |
|---|---|---|
| **0. Infra** | Design tokens + primitives library + lint rule | Nothing can retrofit without this. |
| **1. Shell** | New sidebar + top bar + layout shell + ⌘K palette + `@modal` parallel slot applied to all pages. V1 page bodies sit inside the new frame unchanged. | All pages immediately feel "inside V2" even before their content is retrofitted. The `@modal` slot is infra — every subsequent page retrofit uses it. |
| **2. Appointments (native V2)** | Ships the calendar / time-grid / staff-swimlane primitive that Attendance and Staff Queue will later reuse. | Zero migration risk (page does not exist yet). Hardest visual pattern in the app — proves the system under realistic pressure. |
| **3. Dashboard** | Easiest visual win; showcases the system. Kills the remaining legacy-gray contrast bugs. | Low-risk retrofit of a read-only page. Builds confidence after Phase 2. |
| **4. POS** | The Saturday-rush test. Replaces the wall-of-white-cards with a search-first, keyboard-driven service picker. | Highest daily value. Validates speed dimension of the lens. |
| **5. Bills** | The canonical table pattern. Every subsequent list page (Customers, Inventory, Purchases, Expenses, Users & Staff) copies this template. | One table done right = five tables done right. |
| **6. Ledger pages** | Customers, Inventory, Purchases, Expenses, Cash Drawer, EOD Reconciliation follow the Bills template. | Mostly mechanical once the template exists. |
| **7. Insight + Admin** | Reports, P&L, Attendance, Services, Users & Staff, Settings. | Tail end — least daily use, most tolerant of later landing. |

Phases ship serially. Each phase is approved by the user before the next starts.

---

## 5. V1 issues V2 must structurally prevent

These are the recurring V1 failure modes. V2's structural answers are listed — not as page fixes but as system invariants.

| V1 failure | V2 invariant |
|---|---|
| Legacy Tailwind grays at 1.02 contrast on cards (text-gray-900 on #161616) | Lint rule: no raw `text-gray-*` in app/components. All color via tokens. |
| Dialogs overflow mobile viewport (max-w-4xl default) | Dialog primitive enforces responsive `max-w` and `max-h: 90dvh`. |
| Tables don't convert to mobile cards | Table shell primitive ships a mobile card fallback by default; page opts out explicitly. |
| Always-visible delete icons in rows | Destructive actions live behind a row action menu, not in the toolbar. |
| POS cards visually undifferentiated from each other | Services grouped by category with collapsed/expanded state; search-first; recent + frequent boosted to top; keyboard-navigable. |
| 4 KPI cards of "0" with no guidance | Empty states are a primitive with required headline + body + CTA. Dashboard "0 revenue today" shows why ("drawer not opened yet") not just the number. |
| Two list patterns (table vs cards) | One canonical list primitive. Card view is a `<Table density="mobile">` variant, not a different component. |
| Inconsistent accent usage (danger red for filter tabs, accent violet for invoice numbers) | Accent ↔ role mapping in token layer. Semantic tokens (danger, warning) never leak into decorative usage. |
| Inconsistent loading states (spinner / blank / none) | Skeleton primitive, always used. Blank render is a bug. |
| Hardcoded column widths in tables | Table primitive manages width; page passes column priorities, not pixels. |
| Bottom nav overlaps mobile dashboard donut charts | Layout shell reserves bottom-nav height in `pb-` padding on mobile content region. |
| Bill/customer detail lives in list page's local `useState` — palette has nowhere to send you, no deep links, back button does nothing | Every entity detail is a real route. `@modal` parallel slot + intercepting routes render it as a dialog when launched from the list, and as a full page otherwise. Detail state is URL-owned, not page-owned. |

---

## 6. Appointments page (Phase 2) — scope preview

This is the first page designed natively in V2 and the proving ground for the system. It is *not* specced in detail here — a separate spec will follow — but the shape is:

- **Day / Week views** as primary. Month as overview only.
- **Staff swimlanes** in Day view — each column is a stylist; rows are time slots.
- **Drag-to-reschedule**, **drag-to-resize duration**, **click empty slot to create**.
- **Service-type colouring** via data-viz tokens, not accent.
- **Conflict detection** (double-booking / outside hours / on-break) rendered inline.
- **Keyboard shortcuts**: `n` new, `←/→` day nav, `g w` go week, `g d` go day.
- **Mobile**: day view only, horizontal scroll across staff.

The calendar/time-grid primitive built here feeds Attendance and Staff Queue in later phases.

---

## 7. Non-goals (explicit)

- **Not a backend redesign.** V2 is frontend-only. API contracts stay.
- **Not a feature expansion.** Appointments is the one new page; nothing else.
- **Not a multi-tenant pivot.** Multi-accent theming is retired; re-introducing it is explicitly out of scope.
- **Not a full accessibility audit.** We target WCAG AA on colour contrast and keyboard reach. ARIA live regions and screen-reader optimisation are a follow-up.
- **Not a perf pass.** Tables that need virtualisation will get it in the retrofit for that page, not in Phase 0.
- **Not a receipt restyle.** The printed receipt template stays as-is in V2. Display serif is permitted in-app only, not on print output.

---

## 8. Success criteria

V2 is successful when:

1. **No page renders body text below 4.5:1 contrast in either theme.** Automated via lint + CI snapshot test.
2. **Every page uses tokens.** Zero raw `text-gray-*` / hex literals in `app/` or `components/` outside the token file.
3. **The Saturday-rush test.** A receptionist, without training, takes a walk-in from POS → service select → payment → receipt in under 45 seconds on a 14" laptop.
4. **The 5-second test.** An owner opening Today sees revenue, active services, and "what needs attention" within 5 seconds of landing.
5. **Appointments ships** in V2 as the hardest-pattern proof.
6. **Mobile-usable.** Every Phase-retrofitted page passes at 390px with no horizontal body scroll and all primary actions reachable.

---

## 9. Open questions (for implementation planning)

These are tracked but not blocking this spec:

- Final dark-mode copper shade (needs calibration against surface tokens).
- Whether Tremor's default chart styling needs a custom theme layer or works with our tokens directly.
- Keyboard-shortcut collision policy (system shortcuts on Mac/Windows vs app shortcuts).

---

## 10. Next step

A separate implementation plan will break this spec into executable tasks, starting with Phase 0 (tokens + primitives). That plan is the artifact produced by the `writing-plans` skill after this spec is approved.
