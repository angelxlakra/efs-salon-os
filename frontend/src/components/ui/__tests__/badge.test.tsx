import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { Badge } from "@/components/ui/badge";

describe("Badge", () => {
  it.each([
    ["neutral"], ["success"], ["warning"], ["danger"], ["info"], ["accent"],
  ] as const)("renders %s tone", (tone) => {
    render(<Badge tone={tone}>x</Badge>);
    expect(screen.getByText("x")).toHaveAttribute("data-tone", tone);
  });

  it("defaults to neutral", () => {
    render(<Badge>default</Badge>);
    expect(screen.getByText("default")).toHaveAttribute("data-tone", "neutral");
  });

  it("danger tone emits the danger class string (cva mapping is wired)", () => {
    render(<Badge tone="danger">x</Badge>);
    const el = screen.getByText("x");
    expect(el.className).toMatch(/bg-danger-bg-soft/);
    expect(el.className).toMatch(/text-danger-fg/);
    expect(el.className).toMatch(/border-danger-border/);
  });

  it("defaults to size=sm", () => {
    render(<Badge>x</Badge>);
    expect(screen.getByText("x").className).toMatch(/text-\[11px\]/);
  });

  it("renders size=md", () => {
    render(<Badge size="md">x</Badge>);
    expect(screen.getByText("x").className).toMatch(/text-\[12px\]/);
  });

  // ---------------------------------------------------------------------
  // Legacy variant shim — the entire describe block below deletes during
  // Phase 1 retrofit once all 24 V1 caller files are migrated to `tone`.
  // ---------------------------------------------------------------------
  describe("legacy variant shim (remove in Phase 1)", () => {
    it.each([
      ["default", "neutral"],
      ["secondary", "neutral"],
      ["destructive", "danger"],
      ["outline", "neutral"],
    ] as const)("variant=%s maps to tone=%s", (variant, tone) => {
      render(<Badge variant={variant}>x</Badge>);
      expect(screen.getByText("x")).toHaveAttribute("data-tone", tone);
    });

    it("legacy variant is not spread to the DOM", () => {
      const { container } = render(<Badge variant="secondary">s</Badge>);
      const span = container.querySelector("span");
      expect(span).not.toHaveAttribute("variant");
    });

    it("explicit tone takes precedence over legacy variant", () => {
      render(<Badge tone="success" variant="destructive">mixed</Badge>);
      expect(screen.getByText("mixed")).toHaveAttribute("data-tone", "success");
    });
  });
});
