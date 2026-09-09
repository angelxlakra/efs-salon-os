# Procurement, Inventory & Operations Rebuild — Discovery Brief

**Status:** Discovery only — no implementation approved  
**Date:** 2026-09-09  
**Audience:** Future Codex / Claude Code sessions, product owner, accountant, and implementation team

## Purpose

This document records the findings behind a proposed rebuild of Aasan's purchase, inventory, and related operations experience.

The goal is to make a real salon delivery easy to receive correctly, make approved retail products available in POS without a separate hidden configuration journey, and preserve existing audit history throughout.

## Business context supplied by the owner

- Aasan has individual branch deployments plus a central API and dashboard ecosystem.
- The central system is a logical hub, not a physical store.
- Supplier products and invoices physically arrive at one salon.
- That salon is the only location with a GSTIN; stock is then distributed to other, unregistered salons.

### Working interpretation

The GST-registered salon is the physical inbound receiving location and procurement owner. The central API should coordinate procurement, catalogue, allocation, and transfers; it should not pretend to be a separate warehouse or GST registration.

This is an architectural interpretation, not tax advice. The accountant must confirm the legal entity, registrations, ownership, and documentation required for each distribution route before the system encodes tax behaviour.

## Evidence and discovery boundary

The branch repository was examined at GitHub main commit 3ae4f242f4f0dd03547c626305dcd918b807b550 (2026-07-04). The local working tree and the separate central API/dashboard repository were not inspected in this discovery pass. Re-verify source and migrations before implementation.

Key branch implementation evidence:

- backend/app/api/purchases.py
- backend/app/api/inventory.py
- backend/app/models/purchase.py
- backend/app/models/inventory.py
- backend/app/models/inventory_transfer.py
- backend/app/services/inventory_service.py
- backend/app/services/inventory_transfer_service.py
- backend/app/services/central_sync_service.py
- frontend/src/app/(shell)/dashboard/purchases/
- frontend/src/app/(shell)/dashboard/inventory/

## Current architecture relevant to this work

- Frontend: Next.js 16, React 19, TypeScript, Tailwind, Zustand.
- Backend: FastAPI, SQLAlchemy, Alembic, PostgreSQL, Redis/RQ, APScheduler.
- Monetary amounts are intended to use integer paise; primary identifiers are ULIDs.
- POS validates that a retail product is active, sellable, priced, and in stock before it can be sold.

### Existing records that must be preserved

| Record | Existing responsibility | Preservation rule |
|---|---|---|
| Supplier | Vendor identity, GSTIN, terms, balances | Preserve IDs and supplier history. |
| PurchaseInvoice | Supplier invoice header, status, totals, balance | Do not rewrite posted or received history. |
| PurchaseItem | Supplier invoice line and current tax/cost fields | Keep as historical evidence; clarify semantics for new records. |
| SupplierPayment | Supplier payment audit and allocation | Preserve payment links and balances. |
| SKU | Local product/stock identity and retail settings | Preserve IDs, barcodes, stock, and POS links. |
| StockLedger | Immutable inventory movement record | Never replace with a calculated stock snapshot. |
| InventoryTransfer | Branch IN/OUT transfer record linked to central | Extend the contract rather than delete the audit trail. |
| POS bills/items | Sales, COGS, GST, and receipts | Must remain compatible with SKU identities. |

### Current central integration

The branch can authenticate to a central API, push/pull customer data, push metrics and heartbeats, and create/poll/cancel inventory transfers using central transfer IDs. It does not currently centralise supplier invoices, procurement approval, product-master ownership, or purchase receipts. Inspect the central repository before defining its new contract.

## Verified current purchase-to-POS flow

    Supplier delivery
      → user creates supplier invoice in Purchases
      → invoice is a draft
      → invoice line matches or creates an SKU
      → user marks invoice received
      → stock and weighted average cost are updated; ledger entry is written
      → user opens Inventory separately
      → user enables sellable and sets a retail price
      → item appears in POS

### Current implementation behaviour

1. Suppliers are managed before invoice entry.
2. A new purchase invoice requires a supplier, invoice number/date, and at least one line.
3. A barcode search can pre-fill a known SKU or prior purchase item. An unknown barcode can be quick-added.
4. If a line has no SKU, the purchase API tries an exact barcode match; otherwise it may create an SKU in a default General category with a generated PUR- code.
5. Automatically created SKUs start with stock 0 and are not automatically retail-sellable.
6. Receiving a purchase invoice creates the stock effect and updates weighted average cost.
7. POS only lists stock that is active, sellable, has a positive retail price, and is in stock.
8. Supplier payment is a separate workflow.

## Problems found

### Fragmented journey

Purchases, inventory, supplier payments, and POS readiness are separate page-level journeys. A product can be received yet remain invisible to POS with no single operational completion state. The application does not express the real job: **receive a delivery**.

### Two overlapping receipt paths

Stock can enter through purchase-invoice receipt or inventory change requests of type RECEIVE. These have overlapping cost and discount logic. Normal vendor delivery needs one canonical path; manual adjustment should remain a controlled exception.

### Supplier API duplication

Purchases and inventory expose supplier-management endpoints over the same supplier concept, with differing schemas and permissions. This is a split domain boundary and should be consolidated behind one canonical supplier contract.

### Fragile product creation and matching

The fallback creates a General SKU from a barcode or shortened product name. It is convenient but unsafe as a long-term product master: name variants can duplicate products; no-barcode goods are difficult to identify; the category is not useful for reporting; and the product is not POS-ready.

### Confusing tax and discount model

The invoice form's automatic calculator assumes a rate inclusive of tax. Supplier invoices also commonly arrive with tax excluded, invoice-level discounts, fixed line discounts, free-quantity schemes, mixed tax rates, and rounding.

The schema documents unit cost as all-in and after discount, while a separate discount amount is also subtracted by the model total calculation. That semantic ambiguity must be resolved before trusting weighted cost or invoice reconciliation.

New records must distinguish:

- supplier base rate;
- tax mode: inclusive, exclusive, exempt, or unknown/unclaimed;
- line percentage and fixed discounts;
- invoice-level discount;
- free/scheme quantity;
- printed tax amount and rounding; and
- landed/stock-cost policy.

Supplier purchase GST and customer-sale GST are separate concerns. Product POS billing currently uses MRP-inclusive GST; supplier invoices represent inward purchases and potential input tax.

## Target information architecture

Replace separate Purchases and Inventory entry points with one **Stock & Suppliers** operations workspace.

| Job | Workspace view |
|---|---|
| Receive a vendor delivery | Deliveries / Receive stock |
| Find or configure a product | Product catalogue |
| Check quantities and movements | Stock on hand / movement ledger |
| Send goods to a branch | Allocations / dispatches |
| Confirm goods arrived | Incoming transfers |
| Track supplier liability | Supplier invoices / payments / statement |

POS remains a fast branch-local selling experience and consumes a read model of products approved for that branch.

## Recommended central-hub design

### Ownership boundaries

| Capability | Central hub | GST receiving salon | Other branch |
|---|---|---|---|
| Supplier master and vendor invoice document | Authoritative | Operates through central | Read-only as appropriate |
| Product master, barcode aliases, category defaults | Authoritative | Can propose/approve by role | Receives assigned catalogue |
| Physical inbound receipt | Coordinates and records | Confirms delivered quantities | No |
| Input-tax evidence | Stores and reconciles | Owns/approves as GST recipient | No independent claim assumed |
| Stock at GST receiving salon | Projected/audited centrally | Physically held and confirmed | No |
| Branch allocation/dispatch | Authoritative workflow | Dispatches | Receives/accepts |
| Branch stock on hand | Synchronised view | Own local ledger projection | Own local ledger projection |
| POS sellability | Default policy/catalogue | Can approve | Applies only after local receipt |

### Model these facts independently

1. legal entity
2. GST registration / recipient GSTIN
3. location, including the GST receiving salon
4. branch
5. product
6. stock location
7. supplier invoice
8. purchase receipt
9. allocation / transfer
10. branch receipt

Do not infer legal ownership from a branch name or physical location.

### Auditable event sequence

    Vendor invoice captured
      → invoice extraction + operator review
      → central approval
      → physical receipt at GST salon
      → supplier invoice and central receipt recorded
      → stock ledger entry at receiving location
      → allocation to one or more branches
      → dispatch from receiving salon
      → branch confirms physical receipt
      → branch stock projection increases
      → branch POS makes sellable products available

A dispatch must not silently increase stock at the destination, and a branch must not sell goods merely because they were allocated on paper.

### Compatibility strategy

- Preserve existing ULIDs, paise amounts, supplier invoices, SKU IDs, bills, and stock ledgers.
- Add central IDs and source references; do not mutate historical documents to make them look central.
- Introduce a compatibility layer that translates the new central contract into current branch records during migration.
- Reuse existing InventoryTransfer central-transfer IDs and IN/OUT records where safe.
- Use idempotency keys for every central-to-branch write.
- Reconcile quantity and value after every migration/cutover batch.
- Keep old documents read-only and visible in the new workspace as historical records.

## Target delivery workflow

The core action is **Receive supplier delivery**, not “create purchase invoice.”

1. **Capture:** Upload or photograph the invoice. Select an existing supplier or create one inline only when necessary.
2. **Extract and review:** Show the image beside a structured draft with supplier/GSTIN, invoice number/date, recipient GSTIN, receiving location, lines, tax, discounts, schemes, rounding, and grand-total difference.
3. **Resolve each line:** Match an existing product, create a new retail product, create a salon-use consumable, or flag an exception. For retail products, propose printed MRP but require explicit confirmation if it is missing or unsuitable.
4. **Validate:** Calculate totals by selected tax mode and discounts. A mismatch needs correction or an authorised reason/round-off.
5. **Receive and publish:** One reviewed approval stores evidence, records payable and stock movements/cost, records catalogue decisions, and publishes approved retail products to the receiving salon POS.

Allocation to another branch is a subsequent, explicit action—not an implicit side effect of receiving.

## AI invoice parser recommendation

Use AI/OCR as a **drafting and matching assistant**, not as an autonomous posting engine.

It should return structured fields plus confidence per field/line, image evidence for important values, candidate product matches with reasons, full invoice-total reconciliation, and warnings for missing tax, unknown products, low confidence, or mismatch.

### Matching rules

1. Exact barcode: strongest automatic match.
2. Exact vendor product code/alias: strong suggested match.
3. Known supplier-specific product alias: suggested match.
4. Fuzzy name/brand/volume: review-required candidate only.
5. No confident match: create a draft product; never silently merge it into an existing SKU.

AI must not decide whether GST input credit is legally claimable, the stock-cost policy, an unverified product match, a retail selling price, or invoice/stock posting.

Because Aasan is local-first, decide whether invoices use an approved cloud model, a self-hosted OCR service, or an opt-in provider. Retain original evidence, extraction version, parser output, and reviewer decisions for audit and model improvement.

## GST and accounting guardrails

The system must be configured from the salon's legal/accounting policy rather than assuming a tax outcome.

- Input-tax credit depends on the registered recipient, prescribed invoice/documentation, receipt of goods/services, and other statutory conditions. [CBIC CGST Act, Section 16](https://cbic-gst.gov.in/pdf/CGST-Act-Updated-31082021.pdf)
- GST registrations across states are treated as distinct persons; credit is not freely cross-utilised between different registered persons. [CBIC guidance on scope of supply](https://cbic-gst.gov.in/pdf/e-version-gst-fliers/eflier-meaning-scopeofsupply14062017.pdf) and [CBIC FAQs](https://cbic-gst.gov.in/faq.html)
- An Input Service Distributor is defined for tax invoices concerning **services**; it is not an inventory-transfer model for goods. [CBIC CGST Act](https://cbic-gst.gov.in/hindi/CGST-bill-e.html)

Before implementation, the accountant must specify:

1. whether the unregistered salons are the same legal entity and operate under the GST salon's registration/declared places of business;
2. whether input GST is recoverable for each product class and therefore excluded from, or included in, inventory cost;
3. documentation and tax treatment required when stock moves from the GST salon to an unregistered salon;
4. how credit notes, returns, damages, free goods, and partial deliveries affect input tax and stock cost; and
5. authorised roles for tax discrepancies and stock-receipt differences.

## Proposed phases

### A. Operational and data discovery

- Inspect central API/dashboard source and current database schema.
- Shadow 10–20 real deliveries.
- Collect anonymised invoices covering inclusive/exclusive tax, discounts, free quantity, credit notes, partial receipt, and no-barcode products.
- Produce canonical field definitions and a state-transition diagram.

### B. Accounting rules and tests

- Obtain signed-off cost/tax/transfer rules from the accountant.
- Write reconciliation examples and invariant tests for every invoice archetype.

### C. Vertical slice

- Build one central delivery draft and one branch-compatible receiving flow.
- Start with manual entry plus deterministic calculations, not AI.
- Prove existing retail SKU, new retail SKU, and consumable receipt without breaking POS or ledgers.

### D. Central allocation and branch confirmation

- Implement allocation, dispatch, branch receipt, idempotency, retry, and reconciliation.

### E. AI and broader frontend replacement

- Add upload, extraction, evidence review, product matching, and feedback loop.
- Replace legacy Purchases/Inventory only after the new workflow is stable.
- Expand this operations design language to the wider frontend in controlled vertical slices.

## Non-negotiable invariants

- All money remains integer paise.
- Existing ULIDs and historical records remain stable.
- Stock cannot be created, destroyed, or moved without an immutable movement/audit record.
- A received supplier invoice cannot be silently reinterpreted after posting.
- A POS sale can only reduce stock that the selling branch has confirmed as received.
- A product cannot become POS-sellable without an explicit retail price and sale eligibility.
- Central-to-branch operations are idempotent and safe to retry.
- Invoice total, payment balance, stock quantity, and stock value reconciliations are testable.
- AI output is reviewable evidence, never an unreviewed accounting authority.

## Open questions

1. Where is the central API/dashboard repository, and what contracts/database models already exist?
2. Are all salons owned by the same legal entity, and are the unregistered salons declared/treated as places of business under the GST registration? Confirm with the accountant.
3. Which items are retail stock, which are salon consumables, and can one SKU serve both roles?
4. Is MRP normally available for retail products, and may branches override a central retail price?
5. What must work while the central connection is unavailable?
6. Which invoice-image processing option meets privacy and cost requirements?
7. What approval roles are required for receipt, product creation, tax mismatch, allocation, dispatch, and branch receipt?

## Immediate next step

Do not begin by editing existing purchase forms. Inspect the central repository, collect representative real invoices, and obtain accountant answers to the GST/cost/transfer questions. Then write an approved implementation plan for one vertical slice:

    central delivery draft → GST-salon receipt → one branch allocation → branch confirmation → POS availability
