# GST Split Billing — Implementation Plan (2026-06-11)

Salon obtained GST registration. Replace the display-only GST behavior with a real
dual-rate, dual-bill scheme.

## Business decisions (confirmed by owner)

| Decision | Choice |
|---|---|
| Services | 5% GST **exclusive** — added on top of menu price (2.5% CGST + 2.5% SGST) |
| Retail products | 18% GST **inclusive** in MRP (9% + 9%) — extracted from selling price |
| Mixed cart | One checkout → two bills (service + product), **one payment**, both shown separately + grand total |
| Invoice series | Separate: `SRV-YY-NNNN` for service bills, `PRD-YY-NNNN` for product bills (legacy `SAL` untouched) |
| Rounding | All tax amounts **floor to paise**; payable total **floors to whole rupee** (GST mode only; legacy bills keep ROUND_HALF_UP) |
| Old bills | Backfill: zero out `cgst_amount`/`sgst_amount`/`tax_amount` (totals unchanged); exclude from GST reports |
| Package redemption | No tax on redemption lines (₹0 realized value → ₹0 tax); package sales keep current behavior for now |
| Refunds | Per-bill refunds allowed (each half of a group refundable independently, credit note in its own series) |
| Cart preview | Frontend preview replicates server floor math exactly |
| Discounts | Allocated proportionally across lines BEFORE tax; remainder to largest line; service discount reduces base before 5% added; product discount reduces inclusive price before extraction |

## Design

- **Mode switch**: `SalonSettings.gst_registered` (bool) + `gst_effective_from` (date) + invoice prefix settings. GST behavior active only when registered AND bill date ≥ effective date. GSTIN remains the displayed number.
- **Per-line tax**: `BillItem` gains `tax_rate` (int %, 0/5/18), `tax_mode` (`exclusive|inclusive|none`), `taxable_value`, `cgst_amount`, `sgst_amount` (paise). Bill tax columns = sum of lines.
- **Bill split**: `Bill.bill_group_id` (ULID, shared by siblings), `Bill.bill_class` (`service|product|mixed_legacy`). `bill_type` (normal/credit_note) axis unchanged.
- **Payments**: `Payment.bill_id` stays one-to-one. One UI tender splits into one Payment row per bill, tied by `Payment.payment_group_id`. Group creation + payment posting in ONE transaction (no partial post).
- **Invoice generator**: parametrize `generate(db, prefix, lock_id)` — SAL/987123, SRV/987124, PRD/987125. Credit notes use their bill's series.
- **Accounting**: DaySummary/GST report gain per-rate (5% vs 18%) breakdown; legacy `mixed_legacy` bills excluded from GST taxable totals.

## Phases (each ≤3 files, implement → test → verify)

0. **Settings & mode flag** — `models/settings.py`, migration, `api/settings.py`
1. **Tax calculator pure functions** — `services/tax_calculator.py` + tests (`calculate_line_tax`, `round_down_to_rupee`; legacy methods untouched)
2. **Schema: per-line tax + groups** — `models/billing.py`, migration w/ legacy zero-tax backfill, model tests
3. **Discount allocator** — new `services/discount_allocator.py` + tests (sum of line discounts == entered discount)
4. **Billing service single-bill path** — `services/billing_service.py`, `services/invoice_generator.py`, tests
5. **Checkout group / split orchestration** — `billing_service.py` (`create_bill_group`, `pay_bill_group`), `api/pos.py`, tests
6. **Refunds of split bills (per-bill)** — `billing_service.py`, `api/pos.py`, tests
7. **Accounting per-rate breakdown** — `models/accounting.py` + migration, `services/accounting_service.py`, tests
8. **Cart UI sections** — `stores/cart-store.ts`, `components/pos/cart-sidebar.tsx`, `stores/settings-store.ts`
9. **Payment UI for two bills** — `components/pos/payment-modal.tsx` + checkout caller
10. **Receipts per bill** — `components/bills/bill-details-dialog.tsx`, `lib/whatsapp-receipt.ts`, receipt endpoint

## Invoice compliance (Rule 46, CGST Rules — owner requires full compliance)

Receipts in GST mode must show:
- Supplier: salon name, address, **GSTIN** (from settings)
- Consecutive invoice number ≤16 alphanumeric chars (`SRV-YY-NNNN` / `PRD-YY-NNNN` ✓)
- Date of issue
- **HSN/SAC code per line** — add `hsn_sac_code` to `Service` (SAC, default `999721` beauty/grooming)
  and `InventorySku`/product (HSN, e.g. 3305 hair preparations); settings-level defaults, per-item override
- Description, quantity, unit, line value
- Taxable value (after discount), tax rate, **CGST and SGST amounts as separate lines**
- Recipient name (and address if invoice value ≥ ₹50,000)
- "Whether tax is payable on reverse charge: No" declaration
- Authorized signatory line
- Phase 2 gains the HSN/SAC columns; Phase 10 renders all of the above.

## Risks / edge cases

- Atomic group post: never commit one sibling bill without the other.
- Overpayment / pending-balance tolerance must be applied once at group level, not per bill.
- Per-line discount rounding must be deterministic (remainder → largest line).
- Three advisory lock IDs must not collide.
- `gst_effective_from` should be a clean date boundary (no mixed-mode day summaries).
- Cart persistence (`populateFromSession`) must survive the sectioned cart refactor.

## Docs to update on completion

`docs/models/03-billing.md`, `docs/models/08-accounting.md`,
`docs/architecture/04-backend-spec.md`, `docs/deployment/04-handover-guide.md`,
new `docs/features/11-gst-billing.md`, link in `docs/INDEX.md`.
