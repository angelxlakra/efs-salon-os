"use client";

import * as React from "react";
import { usePathname } from "next/navigation";
import { MoreHorizontal } from "lucide-react";
import { NavItem } from "@/components/ui/nav-item";
import { MOBILE_TABS } from "@/components/shell/section-config";
import { MoreSheet } from "@/components/shell/more-sheet";
import { cn } from "@/lib/utils";

function isActive(itemHref: string, pathname: string): boolean {
  if (itemHref === "/dashboard") return pathname === "/dashboard";
  return pathname === itemHref || pathname.startsWith(itemHref + "/");
}

export function BottomTabNav({ className }: { className?: string }) {
  const pathname = usePathname() ?? "/";
  const [moreOpen, setMoreOpen] = React.useState(false);

  return (
    <>
      <nav
        className={cn(
          "md:hidden fixed bottom-0 inset-x-0 z-30 h-14 bg-surface-card border-t border-border-subtle flex items-stretch",
          className,
        )}
        aria-label="Primary mobile navigation"
      >
        {MOBILE_TABS.map((tab) => {
          const Icon = tab.icon;
          return (
            <NavItem
              key={tab.href}
              variant="bottom"
              label={tab.label}
              href={tab.href}
              icon={<Icon />}
              active={isActive(tab.href, pathname)}
            />
          );
        })}
        <button
          type="button"
          onClick={() => setMoreOpen(true)}
          className="flex-1 flex flex-col items-center justify-center gap-0.5 text-[11px] text-text-secondary hover:text-text-primary"
          aria-label="More navigation"
        >
          <MoreHorizontal className="size-5" />
          <span>More</span>
        </button>
      </nav>
      <MoreSheet open={moreOpen} onOpenChange={setMoreOpen} />
    </>
  );
}
