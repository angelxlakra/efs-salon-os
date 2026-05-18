"use client";

import * as React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogBody,
} from "@/components/ui/dialog";
import { SHELL_SECTIONS, MOBILE_TABS } from "@/components/shell/section-config";
import { cn } from "@/lib/utils";

function isActive(itemHref: string, pathname: string): boolean {
  if (itemHref === "/dashboard") return pathname === "/dashboard";
  return pathname === itemHref || pathname.startsWith(itemHref + "/");
}

export function MoreSheet({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (next: boolean) => void;
}) {
  const pathname = usePathname() ?? "/";

  // Items already in the bottom tabs — exclude from overflow.
  const tabHrefs = new Set(MOBILE_TABS.map((t) => t.href));

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent size="full" className="md:hidden">
        <DialogHeader>
          <DialogTitle>More</DialogTitle>
        </DialogHeader>
        <DialogBody>
          <div className="flex flex-col gap-4">
            {SHELL_SECTIONS.map((section) => {
              const overflowItems = section.items.filter((it) => !tabHrefs.has(it.href));
              if (overflowItems.length === 0) return null;
              return (
                <div key={section.id} className="flex flex-col gap-1">
                  <div className="px-3 pt-2 pb-1 text-overline text-text-muted">{section.label}</div>
                  {overflowItems.map((item) => {
                    const Icon = item.icon;
                    const active = isActive(item.href, pathname);
                    return (
                      <Link
                        key={item.href}
                        href={item.href}
                        onClick={() => onOpenChange(false)}
                        className={cn(
                          "flex items-center gap-3 px-3 h-10 rounded-md text-body text-text-primary",
                          "hover:bg-surface-row-hover",
                          active && "bg-accent-bg-soft text-accent font-semibold",
                        )}
                        data-active={active || undefined}
                      >
                        <Icon className="size-4 text-text-muted" />
                        <span>{item.label}</span>
                      </Link>
                    );
                  })}
                </div>
              );
            })}
          </div>
        </DialogBody>
      </DialogContent>
    </Dialog>
  );
}
