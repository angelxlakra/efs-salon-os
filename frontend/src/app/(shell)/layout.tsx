"use client";

import * as React from "react";
import { SidebarV2 } from "@/components/shell/sidebar-v2";
import { SidebarRail } from "@/components/shell/sidebar-rail";
import { TopBar } from "@/components/shell/topbar";
import { BottomTabNav } from "@/components/shell/bottom-tab-nav";
import { SidebarStateProvider, useSidebarState } from "@/components/shell/sidebar-state";
import { PaletteProvider } from "@/components/command-palette/use-palette";
import { CommandPalette } from "@/components/command-palette/command-palette";

function ShellChrome({ children, modal }: { children: React.ReactNode; modal: React.ReactNode }) {
  const { collapsed } = useSidebarState();
  return (
    <div className="min-h-dvh bg-surface-page text-text-primary flex">
      {/* Desktop sidebar — collapses to rail. */}
      <div className="hidden md:block">
        {collapsed ? <SidebarRail /> : <SidebarV2 />}
      </div>
      <div className="flex-1 flex flex-col min-w-0">
        <TopBar />
        {/* pb-16 reserves space for BottomTabNav on mobile (T18 adds safe-area inset). */}
        <main className="flex-1 pb-[calc(theme(spacing.16)+env(safe-area-inset-bottom))] md:pb-0">
          {children}
        </main>
      </div>
      {/* Mobile bottom nav. */}
      <BottomTabNav />
      {/* Parallel modal slot. */}
      {modal}
      {/* Global command palette. */}
      <CommandPalette />
    </div>
  );
}

export default function ShellLayout({
  children,
  modal,
}: {
  children: React.ReactNode;
  modal: React.ReactNode;
}) {
  return (
    <SidebarStateProvider>
      <PaletteProvider>
        <ShellChrome modal={modal}>{children}</ShellChrome>
      </PaletteProvider>
    </SidebarStateProvider>
  );
}
