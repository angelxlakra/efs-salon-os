"use client";
import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { PackageBuilder } from "@/components/packages/PackageBuilder";
import { packagesApi } from "@/lib/api/packages";
import type { PackageDefinitionCreate } from "@/types/package";
import { toast } from "sonner";

export default function EditPackagePage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [initial, setInitial] = useState<PackageDefinitionCreate | null>(null);

  useEffect(() => {
    packagesApi
      .getDefinition(id)
      .then((r) => {
        const d = r.data;
        setInitial({
          name: d.name,
          description: d.description ?? undefined,
          entitlement_type: d.entitlement_type,
          total_sessions: d.total_sessions ?? undefined,
          shareability: d.shareability,
          validity_days: d.validity_days,
          auto_apply: d.auto_apply,
          cancellation_fee_pct: d.cancellation_fee_pct,
          items: d.items.map((it) => ({
            service_id: it.service_id,
            quantity: it.quantity,
            unit_price_paise: it.unit_price_paise,
            locked: it.locked,
            display_order: it.display_order,
          })),
        });
      })
      .catch(() => toast.error("Failed to load"));
  }, [id]);

  if (!initial) return <div className="p-6 text-muted-foreground">Loading...</div>;

  return (
    <PackageBuilder
      initial={initial}
      onSaved={() => router.push(`/dashboard/packages/${id}`)}
    />
  );
}
