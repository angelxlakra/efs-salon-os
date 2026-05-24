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
        "w-48 shrink-0 h-dvh sticky top-0 flex flex-col",
        className,
      )}
      style={{
        background: '#1c104c',
        borderRight: '1px solid rgba(240,237,232,0.12)',
        // Override semantic tokens so NavItem colours work on navy
        '--text-primary':        '#f0ede8',
        '--text-secondary':      'rgba(240,237,232,0.70)',
        '--text-muted':          'rgba(240,237,232,0.42)',
        '--border-subtle':       'rgba(240,237,232,0.12)',
        '--surface-row-hover':   'rgba(255,255,255,0.08)',
        '--accent-bg-soft':      'rgba(232,201,122,0.18)',
        '--accent':              '#e8c97a',
      } as React.CSSProperties}
    >
      <div className="px-4 py-3" style={{ borderBottom: '1px solid rgba(240,237,232,0.12)' }}>
        <span className="font-display text-heading-md" style={{ color: '#f0ede8' }}>SalonOS</span>
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
