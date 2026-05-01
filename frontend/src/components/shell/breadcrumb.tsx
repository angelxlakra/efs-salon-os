"use client";

import * as React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { ChevronRight } from "lucide-react";
import { SHELL_SECTIONS } from "@/components/shell/section-config";
import { cn } from "@/lib/utils";

/** Build a label-lookup table from the section config so /dashboard/bills → "Bills". */
const HREF_TO_LABEL = (() => {
  const map = new Map<string, string>();
  for (const section of SHELL_SECTIONS) {
    for (const item of section.items) {
      map.set(item.href, item.label);
    }
  }
  return map;
})();

type Crumb = { href: string; label: string };

function buildCrumbs(pathname: string): Crumb[] {
  // Always begin with Today (the dashboard root).
  const crumbs: Crumb[] = [{ href: "/dashboard", label: "Today" }];
  if (pathname === "/dashboard" || !pathname.startsWith("/dashboard")) return crumbs;

  // Walk the path segment-by-segment, building accumulated hrefs.
  const segments = pathname.replace(/^\/dashboard\//, "").split("/").filter(Boolean);
  let acc = "/dashboard";
  for (const seg of segments) {
    acc = `${acc}/${seg}`;
    const labelFromConfig = HREF_TO_LABEL.get(acc);
    crumbs.push({
      href: acc,
      label: labelFromConfig ?? seg, // unknown segments (IDs) shown verbatim
    });
  }
  return crumbs;
}

export function Breadcrumb({ className }: { className?: string }) {
  const pathname = usePathname() ?? "/dashboard";
  const crumbs = buildCrumbs(pathname);
  return (
    <nav className={cn("flex items-center gap-1 text-body-sm text-text-secondary truncate", className)} aria-label="Breadcrumb">
      {crumbs.map((crumb, i) => {
        const isLast = i === crumbs.length - 1;
        return (
          <React.Fragment key={crumb.href}>
            {i > 0 && <ChevronRight className="size-3 text-text-muted shrink-0" aria-hidden />}
            {isLast ? (
              <span className="text-text-primary font-medium truncate" aria-current="page">{crumb.label}</span>
            ) : (
              <Link href={crumb.href} className="hover:text-text-primary truncate">{crumb.label}</Link>
            )}
          </React.Fragment>
        );
      })}
    </nav>
  );
}
