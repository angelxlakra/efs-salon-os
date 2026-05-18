import { describe, expect, it, beforeEach, vi } from "vitest";
import { render, screen, act } from "@testing-library/react";
import { CommandPalette } from "@/components/command-palette/command-palette";
import { PaletteProvider } from "@/components/command-palette/use-palette";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
}));

beforeEach(() => {
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

describe("CommandPalette", () => {
  it("is closed by default (no input visible)", () => {
    render(
      <PaletteProvider>
        <CommandPalette />
      </PaletteProvider>,
    );
    expect(screen.queryByPlaceholderText(/Type a command/i)).toBeNull();
  });

  it("opens on Cmd+K keyboard shortcut", () => {
    render(
      <PaletteProvider>
        <CommandPalette />
      </PaletteProvider>,
    );
    act(() => {
      window.dispatchEvent(new KeyboardEvent("keydown", { key: "k", metaKey: true }));
    });
    expect(screen.getByPlaceholderText(/Type a command/i)).toBeInTheDocument();
  });

  it("opens on Ctrl+K (Win/Linux)", () => {
    render(
      <PaletteProvider>
        <CommandPalette />
      </PaletteProvider>,
    );
    act(() => {
      window.dispatchEvent(new KeyboardEvent("keydown", { key: "k", ctrlKey: true }));
    });
    expect(screen.getByPlaceholderText(/Type a command/i)).toBeInTheDocument();
  });

  it("closes on Escape", () => {
    render(
      <PaletteProvider>
        <CommandPalette />
      </PaletteProvider>,
    );
    act(() => {
      window.dispatchEvent(new KeyboardEvent("keydown", { key: "k", metaKey: true }));
    });
    expect(screen.getByPlaceholderText(/Type a command/i)).toBeInTheDocument();
    act(() => {
      window.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape" }));
    });
    expect(screen.queryByPlaceholderText(/Type a command/i)).toBeNull();
  });
});
