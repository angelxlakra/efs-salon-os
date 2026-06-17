// frontend/src/lib/packages/entitlement-progress.ts
//
// Derive block-labelled progress rows for the customer entitlements view from a
// sold PackageSale. v2 sales carry blocks_snapshot for labels; per-line
// consumption is matched from sale.items by service_id. v1 sales fall back to a
// single counted row driven by sessions_remaining.

import type { PackageSale, PackageSaleItem, PackageBlock } from "@/types/package";

export type EntitlementTone = "accent" | "info" | "gold" | "success";

export interface EntitlementRow {
  key: string;
  label: string; // block summary / line label
  detail: string; // e.g. "4 of 10 used", "∞ unlimited", "₹3,250 of ₹5,000"
  used: number;
  total: number; // 0 ⇒ no bar (unlimited / informational)
  tone: EntitlementTone;
  bonus: boolean;
}

function itemsFor(sale: PackageSale, serviceIds: string[]): PackageSaleItem[] {
  const set = new Set(serviceIds);
  return sale.items.filter((i) => set.has(i.service_id));
}

const rupees = (paise: number) => Math.round(paise / 100).toLocaleString("en-IN");

function blockRows(block: PackageBlock, sale: PackageSale): EntitlementRow[] {
  const bonus = block.bonus;
  switch (block.kind) {
    case "items": {
      const ids = block.rows.map((r) => r.service_id);
      const lines = itemsFor(sale, ids);
      const total = lines.reduce((s, i) => s + (i.max_redemptions ?? 0), 0);
      const used = lines.reduce(
        (s, i) => s + ((i.max_redemptions ?? 0) - (i.remaining ?? 0)),
        0
      );
      return [
        {
          key: block.id,
          label: block.rows.map((r) => r.service_name).join(", ") || "Items",
          detail: total ? `${used} of ${total} used` : "included",
          used,
          total,
          tone: "accent",
          bonus,
        },
      ];
    }
    case "choice": {
      if (block.choose_at === "purchase") {
        // Locked services are exactly the sale items present from this block.
        const ids = block.rows.map((r) => r.service_id);
        const lines = itemsFor(sale, ids);
        return lines.map((i) => ({
          key: `${block.id}-${i.service_id}`,
          label: i.service_name ?? "Choice",
          detail:
            (i.remaining ?? 0) <= 0 ? "1 of 1 used ✓" : "0 of 1 used",
          used: (i.max_redemptions ?? 1) - (i.remaining ?? 0),
          total: 1,
          tone: "gold",
          bonus,
        }));
      }
      const picks = parseInt(block.picks) || 0;
      return [
        {
          key: block.id,
          label: `${picks} use${picks === 1 ? "" : "s"} · any of ${block.rows.length}`,
          detail: block.rows.map((r) => r.service_name).join(" · "),
          used: 0,
          total: 0,
          tone: "gold",
          bonus,
        },
      ];
    }
    case "unlimited":
      return [
        {
          key: block.id,
          label: block.rows.map((r) => r.service_name).join(", ") || "Unlimited",
          detail:
            "∞ unlimited" + (block.daily_cap ? ` · ${block.daily_cap}/day` : ""),
          used: 0,
          total: 0,
          tone: "info",
          bonus,
        },
      ];
    case "pool": {
      const sessions = parseInt(block.sessions) || 0;
      return [
        {
          key: block.id,
          label: `${sessions} sessions · ${block.rows
            .map((r) => r.service_name)
            .join(", ")}`,
          detail: "shared pool",
          used: 0,
          total: 0,
          tone: "accent",
          bonus,
        },
      ];
    }
    case "credit":
      return [
        {
          key: block.id,
          label: "Credit wallet",
          detail: `₹${rupees(block.amount_paise)} balance`,
          used: 0,
          total: 0,
          tone: "success",
          bonus,
        },
      ];
  }
}

/** Block-labelled rows for the entitlements card. */
export function entitlementRows(sale: PackageSale): EntitlementRow[] {
  if (sale.blocks_snapshot?.length) {
    return sale.blocks_snapshot.flatMap((b) => blockRows(b, sale));
  }
  // v1 fallback: a single counted progress row.
  const total = sale.total_sessions_snapshot ?? 0;
  const used = total - (sale.sessions_remaining ?? 0);
  return [
    {
      key: sale.id,
      label: "Sessions",
      detail: total ? `${used} of ${total} used` : "active",
      used,
      total,
      tone: "accent",
      bonus: false,
    },
  ];
}
