"use client";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Loader2, ShoppingBag } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { ExpiryBadge } from "@/components/ui/ExpiryBadge";
import { SessionsLeft } from "@/components/ui/SessionsLeft";
import { RefundPackageModal } from "@/components/packages/RefundPackageModal";
import { ExtendExpiryModal } from "@/components/packages/ExtendExpiryModal";
import { packagesApi } from "@/lib/api/packages";
import { useAuthStore } from "@/stores/auth-store";
import type { PackageSale, PackageSaleStatus } from "@/types/package";

const STATUS_TONE: Record<string, "neutral" | "success" | "warning" | "danger"> = {
  active: "success",
  expired: "neutral",
  refunded: "danger",
  exhausted: "warning",
};

export default function SoldPackagesPage() {
  const { hasPermission } = useAuthStore();
  const canRefund = hasPermission("packages", "refund");
  const canExtend = hasPermission("packages", "extend_expiry");

  const [sales, setSales] = useState<PackageSale[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState<PackageSaleStatus | "all">("all");
  const [refundTarget, setRefundTarget] = useState<PackageSale | null>(null);
  const [extendTarget, setExtendTarget] = useState<PackageSale | null>(null);

  async function fetchSales() {
    try {
      const params = statusFilter !== "all" ? { status: statusFilter } : {};
      const res = await packagesApi.listSales(params);
      setSales(res.data);
    } catch {
      toast.error("Failed to load sold packages");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { fetchSales(); }, [statusFilter]);

  return (
    <div className="p-6 space-y-4">
      <h1 className="text-heading-lg font-display">Sold Packages</h1>

      {/* Status filter */}
      <div className="flex gap-2 flex-wrap">
        {(["all", "active", "expired", "refunded", "exhausted"] as const).map((f) => (
          <button
            key={f}
            onClick={() => setStatusFilter(f)}
            className={`px-3 py-1 rounded-full text-sm border capitalize transition-colors ${
              statusFilter === f
                ? "bg-accent text-accent-foreground border-accent"
                : "border-border text-muted-foreground hover:border-border-strong"
            }`}
          >
            {f}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-16">
          <Loader2 size={24} className="animate-spin text-muted-foreground" />
        </div>
      ) : sales.length === 0 ? (
        <EmptyState
          icon={<ShoppingBag size={32} />}
          title="No sold packages"
          body={
            statusFilter !== "all"
              ? `No ${statusFilter} packages. Switch the filter to see others.`
              : "Packages will appear here once a customer purchases one from the POS."
          }
          headingLevel={2}
        />
      ) : (
        <div className="rounded-xl border border-border overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-surface-row border-b border-border">
              <tr>
                <th className="text-left px-4 py-2.5 font-medium text-muted-foreground">Package</th>
                <th className="text-left px-4 py-2.5 font-medium text-muted-foreground">Customer</th>
                <th className="text-left px-4 py-2.5 font-medium text-muted-foreground">Sessions</th>
                <th className="text-left px-4 py-2.5 font-medium text-muted-foreground">Expiry</th>
                <th className="text-left px-4 py-2.5 font-medium text-muted-foreground">Status</th>
                <th className="px-4 py-2.5" />
              </tr>
            </thead>
            <tbody>
              {sales.map((sale) => (
                <tr key={sale.id} className="border-b border-border-subtle last:border-0 hover:bg-surface-row-hover">
                  <td className="px-4 py-3 font-medium">
                    {sale.package_definition_name ?? sale.package_definition_id.slice(0, 8)}
                  </td>
                  <td className="px-4 py-3 text-muted-foreground">
                    {sale.customer_name ?? sale.customer_id.slice(0, 8)}
                  </td>
                  <td className="px-4 py-3">
                    <SessionsLeft remaining={sale.sessions_remaining} total={sale.total_sessions_snapshot} />
                  </td>
                  <td className="px-4 py-3">
                    <ExpiryBadge expiresAt={sale.expires_at} />
                  </td>
                  <td className="px-4 py-3">
                    <Badge tone={STATUS_TONE[sale.status] ?? "neutral"} size="sm">
                      {sale.status}
                    </Badge>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex gap-2 justify-end">
                      {canExtend && sale.status === "active" && (
                        <Button variant="outline" size="sm" onClick={() => setExtendTarget(sale)}>
                          Extend
                        </Button>
                      )}
                      {canRefund && sale.status !== "refunded" && (
                        <Button variant="outline" size="sm" onClick={() => setRefundTarget(sale)}>
                          Refund
                        </Button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <RefundPackageModal
        open={!!refundTarget}
        sale={refundTarget}
        onClose={() => setRefundTarget(null)}
        onRefunded={fetchSales}
      />
      <ExtendExpiryModal
        open={!!extendTarget}
        sale={extendTarget}
        onClose={() => setExtendTarget(null)}
        onExtended={fetchSales}
      />
    </div>
  );
}
