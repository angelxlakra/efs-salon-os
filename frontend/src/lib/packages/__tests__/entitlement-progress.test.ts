import { describe, expect, it } from "vitest";
import { entitlementRows } from "@/lib/packages/entitlement-progress";
import type { PackageSale, PackageSaleItem, PackageBlock } from "@/types/package";

function item(p: Partial<PackageSaleItem>): PackageSaleItem {
  return {
    id: "i",
    service_id: "s",
    service_name: "Svc",
    quantity: 1,
    snapshot_unit_price_paise: 0,
    snapshot_gst_rate_pct: "0",
    locked: false,
    max_redemptions: null,
    remaining: null,
    pool_exempt: false,
    ...p,
  };
}

function sale(blocks: PackageBlock[] | null, items: PackageSaleItem[], extra: Partial<PackageSale> = {}): PackageSale {
  return {
    id: "sale1",
    bill_id: "b",
    package_definition_id: "d",
    customer_id: "c",
    selling_staff_id: null,
    sold_at: "2026-06-01",
    expires_at: "2026-09-01",
    entitlement_type_snapshot: "counted",
    shareability_snapshot: "owner_only",
    cancellation_fee_pct_snapshot: "20",
    total_sessions_snapshot: 10,
    sessions_remaining: 6,
    status: "active",
    refunded_at: null,
    refund_bill_id: null,
    blocks_snapshot: blocks,
    items,
    created_at: "",
    updated_at: "",
    ...extra,
  };
}

describe("entitlementRows", () => {
  it("computes used/total for a fixed-items block", () => {
    const blocks: PackageBlock[] = [
      { id: "b1", kind: "items", bonus: false, rows: [
        { service_id: "hair", service_name: "Haircut", quantity: "10", unit_price_paise: 50000 },
      ] },
    ];
    const rows = entitlementRows(sale(blocks, [
      item({ service_id: "hair", service_name: "Haircut", max_redemptions: 10, remaining: 6 }),
    ]));
    expect(rows[0].used).toBe(4);
    expect(rows[0].total).toBe(10);
    expect(rows[0].detail).toBe("4 of 10 used");
  });

  it("renders unlimited as an informational ∞ row (no bar)", () => {
    const blocks: PackageBlock[] = [
      { id: "b1", kind: "unlimited", bonus: false, assigned_value_paise: 0, daily_cap: "1",
        rows: [{ service_id: "wash", service_name: "Wash" }] },
    ];
    const rows = entitlementRows(sale(blocks, [
      item({ service_id: "wash", service_name: "Wash", pool_exempt: true }),
    ]));
    expect(rows[0].total).toBe(0);
    expect(rows[0].detail).toContain("∞ unlimited");
    expect(rows[0].tone).toBe("info");
  });

  it("shows a credit balance row", () => {
    const blocks: PackageBlock[] = [
      { id: "b1", kind: "credit", bonus: false, amount_paise: 500000, scope: "any" },
    ];
    const rows = entitlementRows(sale(blocks, []));
    expect(rows[0].detail).toBe("₹5,000 balance");
    expect(rows[0].tone).toBe("success");
  });

  it("falls back to a session row for v1 sales (no blocks_snapshot)", () => {
    const rows = entitlementRows(sale(null, []));
    expect(rows[0].used).toBe(4); // 10 - 6
    expect(rows[0].total).toBe(10);
  });

  it("marks purchase-locked choices used/unused", () => {
    const blocks: PackageBlock[] = [
      { id: "b1", kind: "choice", bonus: false, picks: "1", choose_at: "purchase", rows: [
        { service_id: "gold", service_name: "Gold Facial", unit_price_paise: 180000 },
      ] },
    ];
    const rows = entitlementRows(sale(blocks, [
      item({ service_id: "gold", service_name: "Gold Facial", max_redemptions: 1, remaining: 0 }),
    ]));
    expect(rows[0].detail).toBe("1 of 1 used ✓");
  });
});
