import { describe, expect, it } from "vitest";
import { render } from "@testing-library/react";
import { SessionsLeft } from "@/components/ui/SessionsLeft";

describe("SessionsLeft", () => {
  it("renders counted as N/M", () => {
    const { container } = render(<SessionsLeft remaining={7} total={10} />);
    expect(container.textContent).toBe("7/10");
  });

  it("renders unlimited as ∞", () => {
    const { container } = render(
      <SessionsLeft remaining={null} total={null} />
    );
    expect(container.textContent).toBe("∞");
  });

  it("renders 0 sessions remaining (exhausted)", () => {
    const { container } = render(<SessionsLeft remaining={0} total={5} />);
    expect(container.textContent).toBe("0/5");
  });

  it("applies size sm class", () => {
    const { container } = render(
      <SessionsLeft remaining={3} total={5} size="sm" />
    );
    expect(container.querySelector("span")?.className).toMatch(/text-sm/);
  });
});
