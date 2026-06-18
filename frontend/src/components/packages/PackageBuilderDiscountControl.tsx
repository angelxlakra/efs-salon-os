"use client";
import { useId } from "react";
import { cn } from "@/lib/utils";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import type { DiscountMode } from "@/types/package";

interface Discount {
  mode: DiscountMode;
  value: string;
}

interface Props {
  /** Chargeable total (paise) the discount applies to. */
  totalPaise: number;
  discount: Discount | undefined;
  onChange: (discount: Discount | undefined) => void;
}

const FIELDS: Array<{ mode: DiscountMode; label: string; step: string }> = [
  { mode: "pct", label: "% off", step: "0.1" },
  { mode: "flat", label: "₹ off", step: "0.01" },
  { mode: "final", label: "Final price", step: "0.01" },
];

// Format a paise amount as a rupee string without trailing zeros ("900", "12.5")
function paiseToRupeeString(paise: number): string {
  return String(Math.round(paise) / 100);
}

function trimNumber(n: number): string {
  return String(Math.round(n * 100) / 100);
}

export function PackageBuilderDiscountControl({
  totalPaise,
  discount,
  onChange,
}: Props) {
  const idPrefix = useId();

  // The last-edited field is authoritative (saved as-is); the other two are
  // derived from it and the current package total.
  function derivedValue(mode: DiscountMode): string {
    if (!discount?.value) return "";
    if (discount.mode === mode) return discount.value;
    if (totalPaise <= 0) return "";

    const v = parseFloat(discount.value);
    if (!Number.isFinite(v)) return "";

    let discountPaise: number;
    if (discount.mode === "pct") {
      discountPaise = Math.round((totalPaise * v) / 100);
    } else if (discount.mode === "flat") {
      discountPaise = Math.round(v * 100);
    } else {
      discountPaise = totalPaise - Math.round(v * 100);
    }

    if (mode === "pct") return trimNumber((discountPaise / totalPaise) * 100);
    if (mode === "flat") return paiseToRupeeString(discountPaise);
    return paiseToRupeeString(totalPaise - discountPaise);
  }

  function setValue(mode: DiscountMode, v: string) {
    onChange(v ? { mode, value: v } : undefined);
  }

  return (
    <div className="space-y-1.5">
      <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
        Package discount
      </p>

      <div className="grid grid-cols-3 gap-2">
        {FIELDS.map((f) => (
          <div key={f.mode} className="space-y-1">
            <Label
              htmlFor={`${idPrefix}-${f.mode}`}
              className={cn(
                "text-xs",
                discount?.mode === f.mode && discount.value
                  ? "text-accent-foreground font-medium"
                  : "text-muted-foreground"
              )}
            >
              {f.label}
            </Label>
            <Input
              id={`${idPrefix}-${f.mode}`}
              type="number"
              step={f.step}
              min={0}
              value={derivedValue(f.mode)}
              onChange={(e) => setValue(f.mode, e.target.value)}
              size="sm"
              leadingAddon={f.mode !== "pct" ? "₹" : undefined}
              trailingAddon={f.mode === "pct" ? "%" : undefined}
            />
          </div>
        ))}
      </div>
    </div>
  );
}
