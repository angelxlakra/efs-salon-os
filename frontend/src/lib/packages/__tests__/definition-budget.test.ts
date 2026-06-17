import { describe, expect, it } from "vitest";
import { definitionServiceBudgets } from "@/lib/packages/definition-budget";
import type { PackageBlock } from "@/types/package";

const items = (rows: Array<[string, number]>): PackageBlock => ({
  id: "i", kind: "items", bonus: false,
  rows: rows.map(([service_id, qty]) => ({
    service_id, service_name: service_id, quantity: String(qty), unit_price_paise: 3000,
  })),
});

describe("definitionServiceBudgets", () => {
  it("gives each fixed-items service its own cap + a shared global pool", () => {
    const b = definitionServiceBudgets("def1", [items([["eyebrow", 1], ["upperlip", 1]])]);
    expect(b.get("eyebrow")).toEqual({
      lineRemaining: 1, sharedKey: "def1:pool", sharedRemaining: 2,
    });
    expect(b.get("upperlip")!.lineRemaining).toBe(1);
  });

  it("gives a choice@visit block its own shared counter (no per-line cap)", () => {
    const block: PackageBlock = {
      id: "c", kind: "choice", bonus: false, picks: "2", choose_at: "visit",
      rows: [
        { service_id: "a", service_name: "A", unit_price_paise: 1 },
        { service_id: "b", service_name: "B", unit_price_paise: 1 },
      ],
    };
    const b = definitionServiceBudgets("def1", [block]);
    expect(b.get("a")).toEqual({
      lineRemaining: 9999, sharedKey: "def1:block:c", sharedRemaining: 2,
    });
  });
});
