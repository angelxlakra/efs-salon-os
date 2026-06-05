"use client";
import { useState } from "react";
import { AlertTriangle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { SessionsLeft } from "@/components/ui/SessionsLeft";
import { ExpiryBadge } from "@/components/ui/ExpiryBadge";
import type { PackageSaleSummary } from "@/types/package";
import { cn } from "@/lib/utils";

interface Props {
  /** 2+ eligible packages — sorted by expires_at ASC (FIFO pre-selection). */
  packages: PackageSaleSummary[];
  onSelect: (packageSaleId: string) => void;
  onDismiss: () => void;
}

/**
 * Inline radio panel shown when add_bill_item returns 2+ eligible packages.
 * Pre-selects the soonest-expiring (FIFO). Requires cashier confirmation.
 */
export function MultiPackageSelector({ packages, onSelect, onDismiss }: Props) {
  // Packages are pre-sorted expires_at ASC from the server (FIFO)
  const [selected, setSelected] = useState<string>(packages[0]?.id ?? "");

  return (
    <div className="rounded-lg border border-warning-border bg-warning-bg-soft p-3 space-y-2.5">
      {/* Warning banner */}
      <div className="flex items-start gap-2">
        <AlertTriangle size={14} className="mt-0.5 text-warning-fg shrink-0" />
        <p className="text-xs text-warning-fg font-medium">
          Multiple packages available — confirm with customer which to use.
        </p>
      </div>

      {/* Radio options */}
      <div className="flex flex-col gap-1.5">
        {packages.map((pkg) => (
          <label
            key={pkg.id}
            className={cn(
              "flex items-center gap-2.5 px-3 py-2 rounded-lg border cursor-pointer transition-colors",
              selected === pkg.id
                ? "border-accent bg-accent/5"
                : "border-border bg-card hover:bg-surface-row"
            )}
          >
            <input
              type="radio"
              name="package-choice"
              value={pkg.id}
              checked={selected === pkg.id}
              onChange={() => setSelected(pkg.id)}
              className="accent-accent"
            />
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium truncate">
                {pkg.package_definition_name ?? "Package"}
              </p>
              <div className="flex items-center gap-2 mt-0.5">
                <SessionsLeft
                  remaining={pkg.sessions_remaining}
                  total={pkg.total_sessions_snapshot}
                  size="sm"
                />
                <ExpiryBadge expiresAt={pkg.expires_at} />
                {pkg.shareability_snapshot === "shared" && pkg.customer_name && (
                  <span className="text-[10px] text-muted-foreground">
                    Owned by {pkg.customer_name}
                  </span>
                )}
              </div>
            </div>
          </label>
        ))}
      </div>

      {/* Actions */}
      <div className="flex gap-2 pt-1">
        <Button
          size="sm"
          onClick={() => onSelect(selected)}
          disabled={!selected}
          className="flex-1"
        >
          Apply package
        </Button>
        <Button size="sm" variant="outline" onClick={onDismiss}>
          Pay full price
        </Button>
      </div>
    </div>
  );
}
