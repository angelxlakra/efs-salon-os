import { cn } from "@/lib/utils";
import { SessionsLeft } from "@/components/ui/SessionsLeft";
import { ExpiryBadge } from "@/components/ui/ExpiryBadge";
import type { PackageSaleSummary } from "@/types/package";

interface Props {
  sale: PackageSaleSummary;
  compact?: boolean;
  className?: string;
}

export function PackageCard({ sale, compact = false, className }: Props) {
  return (
    <div
      className={cn(
        "rounded-lg border border-border bg-card p-3 flex flex-col gap-1.5",
        "border-l-[3px] border-l-[#c9a96e]", // gold left-rail: "already owned"
        className
      )}
    >
      <p className={cn("font-medium leading-tight", compact ? "text-xs" : "text-sm")}>
        {sale.package_definition_name ?? "Package"}
      </p>
      <div className="flex items-center gap-2 flex-wrap">
        <SessionsLeft
          remaining={sale.sessions_remaining}
          total={sale.total_sessions_snapshot}
          size="sm"
        />
        <ExpiryBadge expiresAt={sale.expires_at} />
        {sale.shareability_snapshot === "shared" && (
          <span className="text-[10px] text-muted-foreground border border-border rounded-full px-1.5 py-0.5">
            Shared
          </span>
        )}
      </div>
    </div>
  );
}
