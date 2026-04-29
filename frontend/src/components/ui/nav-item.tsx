import * as React from "react";
import Link from "next/link";
import { cn } from "@/lib/utils";

type Props = {
  label: string;
  href: string;
  icon?: React.ReactNode;
  active?: boolean;
  badge?: React.ReactNode;
  variant?: "sidebar" | "rail" | "bottom";
  className?: string;
};

export function NavItem({
  label,
  href,
  icon,
  active,
  badge,
  variant = "sidebar",
  className,
}: Props) {
  return (
    <Link
      href={href}
      data-active={active || undefined}
      aria-current={active ? "page" : undefined}
      className={cn(
        "flex items-center gap-2 transition-colors rounded-md",
        "text-body-sm text-text-secondary hover:text-text-primary hover:bg-surface-row-hover",
        "data-[active=true]:bg-accent-bg-soft data-[active=true]:text-accent data-[active=true]:font-semibold",
        variant === "sidebar" && "px-3 h-8",
        variant === "rail" && "flex-col justify-center w-12 h-14 text-[10px] gap-0.5",
        variant === "bottom" && "flex-col justify-center flex-1 h-14 text-[11px] gap-0.5",
        className
      )}
    >
      {icon && <span aria-hidden className="[&_svg]:size-4 shrink-0">{icon}</span>}
      <span className={cn("flex-1", variant !== "sidebar" && "text-center")}>{label}</span>
      {badge && variant === "sidebar" && <span className="ml-auto">{badge}</span>}
    </Link>
  );
}
