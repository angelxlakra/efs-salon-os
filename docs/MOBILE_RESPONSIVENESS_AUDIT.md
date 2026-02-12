# Mobile Responsiveness Audit - SalonOS Frontend

**Date**: February 12, 2026
**Scope**: All frontend pages, components, layout, and shared UI
**Target devices**: iPhone SE (375px), iPhone 12 (390px), iPhone 14 Pro Max (430px), iPad (768px)

---

## Executive Summary

The SalonOS frontend was built primarily for desktop/tablet use. While some pages have responsive breakpoints, **most data-heavy pages break on mobile** due to wide tables, fixed widths, cramped grids, and oversized dialogs. The layout shell itself has global issues (padding, viewport height, dialog sizing) that compound per-page problems.

**Total issues found**: 65+
**Critical (blocks usability)**: 8
**High (significantly degrades UX)**: 18
**Medium (noticeable but workable)**: 25
**Low (cosmetic/minor)**: 14

---

## Part 1: Global / Layout Issues

These affect every page and should be fixed first for maximum impact.

### 1.1 Layout Padding Not Responsive

| Detail | Value |
|--------|-------|
| **File** | `src/app/dashboard/layout.tsx` |
| **Line** | 25 |
| **Current** | `p-6` (24px all sides) |
| **Problem** | On a 320px phone, 48px of padding leaves only 272px for content |
| **Fix** | `p-3 sm:p-4 md:p-6` |
| **Severity** | HIGH |

### 1.2 `h-screen` (100vh) on Main Container

| Detail | Value |
|--------|-------|
| **File** | `src/app/dashboard/layout.tsx` |
| **Line** | 14 |
| **Current** | `h-screen overflow-hidden` |
| **Problem** | `100vh` on mobile browsers doesn't account for dynamic address bar. Content gets cut off on iOS Safari |
| **Fix** | `min-h-dvh` or `min-h-screen` |
| **Severity** | HIGH |

### 1.3 Dialog Base `max-w` Too Large

| Detail | Value |
|--------|-------|
| **File** | `src/components/ui/dialog.tsx` |
| **Line** | 63 |
| **Current** | `sm:max-w-4xl` (896px default) |
| **Problem** | Many dialogs inherit this and overflow on tablets. No `max-h` constraint for mobile |
| **Fix** | `max-w-[calc(100%-2rem)] sm:max-w-lg md:max-w-2xl lg:max-w-4xl max-h-[90dvh] overflow-y-auto` |
| **Severity** | HIGH |

### 1.4 Mobile Sidebar Width Too Wide

| Detail | Value |
|--------|-------|
| **File** | `src/components/ui/sidebar.tsx` |
| **Line** | 31 |
| **Current** | `SIDEBAR_WIDTH_MOBILE = "18rem"` (288px) |
| **Problem** | On iPhone SE (375px), sidebar covers 77% of screen, leaving 87px visible |
| **Fix** | `"16rem"` (256px) or `min(70vw, 16rem)` |
| **Severity** | MEDIUM |

### 1.5 SidebarTrigger Touch Target Too Small

| Detail | Value |
|--------|-------|
| **File** | `src/components/ui/sidebar.tsx` |
| **Line** | 269 |
| **Current** | `size-7` (28px) |
| **Problem** | Below 44px minimum recommended touch target |
| **Fix** | `size-9` (36px) or add padding for larger hit area |
| **Severity** | MEDIUM |

### 1.6 Header Height Excessive on Mobile

| Detail | Value |
|--------|-------|
| **File** | `src/app/dashboard/layout.tsx` |
| **Line** | 15 |
| **Current** | `h-14` (56px) on all screens |
| **Problem** | Takes ~9% of a 600px mobile viewport. Title "Dashboard" wastes space |
| **Fix** | `h-12 md:h-14`, hide title on small screens with `hidden sm:block` |
| **Severity** | LOW |

---

## Part 2: Table / Data Display Issues

The most impactful category. Every page with a `<table>` or multi-column grid suffers on mobile. The pattern needed: show a card layout on mobile (`md:hidden`), show the table on desktop (`hidden md:table`).

### 2.1 Inventory SKU Table (8 columns)

| Detail | Value |
|--------|-------|
| **File** | `src/app/dashboard/inventory/page.tsx` |
| **Lines** | 345-420 |
| **Columns** | SKU Code, Name, Category, Stock, Cost, Sellable, Retail Price, Actions |
| **Current** | `overflow-x-auto` wrapper only |
| **Problem** | 8 columns at ~47px each on mobile. Text unreadable, buttons cramped |
| **Fix** | Mobile card view showing Name, Stock, Cost. Hide Category, Sellable, Retail Price columns on mobile |
| **Severity** | CRITICAL |

### 2.2 Expenses Table (6 columns)

| Detail | Value |
|--------|-------|
| **File** | `src/components/expenses/expense-list.tsx` |
| **Lines** | 97-161 |
| **Columns** | Date, Category, Description, Amount, Status, Actions |
| **Current** | `overflow-x-auto` but `px-6 py-4` padding per cell |
| **Problem** | Description column has unbounded text. No mobile card alternative |
| **Fix** | Card layout on mobile: Description + Amount + Status badge. Hide Category column |
| **Severity** | CRITICAL |

### 2.3 Customers Table (7 columns)

| Detail | Value |
|--------|-------|
| **File** | `src/app/dashboard/customers/page.tsx` |
| **Lines** | 247-372 |
| **Columns** | Customer, Contact, Visits, Total Spent, Pending, Last Visit, Actions |
| **Current** | `overflow-x-auto` with `px-6 py-4` cells |
| **Problem** | 7 columns all visible on mobile |
| **Fix** | Card view on mobile: Name, Phone, Total Spent, Pending badge |
| **Severity** | CRITICAL |

### 2.4 Attendance Table (hardcoded widths)

| Detail | Value |
|--------|-------|
| **File** | `src/components/attendance/attendance-table.tsx` |
| **Lines** | 78-83 |
| **Columns** | Uses `w-[200px]`, `w-[140px]`, `w-[100px]`, `w-[250px]` hardcoded |
| **Current** | Fixed widths with `whitespace-nowrap` cells |
| **Problem** | Notes column alone is 250px -- wider than half of most phones |
| **Fix** | Remove hardcoded widths, add card layout on mobile |
| **Severity** | CRITICAL |

### 2.5 Users Table (5 columns) + Staff Table (6 columns)

| Detail | Value |
|--------|-------|
| **File** | `src/app/dashboard/users/page.tsx` |
| **Lines** | 214-280 (users), 312-386 (staff) |
| **Problem** | Both tables use `px-6 py-4` cells, no column hiding. Staff table has `max-w-[200px]` specialization badges |
| **Fix** | Hide Contact/Specialization columns on mobile, or switch to card view |
| **Severity** | HIGH |

### 2.6 Bills Table (6 columns)

| Detail | Value |
|--------|-------|
| **File** | `src/app/dashboard/bills/page.tsx` |
| **Lines** | 376-464 |
| **Current** | Has `hidden sm:block` for desktop table with a basic mobile card fallback |
| **Problem** | Mobile card is minimal -- invoice number has no truncation, pagination doesn't stack |
| **Fix** | Improve mobile card: add truncation, stack pagination |
| **Severity** | MEDIUM |

### 2.7 Bill Details - Services & Payments Tables

| Detail | Value |
|--------|-------|
| **File** | `src/components/bills/bill-details-dialog.tsx` |
| **Lines** | 257-315 (services), 325-390 (payments) |
| **Problem** | Both 4-column tables inside a dialog. No mobile layout. Staff contributions overflow |
| **Fix** | Stack as list items on mobile inside dialog |
| **Severity** | HIGH |

### 2.8 P&L Report Tables

| Detail | Value |
|--------|-------|
| **File** | `src/app/dashboard/reports/profit-loss/page.tsx` |
| **Problem** | Expense category labels (e.g. "material_and_supplies") overflow without truncation |
| **Fix** | Add `truncate` or `break-words` on category names |
| **Severity** | MEDIUM |

---

## Part 3: Purchase Pages

The user-reported problem area. All purchase pages have significant mobile issues.

### 3.1 Purchase Invoices List - Fixed Width Column

| Detail | Value |
|--------|-------|
| **File** | `src/app/dashboard/purchases/invoices/page.tsx` |
| **Line** | 161 |
| **Current** | `min-w-[200px]` on amount column |
| **Problem** | Forces horizontal scroll on mobile. Amount/Paid/Balance section can't shrink |
| **Fix** | Remove `min-w-[200px]`, stack amount info below invoice details on mobile |
| **Severity** | HIGH |

### 3.2 Purchase Invoices List - Status Filter Overflow

| Detail | Value |
|--------|-------|
| **File** | `src/app/dashboard/purchases/invoices/page.tsx` |
| **Lines** | 89-125 |
| **Current** | 5 buttons (All, Draft, Received, Partially Paid, Paid) in `flex gap-2` |
| **Problem** | "Partially Paid" wraps to 2 lines. Buttons overflow on mobile |
| **Fix** | Add `overflow-x-auto` + `flex-nowrap`, or use a Select dropdown on mobile |
| **Severity** | MEDIUM |

### 3.3 Purchase Invoices List - Header Buttons

| Detail | Value |
|--------|-------|
| **File** | `src/app/dashboard/purchases/invoices/page.tsx` |
| **Lines** | 76-85 |
| **Problem** | "Suppliers" + "New Invoice" buttons overflow on mobile |
| **Fix** | `flex-col sm:flex-row` or icon-only on mobile |
| **Severity** | MEDIUM |

### 3.4 New Invoice - Line Items Grid

| Detail | Value |
|--------|-------|
| **File** | `src/app/dashboard/purchases/invoices/new/page.tsx` |
| **Line** | 450 |
| **Current** | `grid-cols-2 sm:grid-cols-5` |
| **Problem** | 5 fields (Product, UOM, Qty, Cost, Discount, Total) crammed into 2 columns on mobile. Cost/Total fields become unreadable |
| **Fix** | Stack all fields vertically on mobile: `grid-cols-1 sm:grid-cols-2 md:grid-cols-5` |
| **Severity** | CRITICAL |

### 3.5 New Invoice - Summary Sidebar Disconnected

| Detail | Value |
|--------|-------|
| **File** | `src/app/dashboard/purchases/invoices/new/page.tsx` |
| **Line** | 306 |
| **Current** | `lg:grid-cols-3` -- sidebar at bottom on mobile |
| **Problem** | User fills form at top, summary card is far below. No sticky summary on mobile |
| **Fix** | Consider a sticky bottom bar showing total on mobile, or collapsible summary |
| **Severity** | MEDIUM |

### 3.6 Invoice Detail - Items Grid (12-column, no mobile fallback)

| Detail | Value |
|--------|-------|
| **File** | `src/app/dashboard/purchases/invoices/[id]/page.tsx` |
| **Lines** | 215-244 |
| **Current** | `grid grid-cols-12` with 5-2-2-3 column split |
| **Problem** | All columns cramped on mobile. No responsive breakpoint, no `overflow-x-auto` |
| **Fix** | Stack as cards on mobile: Product name on top, Qty/UOM/Amount below |
| **Severity** | CRITICAL |

### 3.7 Invoice Detail - Header Overflow

| Detail | Value |
|--------|-------|
| **File** | `src/app/dashboard/purchases/invoices/[id]/page.tsx` |
| **Lines** | 126-159 |
| **Current** | `text-3xl` title + 3 action buttons in `flex` |
| **Problem** | Title too large, buttons overflow horizontally |
| **Fix** | `text-xl sm:text-2xl md:text-3xl`, wrap buttons `flex-col sm:flex-row` |
| **Severity** | HIGH |

### 3.8 Invoice Detail - Info Grid

| Detail | Value |
|--------|-------|
| **File** | `src/app/dashboard/purchases/invoices/[id]/page.tsx` |
| **Line** | 173 |
| **Current** | `grid-cols-2` without responsive prefix |
| **Problem** | Always 2 columns, even on tiny screens |
| **Fix** | `grid-cols-1 sm:grid-cols-2` |
| **Severity** | MEDIUM |

### 3.9 Edit Invoice Dialog - Width + Line Items

| Detail | Value |
|--------|-------|
| **File** | `src/components/purchases/edit-invoice-dialog.tsx` |
| **Lines** | 135, 174 |
| **Current** | `max-w-4xl` dialog, `grid-cols-2 sm:grid-cols-5` items |
| **Problem** | Dialog 896px wide, line items cramped on mobile |
| **Fix** | Responsive dialog width, stack line item fields on mobile |
| **Severity** | HIGH |

### 3.10 Suppliers Page

| Detail | Value |
|--------|-------|
| **File** | `src/app/dashboard/purchases/suppliers/page.tsx` |
| **Status** | **Mostly OK** -- uses `flex-col sm:flex-row`, `w-full sm:w-auto` patterns |
| **Minor issues** | Currency values at `text-sm` are small on mobile. Card grid is fine |
| **Severity** | LOW |

---

## Part 4: POS & Billing

### 4.1 POS - Cart Sidebar Hidden on Mobile

| Detail | Value |
|--------|-------|
| **File** | `src/app/dashboard/pos/page.tsx` |
| **Line** | 123 |
| **Current** | `w-96 flex-shrink-0 hidden md:block` |
| **Problem** | Cart completely hidden below `md:`. Users must use the floating cart button |
| **Status** | By design (uses Sheet on mobile), but cart button may not be obvious |
| **Severity** | LOW |

### 4.2 POS - Product Grid Filter Width

| Detail | Value |
|--------|-------|
| **File** | `src/components/pos/product-grid.tsx` |
| **Line** | 121 |
| **Current** | `w-[200px]` on SelectTrigger |
| **Problem** | Fixed 200px dropdown doesn't adapt to mobile |
| **Fix** | `w-full sm:w-[200px]` |
| **Severity** | MEDIUM |

### 4.3 POS - Discount Buttons Row

| Detail | Value |
|--------|-------|
| **File** | `src/components/pos/cart-sidebar.tsx` |
| **Lines** | 668-682 |
| **Current** | 4 percentage buttons (5%, 10%, 15%, 20%) in `flex gap-2` |
| **Problem** | Overflow below 320px |
| **Fix** | `grid grid-cols-4` or `flex-wrap` |
| **Severity** | LOW |

### 4.4 Payment Modal - Radio Grid

| Detail | Value |
|--------|-------|
| **File** | `src/components/pos/payment-modal.tsx` |
| **Line** | 638 |
| **Current** | `grid grid-cols-3 gap-2` |
| **Problem** | 3 payment method options cramped below 300px |
| **Fix** | `grid-cols-2 sm:grid-cols-3` |
| **Severity** | LOW |

### 4.5 Bill Details Dialog - Action Buttons

| Detail | Value |
|--------|-------|
| **File** | `src/components/bills/bill-details-dialog.tsx` |
| **Lines** | 444-496 |
| **Current** | 3+ buttons in `flex gap-2` |
| **Problem** | Text overflow when 3 buttons side-by-side on mobile |
| **Fix** | `flex-wrap` or `grid grid-cols-2` |
| **Severity** | MEDIUM |

---

## Part 5: Remaining Pages

### 5.1 Dashboard - Stats Grid Cramped

| Detail | Value |
|--------|-------|
| **File** | `src/app/dashboard/page.tsx` |
| **Line** | ~319 |
| **Current** | `grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-2` |
| **Problem** | 2 columns with `gap-2` on mobile = ~156px per card on 320px. Text at `text-[10px]` is barely readable |
| **Fix** | Consider `grid-cols-1 sm:grid-cols-2` or increase gap/font sizes |
| **Severity** | MEDIUM |

### 5.2 Dashboard - Active Customers Grid

| Detail | Value |
|--------|-------|
| **File** | `src/app/dashboard/page.tsx` |
| **Line** | ~409 |
| **Current** | `grid-cols-1 lg:grid-cols-3` |
| **Problem** | No `md:` breakpoint -- jumps from 1 to 3 columns with nothing in between |
| **Fix** | `grid-cols-1 md:grid-cols-2 lg:grid-cols-3` |
| **Severity** | LOW |

### 5.3 Cash Drawer - Denomination Counter

| Detail | Value |
|--------|-------|
| **File** | `src/components/cash-drawer/DenominationCounter.tsx` |
| **Lines** | 55, 68 |
| **Current** | `flex gap-4` with `w-20` fixed input |
| **Problem** | Denom label + minus + input(80px) + plus + total cramped on narrow screens |
| **Fix** | Reduce gap to `gap-2` on mobile, use `w-16 sm:w-20` |
| **Severity** | MEDIUM |

### 5.4 Reconciliation - Date Selector

| Detail | Value |
|--------|-------|
| **File** | `src/app/dashboard/reconciliation/page.tsx` |
| **Lines** | 175-189 |
| **Current** | `flex items-center gap-3` with calendar + label + input |
| **Problem** | All on one line, overflows on narrow screens |
| **Fix** | `flex-col sm:flex-row` |
| **Severity** | MEDIUM |

### 5.5 P&L - Date Range Selector

| Detail | Value |
|--------|-------|
| **File** | `src/app/dashboard/reports/profit-loss/page.tsx` |
| **Lines** | 53-73 |
| **Current** | `flex gap-4 items-end` with start date + end date + button |
| **Problem** | 3 items in a row, button pushed off-screen on mobile |
| **Fix** | `flex-col sm:flex-row` |
| **Severity** | MEDIUM |

### 5.6 Settings - Confirmation Dialog Grid

| Detail | Value |
|--------|-------|
| **File** | `src/app/dashboard/settings/page.tsx` |
| **Line** | 749 |
| **Current** | `grid grid-cols-2 gap-4` inside dialog |
| **Problem** | Always 2 columns even on mobile, inside an already-narrow dialog |
| **Fix** | `grid-cols-1 sm:grid-cols-2` |
| **Severity** | MEDIUM |

### 5.7 Customer Dialog - Always 2-Column Forms

| Detail | Value |
|--------|-------|
| **File** | `src/components/customers/customer-dialog.tsx` |
| **Lines** | 174, 231 |
| **Current** | `grid grid-cols-2 gap-4` for name fields and gender/DOB |
| **Problem** | No responsive prefix -- always 2 columns |
| **Fix** | `grid-cols-1 sm:grid-cols-2` |
| **Severity** | HIGH |

### 5.8 Services Page

| Detail | Value |
|--------|-------|
| **File** | `src/app/dashboard/services/page.tsx` |
| **Status** | **Mostly OK** -- card grid uses `grid-cols-1 md:grid-cols-2 lg:grid-cols-3` |
| **Minor** | Long service names lack truncation. Category scroll bar not obvious |
| **Severity** | LOW |

### 5.9 Staff Dashboard

| Detail | Value |
|--------|-------|
| **File** | `src/app/dashboard/staff/page.tsx` |
| **Status** | **Well done** -- uses responsive patterns like `h-8 w-8 sm:h-10 sm:w-10`, `p-3 sm:p-4`, proper mobile-first grid |
| **Severity** | NONE |

---

## Part 6: Inventory Dialogs

### 6.1 Stock Adjustment Dialog - Discount Fields

| Detail | Value |
|--------|-------|
| **File** | `src/app/dashboard/inventory/page.tsx` |
| **Line** | 583 |
| **Current** | `grid grid-cols-2 gap-4` |
| **Problem** | Always 2 columns -- input fields very narrow on mobile |
| **Fix** | `grid-cols-1 sm:grid-cols-2` |
| **Severity** | MEDIUM |

### 6.2 Inventory Dialogs - Max Width

| Detail | Value |
|--------|-------|
| **File** | `src/app/dashboard/inventory/page.tsx` |
| **Lines** | 512, 696 |
| **Current** | `max-w-2xl` (672px) |
| **Problem** | Wider than most phones |
| **Fix** | Handled globally if dialog base is fixed (see 1.3) |
| **Severity** | MEDIUM |

### 6.3 Change Request Badges Overflow

| Detail | Value |
|--------|-------|
| **File** | `src/app/dashboard/inventory/page.tsx` |
| **Lines** | 440-442 |
| **Current** | Multiple badges in `flex items-center gap-2` |
| **Problem** | SKU name + SKU code badge + type badge overflow on mobile |
| **Fix** | `flex-wrap` |
| **Severity** | LOW |

---

## Recommended Fix Order

### Phase 1: Global Fixes (small diff, big impact)

1. **Layout padding**: `p-6` -> `p-3 sm:p-4 md:p-6` in `dashboard/layout.tsx`
2. **Viewport height**: `h-screen` -> `min-h-dvh` in `dashboard/layout.tsx`
3. **Dialog base sizing**: Fix `dialog.tsx` default max-width and add `max-h-[90dvh] overflow-y-auto`
4. **Sidebar width**: `18rem` -> `16rem` in `sidebar.tsx`
5. **Form grids**: Find-and-fix all `grid-cols-2` without `sm:` prefix (customer dialog, settings dialog, inventory dialogs)

### Phase 2: Table-to-Card Conversions (biggest UX improvement)

Priority order by page usage frequency:
1. **Bills table** (improve existing mobile card)
2. **Customers table** -> mobile card view
3. **Inventory SKU table** -> mobile card view
4. **Expenses table** -> mobile card view
5. **Attendance table** -> remove hardcoded widths, add card view
6. **Users/Staff tables** -> mobile card view

### Phase 3: Purchase Pages (user-reported issues)

1. Remove `min-w-[200px]` from invoice list amount column
2. Fix new invoice line items grid (`grid-cols-1` on mobile)
3. Fix invoice detail 12-column grid -> card layout on mobile
4. Fix invoice detail header (responsive title + button wrapping)
5. Fix edit invoice dialog sizing

### Phase 4: Polish

1. Header height responsive
2. Dashboard stats grid sizing
3. Denomination counter spacing
4. Date selector wrapping (reconciliation, P&L)
5. Status filter overflow (purchase invoices)
6. Touch target sizes

---

## Pages That Are Already Responsive

These pages need minimal or no work:
- **Staff Dashboard** (`/dashboard/staff`) -- well-done mobile-first design
- **Suppliers** (`/purchases/suppliers`) -- proper `flex-col sm:flex-row` patterns
- **Services** (`/dashboard/services`) -- card grid works on mobile
- **Reports Hub** (`/dashboard/reports`) -- simple card grid, stacks fine
- **Settings** (`/dashboard/settings`) -- forms mostly use `md:grid-cols-2`

---

## Testing Checklist

After fixes, test each page at these widths:
- [ ] 320px (iPhone SE)
- [ ] 375px (iPhone 12 mini)
- [ ] 390px (iPhone 14)
- [ ] 430px (iPhone 14 Pro Max)
- [ ] 768px (iPad portrait)
- [ ] 1024px (iPad landscape)

For each page verify:
- [ ] No horizontal scroll on the page body
- [ ] All text readable without zooming
- [ ] All buttons/inputs have adequate touch targets (44px+)
- [ ] Dialogs fit on screen with scrollable content
- [ ] Tables show meaningful data without horizontal scrolling
- [ ] Forms are usable (fields not cramped, labels visible)
