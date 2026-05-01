import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { TopBar } from "@/components/shell/topbar";
import { PaletteProvider } from "@/components/command-palette/use-palette";

vi.mock("next/navigation", () => ({
  usePathname: () => "/dashboard/bills",
}));

describe("TopBar", () => {
  it("renders breadcrumb (Today / Bills) for /dashboard/bills", () => {
    render(
      <PaletteProvider>
        <TopBar />
      </PaletteProvider>,
    );
    expect(screen.getByText("Today")).toBeInTheDocument();
    expect(screen.getByText("Bills")).toBeInTheDocument();
  });

  it("renders the Cmd+K palette trigger button", () => {
    render(
      <PaletteProvider>
        <TopBar />
      </PaletteProvider>,
    );
    const trigger = screen.getByRole("button", { name: /search|palette/i });
    expect(trigger).toBeInTheDocument();
  });

  it("renders a user menu placeholder", () => {
    render(
      <PaletteProvider>
        <TopBar />
      </PaletteProvider>,
    );
    expect(screen.getByLabelText(/user menu/i)).toBeInTheDocument();
  });

  it("uses sticky positioning + surface-card background", () => {
    const { container } = render(
      <PaletteProvider>
        <TopBar />
      </PaletteProvider>,
    );
    expect(container.firstChild).toHaveClass("sticky");
    expect(container.firstChild).toHaveClass("bg-surface-card");
  });
});
