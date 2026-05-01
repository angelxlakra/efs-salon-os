"use client";

import * as React from "react";
import { usePathname } from "next/navigation";
import { NavItem } from "@/components/ui/nav-item";
import { SHELL_SECTIONS } from "@/components/shell/section-config";
import { cn } from "@/lib/utils";

/**
 * Labelled 192px sidebar. Reads structure from `section-config.ts`.
 * Active route detection: exact match for /dashboard, prefix match for sub-routes.
 */
function isActive(itemHref: string, pathname: string): boolean {
  if (itemHref === "/dashboard") return pathname === "/dashboard";
  return pathname === itemHref || pathname.startsWith(itemHref + "/");
}

export function SidebarV2({ className }: { className?: string }) {
  const pathname = usePathname() ?? "/";
  return (
    <aside
      className={cn(
        "w-48 shrink-0 bg-surface-sidebar border-r border-border-subtle h-dvh sticky top-0 flex flex-col",
        className,
      )}
    >
      <div className="px-4 py-3 border-b border-border-subtle">
        <span className="font-display text-heading-md text-text-primary">SalonOS</span>
      </div>
      <nav className="flex-1 overflow-y-auto p-2 flex flex-col gap-4">
        {SHELL_SECTIONS.map((section) => (
          <div key={section.id} className="flex flex-col gap-1">
            <div className="px-3 pt-2 pb-1 text-overline text-text-muted">{section.label}</div>
            {section.items.map((item) => {
              const Icon = item.icon;
              return (
                <NavItem
                  key={item.href}
                  label={item.label}
                  href={item.href}
                  icon={<Icon />}
                  active={isActive(item.href, pathname)}
                />
              );
            })}
          </div>
        ))}
      </nav>
    </aside>
  );
}
