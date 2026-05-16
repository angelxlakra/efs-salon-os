"use client";

import * as React from "react";
import { Search, User, LogOut } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Kbd } from "@/components/ui/kbd";
import { Breadcrumb } from "@/components/shell/breadcrumb";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { usePalette } from "@/components/command-palette/use-palette";
import { useAuthStore } from "@/stores/auth-store";
import { useRouter } from "next/navigation";
import { cn } from "@/lib/utils";

export function TopBar({ className }: { className?: string }) {
  const { open } = usePalette();
  const { user, logout } = useAuthStore();
  const router = useRouter();

  const handleLogout = () => {
    logout();
    router.push("/login");
  };

  return (
    <header
      className={cn(
        "sticky top-0 z-30 flex items-center gap-3 px-4 h-12 bg-surface-card border-b border-border-subtle",
        className,
      )}
    >
      <Breadcrumb className="flex-1 min-w-0" />
      <button
        type="button"
        onClick={open}
        aria-label="Open search palette"
        className="hidden sm:inline-flex items-center gap-2 h-8 px-3 rounded-md bg-surface-row text-text-secondary border border-border-subtle hover:bg-surface-row-hover text-body-sm"
      >
        <Search className="size-4" />
        <span className="hidden md:inline">Search…</span>
        <Kbd keys={["⌘", "K"]} />
      </button>

      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button
            type="button"
            variant="ghost"
            size="sm"
            aria-label="User menu"
            className="size-8 p-0"
          >
            <User className="size-4" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" className="w-48">
          <DropdownMenuLabel className="font-normal">
            <p className="text-sm font-semibold text-text-primary truncate">
              {user?.username || "Account"}
            </p>
            <p className="text-xs text-text-muted capitalize">{user?.role}</p>
          </DropdownMenuLabel>
          <DropdownMenuSeparator />
          <DropdownMenuItem
            onClick={handleLogout}
            className="text-danger-fg focus:text-danger-fg focus:bg-danger-bg-soft"
          >
            <LogOut className="mr-2 h-4 w-4" />
            Sign out
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </header>
  );
}
