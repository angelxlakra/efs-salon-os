"use client";

import * as React from "react";
import { Skeleton } from "@/components/ui/skeleton";

type Bill = {
  id: string;
  invoice_number: string;
  total_paise: number;
  customer_name?: string;
  status: string;
};

export function BillDetail({ id }: { id: string }) {
  const [bill, setBill] = React.useState<Bill | null>(null);
  const [error, setError] = React.useState<string | null>(null);

  React.useEffect(() => {
    let cancelled = false;
    fetch(`/api/pos/bills/${id}`)
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`))))
      .then((data: Bill) => {
        if (!cancelled) setBill(data);
      })
      .catch((e) => {
        if (!cancelled) setError(e instanceof Error ? e.message : "Failed to load");
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

  return (
    <div className="p-6 flex flex-col gap-2">
      <h2 className="text-heading-md text-text-primary">{bill.invoice_number}</h2>
      {bill.customer_name && (
        <p className="text-body-sm text-text-secondary">{bill.customer_name}</p>
      )}
      <p className="text-money-lg text-text-primary tabular">
        ₹{(bill.total_paise / 100).toFixed(2)}
      </p>
      <p className="text-body-sm text-text-secondary capitalize">{bill.status}</p>
    </div>
  );
}
