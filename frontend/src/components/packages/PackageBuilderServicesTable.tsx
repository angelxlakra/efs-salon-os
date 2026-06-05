"use client";
import { Lock, Unlock, Trash2, Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type { EntitlementType } from "@/types/package";

interface LineItem {
  service_id: string;
  service_name: string; // display only
  quantity: number;
  unit_price_paise: number;
  locked: boolean;
  display_order: number;
}

interface Props {
  items: LineItem[];
  onChange: (items: LineItem[]) => void;
  entitlementType: EntitlementType;
}

function paise(rupees: string): number {
  return Math.round(parseFloat(rupees || "0") * 100);
}

function rupees(p: number): string {
  return (p / 100).toFixed(2);
}

// Shared base classes for inline inputs — bypasses the wrapper div from the full Input component
const inlineInput =
  "h-7 rounded-md border border-border-default bg-surface-card px-2 text-sm text-text-primary placeholder:text-text-muted " +
  "focus-visible:outline-none focus-visible:border-accent focus-visible:shadow-[var(--shadow-focus)] " +
  "disabled:opacity-50 disabled:cursor-not-allowed w-full";

export function PackageBuilderServicesTable({ items, onChange, entitlementType }: Props) {
  const isUnlimited = entitlementType === "unlimited";

  function update(index: number, patch: Partial<LineItem>) {
    const next = items.map((item, i) => (i === index ? { ...item, ...patch } : item));
    onChange(next);
  }

  function remove(index: number) {
    onChange(items.filter((_, i) => i !== index));
  }

  function addRow() {
    onChange([
      ...items,
      {
        service_id: "",
        service_name: "",
        quantity: 1,
        unit_price_paise: 0,
        locked: false,
        display_order: items.length,
      },
    ]);
  }

  const total = items.reduce(
    (s, i) => s + i.unit_price_paise * (isUnlimited ? 1 : i.quantity),
    0
  );

  return (
    <div className="space-y-2">
      <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
        Included services
      </p>

      {/* Header */}
      <div
        className={cn(
          "grid gap-2 text-[10px] font-medium text-muted-foreground uppercase",
          isUnlimited
            ? "grid-cols-[1fr_100px_40px_32px]"
            : "grid-cols-[1fr_48px_100px_40px_32px]"
        )}
      >
        <span>Service</span>
        {!isUnlimited && <span className="text-center">Qty</span>}
        <span className="text-right">Price (₹)</span>
        <span className="text-center">Lock</span>
        <span />
      </div>

      {/* Rows */}
      {items.map((item, i) => (
        <div
          key={i}
          className={cn(
            "grid gap-2 items-center rounded-lg border px-2 py-1.5",
            isUnlimited
              ? "grid-cols-[1fr_100px_40px_32px]"
              : "grid-cols-[1fr_48px_100px_40px_32px]",
            item.locked
              ? "bg-amber-50 dark:bg-amber-950/20 border-amber-200 dark:border-amber-800"
              : "border-border"
          )}
        >
          {/* Service name */}
          <input
            value={item.service_name}
            onChange={(e) => update(i, { service_name: e.target.value })}
            placeholder="Service name"
            className={cn(inlineInput, "border-0 bg-transparent p-0 focus-visible:shadow-none focus-visible:border-transparent")}
          />

          {/* Qty (hidden for unlimited) */}
          {!isUnlimited && (
            <input
              type="number"
              min={1}
              value={item.quantity}
              onChange={(e) =>
                update(i, { quantity: parseInt(e.target.value) || 1 })
              }
              className={cn(inlineInput, "text-center")}
            />
          )}

          {/* Price */}
          <input
            type="number"
            step="0.01"
            min={0}
            value={rupees(item.unit_price_paise)}
            onChange={(e) =>
              update(i, { unit_price_paise: paise(e.target.value) })
            }
            className={cn(inlineInput, "text-right")}
          />

          {/* Lock toggle */}
          <button
            type="button"
            onClick={() => update(i, { locked: !item.locked })}
            className="flex items-center justify-center h-7 w-7 rounded text-muted-foreground hover:text-foreground"
          >
            {item.locked ? <Lock size={14} /> : <Unlock size={14} />}
          </button>

          {/* Delete */}
          <button
            type="button"
            onClick={() => remove(i)}
            className="flex items-center justify-center h-7 w-7 rounded text-muted-foreground hover:text-danger-fg"
          >
            <Trash2 size={14} />
          </button>
        </div>
      ))}

      <Button
        type="button"
        variant="outline"
        size="sm"
        onClick={addRow}
        className="w-full"
      >
        <Plus size={14} className="mr-1" /> Add service
      </Button>

      {/* Total */}
      <div className="flex justify-between items-center pt-2 border-t border-border-subtle">
        <span className="text-sm text-muted-foreground">Package MRP</span>
        <span className="text-sm font-semibold tabular-nums">
          ₹{(total / 100).toFixed(2)}
        </span>
      </div>
    </div>
  );
}
