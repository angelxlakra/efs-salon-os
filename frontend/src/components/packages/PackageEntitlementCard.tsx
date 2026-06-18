"use client";
// Customer entitlements card: one active PackageSale with block-level progress.
// Redemption machinery (rail/undo on bills) is unchanged — this is read-only.

import { cn } from "@/lib/utils";
import { ExpiryBadge } from "@/components/ui/ExpiryBadge";
import { Badge } from "@/components/ui/badge";
import { entitlementRows, type EntitlementTone } from "@/lib/packages/entitlement-progress";
import type { PackageSale } from "@/types/package";

const TONE_FILL: Record<EntitlementTone, string> = {
  accent: "bg-accent",
  info: "bg-info-fg",
  gold: "bg-gold",
  success: "bg-success-fg",
};

const TONE_CHIP: Record<EntitlementTone, string> = {
  accent: "bg-accent-bg-soft text-accent",
  info: "bg-info-bg-soft text-info-fg",
  gold: "bg-gold-soft text-gold-fg",
  success: "bg-success-bg-soft text-success-fg",
};

// 10-segment progress bar (filled = tone, empty = border-default).
function SegmentBar({ used, total, tone }: { used: number; total: number; tone: EntitlementTone }) {
  const segments = Math.min(total, 10);
  const filledFraction = total > 0 ? used / total : 0;
  return (
    <div className="flex gap-1" aria-label={`${used} of ${total} used`}>
      {Array.from({ length: segments }).map((_, i) => {
        const filled = i < Math.round(filledFraction * segments);
        return (
          <span
            key={i}
            className={cn(
              "h-[7px] flex-1 rounded-full",
              filled ? TONE_FILL[tone] : "bg-border-default"
            )}
          />
        );
      })}
    </div>
  );
}

export function PackageEntitlementCard({ sale }: { sale: PackageSale }) {
  const rows = entitlementRows(sale);
  const expired = sale.status === "expired" || sale.status === "refunded";

  return (
    <div className="space-y-3 rounded-[10px] border border-border-default bg-surface-card p-4">
      <div className="flex items-center justify-between gap-2">
        <p className="text-[14px] font-semibold text-text-primary">
          {sale.package_definition_name ?? "Package"}
        </p>
        <div className="flex items-center gap-1.5">
          {sale.status !== "active" && (
            <Badge tone={expired ? "neutral" : "warning"} size="sm">
              {sale.status}
            </Badge>
          )}
          <ExpiryBadge expiresAt={sale.expires_at} />
        </div>
      </div>

      <div className="space-y-2.5">
        {rows.map((row) => (
          <div key={row.key} className="space-y-1">
            <div className="flex items-center justify-between gap-2">
              <span className="flex min-w-0 items-center gap-1.5 text-[13px] text-text-secondary">
                <span className="truncate">{row.label}</span>
                {row.bonus && (
                  <span className="shrink-0 rounded-full bg-gold-soft px-1.5 py-0.5 text-[10px] font-medium text-gold-fg">
                    free
                  </span>
                )}
              </span>
              {row.total > 0 ? (
                <span className="shrink-0 text-[12px] tabular-nums text-text-muted">
                  {row.detail}
                </span>
              ) : (
                <span
                  className={cn(
                    "shrink-0 rounded-full px-2 py-0.5 text-[11px] font-medium tabular-nums",
                    TONE_CHIP[row.tone]
                  )}
                >
                  {row.detail}
                </span>
              )}
            </div>
            {row.total > 0 && <SegmentBar used={row.used} total={row.total} tone={row.tone} />}
          </div>
        ))}
      </div>

      <p className="border-t border-border-subtle pt-2 text-[11px] text-text-muted">
        {sale.shareability_snapshot === "shared" ? "Shared" : "Personal"} · expires{" "}
        {new Date(sale.expires_at).toLocaleDateString("en-IN", {
          day: "numeric",
          month: "short",
          year: "numeric",
        })}
      </p>
    </div>
  );
}
