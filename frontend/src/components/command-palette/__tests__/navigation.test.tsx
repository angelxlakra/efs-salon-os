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

describe("CommandPalette navigation provider", () => {
  it("lists navigation entries from section-config", async () => {
    render(
      <PaletteProvider>
        <CommandPalette />
      </PaletteProvider>,
    );
    openPalette();
    expect(await screen.findByText("Today")).toBeInTheDocument();
    expect(screen.getByText("Bills")).toBeInTheDocument();
    expect(screen.getByText("Customers")).toBeInTheDocument();
  });

  it("navigates on Enter and closes the palette", async () => {
    const user = userEvent.setup();
    render(
      <PaletteProvider>
        <CommandPalette />
      </PaletteProvider>,
    );
    openPalette();
    await user.type(screen.getByPlaceholderText(/Type a command/i), "bills");
    await user.keyboard("{Enter}");
    expect(push).toHaveBeenCalledWith("/dashboard/bills");
    expect(screen.queryByPlaceholderText(/Type a command/i)).toBeNull();
  });
});
