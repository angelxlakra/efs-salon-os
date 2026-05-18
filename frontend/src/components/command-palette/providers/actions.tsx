"use client";

import * as React from "react";
import { Command } from "cmdk";
import { useRouter } from "next/navigation";
import { Plus, CreditCard, Sun } from "lucide-react";
import { usePalette } from "@/components/command-palette/use-palette";

function toggleTheme() {
  if (typeof document === "undefined") return;
  const current = document.documentElement.getAttribute("data-theme");
  const next = current === "dark" ? "light" : "dark";
  document.documentElement.setAttribute("data-theme", next);
  try {
    window.localStorage.setItem("salon.theme", next);
  } catch {
    // storage may be unavailable in private mode — fail silent.
  }
}

export function ActionsProvider() {
  const router = useRouter();
  const { close } = usePalette();

  const items: { id: string; label: string; icon: typeof Plus; run: () => void }[] = [
    {
      id: "new-bill",
      label: "New bill",
      icon: Plus,
      run: () => {
        router.push("/dashboard/pos");
        close();
      },
    },
    {
      id: "open-cash-drawer",
      label: "Open cash drawer",
      icon: CreditCard,
      run: () => {
        router.push("/dashboard/cash-drawer");
        close();
      },
    },
    {
      id: "toggle-theme",
      label: "Toggle theme",
      icon: Sun,
      run: () => {
        toggleTheme();
        close();
      },
    },
  ];

  return (
    <Command.Group heading="Actions" className="text-overline text-text-muted px-2 py-1">
      {items.map((it) => {
        const Icon = it.icon;
        return (
          <Command.Item
            key={it.id}
            value={`action-${it.id} ${it.label}`}
            keywords={[it.label]}
            onSelect={it.run}
            className="flex items-center gap-2 px-3 h-9 rounded-md text-body-sm text-text-primary cursor-pointer aria-selected:bg-surface-row-hover"
          >
            <Icon className="size-4 text-text-muted" />
            <span>{it.label}</span>
          </Command.Item>
        );
      })}
    </Command.Group>
  );
}
