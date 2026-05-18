import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { NavItem } from "@/components/ui/nav-item";

describe("NavItem", () => {
  it("renders label and icon", () => {
    render(<NavItem label="Today" href="/dashboard" icon={<span data-testid="ico">I</span>} />);
    expect(screen.getByText("Today")).toBeInTheDocument();
    expect(screen.getByTestId("ico")).toBeInTheDocument();
  });

  it("marks active when active=true", () => {
    render(<NavItem label="Today" href="/dashboard" active />);
    expect(screen.getByRole("link")).toHaveAttribute("data-active", "true");
    expect(screen.getByRole("link")).toHaveAttribute("aria-current", "page");
  });

  it("omits aria-current and data-active when active is falsy", () => {
    render(<NavItem label="Today" href="/dashboard" />);
    const link = screen.getByRole("link");
    expect(link).not.toHaveAttribute("aria-current");
    expect(link).not.toHaveAttribute("data-active");
  });

  it("renders badge when provided", () => {
    render(<NavItem label="Bills" href="/bills" badge={<span>3</span>} />);
    expect(screen.getByText("3")).toBeInTheDocument();
  });
});
