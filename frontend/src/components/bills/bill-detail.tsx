"use client";

import * as React from "react";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { apiClient } from "@/lib/api-client";
import { packagesApi } from "@/lib/api/packages";
import { useAuthStore } from "@/stores/auth-store";
import { RefundPackageModal } from "@/components/packages/RefundPackageModal";
import { toast } from "sonner";
import type { PackageSale } from "@/types/package";

type BillItem = {
  id: string;
  item_type: string;
  package_sale_id?: string | null;
};

type Bill = {
  id: string;
  invoice_number: string | null;
  rounded_total: number; // paise
  customer_name?: string | null;
  status: string;
  items?: BillItem[];
};

export function BillDetail({ id }: { id: string }) {
  const [bill, setBill] = React.useState<Bill | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const [refundSale, setRefundSale] = React.useState<PackageSale | null>(null);
  const { hasPermission } = useAuthStore();

  React.useEffect(() => {
    let cancelled = false;
    apiClient
      .get<Bill>(`/pos/bills/${id}`)
      .then(({ data }) => {
        if (!cancelled) setBill(data);
      })
      .catch((e: unknown) => {
        if (!cancelled)
          setError(
            e instanceof Error ? e.message : "Failed to load"
          );
      });
    return () => {
      cancelled = true;
    };
  }, [id]);

  if (error) return <div className="p-6 text-danger-fg">{error}</div>;
  if (!bill) {
    return (
      <div className="p-6 flex flex-col gap-3">
        <Skeleton shape="text" width="60%" />
        <Skeleton shape="text" width="40%" />
        <Skeleton shape="row" />
        <Skeleton shape="row" />
      </div>
    );
  }

  const packageSaleItem = bill.items?.find(
    (i) => i.item_type === "package_sale_line" && i.package_sale_id
  );

  function handleRefundPackageClick() {
    if (!packageSaleItem?.package_sale_id) return;
    packagesApi
      .getSale(packageSaleItem.package_sale_id)
      .then((r) => setRefundSale(r.data))
      .catch(() => toast.error("Failed to load package"));
  }

  return (
    <div className="p-6 flex flex-col gap-2">
      <h2 className="text-heading-md text-text-primary">{bill.invoice_number}</h2>
      {bill.customer_name && (
        <p className="text-body-sm text-text-secondary">{bill.customer_name}</p>
      )}
      <p className="text-money-lg text-text-primary tabular">
        ₹{(bill.rounded_total / 100).toFixed(2)}
      </p>
      <p className="text-body-sm text-text-secondary capitalize">{bill.status}</p>

      {/* Package refund action */}
      {hasPermission("packages", "refund") && packageSaleItem && (
        <div className="mt-2">
          <Button variant="outline" size="sm" onClick={handleRefundPackageClick}>
            Refund Package
          </Button>
        </div>
      )}

      <RefundPackageModal
        open={!!refundSale}
        sale={refundSale}
        onClose={() => setRefundSale(null)}
        onRefunded={() => {
          setRefundSale(null);
          // Refresh bill data to reflect new status
          apiClient
            .get<Bill>(`/pos/bills/${id}`)
            .then(({ data }) => setBill(data))
            .catch(() => {});
        }}
      />
    </div>
  );
}
