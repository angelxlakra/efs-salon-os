import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { EmptyState } from "@/components/ui/empty-state";

describe("EmptyState", () => {
  it("renders title in display serif", () => {
    render(<EmptyState title="No bookings yet today" body="Add a walk-in." />);
    const title = screen.getByText("No bookings yet today");
    expect(title.className).toMatch(/font-display|text-display/);
  });

  it("renders body and primary action", () => {
    render(
      <EmptyState
        title="No results"
        body="Try a different search."
        primaryAction={<button>Retry</button>}
      />
    );
    expect(screen.getByText("Try a different search.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Retry" })).toBeInTheDocument();
  });

  it("renders no action row when no actions provided", () => {
    const { container } = render(<EmptyState title="t" body="b" />);
    expect(container.querySelectorAll("button")).toHaveLength(0);
    // Action row is the only element with `mt-2 flex gap-2`
    expect(container.querySelector(".mt-2")).toBeNull();
  });

  it("does NOT render secondaryAction without primaryAction (subordinate semantics)", () => {
    render(
      <EmptyState
        title="t"
        body="b"
        secondaryAction={<button>SecondaryOnly</button>}
      />
    );
    expect(screen.queryByRole("button", { name: "SecondaryOnly" })).toBeNull();
  });

  it("marks the icon wrapper as decorative (aria-hidden)", () => {
    const { container } = render(
      <EmptyState title="t" body="b" icon={<svg data-testid="i" />} />
    );
    const wrapper = container.querySelector("[aria-hidden]");
    expect(wrapper).toBeTruthy();
    expect(wrapper?.querySelector('[data-testid="i"]')).toBeTruthy();
  });

  it("merges className via cn() preserving base classes", () => {
    const { container } = render(
      <EmptyState title="t" body="b" className="custom-extra" />
    );
    expect(container.firstChild).toHaveClass("custom-extra");
    expect(container.firstChild).toHaveClass("text-center");
  });

  it("renders configurable headingLevel (default h3, supports h2/h4)", () => {
    const { container, rerender } = render(<EmptyState title="t" body="b" />);
    expect(container.querySelector("h3")).toBeTruthy();

    rerender(<EmptyState title="t" body="b" headingLevel={2} />);
    expect(container.querySelector("h2")).toBeTruthy();
    expect(container.querySelector("h3")).toBeNull();

    rerender(<EmptyState title="t" body="b" headingLevel={4} />);
    expect(container.querySelector("h4")).toBeTruthy();
  });
});
