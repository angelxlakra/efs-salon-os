"use client";
import { cn } from "@/lib/utils";
import { Package } from "lucide-react";

interface BillItemLike {
  id: string;
  item_name: string;
  quantity: number;
  base_price: number;  // paise
  line_total: number;  // paise
  item_type: string;
}

interface Props {
  item: BillItemLike;
  className?: string;
}

/** Bill line for item_type='package_sale_line'. Navy left-rail = paid now. */
export function PackageSaleLine({ item, className }: Props) {
  return (
    <div
      className={cn(
        "flex items-start gap-3 px-3 py-2.5 rounded-lg border border-border bg-card",
        className
      )}
      style={{ borderLeftWidth: "3px", borderLeftColor: "#0F7B83" }}
    >
      <Package size={16} className="mt-0.5 text-muted-foreground shrink-0" />
      <div className="flex-1 min-w-0">
        <div className="flex items-start justify-between gap-2">
          <p className="text-sm font-medium leading-tight truncate">{item.item_name}</p>
          <p className="text-sm font-semibold tabular-nums shrink-0">
            ₹{(item.line_total / 100).toFixed(2)}
          </p>
        </div>
        <p className="text-xs text-muted-foreground mt-0.5">
          Package sale · {item.quantity} × ₹{(item.base_price / 100).toFixed(2)}
        </p>
      </div>
    </div>
  );
}
