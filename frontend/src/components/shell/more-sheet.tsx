"use client";

import * as React from "react";
import Link from "next/link";

// Placeholder — T17 replaces with full Sheet UI.
export function MoreSheet({ open, onOpenChange }: { open: boolean; onOpenChange: (next: boolean) => void }) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-40 bg-surface-overlay" onClick={() => onOpenChange(false)}>
      <div className="absolute bottom-0 inset-x-0 bg-surface-card p-4 rounded-t-lg" onClick={(e) => e.stopPropagation()}>
        <Link href="/dashboard/customers">Customers</Link>
        <Link href="/dashboard/inventory" className="ml-2">Inventory</Link>
      </div>
    </div>
  );
}
