"use client";

import * as React from "react";
import { Command } from "cmdk";
import { useRouter } from "next/navigation";
import { SHELL_SECTIONS } from "@/components/shell/section-config";
import { usePalette } from "@/components/command-palette/use-palette";

export function NavigationProvider() {
  const router = useRouter();
  const { close } = usePalette();
  return (
    <Command.Group heading="Go to" className="text-overline text-text-muted px-2 py-1">
      {SHELL_SECTIONS.flatMap((section) => section.items).map((item) => {
        const Icon = item.icon;
        return (
          <Command.Item
            key={item.href}
            value={`go-${item.label.toLowerCase()}`}
            onSelect={() => {
              router.push(item.href);
              close();
            }}
            className="flex items-center gap-2 px-3 h-9 rounded-md text-body-sm text-text-primary cursor-pointer aria-selected:bg-surface-row-hover"
          >
            <Icon className="size-4 text-text-muted" />
            <span>{item.label}</span>
          </Command.Item>
        );
      })}
    </Command.Group>
  );
}
