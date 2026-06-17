"use client";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { toast } from "sonner";
import {
  PackageBuilder,
  type PackageBuilderInitial,
} from "@/components/packages/PackageBuilder";
import { packagesApi } from "@/lib/api/packages";
import type { PackageBlock, PackageDefinition } from "@/types/package";

// Legacy v1 packages (items, no blocks) open as a single Fixed-items block so
// they remain editable in the v2 builder without data loss.
function legacyItemsToBlocks(def: PackageDefinition): PackageBlock[] {
  if (!def.items.length) return [];
  return [
    {
      id: "legacy-items",
      kind: "items",
      bonus: false,
      rows: def.items.map((it) => ({
        service_id: it.service_id,
        service_name: it.service_name ?? "",
        quantity: String(it.quantity),
        unit_price_paise: it.unit_price_paise,
      })),
    },
  ];
}

export default function EditPackagePage() {
  const { id } = useParams<{ id: string }>();
  const [initial, setInitial] = useState<PackageBuilderInitial | null>(null);

  useEffect(() => {
    packagesApi
      .getDefinition(id)
      .then((r) => {
        const d = r.data;
        setInitial({
          name: d.name,
          description: d.description ?? undefined,
          validity_days: d.validity_days,
          cancellation_fee_pct: d.cancellation_fee_pct,
          shareability: d.shareability,
          auto_apply: d.auto_apply,
          status: d.status,
          // The v2 builder works in rupees for flat/final discounts; the API
          // stores those values in paise.
          discount: d.discount
            ? {
                mode: d.discount.mode,
                value:
                  d.discount.mode === "pct"
                    ? String(parseFloat(d.discount.value))
                    : String(parseFloat(d.discount.value) / 100),
              }
            : undefined,
          blocks: d.blocks ?? legacyItemsToBlocks(d),
        });
      })
      .catch(() => toast.error("Failed to load"));
  }, [id]);

  if (!initial)
    return <div className="p-6 text-text-muted">Loading…</div>;

  return <PackageBuilder initial={initial} definitionId={id} />;
}
