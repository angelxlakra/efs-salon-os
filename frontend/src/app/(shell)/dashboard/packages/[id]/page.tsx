"use client";
import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { packagesApi } from "@/lib/api/packages";
import { useAuthStore } from "@/stores/auth-store";
import { SessionsLeft } from "@/components/ui/SessionsLeft";
import type { PackageDefinition } from "@/types/package";
import { toast } from "sonner";

export default function PackageDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const { hasPermission } = useAuthStore();
  const [pkg, setPkg] = useState<PackageDefinition | null>(null);

  useEffect(() => {
    packagesApi
      .getDefinition(id)
      .then((r) => setPkg(r.data))
      .catch(() => toast.error("Not found"));
  }, [id]);

  if (!pkg) return <div className="p-6 text-muted-foreground">Loading...</div>;

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-heading-lg font-display">{pkg.name}</h1>
          {pkg.description && (
            <p className="text-muted-foreground text-sm">{pkg.description}</p>
          )}
        </div>
        {hasPermission("packages", "update") && (
          <Button
            variant="outline"
            onClick={() => router.push(`/dashboard/packages/${id}/edit`)}
          >
            Edit
          </Button>
        )}
      </div>
      <div className="flex gap-4 text-sm">
        <span>
          Type: <strong className="capitalize">{pkg.entitlement_type}</strong>
        </span>
        {pkg.total_sessions != null && (
          <span>
            Sessions:{" "}
            <SessionsLeft
              remaining={pkg.total_sessions}
              total={pkg.total_sessions}
            />
          </span>
        )}
        <span>
          Validity: <strong>{pkg.validity_days}d</strong>
        </span>
        <span>
          Status:{" "}
          <Badge
            tone={
              pkg.status === "published"
                ? "success"
                : pkg.status === "draft"
                  ? "warning"
                  : "neutral"
            }
            size="sm"
          >
            {pkg.status}
          </Badge>
        </span>
      </div>
      <div className="rounded-xl border border-border overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-surface-row border-b border-border">
            <tr>
              <th className="text-left px-4 py-2.5 font-medium text-muted-foreground">
                Service
              </th>
              <th className="text-center px-4 py-2.5 font-medium text-muted-foreground">
                Qty
              </th>
              <th className="text-right px-4 py-2.5 font-medium text-muted-foreground">
                Price
              </th>
            </tr>
          </thead>
          <tbody>
            {pkg.items.map((item) => (
              <tr key={item.id} className="border-b border-border-subtle last:border-0">
                <td className="px-4 py-3">{item.service_name ?? item.service_id}</td>
                <td className="px-4 py-3 text-center tabular-nums">{item.quantity}</td>
                <td className="px-4 py-3 text-right tabular-nums">
                  ₹{(item.unit_price_paise / 100).toFixed(2)}
                </td>
              </tr>
            ))}
          </tbody>
          <tfoot>
            {(() => {
              const mrp = pkg.items.reduce(
                (s, i) => s + i.unit_price_paise * i.quantity,
                0
              );
              const discounted = pkg.final_price_paise < mrp;
              return (
                <>
                  <tr className="border-t border-border">
                    <td className="px-4 py-2.5 font-medium" colSpan={2}>
                      Package MRP
                    </td>
                    <td className="px-4 py-2.5 text-right tabular-nums">
                      ₹{(mrp / 100).toFixed(2)}
                    </td>
                  </tr>
                  {discounted && (
                    <tr>
                      <td className="px-4 py-2.5 font-semibold" colSpan={2}>
                        Final price
                      </td>
                      <td className="px-4 py-2.5 text-right tabular-nums font-semibold">
                        ₹{(pkg.final_price_paise / 100).toFixed(2)}
                      </td>
                    </tr>
                  )}
                </>
              );
            })()}
          </tfoot>
        </table>
      </div>
    </div>
  );
}
