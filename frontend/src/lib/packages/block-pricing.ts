// frontend/src/lib/packages/block-pricing.ts
//
// Pure derived math for the Package Builder v2 block model. Mirrors the design
// prototype's blockValue / blockSummary / discountAmt / priceOf, but works in
// PAISE (integers) to match the rest of the money layer. No React, no I/O.

import type { DiscountMode, PackageBlock } from "@/types/package";

export interface Discount {
  mode: DiscountMode;
  value: string; // rupees for flat/final, a percentage for pct (UI convention)
}

function num(v: string | number | null | undefined): number {
  const n = typeof v === "number" ? v : parseFloat(v ?? "");
  return Number.isFinite(n) ? n : 0;
}

function avgPaise(rows: Array<{ unit_price_paise: number }>): number {
  if (!rows.length) return 0;
  return rows.reduce((s, r) => s + r.unit_price_paise, 0) / rows.length;
}

/** Customer-facing value of a single block, in paise. */
export function blockValue(b: PackageBlock): number {
  switch (b.kind) {
    case "items":
      return b.rows.reduce(
        (s, r) => s + (num(r.quantity) || 1) * r.unit_price_paise,
        0
      );
    case "choice":
      return Math.round(num(b.picks) * avgPaise(b.rows));
    case "unlimited":
      return b.assigned_value_paise;
    case "pool":
      return Math.round(num(b.sessions) * avgPaise(b.rows));
    case "credit":
      return b.amount_paise;
  }
}

/** Choice and pool blocks are estimates (average of options) — flag with "≈". */
export function isEstimated(b: PackageBlock): boolean {
  return b.kind === "choice" || b.kind === "pool";
}

const rupees = (paise: number) => Math.round(paise / 100).toLocaleString("en-IN");

/** Auto-generated, non-editable title for a block (mirrors prototype). */
export function blockSummary(b: PackageBlock): string {
  switch (b.kind) {
    case "items": {
      if (!b.rows.length) return "Empty — add services";
      return b.rows
        .map((r) => `${num(r.quantity) || 1} × ${r.service_name || "…"}`)
        .join(", ");
    }
    case "choice": {
      const n = num(b.picks) || 0;
      if (b.choose_at === "visit") {
        // n is a shared total-use budget across the options (any mix, any visit).
        return `${n} use${n === 1 ? "" : "s"} from ${b.rows.length} options`;
      }
      return `Pick ${n} of ${b.rows.length} — locked at purchase`;
    }
    case "unlimited":
      return b.rows.length
        ? `Unlimited ${b.rows.map((r) => r.service_name || "…").join(", ")}`
        : "Unlimited — add services";
    case "pool":
      return `${num(b.sessions) || 0} sessions across ${b.rows.length} service${
        b.rows.length === 1 ? "" : "s"
      }`;
    case "credit":
      return `₹${rupees(b.amount_paise)} spendable ${
        b.scope === "any"
          ? "on anything"
          : b.scope === "services"
            ? "on services only"
            : "on retail only"
      }`;
  }
}

export const chargeableOf = (blocks: PackageBlock[]): number =>
  blocks.filter((b) => !b.bonus).reduce((s, b) => s + blockValue(b), 0);

export const bonusOf = (blocks: PackageBlock[]): number =>
  blocks.filter((b) => b.bonus).reduce((s, b) => s + blockValue(b), 0);

export const totalValueOf = (blocks: PackageBlock[]): number =>
  chargeableOf(blocks) + bonusOf(blocks);

/** Discount amount in paise. `value` is rupees for flat/final, % for pct. */
export function discountAmtPaise(
  chargeablePaise: number,
  d: Discount | undefined
): number {
  if (!d || !d.value) return 0;
  const v = num(d.value);
  if (d.mode === "pct") return (chargeablePaise * v) / 100;
  if (d.mode === "flat") return v * 100;
  return Math.max(0, chargeablePaise - v * 100); // final
}

/** Final sell price in paise: chargeable minus the (clamped) discount. */
export function priceOf(blocks: PackageBlock[], d: Discount | undefined): number {
  const c = chargeableOf(blocks);
  return Math.max(0, Math.round(c - Math.min(discountAmtPaise(c, d), c)));
}

/** Customer-savings fraction in [0,1]; 0 when there's no value. */
export function savingsFraction(
  blocks: PackageBlock[],
  d: Discount | undefined
): number {
  const total = totalValueOf(blocks);
  if (total <= 0) return 0;
  return Math.max(0, 1 - priceOf(blocks, d) / total);
}
