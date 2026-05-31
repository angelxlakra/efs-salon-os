# Frontend Design Brief — Bundles & Session Packages (SalonOS Sub-Project A)

**Audience:** A separate design-focused Claude session (claude.ai/design) that already has the SalonOS frontend codebase and design system loaded.
**Purpose:** Brainstorm visual treatments, layouts, micro-interactions, and component behaviors for the upcoming "Packages" feature before the engineering spec is finalized.
**Hand-off path:** Read this entire brief, then begin proposing visual approaches for the screens listed in Section 6.

---

## 1. Context: what SalonOS is

SalonOS is a **local-first salon management system** used daily by non-technical staff in a real unisex beauty salon. It runs on the local LAN behind an Nginx reverse proxy, served by a Next.js 16 + React 19 + TypeScript frontend talking to a FastAPI backend over PostgreSQL 15.

**Users you are designing for:**

- **Owner** — full access. Manages catalog, pricing, refunds, all overrides. Power user, uses desktop browser daily.
- **Receptionist** — front-desk, runs the POS all day on a tablet. Speed matters more than aesthetics. Hands occupied (phone, payment, customer interaction) — UI must be reachable with minimal clicks and large hit targets.
- **Staff** — service providers (stylists, therapists). Limited PII access (first name only on customers). Uses POS in moments between services.

**Device contexts:**

- POS: 10–13" Android/iPad tablets, landscape, often in protective cases. **Touch-first.** Hit targets ≥44px.
- Owner/Receptionist admin work: desktop browser, 1440px+ typical.
- Receipts: 80mm thermal printer (already handled by a separate component — out of scope here).

**Existing design system (already in code):**

- Token-based — never use raw Tailwind colors; use semantic tokens (`text-muted`, `bg-surface-card`, `accent-default`, etc.)
- Accent color: **copper `#b0561f`** (light) / `#d97847` (dark)
- Surface: warm white `#fafaf9` (not pure white), card surfaces `#ffffff`
- Typography: **Instrument Serif** for display headings (sparingly), **Inter** for body text, mono for SKUs / invoice numbers
- **Tabular numerals required** on every money/count/time display (`.tabular` utility)
- **Density-first** philosophy: data is the hero; whitespace serves legibility, not decoration
- Primitives library is canonical — no bespoke buttons/inputs/dialogs per page
- Both light and dark themes must work (light is authoritative; dark is perceptually matched)
- **Reference document:** `docs/design_system.md` — read this first
- **Recent V2 redesign:** `docs/superpowers/specs/2026-04-23-v2-redesign-design.md` — the visual language is fresh and intentional

**Existing UI surfaces this feature plugs into:**

- `/dashboard/pos` — the POS billing screen (receptionist's home)
- `/dashboard/customers/[id]` — customer profile (where active packages and history will surface)
- `/dashboard/services` — service catalog management (the closest analog to what we're building)
- `/dashboard/bills/[id]` — bill view (where redemption line items show)

The component directories already in place (use these as patterns): `frontend/src/components/{pos, checkout, customers, services, bills, staff}`.

---

## 2. The feature in one paragraph

**Bundles & Session Packages** lets the salon define and sell pre-paid multi-service products: e.g., a "Bridal Glam Package" (3 services together at a discount) or a "10-Session Hair Spa Pack" (redeem one per visit over 6 months) or an "Unlimited Hair Wash Monthly" (unlimited usage within a 30-day window). Customers buy a package once, the salon issues a tax invoice, and over subsequent visits the system tracks redemptions, applies them automatically at POS, handles family/friend sharing where permitted, and supports refunds with cancellation fees. This is the foundation for memberships, loyalty tiering, and AI recommendations — but those are separate later sub-projects.

---

## 3. Locked product decisions (do not re-design these)

These were brainstormed and approved in detail. Your design must accommodate all of them. Do not propose alternatives at the product level — only at the visual/interaction level.

### 3.1 Package primitives (unified schema)

One database concept, `PackageDefinition`, covers all of:

| | Shareable | Owner-only |
|---|---|---|
| **Counted** (N sessions) | "10 sessions Hair Spa, family can use" | "10 personalized facial sessions" |
| **Unlimited** (time-bound only) | "Unlimited foot massage for 30 days, share with family" | "Unlimited hair wash monthly (personal)" |

A "bundle" (single-sitting combo like Bridal Glam) is just a `PackageDefinition` with `total_sessions = 1` and a single redemption that consumes all included services. No special schema.

### 3.2 Pricing model

"Build-your-own-package" form. Admin:

1. Adds N services to the package (each shows MRP)
2. Sees the **running MRP total**
3. Applies a **package-level discount** via a toggle: `Percentage % | Flat ₹ off | Final amount`
4. System **auto-distributes** the discount across all unlocked lines proportionally to MRP
5. Admin can **override any individual line price** — that line becomes "locked" (icon indicator). Further package-level discount changes redistribute only across unlocked lines.
6. **Per-line prices are snapshotted at save**. Service MRP changes later don't affect existing packages.

### 3.3 GST / billing model (locked)

- **Revenue and GST recognized at sale** — selling a package creates a normal Bill with full tax invoice, per-service GST breakdown comes from the snapshotted per-line prices.
- **Redemptions are bill items** with the snapshotted price, paid via internal payment method `package_redemption` (so the customer pays nothing at the visit but staff commission and revenue reporting work normally).
- **Money is in paise** everywhere. Money displays use `.tabular` numerals.

### 3.4 Validity & expiry

- Per-package `validity_days` (e.g., 180 days)
- At sale, `expires_at = sold_at + validity_days` is **snapshotted** to the `PackageSale` row
- **Hard expiry**: redemption refused after `expires_at`
- **Owner-only audit-logged "Extend Expiry" action** for goodwill
- **Pre-expiry reminder badge** on customer profile starting 30 days before expiry

### 3.5 Shareability

- Per-package config: `owner_only` (default) or `shared`
- Shared packages can be redeemed by any **registered customer**, not just the buyer
- At redemption, cashier picks recipient (defaults to package owner; can change to any existing customer or quick-create one)
- **Audit log** records buyer + recipient + performed_by_user per redemption
- Receipt and bill UI shows "Paid via Package XYZ (owned by [Buyer Name])" when recipient ≠ buyer
- PII redaction for Staff role: show buyer as "Rajesh K." not "Rajesh Kumar"

### 3.6 Redemption behavior at POS

- **Auto-apply by default** when customer has an active applicable package (per-package config `auto_apply` flag, defaults true; unlimited packages always auto-apply)
- **Single-package case**: silent auto-apply with an `[↩ Undo]` pill on the bill line
- **Multi-package case**: inline radio selector pre-selecting **FIFO by expiry**, with a "Confirm with customer" prompt — cashier reads the choice to the customer
- **Exact service match only** — if the package covers "Hair Spa," it does not cover "Premium Hair Spa" unless admin listed both
- **Active packages badge** at top of POS the moment a customer is selected — surfaces "Customer has 3 active packages • 7 Hair Spa sessions left" before any service is added

### 3.7 Refunds

- Allowed via Owner-only action
- **Cancellation fee** withheld — per-package `cancellation_fee_pct`, default 20%
- **Refund math branches** by entitlement type:
  - **Counted**: pro-rata on unredeemed sessions × snapshotted per-line prices
  - **Unlimited**: pro-rata on time remaining
- Refund issues a **Credit Note Bill** (`bill_type='credit_note'`) linked to the original sale
- Reason text required, audit logged
- Refunding an **expired package** is still possible at Owner discretion with a warning banner

### 3.8 Permissions

| Permission | Owner | Receptionist | Staff |
|---|---|---|---|
| View packages & active packages on a customer | ✓ | ✓ | ✓ (with PII redaction) |
| Create / edit / delete package definitions | ✓ | — | — |
| Sell a package at POS | ✓ | ✓ | — |
| Redeem a package for owner | ✓ | ✓ | ✓ |
| Redeem a package for someone else (shared) | ✓ | ✓ | — |
| Refund a package | ✓ | — | — |
| Extend expiry of a package | ✓ | — | — |
| Override snapshotted price on a specific sale | ✓ | — | — |

### 3.9 POS page structural latitude

The POS screen (`/dashboard/pos`) is **explicitly open to structural redesign** as part of this work, not just visual additions. The recent V2 redesign of the Today page (`docs/superpowers/specs/2026-05-21-dashboard-redesign-design.md`) set the precedent — when a feature adds a meaningful new concept (here: packages as a first-class transactional primitive), it's appropriate to revisit the host page's information architecture rather than bolt the new concept on as a sidebar.

**What can change**:

- Page-level IA: where the customer panel, bill canvas, service selector, payment panel sit relative to each other
- How active packages surface — they can be a permanent sidebar rail, a header strip, an overlay above the bill canvas, or something we haven't considered yet
- The relationship between "what the customer is paying today" and "what entitlements they already own" — these were previously two separate concerns and can now be visually unified
- The service selector itself — adding `Packages` as a tab might be the right answer, or the tabs might be replaced entirely by a smarter unified selector
- Empty-canvas state (no customer selected) — can change shape if it earns it
- The order/visibility of secondary actions (discount, hold, void)

**What cannot change**:

- The receptionist's mental model of "select customer → add items → take payment → close bill" — the core flow stays
- Existing keyboard shortcuts, command palette behavior, and accessibility hooks
- The 80mm receipt format (unchanged — out of scope)
- Anything that touches the FastAPI billing endpoints or `BillItem` schema beyond the new `item_type='package_redemption'` discriminator

In other words: **structural is on the table; functional is locked.** If a structural change would force a backend behavior change, that's out of scope — propose the structural change with the caveat and we'll route it through a separate decision.

### 3.10 Out of scope for this brief

- Recurring / auto-renewing billing (memberships are sub-project B)
- Loyalty tiering (sub-project D) — but design should allow a "tier badge" slot near customer name for future use
- AI recommendations (sub-project E) — same; leave a slot for "recommended add-ons" but don't design them
- The print receipt template (handled separately)

---

## 4. Architecture context (locked, just so you know)

Backend is going with a **hybrid schema** ("Gamma"):

- New tables for catalog and sale lifecycle: `PackageDefinition`, `PackageDefinitionItem`, `PackageSale`, `PackageRedemptionAudit`, `PackageExpiryExtension`
- Reuse `BillItem` for actual redemption lines (with a new `item_type` discriminator: `service | product | package_sale_line | package_redemption`)
- Reuse `Bill` for credit notes (one new `bill_type` enum value: `credit_note`)
- New internal `Payment.payment_method = 'package_redemption'` for the zero-customer-cash redemption case
- A single shared `package_pricing_engine.py` module owns all snapshot, eligibility, FIFO, refund-math, expiry-math logic — called by POS, future appointments, future recommendations

You don't need to design around this — it's just the backend's shape so you understand "redemption is a bill line" is real, not a fiction.

---

## 5. Open visual / interaction questions (THE BRAINSTORM)

This is where I want your creative input. For each question, propose **2–3 distinct approaches** with sketches/mockups (text-described is fine; visual is better), then recommend one with reasoning grounded in the SalonOS design system (density, primitives, tabular numerals, copper accent) and the user contexts above (tablet POS, desktop admin).

### Q-VIS-1 — The "Build Your Own Package" form (Owner desktop)

The most novel UI in the feature. Needs to make a complex flow (add services → see total → apply discount → fine-tune per-line → publish) feel obvious.

Specifically:

- How does the **discount toggle** (`%` / `₹` / Final amount) feel native — segmented control? Switcher tabs? Inline label changes?
- How are **locked vs unlocked lines** visually distinguished without screaming for attention? (A lock icon? A subtle color shift? A border treatment?)
- How is the **proportional redistribution** previewed when the admin changes the discount — animated? Just snap to new values? Show "+/-" deltas momentarily?
- Where does the **MRP-vs-final price diff** live for each line — inline? Hover-only? Always visible as a smaller text?
- How is the **"Entitlement × Shareability" matrix** presented — two radio groups stacked? A 2×2 visual selector? Plain dropdowns?
- For **unlimited packages**, the "× sessions" column collapses; show me how the form gracefully reshapes.
- The form has to scale from a 3-service bridal package to a 15-service mega-package. How does the **services table** stay readable at scale?

### Q-VIS-2 — POS sale flow (Receptionist tablet)

The receptionist is selling a package at the counter. The existing POS has a service selector with filter chips (`All | Services | Products`). We're adding a `Packages` chip.

- How should the **package list view** in the selector differ from the existing service list — to convey "this is a multi-line product"? Card-style with a small chip list inside? Expanded row showing included services? Just a normal row with a count?
- When a package is added to the bill, the bill line shows the package name + a **summary of included services**. How is the summary surfaced without bloat — collapsible accordion? Inline chip cluster? "View details" link?
- The **selling staff** picker is per-package-line. Where does it live — inline dropdown on the line, popover, sidebar?
- The customer's **active packages badge** at top of POS: design 2–3 variants of how this badge looks when 0 packages, 1 package, 3+ packages, and one expiring soon.

### Q-VIS-3 — POS redemption (Receptionist tablet)

The most-used flow in this feature. Must be fast and unambiguous.

- The **`[↩ Undo]` pill** on a redemption line — how prominent should it be? Always visible? Visible on hover? Visible only for the most recent line? Consider that the cashier may not realize a redemption was applied if it's too subtle.
- The **multi-package selector** when 2+ packages are eligible — design the inline radio component. It must not feel like a modal but must clearly invite a customer-confirmation moment ("⚠ multiple available, confirm with customer"). 2–3 variants.
- The **active packages badge** above the bill — when there are 4+ active packages, how do you show them without scrolling? Stack with overflow chip? Carousel? Grouped by type?
- For **shared redemption** (recipient ≠ buyer), how prominently is the buyer's name shown on the line — to avoid confusion but not steal attention?

### Q-VIS-4 — Customer profile: Active Packages section

On `/dashboard/customers/[id]`, a new "Packages" tab or section.

- Layout: tab? Accordion section? Always-visible card stack?
- For each active package, show: name, sessions remaining (or "Unlimited"), expiry (with visual urgency state — green / amber / red), gifted-to history if shared.
- How does the **"expiring soon" badge** (≤30 days) read at a glance?
- A small **"Refund" button** (Owner only) — how prominent? Hidden in a kebab menu? Inline?
- **Buyer vs Recipient asymmetry**: this customer might be the buyer of 3 packages and the recipient of redemptions on 2 of someone else's packages. Show both sides clearly without confusion.

### Q-VIS-5 — Refund modal (Owner)

The refund flow shown in this brief's section 6.4. The math is complex (sessions consumed × per-line snapshot price + cancellation fee). Design:

- How is the **math breakdown** laid out so the customer-facing number (the refund amount) is unambiguous but the intermediate calculations are transparent?
- The **counted vs unlimited math** is structurally different — should the form layout shift to reflect that, or use a common shell with branching rows?
- The **"refund to:" payment method picker** (Cash / UPI / Adjust pending balance) — where does it sit in the form?
- For **expired-package goodwill refunds**, where does the warning banner go? Top of the modal? Inline with the math?

### Q-VIS-6 — Empty states & first-run

- The catalog when no packages exist yet
- The POS package selector chip when no published packages exist
- The customer profile when the customer has no packages
- The "first time selling a package" guidance for receptionist — should there be a one-time tooltip walkthrough?

### Q-VIS-7 — Cross-cutting micro-interactions

- **When a package is auto-applied**, what's the affirmative feedback? A subtle pill animation? A toast? A color flash on the bill line?
- **When the discount toggle re-distributes prices**, do the affected numbers animate or snap?
- **When an active package's badge appears** as the customer is selected, does it slide in? Fade in? Both?

### Q-VIS-9 — POS page-level IA (structural latitude)

Per Section 3.9, the POS page can be restructured to make packages a first-class transactional primitive rather than a bolt-on. Use the same critical lens the V2 Today redesign applied — does the current IA still serve the user when packages become a major part of the salon's revenue?

Brainstorm directions to explore (you're not limited to these):

- **"Entitlements panel"** as a permanent rail on the POS, peer to the bill canvas. Shows the customer's active packages, pending balance, and any pre-existing credits — a single unified view of "what this customer already has paid for or is owed." Disappears when no customer is selected.
- **Header strip** carrying customer identity + entitlement summary as a high-density bar, freeing more vertical real estate for the bill canvas itself.
- **Unified item selector** that replaces the `All | Services | Products | Packages` chips with a single search-first selector that ranks by what's relevant to the current customer (their active packages float to the top when applicable).
- **Bill-canvas treatment of redeemed lines** — should redemption lines visually group with their source package? Cluster at the top? Have a subtle treatment that distinguishes them from paid-now lines without dimming them (they're real services, just paid earlier)?
- **What disappears or consolidates** — if entitlements get a permanent home, do any existing badges/banners become redundant?

For each direction you take seriously, sketch the layout for the four meaningful states:

1. No customer selected (idle)
2. Customer selected, no active packages, no items added
3. Customer selected, has active packages, no items added (your chance to make the entitlements visibility shine)
4. Customer selected, has active packages, mid-bill with mixed paid + redeemed lines

Recommend the structure that feels most native to the V2 visual language and most respectful of the receptionist's existing muscle memory (Section 3.9 — functional flow must survive any structural change).

### Q-VIS-8 — Dark mode parity

Confirm each major screen works in dark mode without losing the copper accent's warmth. Specifically the "expiring soon" warning gradient — does it read as urgent without being aggressive on a dark surface?

---

## 6. Mandatory screens to mock (deliverable list)

You should produce visual proposals (low or mid-fidelity) for at minimum these screens:

1. **Package catalog list** (`/dashboard/packages`)
2. **Create/Edit package form** (with all entitlement × shareability × pricing variants)
3. **POS package selector** (filter chip + selection state)
4. **POS bill with a `package_sale_line`** added
5. **POS bill with a `package_redemption` line** (single eligible package, auto-applied)
6. **POS bill with multi-package selector** (2+ eligible packages)
7. **POS bill with shared-package redemption** (recipient ≠ buyer indication)
8. **Customer profile Packages section** (active + expiring soon + history)
9. **Refund modal — counted package**
10. **Refund modal — unlimited package**
11. **Active packages badge** (above POS bill, all states: 0 / 1 / many / expiring)
12. **Empty states** for catalog, POS selector, customer packages section
13. **POS page-level IA proposals** (per Q-VIS-9) — at least 2 distinct structural directions, each with the four state layouts called out in that question

> If a structural POS direction from Q-VIS-9 changes how screens 3-7 are framed (e.g., the package selector becomes part of a unified item search), update those screens accordingly — the brief's screen list (1-12) describes what content needs designing, not necessarily the exact containers.

---

## 7. Hard constraints (non-negotiable)

- Use only the existing **design tokens and primitives**. No new colors. No new typography. If a primitive is missing, propose extending the library — don't one-off.
- **Touch targets ≥44px** on every POS surface
- **Tabular numerals** on all money / count / time
- **WCAG AA contrast** (4.5:1 body, 3:1 large text and non-text UI)
- **Reduced-motion support** — no looping or decorative animation; all motion sub-200ms with `prefers-reduced-motion` opt-out
- **PII redaction logic visible at the design level** — Staff-role views of buyer names must be obviously different from Owner/Receptionist views
- **Both light and dark themes** must be shown for every major surface
- Match the **density-first philosophy** of the V2 redesign — see `docs/superpowers/specs/2026-04-23-v2-redesign-design.md` for tone

---

## 8. Soft constraints (preferences)

- **Copper accent** (`accent-default`) used sparingly — primary actions, active state, focus rings. Don't decorate with it.
- **Serif (Instrument Serif)** reserved for page titles and empty-state headlines. Everywhere else: Inter.
- Prefer **inline affordances** (badges, pills, chips) over modals where possible. The receptionist's flow should rarely have a modal interruption.
- Lean into **information density** the V2 redesign established — these users want to see a lot at once, not be hand-held.

---

## 9. Deliverable format

For each screen in Section 6:

1. A **brief intent statement** ("This screen helps X user do Y in Z context")
2. **2–3 visual variants** where there's a meaningful design choice (per the questions in Section 5), each with a one-line trade-off summary
3. A **recommendation** with reasoning grounded in the design system principles
4. **Both light and dark theme** renderings of the chosen variant
5. Annotations calling out **token usage** (which `surface-*`, `text-*`, `accent-*` token applies where) so the engineering team can implement faithfully
6. **State coverage**: empty, loading, populated, error, role-restricted

For cross-cutting questions in Section 5 (Q-VIS-7, Q-VIS-8), a short written design rationale is enough — no need for separate screens.

---

## 10. Where to start

I'd suggest starting with **Q-VIS-9 (POS page-level IA)** because it has the most leverage — a strong structural answer there reshapes how Q-VIS-2 and Q-VIS-3 get framed. Then move to **Q-VIS-1 (Build Your Own Package form)** as the most novel single-screen design problem. Once the form's visual language settles, the refund modal becomes an application of the same vocabulary. The customer profile section can come last — it's mostly a presentation of data that's already shaped by the earlier decisions.

End with the cross-cutting micro-interactions (Q-VIS-7) and dark mode parity (Q-VIS-8) as a coherence pass over everything.

---

## 11. Hand-off back to the engineering brainstorm (REQUIRED)

Your output needs to be re-ingested by a separate Claude session that's continuing the engineering spec. That session can only see files in the repo — not your chat — so package your output as files at these exact paths:

### Required: a single markdown deliverable

**Path**: `docs/superpowers/specs/2026-05-29-bundles-packages-design-output.md`

**Structure** (one section per brainstorm question from §5, in question order):

```markdown
# Bundles & Packages — Frontend Design Output

## Q-VIS-9: POS page-level IA

### Direction A — [name]
- **Intent**: one sentence
- **Sketch / mockup**: ![](design-assets/2026-05-29-bundles-packages/q9-direction-a-light.png)
  (also link the dark theme version)
- **Trade-offs**: what this gives up vs. what it gains
- **Token usage**: which `surface-*`, `text-*`, `accent-*`, semantic tokens apply where

### Direction B — [name]
(same structure)

### Recommendation: Direction X
Reasoning grounded in the design system principles (density, primitives, tokens) and the user contexts (Owner desktop / Receptionist tablet).

## Q-VIS-1: Build Your Own Package form
(same shape)

(...etc through every Q-VIS-N from §5 and every screen from §6...)
```

Where you have multiple state variants for a screen (empty / loading / populated / error / role-restricted), include all states inline under that screen's section.

### Required: a Decision Log at the bottom of the same file

```markdown
## Decision Log (machine-readable summary)

| Concern | Decision | Brief section |
|---|---|---|
| POS IA | [your recommendation in 4-6 words] | Q-VIS-9 |
| Build form discount toggle UX | [your recommendation] | Q-VIS-1 |
| Multi-package selector style | [your recommendation] | Q-VIS-3 |
| Active packages badge format | [your recommendation] | Q-VIS-3 |
| Refund modal layout (counted) | [your recommendation] | Q-VIS-5 |
| Refund modal layout (unlimited) | [your recommendation] | Q-VIS-5 |
| Dark mode anomalies discovered | [list any, or "none"] | Q-VIS-8 |
| ...rest of decisions | | |
```

This table is what the engineering session reads first to confirm scope before diving into the full document. Don't skip it — without it, decisions buried in prose may be missed.

### Optional but valued: image/mockup assets

If you produce visual mockups (low or mid-fidelity is fine), save them under:

**Folder**: `docs/superpowers/specs/design-assets/2026-05-29-bundles-packages/`

**Naming**: `q<question-number>-<short-name>-<theme>.png`
Examples:
- `q9-entitlements-rail-light.png`
- `q9-entitlements-rail-dark.png`
- `q1-package-builder-form-light.png`
- `q3-multi-package-selector-light.png`

PNG or JPG both work. Reference them from the markdown deliverable using relative paths (as shown in the structure above). The engineering session can read images via its file-reading tools and will pick up visual nuance from the mockups directly.

### Optional: a sibling "open questions" file

If during your work you encounter questions that need product input (something I-as-product-owner need to decide, not something you can resolve from the brief), put them in:

**Path**: `docs/superpowers/specs/2026-05-29-bundles-packages-design-open-questions.md`

A simple list — one question per item, with the context needed to answer. The engineering session reads this and routes them back to the product brainstorm before writing the spec.

---

## 12. What this brief is NOT

- Not the engineering spec (that's coming after this visual round)
- Not the final UX — your output will feed back into refinement before code is written
- Not exhaustive — if you see a screen or interaction that needs design and isn't listed, flag it and propose

When you've worked through this, save the deliverables at the paths in §11 and the engineering session will pick them up to shape the final spec.
