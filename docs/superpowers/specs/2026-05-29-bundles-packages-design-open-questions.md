# Bundles & Packages — Open Questions for Product

Questions surfaced during the design round that need **product-owner** input (not resolvable from the brief alone). The engineering session should route these back to the product brainstorm before the spec is finalized.

---

1. **Design-system reconciliation (highest priority).**
   The brief's §1 specifies copper `#b0561f`, Instrument Serif, Inter, surface `#fafaf9`. The **shipped codebase** uses Navy `#1c104c` + Gold `#c9a96e`, Cormorant Garamond + DM Sans, cream `#f8f5f0`. All mockups were built against the **live tokens**. *Is the brief describing an intended re-skin that hasn't landed yet, or is it simply stale?* If a re-skin is planned, the package colour grammar (Navy = paid-now / Gold = owned) needs re-mapping onto the new palette before build.

2. **POS rail width on the smallest tablet.**
   Direction A (Entitlements Rail) costs ~240px. On a 10" tablet in landscape inside a protective case, that drops the service grid to 3 columns. *Is that acceptable, or do we need a breakpoint where the rail collapses to the Direction-B strip below some width?* This determines whether the "active packages badge" stays a first-class fallback or can be retired.

3. **Customer profile is a dialog today, not a page.**
   The current customer detail is `customer-history-dialog.tsx` (a modal), but the brief assumes packages surface on `/dashboard/customers/[id]` (a page). The Packages + Overview tabs were designed as a **new tabbed profile page**. *Confirm we're promoting customer detail from dialog → full page as part of (or as a prerequisite to) this work* — it's a larger change than "add a packages section" and affects routing.

4. **Bundle (single-sitting combo) at POS — redeem timing.**
   A bundle is `total_sessions = 1` consuming all included services in one redemption. *When a bundle is sold and redeemed in the **same** visit (the common bridal case), is it one combined sale+redeem action at POS, or always two steps (sell → then redeem)?* Affects whether we need a "sell & redeem now" affordance on the sale line.

5. **Multi-package FIFO override friction.**
   The multi-package selector pre-selects soonest-expiry (FIFO). *Should the cashier be able to override silently, or does choosing a non-FIFO package require a reason/confirmation (e.g. for audit)?* Currently designed as a silent override with a confirm-with-customer prompt only.

6. **First-time-selling coachmark.**
   Q-VIS-6 asks about one-time guidance for receptionists. *Do we want a dismissible inline coachmark on the new Packages chip this round, or defer all onboarding to a later pass?* Designed but not assumed.

7. **Tier badge + AI add-ons slots.**
   Slots are reserved next to the customer name (tier, sub-project D) and in the Overview right rail (recommended add-ons, sub-project E). *Confirm these are placeholders only for now* — no behavior designed, just spatial reservation, per §3.10.

8. **Extend-expiry entry point.**
   The Owner-only "Extend Expiry" action is referenced (§3.4) but has no dedicated screen in §6. It's currently tucked in the profile package-card kebab. *Does it need its own confirmation modal with the audit-reason field (like refund), or is an inline date-bump with a logged reason enough?*

9. **Pending-balance interaction with package refunds.**
   The refund-to picker offers "Adjust pending balance." *If a customer has both a refundable package and an outstanding pending balance, should the refund default to netting against the pending balance, or always default to Cash?* Affects the picker's default selection.

10. **Redemption line price visibility to the customer.**
    Redemption lines show the snapshotted price struck through with "Redeemed." *On the 80mm printed receipt (out of scope here but adjacent), do we show the redeemed value or just "Paid via package"?* Flagging because the on-screen treatment may need to match the receipt decision for consistency.
