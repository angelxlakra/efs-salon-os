"use client";

import * as React from "react";
import { usePathname } from "next/navigation";
import { NavItem } from "@/components/ui/nav-item";
import { SHELL_SECTIONS, resolveActiveHref } from "@/components/shell/section-config";
import { useSettingsStore } from "@/stores/settings-store";
import { cn } from "@/lib/utils";

/**
 * Labelled 192px sidebar — calm, salon-led (brand guidelines §07/§09: the salon
 * is the hero of its own workspace; Aasan recedes to a "powered by" footer).
 * Reads structure from `section-config.ts`. Active route: the single
 * longest-matching href (see resolveActiveHref).
 */
export function SidebarV2({ className }: { className?: string }) {
  const pathname = usePathname() ?? "/";
  const activeHref = resolveActiveHref(pathname);
  const { settings, fetchSettings } = useSettingsStore();

  React.useEffect(() => {
    if (!settings) fetchSettings();
  }, [settings, fetchSettings]);

  const salonName = settings?.salon_name || "Your Salon";
  const salonSub = settings?.salon_tagline || "Owner";
  const initial = (salonName.trim()[0] || "A").toUpperCase();

  return (
    <aside
      className={cn(
        "w-48 shrink-0 h-dvh sticky top-0 flex flex-col bg-surface-sidebar border-r border-border-subtle",
        className,
      )}
    >
      {/* Salon identity — the hero of the workspace */}
      <div className="px-3 py-4 border-b border-border-subtle">
        <div className="flex items-center gap-2.5">
          <div
            className="flex items-center justify-center shrink-0 overflow-hidden"
            style={{ width: 36, height: 36, borderRadius: 9, background: "var(--text-primary)" }}
          >
            {settings?.logo_url ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img src={settings.logo_url} alt="" width={36} height={36} style={{ objectFit: "cover" }} />
            ) : (
              <span className="font-display" style={{ fontSize: 18, fontWeight: 600, color: "var(--gold-default)" }}>
                {initial}
              </span>
            )}
          </div>
          <div className="min-w-0 flex-1">
            <div className="truncate font-semibold text-text-primary" style={{ fontSize: 14 }} title={salonName}>
              {salonName}
            </div>
            <div className="truncate text-text-muted" style={{ fontSize: 11 }}>
              {salonSub}
            </div>
          </div>
        </div>
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
                  active={item.href === activeHref}
                />
              );
            })}
          </div>
        ))}
      </nav>

      {/* Aasan recedes to a quiet platform footer */}
      <div className="px-4 py-3 flex items-center gap-2 border-t border-border-subtle">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src="/aasan-mark.svg" width={16} height={16} alt="" style={{ opacity: 0.85 }} />
        <span className="text-text-muted" style={{ fontSize: 11 }}>
          Powered by{" "}
          <span className="font-brand" style={{ fontWeight: 600, color: "var(--text-secondary)" }}>
            Aasan
          </span>
        </span>
      </div>
    </aside>
  );
}
