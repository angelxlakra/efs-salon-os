"use client";
import { useEffect } from "react";
import { usePackagesStore } from "@/stores/packages-store";
import { PackageCard } from "@/components/packages/PackageCard";

interface Props {
  customerId: string;
}

/** Vertical rail (>=1024px) showing customer's active packages. */
export function EntitlementsRail({ customerId }: Props) {
  const loadEligibility = usePackagesStore((s) => s.loadEligibility);
  const entry = usePackagesStore((s) => s.eligibilityCache.get(customerId));
  const packages = entry?.packages ?? [];

  useEffect(() => {
    loadEligibility(customerId);
  }, [customerId, loadEligibility]);

  if (packages.length === 0) return null;

  return (
    <aside
      className="w-52 shrink-0 flex flex-col gap-2 p-3 border-r border-border bg-surface-sidebar overflow-y-auto"
      aria-label="Active packages"
    >
      <p className="text-overline text-muted-foreground px-1 pt-1">
        Already paid for
      </p>
      {packages.map((sale) => (
        <PackageCard key={sale.id} sale={sale} compact />
      ))}
    </aside>
  );
}
