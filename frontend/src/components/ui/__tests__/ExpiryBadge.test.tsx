import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { render } from "@testing-library/react";
import { ExpiryBadge } from "@/components/ui/ExpiryBadge";

// Pin time to 2026-01-01T00:00:00Z
const FIXED_NOW = new Date("2026-01-01T00:00:00Z").getTime();

function addDays(base: number, days: number): string {
  return new Date(base + days * 24 * 60 * 60 * 1000).toISOString();
}

describe("ExpiryBadge", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(FIXED_NOW);
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("shows green badge when > 30 days left", () => {
    const { container } = render(
      <ExpiryBadge expiresAt={addDays(FIXED_NOW, 60)} />
    );
    expect(container.textContent).toBe("60d left");
    expect(container.querySelector("span")?.className).toMatch(
      /bg-success-bg-soft/
    );
  });

  it("shows amber badge when 8–30 days left", () => {
    const { container } = render(
      <ExpiryBadge expiresAt={addDays(FIXED_NOW, 15)} />
    );
    expect(container.textContent).toBe("15d left");
    expect(container.querySelector("span")?.className).toMatch(
      /bg-warning-bg-soft/
    );
  });

  it("shows red badge when 0–7 days left", () => {
    const { container } = render(
      <ExpiryBadge expiresAt={addDays(FIXED_NOW, 3)} />
    );
    expect(container.textContent).toBe("3d left");
    expect(container.querySelector("span")?.className).toMatch(
      /bg-danger-bg-soft/
    );
  });

  it("shows expired badge for past dates", () => {
    const { container } = render(
      <ExpiryBadge expiresAt={addDays(FIXED_NOW, -5)} />
    );
    expect(container.textContent).toBe("Expired 5d ago");
    expect(container.querySelector("span")?.className).toMatch(/bg-muted/);
  });

  it("shows 0d left on expiry day (boundary)", () => {
    // Same day (daysLeft = 0, rounds down) — falls into ≤7 bucket
    const { container } = render(
      <ExpiryBadge expiresAt={addDays(FIXED_NOW, 0)} />
    );
    expect(container.textContent).toBe("0d left");
    expect(container.querySelector("span")?.className).toMatch(
      /bg-danger-bg-soft/
    );
  });
});
