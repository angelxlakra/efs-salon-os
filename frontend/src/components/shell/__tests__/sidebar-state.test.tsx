import { describe, expect, it, beforeEach, afterEach } from "vitest";
import { render, screen, act } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import {
  SidebarStateProvider,
  useSidebarState,
} from "@/components/shell/sidebar-state";

function Probe() {
  const { collapsed, toggle, setCollapsed } = useSidebarState();
  return (
    <div>
      <span data-testid="state">{collapsed ? "collapsed" : "expanded"}</span>
      <button onClick={toggle}>toggle</button>
      <button onClick={() => setCollapsed(true)}>collapse</button>
    </div>
  );
}

describe("SidebarStateProvider", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  afterEach(() => {
    window.localStorage.clear();
  });

  it("defaults to expanded when no localStorage value", () => {
    render(
      <SidebarStateProvider>
        <Probe />
      </SidebarStateProvider>,
    );
    expect(screen.getByTestId("state")).toHaveTextContent("expanded");
  });

  it("hydrates from localStorage on mount", () => {
    window.localStorage.setItem("salon.sidebar.collapsed", "true");
    render(
      <SidebarStateProvider>
        <Probe />
      </SidebarStateProvider>,
    );
    expect(screen.getByTestId("state")).toHaveTextContent("collapsed");
  });

  it("toggle flips state and persists to localStorage", async () => {
    const user = userEvent.setup();
    render(
      <SidebarStateProvider>
        <Probe />
      </SidebarStateProvider>,
    );
    await user.click(screen.getByText("toggle"));
    expect(screen.getByTestId("state")).toHaveTextContent("collapsed");
    expect(window.localStorage.getItem("salon.sidebar.collapsed")).toBe("true");
  });

  it("Cmd+\\ (Meta+Backslash) toggles collapse via keyboard", () => {
    render(
      <SidebarStateProvider>
        <Probe />
      </SidebarStateProvider>,
    );
    expect(screen.getByTestId("state")).toHaveTextContent("expanded");
    act(() => {
      window.dispatchEvent(new KeyboardEvent("keydown", { key: "\\", metaKey: true }));
    });
    expect(screen.getByTestId("state")).toHaveTextContent("collapsed");
  });
});
