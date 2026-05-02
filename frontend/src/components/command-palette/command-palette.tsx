"use client";

import * as React from "react";
import { Command } from "cmdk";
import {
  Dialog,
  DialogContent,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { usePalette } from "@/components/command-palette/use-palette";
import { NavigationProvider } from "@/components/command-palette/providers/navigation";
import { ActionsProvider } from "@/components/command-palette/providers/actions";
import { CustomersProvider } from "@/components/command-palette/providers/customers";
import { BillsProvider } from "@/components/command-palette/providers/bills";
import { SkusProvider } from "@/components/command-palette/providers/skus";

/**
 * Root command palette. T8–T10 will mount providers (navigation actions,
 * customer/bill/SKU search, global actions) inside the cmdk Command element.
 * T11 wires persisted history.
 */
export function CommandPalette() {
  const { isOpen, close } = usePalette();
  const [query, setQuery] = React.useState("");

  // Reset query each time the palette closes so the next open starts fresh.
  React.useEffect(() => {
    if (!isOpen) setQuery("");
  }, [isOpen]);

  return (
    <Dialog open={isOpen} onOpenChange={(o) => (o ? null : close())}>
      <DialogContent size="md" hideClose className="p-0 overflow-hidden">
        <DialogTitle className="sr-only">Command palette</DialogTitle>
        <DialogDescription className="sr-only">
          Type to search customers, bills, SKUs, or run an action.
        </DialogDescription>
        <Command label="Command palette" className="flex flex-col">
          <Command.Input
            value={query}
            onValueChange={setQuery}
            placeholder="Type a command or search…"
            className="px-4 h-12 text-body bg-transparent border-b border-border-subtle outline-none"
          />
          <Command.List className="max-h-[60dvh] overflow-y-auto p-2">
            <Command.Empty className="px-3 py-6 text-center text-text-muted text-body-sm">
              No results.
            </Command.Empty>
            <NavigationProvider />
            <ActionsProvider />
            <CustomersProvider query={query} />
            <BillsProvider query={query} />
            <SkusProvider query={query} />
          </Command.List>
        </Command>
      </DialogContent>
    </Dialog>
  );
}
