"use client";

import * as React from "react";
import { usePathname } from "next/navigation";
import { NavItem } from "@/components/ui/nav-item";
import { SHELL_SECTIONS, resolveActiveHref } from "@/components/shell/section-config";
import { useSettingsStore } from "@/stores/settings-store";
import { cn } from "@/lib/utils";

export function SidebarRail({ className }: { className?: string }) {
  const pathname = usePathname() ?? "/";
  const activeHref = resolveActiveHref(pathname);
  const { settings, fetchSettings } = useSettingsStore();

  React.useEffect(() => {
    if (!settings) fetchSettings();
  }, [settings, fetchSettings]);

  const initial = (settings?.salon_name?.trim()[0] || "A").toUpperCase();

  return (
    <aside
      className={cn(
        "w-14 shrink-0 bg-surface-sidebar border-r border-border-subtle h-dvh sticky top-0 flex flex-col items-center",
        className,
      )}
    >
      {/* Salon initial on ink + gold — the workspace mark when collapsed */}
      <div className="h-12 flex items-center justify-center border-b border-border-subtle w-full">
        <span
          className="font-display flex items-center justify-center"
          style={{ width: 30, height: 30, borderRadius: 8, background: "var(--text-primary)", color: "var(--gold-default)", fontSize: 16, fontWeight: 600 }}
          title={settings?.salon_name || undefined}
        >
          {initial}
        </span>
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
              active={item.href === activeHref}
              variant="rail"
            />
          );
        })}
      </nav>
      {/* Aasan platform mark — quiet footer */}
      <div className="py-3 w-full flex items-center justify-center border-t border-border-subtle">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src="/aasan-mark.svg" width={18} height={18} alt="Powered by Aasan" title="Powered by Aasan" style={{ opacity: 0.85 }} />
      </div>
    </aside>
  );
}
