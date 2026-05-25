"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { BillDetailsDialog } from "@/components/bills/bill-details-dialog";

export default function BillInterceptedPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = React.use(params);
  const router = useRouter();

  return (
    <BillDetailsDialog
      billId={id}
      open
      onOpenChange={(open) => { if (!open) router.back(); }}
    />
  );
}
