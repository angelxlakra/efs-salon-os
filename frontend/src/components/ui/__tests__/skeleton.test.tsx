import { describe, expect, it } from "vitest";
import { render } from "@testing-library/react";
import * as React from "react";
import { Skeleton } from "@/components/ui/skeleton";

describe("Skeleton", () => {
  it.each([["text"], ["row"], ["card"], ["kpi"]] as const)("renders %s shape", (shape) => {
    const { container } = render(<Skeleton shape={shape} />);
    expect(container.firstChild).toHaveAttribute("data-shape", shape);
  });

  it("defaults to text shape when no shape prop given", () => {
    const { container } = render(<Skeleton />);
    expect(container.firstChild).toHaveAttribute("data-shape", "text");
  });

  it("applies custom width via inline style", () => {
    const { container } = render(<Skeleton shape="text" width="60%" />);
    expect(container.firstChild).toHaveStyle({ width: "60%" });
  });

  it("forwards arbitrary HTML attrs (regression guard for sidebar caller)", () => {
    const { container } = render(
      <Skeleton shape="text" data-sidebar="menu-skeleton-text" />
    );
    expect(container.firstChild).toHaveAttribute("data-sidebar", "menu-skeleton-text");
  });

  it("forwards inline style attrs alongside width prop", () => {
    const { container } = render(
      <Skeleton
        shape="text"
        style={{ "--skeleton-width": "70%" } as React.CSSProperties}
      />
    );
    const el = container.firstChild as HTMLElement;
    expect(el.style.getPropertyValue("--skeleton-width")).toBe("70%");
  });

  it("renders as decorative (aria-hidden)", () => {
    const { container } = render(<Skeleton shape="row" />);
    expect(container.firstChild).toHaveAttribute("aria-hidden");
  });

  it("applies w-3/4 default for text shape", () => {
    const { container } = render(<Skeleton shape="text" />);
    expect(container.firstChild).toHaveClass("w-3/4");
  });

  it("applies w-full default for card shape", () => {
    const { container } = render(<Skeleton shape="card" />);
    expect(container.firstChild).toHaveClass("w-full");
  });

  it("omits default-width class when width prop is provided (including width=0)", () => {
    const { container, rerender } = render(<Skeleton shape="text" width="50%" />);
    expect(container.firstChild).not.toHaveClass("w-3/4");

    rerender(<Skeleton shape="text" width={0} />);
    expect(container.firstChild).not.toHaveClass("w-3/4");
    expect(container.firstChild).toHaveStyle({ width: "0" });
  });
});
