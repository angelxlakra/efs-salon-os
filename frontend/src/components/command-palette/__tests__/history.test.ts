import { describe, expect, it, beforeEach } from "vitest";
import { recordCommand, readHistory, clearHistory } from "@/components/command-palette/history";

describe("palette history", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it("readHistory returns empty array when nothing stored", () => {
    expect(readHistory()).toEqual([]);
  });

  it("recordCommand appends and persists", () => {
    recordCommand({ id: "go-bills", label: "Bills", href: "/dashboard/bills" });
    expect(readHistory()).toHaveLength(1);
    expect(readHistory()[0].id).toBe("go-bills");
  });

  it("recordCommand deduplicates — same id moves to front, not duplicated", () => {
    recordCommand({ id: "go-bills", label: "Bills", href: "/dashboard/bills" });
    recordCommand({ id: "go-customers", label: "Customers", href: "/dashboard/customers" });
    recordCommand({ id: "go-bills", label: "Bills", href: "/dashboard/bills" });
    const h = readHistory();
    expect(h).toHaveLength(2);
    expect(h[0].id).toBe("go-bills");
    expect(h[1].id).toBe("go-customers");
  });

  it("recordCommand caps history at 10 entries", () => {
    for (let i = 0; i < 15; i++) {
      recordCommand({ id: `cmd-${i}`, label: `Cmd ${i}`, href: `/x/${i}` });
    }
    expect(readHistory()).toHaveLength(10);
    // Most recent first.
    expect(readHistory()[0].id).toBe("cmd-14");
  });

  it("clearHistory empties storage", () => {
    recordCommand({ id: "x", label: "X", href: "/x" });
    clearHistory();
    expect(readHistory()).toEqual([]);
  });
});
