import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { SidebarV2 } from "@/components/shell/sidebar-v2";

vi.mock("next/navigation", () => ({
  usePathname: () => "/dashboard/bills",
}));

describe("SidebarV2", () => {
  it("renders all 4 section labels", () => {
    render(<SidebarV2 />);
    expect(screen.getByText("Today's work")).toBeInTheDocument();
    expect(screen.getByText("Ledger")).toBeInTheDocument();
    expect(screen.getByText("Insight")).toBeInTheDocument();
    expect(screen.getByText("Admin")).toBeInTheDocument();
  });

  it("renders the active route with data-active=true", () => {
    render(<SidebarV2 />);
    // /dashboard/bills is the active route
    const billsLink = screen.getByRole("link", { name: /Bills/i });
    expect(billsLink).toHaveAttribute("data-active", "true");
  });

  it("renders Today (root /dashboard) without data-active when on a sub-route", () => {
    render(<SidebarV2 />);
    const todayLink = screen.getByRole("link", { name: /Today/i });
    expect(todayLink).not.toHaveAttribute("data-active");
  });

  it("uses the surface-sidebar token on the wrapper", () => {
    const { container } = render(<SidebarV2 />);
    expect(container.firstChild).toHaveClass("bg-surface-sidebar");
  });
});
