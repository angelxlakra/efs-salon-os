import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { Input } from "@/components/ui/input";

describe("Input", () => {
  it("renders with a label", () => {
    render(<Input label="Email" id="email" />);
    expect(screen.getByLabelText("Email")).toBeInTheDocument();
  });

  it("shows error text and sets aria-invalid", () => {
    render(<Input label="Email" error="Invalid email" />);
    expect(screen.getByText("Invalid email")).toBeInTheDocument();
    expect(screen.getByLabelText("Email")).toHaveAttribute("aria-invalid", "true");
  });

  it("shows hint text when no error", () => {
    render(<Input label="Email" hint="We'll never share" />);
    expect(screen.getByText("We'll never share")).toBeInTheDocument();
  });

  it("renders leadingAddon and trailingAddon", () => {
    render(<Input label="Price" leadingAddon={<span>₹</span>} trailingAddon={<span>.00</span>} />);
    expect(screen.getByText("₹")).toBeInTheDocument();
    expect(screen.getByText(".00")).toBeInTheDocument();
  });
});
