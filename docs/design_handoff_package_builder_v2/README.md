# Handoff: Package Builder v2 — Entitlement Blocks

## Overview
A redesign of Aasan's package system covering three surfaces:

1. **Package Builder** (`/dashboard/packages/new` + `/[id]/edit`) — replaces the current flat-service-list builder with a **stack of entitlement blocks**, so a package can be anything from "10 × Haircut" to "pick 3 of 5 facials (chosen each visit) + 1 hair spa + unlimited threading + a free retail bonus".
2. **POS sell flow** (`/dashboard/pos`, Packages tab) — finishes the currently-unwired TODO: tapping a package card opens a **Configure & Sell sheet** which resolves purchase-time choices and adds **one `package_sale_line` to the existing cart**. The cart itself is NOT redesigned.
3. **Customer entitlements view** — block-level progress display for active package sales. The existing redemption machinery (EntitlementsRail, MultiPackageSelector, RedemptionLineItem, auto-apply, undo) is intentionally kept.

## About the Design Files
`Package Builder v2.dc.html` is a **design reference created in HTML** — a prototype showing intended look and behavior, not production code to copy. The task is to **recreate this design inside the existing `efs-salon-os/frontend` codebase** (Next.js App Router, Tailwind v4 with semantic tokens, shadcn-style primitives in `src/components/ui/`, zustand stores) using its established patterns. Open the HTML file in a browser to interact with all three screens (tab switcher in the header; "Design notes" toggle explains the model).

## Fidelity
**High-fidelity.** The prototype uses the project's real V2 token values (`frontend/src/styles/tokens.css` — navy accent, gold secondary, warm paper surfaces). Recreate the layouts and component anatomy faithfully, but **always use the semantic Tailwind tokens** (`bg-surface-card`, `border-border-default`, `text-text-muted`, `bg-accent`, etc.) — never the raw hex values listed below; lint forbids raw hex outside the token file.

---

## Data Model (proposed changes to `src/types/package.ts`)

The core change: `PackageDefinition.items: PackageDefinitionItem[]` becomes `blocks: PackageBlock[]`. The package-level `entitlement_type` field goes away — entitlement semantics now live per block.

```ts
type PackageBlock =
  | { id: string; kind: "items";     bonus: boolean; rows: { service_id: string; quantity: number; unit_price_paise: number }[] }
  | { id: string; kind: "choice";    bonus: boolean; picks: number; choose_at: "purchase" | "visit";
      rows: { service_id: string; unit_price_paise: number }[] }
  | { id: string; kind: "unlimited"; bonus: boolean; assigned_value_paise: number; daily_cap: number | null;
      rows: { service_id: string }[] }
  | { id: string; kind: "pool";      bonus: boolean; sessions: number;
      rows: { service_id: string; unit_price_paise: number }[] }
  | { id: string; kind: "credit";    bonus: boolean; amount_paise: number; scope: "any" | "services" | "retail" };
```

Kept at package level (unchanged semantics): `name`, `description`, `status` (draft/published/archived), `shareability` (owner_only/shared), `validity_days`, `auto_apply`, `cancellation_fee_pct`, `discount` ({mode: pct|flat|final, value}), `final_price_paise`.

**Value math** (mirrors the prototype's `blockValue`):
- items → Σ qty × price
- choice → picks × average(option prices) — *display with "≈" prefix; it's an estimate*
- unlimited → `assigned_value_paise` (manual, set by the builder; unlimited can't auto-price)
- pool → sessions × average(eligible prices) — also "≈"
- credit → amount

Pricing: `chargeable = Σ value of non-bonus blocks`; `price = chargeable − discount` (discount.value is paise for flat/final, % for pct — keep the existing `toDiscountPayload` rupee→paise conversion). `total_value = chargeable + bonus value`; "Customer saves X%" = `1 − price/total_value`.

`PackageSale` snapshots gain per-block remaining state: counted remaining per row, pool sessions remaining, credit balance remaining, choices locked at purchase (list of service_ids), per-visit choice picks consumed.

---

## Screens / Views

### Screen 1 — Package Builder
Replaces `src/components/packages/PackageBuilder.tsx`, `PackageBuilderServicesTable.tsx`, `PackageBuilderEntitlementMatrix.tsx`. **Keep** `PackageBuilderDiscountControl.tsx` (tri-field) and `ServicePicker.tsx` (combobox) — both are reused nearly as-is.

**Layout:** `grid grid-cols-[320px_1fr] gap-5`, page padding 22–24px, max-width 1240px centered.

**Left column (320px), three cards** (`bg-surface-card border border-border-default rounded-[10px] p-4`, 14px gap between cards). Card section labels are overline style: 11px / 600 / uppercase / 0.06em tracking / `text-text-muted`:
1. **Package** — Name input (34px tall), Description textarea (3 rows).
2. **Rules** — 2-col grid: Validity (days) + Cancellation fee %; "Who can redeem" segmented control (Personal | Shared) with a one-line hint below that changes with selection; "Auto-apply" row with 36×20px pill switch (navy when on, knob 16px, 120ms transition).
3. **Status** — Draft/Published chip (neutral / success-soft) + full-width primary button: "Publish to POS" → after publish becomes "View in POS →" (navigates to POS). Validation before publish: non-empty name, ≥1 block. Hint copy: *"Publishing makes it sellable. Existing sales always keep the snapshot they were sold with."*

**Right column — Contents (block stack):**
- Header row: overline "CONTENTS · N BLOCKS" left, hint text right (12px `text-text-muted`).
- Each block is a card (`rounded-[10px] border border-border-default overflow-hidden`) with:
  - **Header strip** (`bg-[#fcfbfa]`-equivalent ≈ `bg-surface-row` tint, border-bottom `border-subtle`, padding 9px 12px, flex gap 10px): type chip (pill, 10.5px 600 uppercase, per-type soft color — see tokens), auto-generated summary title (13px 600, truncating, flex-1), block value (12.5px 600 tabular, "≈" prefix for choice/pool), **Bonus toggle pill** ("Bonus?" ghost → "★ Free bonus" gold-soft with gold border when on), remove "×".
  - **Body** (padding 10px 12px) varies by type:
    - *Fixed items*: column-header row (SERVICE/PRODUCT · QTY · PRICE ₹) then rows on grid `1fr 60px 92px 24px` — service combobox trigger (30px tall), qty input (centered), price input (right-aligned, tabular), remove ×.
    - *Choice group*: sentence-style config — "Customer picks [n] of the options below —" + segmented control `locked at purchase | chosen each visit`; option rows on grid `1fr 92px 24px` (service, price, remove).
    - *Unlimited*: service rows grid `1fr 24px`; below a dashed-top-border footer with two fields: "Assigned value for pricing (₹)" and "Fair-use cap per day (optional)" (placeholder "None").
    - *Session pool*: sentence config "A pool of [n] sessions, spendable on any service below" + option rows like choice.
    - *Credit*: "Credit amount (₹)" input (600 weight) + "Spendable on" segmented control `Anything | Services only | Retail only`. No service rows.
  - All row-bearing blocks end with a full-width dashed "＋ Add service" button (30px, hover → accent border/text).
- **Add-block palette**: `grid grid-cols-5 gap-2` of dashed-border tiles (10px radius, hover → accent border): 22px colored glyph square + label (12px 600) + description (10.5px muted). Types: Fixed items, Choice group, Unlimited, Session pool, Credit.
- **Pricing card**: "Total value to customer" row; conditional gold sub-row "includes free bonuses (not charged)"; the existing tri-field discount control (% off | ₹ off | Final price ₹ — last-edited field authoritative, others derived, active label in accent); divider; footer row "Sells at" + gold-soft "Customer saves X%" pill + price (24px / 700 / accent / tabular).

### Screen 2 — POS sell flow
Touches `src/app/(shell)/dashboard/pos/page.tsx` (`PackagesSelectorView`) and adds one new component (`ConfigureSellSheet`). **Do not modify** `cart-store.ts` mechanics or `CartSidebar` layout — the package enters as one cart item.

- **Package cards** (2-col grid): name (14px 600) + optional "Just published" success chip; composition summary (12px muted, e.g. "1 × Hair Spa · Pick 3 of 3 — chosen each visit · Unlimited Eyebrow Threading · Free: 1 × Argan Hair Serum"); chip row (validity "90 days" neutral, "Shareable" info-soft, "Choices at purchase" gold-soft when applicable); footer split by subtle border: struck-through "worth ₹9,150" muted left, price (16px 700 accent tabular) right. Hover: accent border + xs shadow.
- **Configure & Sell sheet** (the new piece — use the existing `Sheet` primitive, side="right", 440px): 
  - Header: overline "CONFIGURE & SELL", package name in display serif (Instrument Serif, ~23px), chip row: "For {customer}", "Valid till {date}" (computed: today + validity_days, en-IN format), shareability.
  - Body: one bordered card per block — type chip + summary; **choice blocks with `choose_at: "purchase"` render an option picker**: counter "n of N selected" (warning color until complete, success when done) + option rows as toggleable checkboxes (selected: accent border + accent-bg-soft + filled check square). Selection rules: toggle off on re-tap; ignore extra taps when full; picks=1 behaves like radio (replaces). Blocks needing no config show an italic muted note ("Customer chooses fresh at each visit — nothing to lock now." / "No configuration — usable on every visit (max 1/day)." / "Included free — not charged.").
  - Footer: struck worth + price (20px 700), full-width CTA **"Add to cart — one package line"** — disabled (neutral bg, not-allowed cursor) until every purchase-time group is complete, with helper "Pick the remaining options to continue".
  - **Guard:** selling requires a selected customer (packages bind to a customer). If none, prompt customer selection before opening the sheet.
- **Cart line** for the package: reuse the existing `PackageSaleLine` pattern — 3px navy left rail, name + price, meta "Package · expires {date}", plus (new) an accent-soft inline chip "Chosen: Gold Facial, Hydra Facial" when choices were locked at purchase.
- Checkout, GST split-billing, PaymentModal: **unchanged**.

### Screen 3 — Customer entitlements view
Extends `PackageCard.tsx` / detail views with block-level progress. Card per active sale: name + expiry chip (`ExpiryBadge` — success ≥30d, warning <30d), then one row per block:
- counted items → "4 of 10 used" + 10-segment progress bar (filled = accent, empty = border-default, 7px tall, 99px radius, 4px gaps)
- purchase-locked choices → list the locked services each with "1 of 1 used ✓" (success) or "0 of 1"
- per-visit choices → "1 of 3 · last: Hydra"
- unlimited → "∞ unlimited · 9 visits · 1/day" (info color)
- bonus → "free · delivered ✓" (gold)
- credit → big balance "₹3,250" + "of ₹5,000 remaining" + gold progress bar
Footer: "Personal/Shared · expires {date}" (11px muted).

Bill lines stay exactly as today: navy rail = package sale (paid now), gold rail = redemption (already paid, struck price + Undo pill).

---

## Interactions & Behavior
- Segmented controls: track `bg` ≈ `#f0ede9` with 1px border, 2–3px padding; active segment white bg + xs shadow + `text-primary`; inactive `text-muted`. 
- Numeric inputs: keep the codebase's `NumericCell` draft-while-focused pattern (don't reformat on keystroke).
- Sheet open: 200ms translate-in with the project's `motion-spring` curve; overlay `surface-overlay` fades 120ms. Modal/service-picker: same pattern, centered.
- Toasts via `sonner` (the prototype's bottom-center toast is a stand-in): publish success, added-to-cart, validation errors.
- Focus: accent border + `shadow-focus` ring on all inputs.
- Block summaries auto-generate from content (see `blockSummary` in the prototype's logic) — they are the block's title, not user-editable.

## State Management
- Builder: local component state mirroring the `PackageDefinitionCreate` shape (as today), numeric fields held as strings until submit. Save/publish via `packagesApi.createDefinition/updateDefinition`.
- POS: sheet state = `{ packageId, choices: Record<blockIndex, serviceId[]> }`. On confirm, add a cart item `{ isProduct: false, kind: 'package_sale', packageDefinitionId, lockedChoices, unitPrice: final_price_paise, quantity: 1 }` — flows through the existing cart → bill creation as `item_type: "package_sale_line"`.
- Backend note: `PackageSale` creation happens at bill settlement (as currently designed); locked choices ride along in the sale items snapshot.

## Design Tokens
All from `frontend/src/styles/tokens.css` — use semantic utilities, hex listed for reference only:
- Surfaces: page `#f8f5f0`, card `#ffffff`, block-header tint `#fcfbfa`, segmented track `#f0ede9`
- Borders: subtle `#eeece9`, default `#e3e0db`, strong `#cfcac3`
- Text: primary `#1c1917`, secondary `#44403c`, muted (walnut) `#8b6b4a`, disabled `#a8a29e`
- Accent navy: `#1c104c` (hover `#2a1865`), soft `#ece8f5`, on-accent `#f5f0e8`
- Gold: `#c9a96e`, soft `#f5ecd9`, gold text on soft `#8a5a16`
- Block-type chips: items = accent-soft/accent; choice = gold-soft/`#8a5a16`; unlimited = info-soft/info; pool = `#f3e8ff`/`#6b21a8` (data-series-5 family — consider adding a token); credit = success-soft/success
- Radius: cards/sheets 10px, inputs/buttons 6px, chips 999px · Shadows: xs on hover-raise cards, md on sheet/modal · Type: Inter (body 13–14px, overlines 10.5–11px/600/uppercase), Instrument Serif only for the sheet's package name; `tabular-nums` on every money/count
- Motion: 120ms default, 200ms spring for sheet entry

## Assets
None — no images or icon fonts. The prototype uses text glyphs (×, ✓, ∞, Σ, ₹, ★, ↩); in the codebase use the existing `lucide-react` icons (Lock→n/a, Package, Gift, Infinity, Wallet, Trash2, Plus, Undo2) where natural.

## Annotated Screens
See `screens/` for annotated reference images (each pairs a real capture with a "what the dev builds" callout list):
- `annotated-1-builder.png` — the block-stack builder (all 5 block types, bonus, pricing)
- `annotated-2-pos.png` — POS package grid + unchanged cart
- `annotated-3-sheet.png` — the new Configure & Sell sheet (purchase-time choice picker)
- `annotated-4-customer.png` — customer entitlements / redemption progress

## Files
- `Package Builder v2.dc.html` — the interactive prototype (all 3 screens; open in a browser, use the header tabs; logic at the bottom of the file documents all derived math: `blockValue`, `blockSummary`, `discountAmt`, choice-toggle rules).

## Codebase touchpoints (summary)
| Action | File |
|---|---|
| Replace | `components/packages/PackageBuilder.tsx`, `PackageBuilderServicesTable.tsx`, `PackageBuilderEntitlementMatrix.tsx` |
| Keep & reuse | `PackageBuilderDiscountControl.tsx`, `ServicePicker.tsx`, `PackageSaleLine.tsx`, `RedemptionLineItem.tsx`, `MultiPackageSelector.tsx`, `EntitlementsRail.tsx`, `RefundPackageModal.tsx` |
| Extend | `types/package.ts` (blocks model), `PackageCard.tsx` (block-level progress), `pos/page.tsx` (wire Packages tab) |
| Add | `components/packages/ConfigureSellSheet.tsx` |
| Do not touch | `stores/cart-store.ts` math/UI, `CartSidebar`, `PaymentModal`, GST split-billing |
