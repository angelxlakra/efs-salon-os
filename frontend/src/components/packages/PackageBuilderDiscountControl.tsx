"use client";
import { cn } from "@/lib/utils";
import { Input } from "@/components/ui/input";
import type { DiscountMode } from "@/types/package";

interface Discount {
  mode: DiscountMode;
  value: string;
}

interface Props {
  items: Array<{ unit_price_paise: number; quantity: number; locked: boolean }>;
  discount: Discount | undefined;
  onChange: (discount: Discount | undefined) => void;
}

const MODES: Array<{ value: DiscountMode; label: string }> = [
  { value: "pct", label: "% off" },
  { value: "flat", label: "₹ off" },
  { value: "final", label: "Final" },
];

export function PackageBuilderDiscountControl({ discount, onChange }: Props) {
  const mode = discount?.mode ?? "pct";

  function setMode(m: DiscountMode) {
    onChange({ mode: m, value: discount?.value ?? "" });
  }

  function setValue(v: string) {
    if (!v) {
      onChange(undefined);
      return;
    }
    onChange({ mode, value: v });
  }

  return (
    <div className="space-y-1.5">
      <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
        Package discount
      </p>

      {/* Segmented control */}
      <div className="flex rounded-lg border border-border overflow-hidden">
        {MODES.map((m) => (
          <button
            key={m.value}
            type="button"
            onClick={() => setMode(m.value)}
            className={cn(
              "flex-1 py-1.5 text-xs font-medium transition-colors",
              mode === m.value
                ? "bg-accent text-accent-foreground"
                : "bg-surface-row text-muted-foreground hover:bg-surface-card"
            )}
          >
            {m.label}
          </button>
        ))}
      </div>

      {/* Value input */}
      <Input
        type="number"
        step={mode === "pct" ? "0.1" : "0.01"}
        min={0}
        value={discount?.value ?? ""}
        onChange={(e) => setValue(e.target.value)}
        placeholder={
          mode === "pct" ? "e.g. 10" : mode === "flat" ? "e.g. 200" : "e.g. 1500"
        }
        size="sm"
        leadingAddon={mode === "final" ? "₹" : undefined}
        trailingAddon={mode === "pct" ? "%" : undefined}
      />
    </div>
  );
}
