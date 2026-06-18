"use client";
// Screen 2 — Configure & Sell. Binds the package to the selected customer,
// resolves purchase-time choices, previews expiry, and drops ONE package line
// into the existing cart (cart mechanics unchanged).

import { useMemo, useState } from "react";
import { Check } from "lucide-react";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { useCartStore } from "@/stores/cart-store";
import { BLOCK_META } from "./blocks/block-meta";
import { blockSummary, totalValueOf } from "@/lib/packages/block-pricing";
import type { PackageDefinition, PackageBlock } from "@/types/package";

interface Props {
  pkg: PackageDefinition | null;
  open: boolean;
  onClose: () => void;
}

const fmt = (paise: number) => "₹" + Math.round(paise / 100).toLocaleString("en-IN");

function expiryLabel(validityDays: number): string {
  const d = new Date();
  d.setDate(d.getDate() + validityDays);
  return d.toLocaleDateString("en-IN", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

/** Purchase-time choice blocks the seller must resolve before adding to cart. */
function purchaseChoices(blocks: PackageBlock[]): Array<{ index: number; block: Extract<PackageBlock, { kind: "choice" }> }> {
  return blocks
    .map((block, index) => ({ index, block }))
    .filter(
      (e): e is { index: number; block: Extract<PackageBlock, { kind: "choice" }> } =>
        e.block.kind === "choice" && e.block.choose_at === "purchase"
    );
}

export function ConfigureSellSheet({ pkg, open, onClose }: Props) {
  const addItem = useCartStore((s) => s.addItem);
  const customerName = useCartStore((s) => s.customerName);
  // choices[blockIndex] = selected service_ids
  const [choices, setChoices] = useState<Record<number, string[]>>({});

  const blocks = useMemo<PackageBlock[]>(() => pkg?.blocks ?? [], [pkg]);
  const pickers = useMemo(() => purchaseChoices(blocks), [blocks]);

  const worth = totalValueOf(blocks);
  const price = pkg?.final_price_paise ?? 0;

  const allComplete = pickers.every(
    ({ index, block }) => (choices[index]?.length ?? 0) === (parseInt(block.picks) || 0)
  );

  function toggle(blockIndex: number, serviceId: string, picks: number) {
    setChoices((prev) => {
      const arr = [...(prev[blockIndex] ?? [])];
      const at = arr.indexOf(serviceId);
      if (at >= 0) arr.splice(at, 1);
      else if (arr.length < picks) arr.push(serviceId);
      else if (picks === 1) {
        arr.length = 0;
        arr.push(serviceId);
      }
      return { ...prev, [blockIndex]: arr };
    });
  }

  function handleAdd() {
    if (!pkg || !allComplete) return;
    const locked = pickers.flatMap(({ index, block }) =>
      (choices[index] ?? []).map((sid) => ({
        service_id: sid,
        service_name: block.rows.find((r) => r.service_id === sid)?.service_name ?? "",
      }))
    );
    addItem({
      kind: "package_sale",
      isProduct: false,
      packageDefinitionId: pkg.id,
      packageName: pkg.name,
      serviceName: pkg.name,
      lockedChoices: locked,
      expiresLabel: `expires ${expiryLabel(pkg.validity_days)}`,
      quantity: 1,
      unitPrice: price,
      discount: 0,
      taxRate: 0,
    });
    setChoices({});
    onClose();
  }

  return (
    <Sheet open={open} onOpenChange={(o) => !o && onClose()}>
      <SheetContent side="right" className="w-[440px] sm:max-w-[440px] overflow-y-auto">
        {pkg && (
          <>
            <SheetHeader className="space-y-2">
              <p className="text-[11px] font-semibold uppercase tracking-[0.06em] text-text-muted">
                Configure & sell
              </p>
              <SheetTitle className="font-serif text-[23px] font-normal leading-tight">
                {pkg.name}
              </SheetTitle>
              <div className="flex flex-wrap gap-1.5">
                <span className="rounded-full bg-surface-row px-2 py-0.5 text-[11px] font-medium text-text-secondary">
                  For {customerName ?? "customer"}
                </span>
                <span className="rounded-full bg-surface-row px-2 py-0.5 text-[11px] font-medium text-text-secondary">
                  Valid till {expiryLabel(pkg.validity_days)}
                </span>
                <span className="rounded-full bg-surface-row px-2 py-0.5 text-[11px] font-medium text-text-secondary">
                  {pkg.shareability === "shared" ? "Shareable" : "Personal"}
                </span>
              </div>
            </SheetHeader>

            <div className="space-y-2.5 px-4 py-4">
              {blocks.map((block, bi) => {
                const meta = BLOCK_META[block.kind];
                const Icon = meta.icon;
                const isPicker = block.kind === "choice" && block.choose_at === "purchase";
                const sel = choices[bi] ?? [];
                const picks = block.kind === "choice" ? parseInt(block.picks) || 0 : 0;
                const complete = sel.length === picks;

                let note = "";
                if (block.kind === "choice" && block.choose_at === "visit")
                  note = "Customer chooses fresh at each visit — nothing to lock now.";
                if (block.kind === "unlimited")
                  note =
                    "No configuration — usable on every visit" +
                    (block.daily_cap ? ` (max ${block.daily_cap}/day).` : ".");
                if (block.bonus) note = (note ? note + " " : "") + "Included free — not charged.";

                return (
                  <div
                    key={block.id}
                    className="rounded-[10px] border border-border-default bg-surface-card p-3"
                  >
                    <div className="flex items-center gap-2">
                      <span
                        className={cn(
                          "inline-flex items-center gap-1 rounded-full px-2 py-[2px] text-[10.5px] font-semibold uppercase tracking-wide",
                          meta.chip
                        )}
                      >
                        <Icon size={11} aria-hidden /> {meta.label}
                      </span>
                      <span className="min-w-0 flex-1 truncate text-[13px] font-medium text-text-primary">
                        {blockSummary(block)}
                      </span>
                    </div>

                    {isPicker && block.kind === "choice" && (
                      <div className="mt-2.5 space-y-1.5">
                        <p
                          className={cn(
                            "text-[12px] font-medium",
                            complete ? "text-success-fg" : "text-warning-fg"
                          )}
                        >
                          {sel.length} of {picks} selected
                        </p>
                        {block.rows.map((row) => {
                          const on = sel.includes(row.service_id);
                          return (
                            <button
                              key={row.service_id}
                              type="button"
                              onClick={() => toggle(bi, row.service_id, picks)}
                              className={cn(
                                "flex w-full items-center gap-2 rounded-md border px-2.5 py-2 text-left transition-colors",
                                on
                                  ? "border-accent bg-accent-bg-soft"
                                  : "border-border-default hover:border-border-strong"
                              )}
                            >
                              <span
                                className={cn(
                                  "flex h-4 w-4 items-center justify-center rounded-[4px] border",
                                  on ? "border-accent bg-accent text-accent-fg" : "border-border-strong"
                                )}
                              >
                                {on && <Check size={11} />}
                              </span>
                              <span className="flex-1 text-[13px] text-text-primary">
                                {row.service_name}
                              </span>
                              <span className="text-[12px] tabular-nums text-text-muted">
                                {fmt(row.unit_price_paise)}
                              </span>
                            </button>
                          );
                        })}
                      </div>
                    )}

                    {!isPicker && note && (
                      <p className="mt-2 text-[12px] italic text-text-muted">{note}</p>
                    )}
                  </div>
                );
              })}
            </div>

            <div className="space-y-3 border-t border-border-subtle px-4 py-4">
              <div className="flex items-center justify-between">
                {worth > price ? (
                  <span className="text-[13px] text-text-muted line-through">{fmt(worth)}</span>
                ) : (
                  <span />
                )}
                <span className="text-[20px] font-bold tabular-nums text-accent">
                  {fmt(price)}
                </span>
              </div>
              <Button onClick={handleAdd} disabled={!allComplete} className="w-full">
                Add to cart — one package line
              </Button>
              {!allComplete && (
                <p className="text-center text-[12px] text-text-muted">
                  Pick the remaining options to continue
                </p>
              )}
            </div>
          </>
        )}
      </SheetContent>
    </Sheet>
  );
}
