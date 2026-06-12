# GST Split Billing

Dual-rate GST billing for a GST-registered salon: services taxed at 5%
(exclusive), retail products at 18% (inclusive in MRP), with each checkout
producing a compliant tax invoice per rate-class.

> Activated June 2026 when the salon obtained GST registration. Bills created
> before activation are untouched (see [Migration & activation](#migration--activation)).

---

## Tax model

| Line kind | Rate | Mode | Who pays the tax |
|-----------|------|------|------------------|
| Service (GST-registered) | 5% (2.5% CGST + 2.5% SGST) | **Exclusive** — added on top of the menu price | Customer pays menu price + 5% |
| Service (not registered) | — | None | No GST; customer pays the menu price |
| Retail product | 18% (9% CGST + 9% SGST) | **Inclusive** — extracted from the MRP | Customer pays the MRP (tax already inside) |
| Package sale / redemption | — | None | No GST line (redemptions have zero realised value) |

**Two independent switches:**
- **Effective date** (`gst_effective_from`) activates the *split-billing scheme*:
  retail products always print on their own bill at 18% inclusive, services on
  theirs. This is independent of registration — a salon can separate product
  bills without charging GST on services.
- **GST registered** (`gst_registered`) additionally puts **5% on services**.
  When off, the service bill carries no GST and prints as a plain receipt (no
  TAX INVOICE title/GSTIN/declarations); the product bill is still a 18% tax
  invoice.

- **CGST always equals SGST** (equal halves), each floored to the paise.
- **Discounts apply before tax** and are allocated proportionally across all
  lines (floor-proportional, remainder to the largest lines), so a service
  discount reduces the base before the 5% is added and a product discount
  reduces the inclusive price before extraction.
- **Rounding: floor.** Every tax amount floors to the paise; the payable total
  floors to the whole rupee (the salon absorbs the paise — the customer is
  never charged extra). This replaces the legacy `ROUND_HALF_UP`.

All money is integer paise. The pure tax functions live in
`backend/app/services/tax_calculator.py`
(`calculate_line_tax`, `round_down_to_rupee`); the legacy
`calculate_tax_breakdown` / `round_to_rupee` remain for pre-registration bills.

## Split billing

A single checkout with **both** services and products produces **two bills**
sharing a `bill_group_id`:

- a **service bill** (`bill_class = service`) → `SRV-YY-NNNN` invoice series
- a **product bill** (`bill_class = product`) → `PRD-YY-NNNN` invoice series

Single-class carts produce one bill. Legacy/pre-registration bills are
`bill_class = mixed_legacy` and keep the `SAL-YY-NNNN` series.

**One payment settles both.** `POST /api/pos/bills/group` creates the
group; `POST /api/pos/bills/group/{bill_group_id}/payments` settles it with a
single customer tender (whole rupees, must equal the group grand total
exactly). The tender is split service-bill-first into one `Payment` row per
bill, linked by `payment_group_id`; both bills post atomically (invoices,
stock reduction, package sales, customer stats all in one transaction).

Refunds are **per-bill**: each half can be refunded independently; the credit
note inherits the original bill's `bill_class` and invoice series.

## Invoices (Rule 46 compliance)

Service/product bills render as a **TAX INVOICE** on the 80mm receipt
(`backend/app/services/receipt_service.py`) with:

- salon name, address, and prominent **GSTIN**
- consecutive invoice number (`SRV-`/`PRD-`, ≤16 chars) + date/time
- customer name (and phone if present)
- per-line item name, qty, rate, amount
- **Taxable Value**, then **CGST** and **SGST** as separate lines at the
  applicable rate (products marked *incl.* in MRP), Round Off, bold **TOTAL**
- reverse-charge declaration ("Whether tax is payable under reverse charge: No")
- **Authorised Signatory** line

Credit notes render as **CREDIT NOTE** referencing the original invoice.

> **Deferred:** per-line HSN/SAC codes. The columns exist
> (`Service.sac_code`, `SKU.hsn_code`, with salon-level defaults
> `default_service_sac_code` / `default_product_hsn_code` in settings) but are
> not yet printed on invoices.

## Reporting

The tax report (`GET /api/reports/tax`) gains a **per-rate breakdown**
(`rate_breakdown`): taxable value + CGST + SGST per 5%/18% slab, computed from
posted GST-classed bills' line items. Legacy zero-tax bills and refunded
originals are excluded. GSTIN/name/address come from saved settings.

## Migration & activation

The scheme is gated by two settings fields:

- `gst_registered` (bool) — explicit owner toggle; a GSTIN alone never flips
  billing behaviour
- `gst_effective_from` (date) — clean boundary; bills dated before it use the
  legacy inclusive-18% math

**Activation runbook:**

1. Deploy and run migrations (`alembic upgrade head`). The
   `o8p9q0r1s2t3` migration adds the per-line tax / group columns and
   **zeroes the tax fields of all existing bills** (totals unchanged) — no GST
   was actually collected before registration, so they are excluded from GST
   reports.
2. In Settings, enter the **GSTIN**, enable **GST registered**, and set
   **GST effective from** to the registration date.
3. New bills from that date use the dual-rate split scheme; older bills remain
   exactly as they were.

## Key files

- `backend/app/services/tax_calculator.py` — per-line tax, floor rounding
- `backend/app/services/discount_allocator.py` — proportional discount split
- `backend/app/services/billing_service.py` — `create_bill_group`,
  `pay_bill_group`, `_recalculate_bill_tax`, `_generate_invoice_number`
- `backend/app/services/invoice_generator.py` — SRV/PRD/SAL series (own locks)
- `backend/app/services/receipt_service.py` — Rule 46 tax invoice
- `backend/app/api/pos.py` — `/bills/group` + `/bills/group/{id}/payments`
- `frontend/src/stores/cart-store.ts` — `computeGstBreakdown` (mirrors server)
- `frontend/src/components/pos/cart-sidebar.tsx` — sectioned cart
- `frontend/src/components/pos/payment-modal.tsx` — group checkout UI
