"use client";

import * as React from "react";

const STORAGE_KEY = "salon.sidebar.collapsed";

type SidebarStateValue = {
  collapsed: boolean;
  toggle: () => void;
  setCollapsed: (next: boolean) => void;
};

const SidebarStateContext = React.createContext<SidebarStateValue | null>(null);

export function SidebarStateProvider({ children }: { children: React.ReactNode }) {
  // SSR-safe: start expanded, hydrate from localStorage in effect.
  const [collapsed, setCollapsedState] = React.useState(false);

  React.useEffect(() => {
    if (typeof window === "undefined") return;
    const stored = window.localStorage.getItem(STORAGE_KEY);
    if (stored === "true") setCollapsedState(true);
  }, []);

  const setCollapsed = React.useCallback((next: boolean) => {
    setCollapsedState(next);
    if (typeof window !== "undefined") {
      window.localStorage.setItem(STORAGE_KEY, String(next));
    }
  }, []);

  const toggle = React.useCallback(() => {
    setCollapsedState((prev) => {
      const next = !prev;
      if (typeof window !== "undefined") {
        window.localStorage.setItem(STORAGE_KEY, String(next));
      }
      return next;
    });
  }, []);

  // Keyboard binding: ⌘\ on Mac, Ctrl+\ on Win/Linux.
  React.useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "\\") {
        e.preventDefault();
        toggle();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [toggle]);

  const value = React.useMemo<SidebarStateValue>(
    () => ({ collapsed, toggle, setCollapsed }),
    [collapsed, toggle, setCollapsed],
  );

  return <SidebarStateContext.Provider value={value}>{children}</SidebarStateContext.Provider>;
}

export function useSidebarState(): SidebarStateValue {
  const ctx = React.useContext(SidebarStateContext);
  if (!ctx) throw new Error("useSidebarState must be used inside <SidebarStateProvider>");
  return ctx;
}
