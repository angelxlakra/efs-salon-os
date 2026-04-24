import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { Card } from "@/components/ui/card";

describe("Card", () => {
  it("renders compound parts", () => {
    render(
      <Card density="md">
        <Card.Header title="Revenue" description="Today" />
        <Card.Body>₹24,800</Card.Body>
        <Card.Footer>+12% vs avg</Card.Footer>
      </Card>
    );
    expect(screen.getByText("Revenue")).toBeInTheDocument();
    expect(screen.getByText("Today")).toBeInTheDocument();
    expect(screen.getByText("₹24,800")).toBeInTheDocument();
    expect(screen.getByText("+12% vs avg")).toBeInTheDocument();
  });

  it("applies density data attribute", () => {
    const { container } = render(<Card density="lg">body</Card>);
    expect(container.firstChild).toHaveAttribute("data-density", "lg");
  });

  it("Card.Header action-only renders action without empty left stack", () => {
    const { container } = render(
      <Card>
        <Card.Header action={<button>Add</button>} />
      </Card>
    );
    expect(screen.getByRole("button", { name: "Add" })).toBeInTheDocument();
    // Header root should have exactly one child (the action wrapper), not two
    const header = container.querySelector('[data-slot="header"]');
    expect(header?.children.length).toBe(1);
  });

  it("V1 legacy shims remain exported (regression guard for Phase 1 retrofit)", async () => {
    const mod = await import("@/components/ui/card");
    expect(typeof mod.CardHeader).toBe("function");
    expect(typeof mod.CardTitle).toBe("function");
    expect(typeof mod.CardDescription).toBe("function");
    expect(typeof mod.CardAction).toBe("function");
    expect(typeof mod.CardFooter).toBe("function");
    expect(typeof mod.CardContent).toBe("function");
  });
});
