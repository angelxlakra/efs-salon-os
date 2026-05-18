import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { Breadcrumb } from "@/components/shell/breadcrumb";

const mockPath = vi.hoisted(() => ({ value: "/dashboard" }));
vi.mock("next/navigation", () => ({
  usePathname: () => mockPath.value,
}));

describe("Breadcrumb", () => {
  it("renders 'Today' alone for /dashboard", () => {
    mockPath.value = "/dashboard";
    render(<Breadcrumb />);
    expect(screen.getByText("Today")).toBeInTheDocument();
    // No separator chevron because it's the only segment.
    expect(screen.queryByText("/")).toBeNull();
  });

  it("renders 'Today / Bills' for /dashboard/bills", () => {
    mockPath.value = "/dashboard/bills";
    render(<Breadcrumb />);
    expect(screen.getByText("Today")).toBeInTheDocument();
    expect(screen.getByText("Bills")).toBeInTheDocument();
  });

  it("renders the leaf as plain text (not a link), parents as links", () => {
    mockPath.value = "/dashboard/bills";
    render(<Breadcrumb />);
    expect(screen.getByRole("link", { name: "Today" })).toBeInTheDocument();
    // "Bills" is the leaf — no link role
    expect(screen.queryByRole("link", { name: "Bills" })).toBeNull();
  });

  it("falls back to verbatim segment when no section-config match", () => {
    mockPath.value = "/dashboard/bills/SAL-25-0171";
    render(<Breadcrumb />);
    // "SAL-25-0171" is unknown to section-config; shown verbatim.
    expect(screen.getByText("SAL-25-0171")).toBeInTheDocument();
  });
});
