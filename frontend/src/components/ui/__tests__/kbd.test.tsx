import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { Kbd } from "@/components/ui/kbd";

describe("Kbd", () => {
  it("renders each key as its own <kbd> element in order", () => {
    const { container } = render(<Kbd keys={["⌘", "K"]} />);
    const kbdElements = container.querySelectorAll("kbd");
    expect(kbdElements).toHaveLength(2);
    expect(kbdElements[0]).toHaveTextContent("⌘");
    expect(kbdElements[1]).toHaveTextContent("K");
  });

  it("renders the keys' text content", () => {
    render(<Kbd keys={["⌘", "K"]} />);
    expect(screen.getByText("⌘")).toBeInTheDocument();
    expect(screen.getByText("K")).toBeInTheDocument();
  });
});
