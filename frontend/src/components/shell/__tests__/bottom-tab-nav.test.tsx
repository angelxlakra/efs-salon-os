import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { BottomTabNav } from "@/components/shell/bottom-tab-nav";

vi.mock("next/navigation", () => ({
  usePathname: () => "/dashboard",
}));

describe("BottomTabNav", () => {
  it("renders the 3 fixed tabs + a More button", () => {
    render(<BottomTabNav />);
    expect(screen.getByRole("link", { name: /Today/ })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Appointments/ })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /POS/ })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /More/i })).toBeInTheDocument();
  });

  it("hides on desktop (md and up)", () => {
    const { container } = render(<BottomTabNav />);
    expect(container.firstChild).toHaveClass("md:hidden");
  });

  it("opens the More sheet on click", async () => {
    const user = userEvent.setup();
    render(<BottomTabNav />);
    await user.click(screen.getByRole("button", { name: /More/i }));
    expect(screen.getByRole("link", { name: /Customers/i })).toBeInTheDocument();
  });

  it("marks the active tab", () => {
    render(<BottomTabNav />);
    const today = screen.getByRole("link", { name: /Today/ });
    expect(today).toHaveAttribute("data-active", "true");
  });
});
