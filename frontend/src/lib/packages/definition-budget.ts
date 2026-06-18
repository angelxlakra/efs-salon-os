// frontend/src/lib/packages/definition-budget.ts
// Per-service redeemable budget derived from a PackageDefinition's blocks —
// the cart-side mirror of the backend _block_sale_lines mapping, so a package
// being SOLD in the cart can be an eligibility source before its sale exists.

import type { PackageBlock } from "@/types/package";

const UNLIMITED = 9999;

export interface ServiceBudget {
  lineRemaining: number;
  sharedKey: string | null;
  sharedRemaining: number;
}

const num = (v: string) => {
  const n = parseInt(v);
  return Number.isFinite(n) ? n : 0;
};

export function definitionServiceBudgets(
  definitionId: string,
  blocks: PackageBlock[]
): Map<string, ServiceBudget> {
  const out = new Map<string, ServiceBudget>();
  // Global pool = Σ over fixed-items qty + choice@purchase picks (mirrors backend).
  let pool = 0;
  for (const b of blocks) {
    if (b.kind === "items") for (const r of b.rows) pool += num(r.quantity) || 1;
    else if (b.kind === "choice" && b.choose_at === "purchase") pool += num(b.picks);
  }
  const poolKey = `${definitionId}:pool`;

  for (const b of blocks) {
    if (b.kind === "items") {
      for (const r of b.rows) {
        out.set(r.service_id, {
          lineRemaining: num(r.quantity) || 1,
          sharedKey: poolKey,
          sharedRemaining: pool,
        });
      }
    } else if (b.kind === "choice" && b.choose_at === "purchase") {
      for (const r of b.rows) {
        out.set(r.service_id, { lineRemaining: 1, sharedKey: poolKey, sharedRemaining: pool });
      }
    } else if (b.kind === "choice") {
      const key = `${definitionId}:block:${b.id}`;
      for (const r of b.rows) {
        out.set(r.service_id, { lineRemaining: UNLIMITED, sharedKey: key, sharedRemaining: num(b.picks) });
      }
    } else if (b.kind === "pool") {
      const key = `${definitionId}:block:${b.id}`;
      for (const r of b.rows) {
        out.set(r.service_id, { lineRemaining: UNLIMITED, sharedKey: key, sharedRemaining: num(b.sessions) });
      }
    } else if (b.kind === "unlimited") {
      for (const r of b.rows) {
        out.set(r.service_id, { lineRemaining: UNLIMITED, sharedKey: null, sharedRemaining: UNLIMITED });
      }
    }
    // credit: no service redemption
  }
  return out;
}
