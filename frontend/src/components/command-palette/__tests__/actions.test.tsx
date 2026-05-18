import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, act } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { CommandPalette } from "@/components/command-palette/command-palette";
import { PaletteProvider } from "@/components/command-palette/use-palette";

const push = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push }),
}));

beforeEach(() => {
  push.mockReset();
  document.documentElement.setAttribute("data-theme", "light");
  if (typeof Element !== "undefined") {
    Element.prototype.scrollIntoView = vi.fn();
  }
  if (typeof window !== "undefined" && !window.ResizeObserver) {
    (window as unknown as { ResizeObserver: typeof ResizeObserver }).ResizeObserver = class {
      observe() {}
      unobserve() {}
      disconnect() {}
    } as unknown as typeof ResizeObserver;
  }
});

function openPalette() {
  act(() => {
    window.dispatchEvent(new KeyboardEvent("keydown", { key: "k", metaKey: true }));
  });
}

describe("CommandPalette actions provider", () => {
  it("lists action commands when palette opens", () => {
    render(
      <PaletteProvider>
        <CommandPalette />
      </PaletteProvider>,
    );
    openPalette();
    expect(screen.getByText(/New bill/i)).toBeInTheDocument();
    expect(screen.getByText(/Open cash drawer/i)).toBeInTheDocument();
    expect(screen.getByText(/Toggle theme/i)).toBeInTheDocument();
  });

  it("New bill navigates to /dashboard/pos", async () => {
    const user = userEvent.setup();
    render(
      <PaletteProvider>
        <CommandPalette />
      </PaletteProvider>,
    );
    openPalette();
    await user.click(screen.getByText(/New bill/i));
    expect(push).toHaveBeenCalledWith("/dashboard/pos");
  });

  it("Toggle theme flips data-theme on html element", async () => {
    const user = userEvent.setup();
    render(
      <PaletteProvider>
        <CommandPalette />
      </PaletteProvider>,
    );
    openPalette();
    expect(document.documentElement.getAttribute("data-theme")).toBe("light");
    await user.click(screen.getByText(/Toggle theme/i));
    expect(document.documentElement.getAttribute("data-theme")).toBe("dark");
  });
});
