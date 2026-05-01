"use client";

import * as React from "react";
import { usePathname } from "next/navigation";
import { NavItem } from "@/components/ui/nav-item";
import { SHELL_SECTIONS } from "@/components/shell/section-config";
import { cn } from "@/lib/utils";

function isActive(itemHref: string, pathname: string): boolean {
  if (itemHref === "/dashboard") return pathname === "/dashboard";
  return pathname === itemHref || pathname.startsWith(itemHref + "/");
}

export function SidebarRail({ className }: { className?: string }) {
  const pathname = usePathname() ?? "/";
  return (
    <aside
      className={cn(
        "w-14 shrink-0 bg-surface-sidebar border-r border-border-subtle h-dvh sticky top-0 flex flex-col items-center",
        className,
      )}
    >
      <div className="h-12 flex items-center justify-center border-b border-border-subtle w-full">
        <span className="font-display text-heading-md text-accent">S</span>
      </div>
      <nav className="flex-1 overflow-y-auto py-2 flex flex-col gap-1 w-full items-center">
        {SHELL_SECTIONS.flatMap((section) => section.items).map((item) => {
          const Icon = item.icon;
          return (
            <NavItem
              key={item.href}
              label={item.label}
              href={item.href}
              icon={<Icon />}
              active={isActive(item.href, pathname)}
              variant="rail"
            />
          );
        })}
      </nav>
    </aside>
  );
}
