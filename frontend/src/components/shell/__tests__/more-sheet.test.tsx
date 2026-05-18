import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MoreSheet } from "@/components/shell/more-sheet";

vi.mock("next/navigation", () => ({
  usePathname: () => "/dashboard",
}));

describe("MoreSheet", () => {
  it("does not render content when closed", () => {
    render(<MoreSheet open={false} onOpenChange={() => {}} />);
    expect(screen.queryByText("Customers")).toBeNull();
  });

  it("renders all overflow sections when open", () => {
    render(<MoreSheet open={true} onOpenChange={() => {}} />);
    // Items NOT in MOBILE_TABS should appear here.
    expect(screen.getByText("Customers")).toBeInTheDocument();
    expect(screen.getByText("Inventory")).toBeInTheDocument();
    expect(screen.getByText("Settings")).toBeInTheDocument();
  });

  it("calls onOpenChange(false) when a link is clicked", async () => {
    const user = userEvent.setup();
    const onOpenChange = vi.fn();
    render(<MoreSheet open={true} onOpenChange={onOpenChange} />);
    await user.click(screen.getByRole("link", { name: /Customers/i }));
    expect(onOpenChange).toHaveBeenCalledWith(false);
  });
});
