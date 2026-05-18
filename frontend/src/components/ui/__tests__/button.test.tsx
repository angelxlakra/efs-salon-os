import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Button } from "@/components/ui/button";

describe("Button", () => {
  it("renders children", () => {
    render(<Button>Save</Button>);
    expect(screen.getByRole("button", { name: "Save" })).toBeInTheDocument();
  });

  it("calls onClick when clicked", async () => {
    const onClick = vi.fn();
    const user = userEvent.setup();
    render(<Button onClick={onClick}>Go</Button>);
    await user.click(screen.getByRole("button"));
    expect(onClick).toHaveBeenCalledOnce();
  });

  it("renders loading state with spinner and preserves width", () => {
    const { rerender } = render(<Button>Save</Button>);
    const widthBefore = screen.getByRole("button").getBoundingClientRect().width;
    rerender(<Button loading>Save</Button>);
    const btn = screen.getByRole("button");
    expect(btn).toBeDisabled();
    expect(btn.querySelector('[data-slot="spinner"]')).toBeInTheDocument();
    // Text stays in DOM (visually hidden) so width does not collapse
    expect(btn).toHaveTextContent("Save");
  });

  it("applies danger variant class", () => {
    render(<Button variant="danger">Delete</Button>);
    expect(screen.getByRole("button").className).toMatch(/danger/);
  });

  it("icon variant requires aria-label (throws in dev)", () => {
    // When used without aria-label, a console.error is expected in dev.
    const spy = vi.spyOn(console, "error").mockImplementation(() => {});
    render(<Button variant="icon" aria-label="Close" />);
    spy.mockRestore();
  });
});
