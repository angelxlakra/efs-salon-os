"use client";
import { useEffect } from "react";
import { usePackagesStore } from "@/stores/packages-store";
import { SessionsLeft } from "@/components/ui/SessionsLeft";
import { ExpiryBadge } from "@/components/ui/ExpiryBadge";

interface Props {
  customerId: string;
}

/** Horizontal strip (768-1024px) for active packages. */
export function EntitlementsStrip({ customerId }: Props) {
  const loadEligibility = usePackagesStore((s) => s.loadEligibility);
  const entry = usePackagesStore((s) => s.eligibilityCache.get(customerId));
  const packages = entry?.packages ?? [];

  useEffect(() => {
    loadEligibility(customerId);
  }, [customerId, loadEligibility]);

  if (packages.length === 0) return null;

  return (
    <div
      className="flex items-center gap-2 px-3 py-2 border-b border-border bg-card overflow-x-auto"
      aria-label="Active packages"
    >
      <span className="text-xs text-muted-foreground shrink-0">Packages:</span>
      {packages.map((sale) => (
        <div
          key={sale.id}
          className="flex items-center gap-1.5 px-2 py-1 rounded-full border border-border bg-surface-row shrink-0"
          style={{ borderLeftWidth: "3px", borderLeftColor: "#c9a96e" }}
        >
          <span className="text-xs font-medium truncate max-w-[120px]">
            {sale.package_definition_name ?? "Package"}
          </span>
          <SessionsLeft
            remaining={sale.sessions_remaining}
            total={sale.total_sessions_snapshot}
            size="sm"
          />
          <ExpiryBadge expiresAt={sale.expires_at} />
        </div>
      ))}
    </div>
  );
}
