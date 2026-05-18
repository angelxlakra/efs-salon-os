import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { SidebarRail } from "@/components/shell/sidebar-rail";

vi.mock("next/navigation", () => ({
  usePathname: () => "/dashboard/customers",
}));

describe("SidebarRail", () => {
  it("renders icon-only items", () => {
    render(<SidebarRail />);
    expect(screen.getAllByRole("link").length).toBeGreaterThan(0);
  });

  it("uses the surface-sidebar token", () => {
    const { container } = render(<SidebarRail />);
    expect(container.firstChild).toHaveClass("bg-surface-sidebar");
  });

  it("marks the active route", () => {
    render(<SidebarRail />);
    const customersLink = screen.getByRole("link", { name: /Customers/i });
    expect(customersLink).toHaveAttribute("data-active", "true");
  });

  it("is exactly 56px wide (w-14)", () => {
    const { container } = render(<SidebarRail />);
    expect(container.firstChild).toHaveClass("w-14");
  });
});
