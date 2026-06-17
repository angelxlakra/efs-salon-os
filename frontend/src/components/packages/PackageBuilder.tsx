"use client";
// Package Builder v2 — an entitlement-block stack. Replaces the old flat
// services-table + entitlement-matrix builder. Left rail configures the
// package envelope (name, rules, status); the right column is the block stack
// with a pricing card driven by the pure helpers in lib/packages/block-pricing.

import { useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { Loader2, ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Switch } from "@/components/ui/switch";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { packagesApi } from "@/lib/api/packages";
import { BlockCard } from "./blocks/BlockCard";
import { AddBlockPalette, makeBlock } from "./blocks/AddBlockPalette";
import { PackageBuilderDiscountControl } from "./PackageBuilderDiscountControl";
import {
  bonusOf,
  chargeableOf,
  priceOf,
  savingsFraction,
  totalValueOf,
} from "@/lib/packages/block-pricing";
import type {
  BlockKind,
  DiscountMode,
  PackageBlock,
  PackageDefinitionStatus,
  Shareability,
} from "@/types/package";

export interface PackageBuilderInitial {
  name: string;
  description?: string;
  validity_days: number;
  cancellation_fee_pct: string;
  shareability: Shareability;
  auto_apply: boolean;
  status?: PackageDefinitionStatus;
  discount?: { mode: DiscountMode; value: string };
  blocks: PackageBlock[];
}

interface Props {
  initial?: PackageBuilderInitial;
  definitionId?: string;
  onSaved?: (id: string) => void;
}

// The backend pricing engine reads discount.value as PAISE for flat/final
// modes (percentage for pct). The UI collects rupees — convert before sending.
export function toDiscountPayload(
  discount: { mode: DiscountMode; value: string } | undefined
): { mode: DiscountMode; value: string } | undefined {
  if (!discount?.value) return undefined;
  if (discount.mode === "pct") return discount;
  const rupees = parseFloat(discount.value);
  if (!Number.isFinite(rupees)) return undefined;
  return { mode: discount.mode, value: String(Math.round(rupees * 100)) };
}

const overline =
  "text-[11px] font-semibold uppercase tracking-[0.06em] text-text-muted";
const fmt = (paise: number) => "₹" + Math.round(paise / 100).toLocaleString("en-IN");

export function PackageBuilder({ initial, definitionId, onSaved }: Props) {
  const router = useRouter();
  const [name, setName] = useState(initial?.name ?? "");
  const [description, setDescription] = useState(initial?.description ?? "");
  const [validityDays, setValidityDays] = useState(
    String(initial?.validity_days ?? "90")
  );
  const [feePct, setFeePct] = useState(initial?.cancellation_fee_pct ?? "20");
  const [shareability, setShareability] = useState<Shareability>(
    initial?.shareability ?? "owner_only"
  );
  const [autoApply, setAutoApply] = useState(initial?.auto_apply ?? true);
  const [status, setStatus] = useState<PackageDefinitionStatus>(
    initial?.status ?? "draft"
  );
  const [blocks, setBlocks] = useState<PackageBlock[]>(initial?.blocks ?? []);
  const [discount, setDiscount] = useState<
    { mode: DiscountMode; value: string } | undefined
  >(initial?.discount);
  const [saving, setSaving] = useState(false);
  const [savedId, setSavedId] = useState<string | null>(definitionId ?? null);

  const chargeable = chargeableOf(blocks);
  const bonus = bonusOf(blocks);
  const totalValue = totalValueOf(blocks);
  const price = priceOf(blocks, discount);
  const savingsPct = Math.round(savingsFraction(blocks, discount) * 100);

  function addBlock(kind: BlockKind) {
    setBlocks((prev) => [...prev, makeBlock(kind)]);
  }
  function updateBlock(id: string, next: PackageBlock) {
    setBlocks((prev) => prev.map((b) => (b.id === id ? next : b)));
  }
  function removeBlock(id: string) {
    setBlocks((prev) => prev.filter((b) => b.id !== id));
  }

  function buildPayload() {
    return {
      name: name.trim(),
      description: description || undefined,
      validity_days: parseInt(validityDays) || 90,
      cancellation_fee_pct: feePct || "20",
      shareability,
      auto_apply: autoApply,
      blocks,
      final_price_paise: price,
      discount: toDiscountPayload(discount),
    };
  }

  async function persist(): Promise<string | null> {
    const payload = buildPayload();
    const res = savedId
      ? await packagesApi.updateDefinition(savedId, payload)
      : await packagesApi.createDefinition(payload);
    const id = res.data.id;
    setSavedId(id);
    onSaved?.(id);
    return id;
  }

  async function handleSaveDraft() {
    if (!name.trim()) return toast.error("Package name is required");
    setSaving(true);
    try {
      await persist();
      toast.success("Draft saved");
    } catch {
      toast.error("Failed to save");
    } finally {
      setSaving(false);
    }
  }

  async function handlePublish() {
    if (status === "published" && savedId) {
      router.push("/dashboard/pos");
      return;
    }
    if (!name.trim()) return toast.error("Package name is required");
    if (blocks.length === 0) return toast.error("Add at least one block");
    setSaving(true);
    try {
      const id = await persist();
      if (!id) throw new Error("no id");
      await packagesApi.publishDefinition(id);
      setStatus("published");
      toast.success("Published to POS");
    } catch {
      toast.error("Failed to publish");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="mx-auto max-w-[1240px] p-[22px]">
      <div className="grid grid-cols-[320px_1fr] gap-5">
        {/* ── Left rail ── */}
        <aside className="space-y-3.5">
          {/* Package */}
          <section className="space-y-3 rounded-[10px] border border-border-default bg-surface-card p-4">
            <p className={overline}>Package</p>
            <Input
              placeholder="e.g. Bridal Radiance — 3 Months"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
            <Textarea
              placeholder="What's included…"
              rows={3}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
          </section>

          {/* Rules */}
          <section className="space-y-3 rounded-[10px] border border-border-default bg-surface-card p-4">
            <p className={overline}>Rules</p>
            <div className="grid grid-cols-2 gap-2">
              <label className="space-y-1">
                <span className="text-[12px] text-text-secondary">Validity (days)</span>
                <Input
                  type="number"
                  min={1}
                  value={validityDays}
                  onChange={(e) => setValidityDays(e.target.value)}
                />
              </label>
              <label className="space-y-1">
                <span className="text-[12px] text-text-secondary">Cancellation fee %</span>
                <Input
                  type="number"
                  min={0}
                  max={100}
                  value={feePct}
                  onChange={(e) => setFeePct(e.target.value)}
                />
              </label>
            </div>
            <div className="space-y-1.5">
              <span className="text-[12px] text-text-secondary">Who can redeem</span>
              <div className="inline-flex w-full rounded-md border border-border-default bg-surface-row p-[2px]">
                {(
                  [
                    ["owner_only", "Personal"],
                    ["shared", "Shared"],
                  ] as const
                ).map(([val, label]) => (
                  <button
                    key={val}
                    type="button"
                    onClick={() => setShareability(val)}
                    className={cn(
                      "flex-1 rounded-[5px] py-1 text-[12px] font-medium transition-colors",
                      shareability === val
                        ? "bg-surface-card text-text-primary shadow-[var(--shadow-xs)]"
                        : "text-text-muted hover:text-text-secondary"
                    )}
                  >
                    {label}
                  </button>
                ))}
              </div>
              <p className="text-[11px] text-text-muted">
                {shareability === "owner_only"
                  ? "Only the buyer can redeem this package."
                  : "Anyone the buyer shares it with can redeem."}
              </p>
            </div>
            <div className="flex items-center justify-between pt-0.5">
              <div>
                <p className="text-[13px] font-medium text-text-primary">Auto-apply</p>
                <p className="text-[11px] text-text-muted">
                  Redeem automatically when only one fits
                </p>
              </div>
              <Switch checked={autoApply} onCheckedChange={setAutoApply} />
            </div>
          </section>

          {/* Status */}
          <section className="space-y-3 rounded-[10px] border border-border-default bg-surface-card p-4">
            <div className="flex items-center justify-between">
              <p className={overline}>Status</p>
              <Badge tone={status === "published" ? "success" : "neutral"} size="sm">
                {status === "published" ? "Published" : "Draft"}
              </Badge>
            </div>
            <Button onClick={handlePublish} disabled={saving} className="w-full">
              {saving && <Loader2 size={15} className="mr-2 animate-spin" />}
              {status === "published" ? (
                <>
                  View in POS <ArrowRight size={15} className="ml-1" />
                </>
              ) : (
                "Publish to POS"
              )}
            </Button>
            {status !== "published" && (
              <button
                type="button"
                onClick={handleSaveDraft}
                disabled={saving}
                className="w-full text-center text-[12px] font-medium text-text-muted hover:text-text-secondary"
              >
                Save as draft
              </button>
            )}
            <p className="text-[11px] leading-snug text-text-muted">
              Publishing makes it sellable. Existing sales always keep the snapshot
              they were sold with.
            </p>
          </section>
        </aside>

        {/* ── Right column: contents ── */}
        <section className="space-y-3">
          <div className="flex items-center justify-between">
            <p className={overline}>
              Contents · {blocks.length} block{blocks.length === 1 ? "" : "s"}
            </p>
            <p className="text-[12px] text-text-muted">
              Stack any mix of entitlements — fixed, choice, unlimited, pool, credit.
            </p>
          </div>

          {blocks.map((b) => (
            <BlockCard
              key={b.id}
              block={b}
              onChange={(next) => updateBlock(b.id, next)}
              onRemove={() => removeBlock(b.id)}
            />
          ))}

          <AddBlockPalette onAdd={addBlock} />

          {/* Pricing card */}
          <div className="space-y-3 rounded-[10px] border border-border-default bg-surface-card p-4">
            <div className="flex items-center justify-between text-[13px]">
              <span className="text-text-secondary">Total value to customer</span>
              <span className="font-semibold tabular-nums text-text-primary">
                {fmt(totalValue)}
              </span>
            </div>
            {bonus > 0 && (
              <div className="flex items-center justify-between text-[12px] text-gold-fg">
                <span>includes free bonuses (not charged)</span>
                <span className="tabular-nums">{fmt(bonus)}</span>
              </div>
            )}

            <PackageBuilderDiscountControl
              totalPaise={chargeable}
              discount={discount}
              onChange={setDiscount}
            />

            <div className="border-t border-border-subtle pt-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="text-[13px] text-text-secondary">Sells at</span>
                  {savingsPct > 0 && (
                    <span className="rounded-full bg-gold-soft px-2 py-0.5 text-[11px] font-medium text-gold-fg">
                      Customer saves {savingsPct}%
                    </span>
                  )}
                </div>
                <span className="text-[24px] font-bold tabular-nums text-accent">
                  {fmt(price)}
                </span>
              </div>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
