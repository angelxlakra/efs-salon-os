import { describe, expect, it } from "vitest";
import {
  blockValue,
  blockSummary,
  chargeableOf,
  bonusOf,
  priceOf,
  savingsFraction,
} from "@/lib/packages/block-pricing";
import type { PackageBlock } from "@/types/package";

const items = (rows: Array<[number, number]>, bonus = false): PackageBlock => ({
  id: "i",
  kind: "items",
  bonus,
  rows: rows.map(([qty, paise]) => ({
    service_id: "s",
    service_name: "Svc",
    quantity: String(qty),
    unit_price_paise: paise,
  })),
});

describe("blockValue", () => {
  it("items = Σ qty × price", () => {
    expect(blockValue(items([[2, 250000], [1, 80000]]))).toBe(580000);
  });

  it("choice = picks × average(option prices), rounded", () => {
    const b: PackageBlock = {
      id: "c",
      kind: "choice",
      bonus: false,
      picks: "2",
      choose_at: "visit",
      rows: [
        { service_id: "a", service_name: "A", unit_price_paise: 180000 },
        { service_id: "b", service_name: "B", unit_price_paise: 250000 },
        { service_id: "c", service_name: "C", unit_price_paise: 120000 },
      ],
    };
    // avg = 183333.33 → ×2 = 366667 (rounded)
    expect(blockValue(b)).toBe(366667);
  });

  it("unlimited = assigned value", () => {
    const b: PackageBlock = {
      id: "u",
      kind: "unlimited",
      bonus: false,
      assigned_value_paise: 150000,
      daily_cap: "1",
      rows: [{ service_id: "t", service_name: "Thread" }],
    };
    expect(blockValue(b)).toBe(150000);
  });

  it("pool = sessions × average(prices)", () => {
    const b: PackageBlock = {
      id: "p",
      kind: "pool",
      bonus: false,
      sessions: "10",
      rows: [
        { service_id: "a", service_name: "A", unit_price_paise: 50000 },
        { service_id: "b", service_name: "B", unit_price_paise: 30000 },
      ],
    };
    expect(blockValue(b)).toBe(400000); // 10 × 40000
  });

  it("credit = amount", () => {
    const b: PackageBlock = {
      id: "cr",
      kind: "credit",
      bonus: false,
      amount_paise: 500000,
      scope: "any",
    };
    expect(blockValue(b)).toBe(500000);
  });
});

describe("chargeable / bonus / price / savings", () => {
  const chargeableBlock = items([[2, 250000]]); // 500000
  const bonusBlock = items([[1, 95000]], true); // 95000 bonus
  const blocks = [chargeableBlock, bonusBlock];

  it("bonus blocks are excluded from chargeable but counted in bonus", () => {
    expect(chargeableOf(blocks)).toBe(500000);
    expect(bonusOf(blocks)).toBe(95000);
  });

  it("final discount sets the sell price directly (rupees → paise)", () => {
    // chargeable 500000 paise (₹5000), final ₹3499
    expect(priceOf(blocks, { mode: "final", value: "3499" })).toBe(349900);
  });

  it("pct discount applies to chargeable only", () => {
    expect(priceOf(blocks, { mode: "pct", value: "10" })).toBe(450000);
  });

  it("savings compares price against total value incl. bonus", () => {
    // price 450000, total value 595000 → saves ~24%
    const pct = Math.round(savingsFraction(blocks, { mode: "pct", value: "10" }) * 100);
    expect(pct).toBe(24);
  });
});

describe("blockSummary", () => {
  it("summarizes a choice block with mode", () => {
    const b: PackageBlock = {
      id: "c",
      kind: "choice",
      bonus: false,
      picks: "3",
      choose_at: "visit",
      rows: [
        { service_id: "a", service_name: "A", unit_price_paise: 1 },
        { service_id: "b", service_name: "B", unit_price_paise: 1 },
        { service_id: "c", service_name: "C", unit_price_paise: 1 },
      ],
    };
    expect(blockSummary(b)).toBe("3 uses from 3 options");
  });

  it("flags an empty items block", () => {
    expect(blockSummary(items([]))).toBe("Empty — add services");
  });
});
