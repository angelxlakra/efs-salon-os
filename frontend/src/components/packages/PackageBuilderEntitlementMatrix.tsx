"use client";
import { cn } from "@/lib/utils";
import type { EntitlementType, Shareability } from "@/types/package";

interface Props {
  entitlementType: EntitlementType;
  shareability: Shareability;
  onChange: (et: EntitlementType, sh: Shareability) => void;
}

export function PackageBuilderEntitlementMatrix({
  entitlementType,
  shareability,
  onChange,
}: Props) {
  const cells: Array<{
    et: EntitlementType;
    sh: Shareability;
    label: string;
    desc: string;
  }> = [
    { et: "counted", sh: "owner_only", label: "Counted · Personal", desc: "N sessions, one customer" },
    { et: "counted", sh: "shared", label: "Counted · Shared", desc: "N sessions, any registered customer" },
    { et: "unlimited", sh: "owner_only", label: "Unlimited · Personal", desc: "Unlimited sessions until expiry" },
    { et: "unlimited", sh: "shared", label: "Unlimited · Shared", desc: "Unlimited sessions, shareable" },
  ];

  return (
    <div className="space-y-1.5">
      <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
        Package type
      </p>
      <div className="grid grid-cols-2 gap-2">
        {cells.map((cell) => {
          const isActive =
            entitlementType === cell.et && shareability === cell.sh;
          return (
            <button
              key={`${cell.et}-${cell.sh}`}
              type="button"
              onClick={() => onChange(cell.et, cell.sh)}
              className={cn(
                "rounded-lg border p-3 text-left transition-all",
                isActive
                  ? "border-accent bg-accent/5 ring-1 ring-accent"
                  : "border-border bg-surface-row hover:border-border-strong"
              )}
            >
              <p className="text-xs font-semibold leading-tight">{cell.label}</p>
              <p className="mt-0.5 text-[10px] text-muted-foreground leading-tight">
                {cell.desc}
              </p>
            </button>
          );
        })}
      </div>
    </div>
  );
}
