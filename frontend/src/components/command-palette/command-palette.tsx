"use client";

import * as React from "react";
import { Command } from "cmdk";
import { useRouter } from "next/navigation";
import { Clock } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { usePalette } from "@/components/command-palette/use-palette";
import { readHistory, type HistoryEntry } from "@/components/command-palette/history";
import { NavigationProvider } from "@/components/command-palette/providers/navigation";
import { ActionsProvider } from "@/components/command-palette/providers/actions";
import { CustomersProvider } from "@/components/command-palette/providers/customers";
import { BillsProvider } from "@/components/command-palette/providers/bills";
import { SkusProvider } from "@/components/command-palette/providers/skus";

export function CommandPalette() {
  const { isOpen, close } = usePalette();
  const router = useRouter();
  const [query, setQuery] = React.useState("");
  const [history, setHistory] = React.useState<HistoryEntry[]>([]);

  // Reset query each time the palette closes so the next open starts fresh.
  React.useEffect(() => {
    if (!isOpen) setQuery("");
    if (isOpen) setHistory(readHistory().slice(0, 5));
  }, [isOpen]);

  const showHistory = !query && history.length > 0;

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
            {showHistory && (
              <Command.Group heading="Recent" className="text-overline text-text-muted px-2 py-1">
                {history.map((h) => (
                  <Command.Item
                    key={`recent-${h.id}`}
                    value={`recent-${h.id} ${h.label}`}
                    keywords={[h.label]}
                    onSelect={() => {
                      router.push(h.href);
                      close();
                    }}
                    className="flex items-center gap-2 px-3 h-9 rounded-md text-body-sm text-text-primary cursor-pointer aria-selected:bg-surface-row-hover"
                  >
                    <Clock className="size-4 text-text-muted" />
                    <span>{h.label}</span>
                  </Command.Item>
                ))}
              </Command.Group>
            )}
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
