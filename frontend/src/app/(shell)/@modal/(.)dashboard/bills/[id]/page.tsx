"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import {
  Dialog,
  DialogContent,
  DialogTitle,
} from "@/components/ui/dialog";
import { BillDetail } from "@/components/bills/bill-detail";

export default function BillInterceptedPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = React.use(params);
  const router = useRouter();
  return (
    <Dialog open onOpenChange={(open) => (open ? null : router.back())}>
      <DialogContent size="md">
        <DialogTitle className="sr-only">Bill detail</DialogTitle>
        <BillDetail id={id} />
      </DialogContent>
    </Dialog>
  );
}
