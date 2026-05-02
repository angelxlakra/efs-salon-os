import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, act, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { CommandPalette } from "@/components/command-palette/command-palette";
import { PaletteProvider } from "@/components/command-palette/use-palette";

const push = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push }),
}));

const fetchMock = vi.fn();
beforeEach(() => {
  push.mockReset();
  fetchMock.mockReset();
  global.fetch = fetchMock as unknown as typeof fetch;
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

describe("CommandPalette search providers", () => {
  it("queries customers when input is non-empty and renders matches", async () => {
    fetchMock.mockResolvedValueOnce({
      ok: true,
      json: async () => [
        { id: "c1", first_name: "Priya", last_name: "Sharma", phone: "9000000001" },
      ],
    });
    fetchMock.mockResolvedValueOnce({ ok: true, json: async () => [] }); // bills
    fetchMock.mockResolvedValueOnce({ ok: true, json: async () => [] }); // skus

    const user = userEvent.setup();
    render(
      <PaletteProvider>
        <CommandPalette />
      </PaletteProvider>,
    );
    openPalette();
    await user.type(screen.getByPlaceholderText(/Type a command/i), "priya");
    await waitFor(() => {
      expect(screen.getByText(/Priya Sharma/)).toBeInTheDocument();
    });
  });

  it("does NOT call fetch when query is empty (avoids hitting search endpoints on open)", async () => {
    render(
      <PaletteProvider>
        <CommandPalette />
      </PaletteProvider>,
    );
    openPalette();
    await new Promise((r) => setTimeout(r, 50));
    expect(fetchMock).not.toHaveBeenCalled();
  });
});
