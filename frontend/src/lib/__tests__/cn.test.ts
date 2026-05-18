import { describe, expect, it } from "vitest";
import { cn } from "@/lib/utils";

describe("cn", () => {
  it("merges class names", () => {
    expect(cn("p-2", "p-4")).toBe("p-4");
  });
  it("handles conditional classes", () => {
    // Constant `false` is intentional — verifies cn() drops falsy conditional classes.
    // eslint-disable-next-line no-constant-binary-expression
    expect(cn("base", false && "hidden", "shown")).toBe("base shown");
  });
});
