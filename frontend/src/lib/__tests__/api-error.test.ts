import { describe, expect, it } from "vitest";
import { getApiErrorMessage } from "@/lib/api-error";

describe("getApiErrorMessage", () => {
  it("flattens a FastAPI 422 detail array into a string (never an object)", () => {
    // The exact shape that caused React error #31 when passed to toast.error.
    const err = {
      response: {
        data: {
          detail: [
            { type: "missing", loc: ["body", "items", 0, "service_id"], msg: "Field required", input: {}, url: "x" },
          ],
        },
      },
    };
    const msg = getApiErrorMessage(err);
    expect(typeof msg).toBe("string");
    expect(msg).toBe("service_id: Field required");
  });

  it("returns a string detail as-is", () => {
    expect(getApiErrorMessage({ response: { data: { detail: "Bill not found" } } })).toBe(
      "Bill not found"
    );
  });

  it("falls back to error.message, then the fallback", () => {
    expect(getApiErrorMessage(new Error("boom"))).toBe("boom");
    expect(getApiErrorMessage({}, "Failed")).toBe("Failed");
  });
});
