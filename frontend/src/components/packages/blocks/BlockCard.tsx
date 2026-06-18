"use client";
// One entitlement block in the builder's right-column stack: a header strip
// (type chip · auto-summary · value · bonus toggle · remove) over a body whose
// shape depends on the block kind.

import { Plus, X, Star } from "lucide-react";
import { cn } from "@/lib/utils";
import { ServicePicker } from "@/components/packages/ServicePicker";
import { CountCell, MoneyCell } from "./numeric-cells";
import { BLOCK_META } from "./block-meta";
import { blockSummary, blockValue, isEstimated } from "@/lib/packages/block-pricing";
import type {
  PackageBlock,
  ChooseAt,
  CreditScope,
  ItemsRow,
  ChoiceRow,
  PoolRow,
  UnlimitedRow,
} from "@/types/package";

interface Props {
  block: PackageBlock;
  onChange: (next: PackageBlock) => void;
  onRemove: () => void;
}

const fmt = (paise: number) => "₹" + Math.round(paise / 100).toLocaleString("en-IN");

const overline =
  "text-[11px] font-semibold uppercase tracking-[0.06em] text-text-muted";
const colHead = "text-[10px] font-semibold uppercase tracking-[0.05em] text-text-muted";

const addRowBtn =
  "flex h-[30px] w-full items-center justify-center gap-1 rounded-md border border-dashed " +
  "border-border-default text-[12px] font-medium text-text-muted transition-colors " +
  "hover:border-accent hover:text-accent";

const removeRowBtn =
  "flex h-[30px] w-6 items-center justify-center rounded text-text-muted hover:text-danger-fg";

// ── Segmented control (track + active white pill) ──────────────────────────
function Segmented<T extends string>({
  value,
  onChange,
  options,
}: {
  value: T;
  onChange: (v: T) => void;
  options: Array<{ value: T; label: string }>;
}) {
  return (
    <div className="inline-flex rounded-md border border-border-default bg-surface-row p-[2px]">
      {options.map((o) => (
        <button
          key={o.value}
          type="button"
          onClick={() => onChange(o.value)}
          className={cn(
            "rounded-[5px] px-2.5 py-1 text-[12px] font-medium transition-colors",
            value === o.value
              ? "bg-surface-card text-text-primary shadow-[var(--shadow-xs)]"
              : "text-text-muted hover:text-text-secondary"
          )}
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}

export function BlockCard({ block, onChange, onRemove }: Props) {
  const meta = BLOCK_META[block.kind];
  const Icon = meta.icon;
  const value = blockValue(block);

  // Immutable row helpers (typed per kind at the call sites below).
  function setRows<R>(rows: R[]) {
    onChange({ ...block, rows } as PackageBlock);
  }

  function picked(sel: { service_id: string; service_name: string; base_price_paise: number } | null) {
    return sel;
  }

  return (
    <div className="overflow-hidden rounded-[10px] border border-border-default bg-surface-card">
      {/* Header strip */}
      <div className="flex items-center gap-2.5 border-b border-border-subtle bg-surface-row px-3 py-[9px]">
        <span
          className={cn(
            "inline-flex items-center gap-1 rounded-full px-2 py-[2px] text-[10.5px] font-semibold uppercase tracking-wide",
            meta.chip
          )}
        >
          <Icon size={11} aria-hidden /> {meta.label}
        </span>
        <span className="min-w-0 flex-1 truncate text-[13px] font-semibold text-text-primary">
          {blockSummary(block)}
        </span>
        <span className="shrink-0 text-[12.5px] font-semibold tabular-nums text-text-secondary">
          {isEstimated(block) && value > 0 ? "≈ " : ""}
          {fmt(value)}
        </span>
        <button
          type="button"
          onClick={() => onChange({ ...block, bonus: !block.bonus })}
          className={cn(
            "inline-flex items-center gap-1 rounded-full border px-2 py-[3px] text-[11px] font-medium transition-colors",
            block.bonus
              ? "border-gold bg-gold-soft text-gold-fg"
              : "border-border-default text-text-muted hover:border-border-strong"
          )}
          aria-pressed={block.bonus}
        >
          {block.bonus ? <Star size={11} className="fill-current" /> : null}
          {block.bonus ? "Free bonus" : "Bonus?"}
        </button>
        <button
          type="button"
          onClick={onRemove}
          aria-label="Remove block"
          className="flex h-6 w-6 items-center justify-center rounded text-text-muted hover:text-danger-fg"
        >
          <X size={15} />
        </button>
      </div>

      {/* Body */}
      <div className="space-y-2 px-3 py-2.5">
        {/* ── Fixed items ── */}
        {block.kind === "items" && (
          <>
            {block.rows.length > 0 && (
              <div className="grid grid-cols-[1fr_60px_92px_24px] gap-2 px-0.5">
                <span className={colHead}>Service / Product</span>
                <span className={cn(colHead, "text-center")}>Qty</span>
                <span className={cn(colHead, "text-right")}>Price ₹</span>
                <span />
              </div>
            )}
            {block.rows.map((row, ri) => (
              <div key={ri} className="grid grid-cols-[1fr_60px_92px_24px] items-center gap-2">
                <ServicePicker
                  value={row.service_id || null}
                  onChange={(sel) => {
                    const s = picked(sel);
                    if (!s) return;
                    const rows = [...block.rows];
                    rows[ri] = {
                      ...rows[ri],
                      service_id: s.service_id,
                      service_name: s.service_name,
                      unit_price_paise: s.base_price_paise,
                    };
                    setRows<ItemsRow>(rows);
                  }}
                />
                <CountCell
                  aria-label="Quantity"
                  min={1}
                  value={row.quantity}
                  onCommit={(raw) => {
                    const rows = [...block.rows];
                    rows[ri] = { ...rows[ri], quantity: raw };
                    setRows<ItemsRow>(rows);
                  }}
                  onBlurEmpty={() => {
                    const rows = [...block.rows];
                    rows[ri] = { ...rows[ri], quantity: "1" };
                    setRows<ItemsRow>(rows);
                  }}
                  className="text-center"
                />
                <MoneyCell
                  aria-label="Price"
                  valuePaise={row.unit_price_paise}
                  onCommit={(paise) => {
                    const rows = [...block.rows];
                    rows[ri] = { ...rows[ri], unit_price_paise: paise };
                    setRows<ItemsRow>(rows);
                  }}
                />
                <button
                  type="button"
                  className={removeRowBtn}
                  aria-label="Remove row"
                  onClick={() => setRows<ItemsRow>(block.rows.filter((_, i) => i !== ri))}
                >
                  <X size={14} />
                </button>
              </div>
            ))}
            <button
              type="button"
              className={addRowBtn}
              onClick={() =>
                setRows<ItemsRow>([
                  ...block.rows,
                  { service_id: "", service_name: "", quantity: "1", unit_price_paise: 0 },
                ])
              }
            >
              <Plus size={14} /> Add service
            </button>
          </>
        )}

        {/* ── Choice group ── */}
        {block.kind === "choice" && (
          <>
            <div className="space-y-1.5">
              <div className="flex flex-wrap items-center gap-2 text-[13px] text-text-secondary">
                <span>{block.choose_at === "visit" ? "Total uses allowed" : "Customer picks"}</span>
                <CountCell
                  aria-label="Number of picks"
                  min={1}
                  value={block.picks}
                  onCommit={(raw) => onChange({ ...block, picks: raw })}
                  onBlurEmpty={() => onChange({ ...block, picks: "1" })}
                  className="w-14 text-center"
                />
                <span>
                  {block.choose_at === "visit"
                    ? `from the ${block.rows.length} options below —`
                    : "of the options below —"}
                </span>
                <Segmented<ChooseAt>
                  value={block.choose_at}
                  onChange={(v) => onChange({ ...block, choose_at: v })}
                  options={[
                    { value: "purchase", label: "locked at purchase" },
                    { value: "visit", label: "chosen each visit" },
                  ]}
                />
              </div>
              <p className="text-[11.5px] text-text-muted">
                {block.choose_at === "visit"
                  ? `Any option, up to ${parseInt(block.picks) || 0} time${
                      (parseInt(block.picks) || 0) === 1 ? "" : "s"
                    } total across all visits — a shared budget, used in any mix.`
                  : "The customer locks these specific options at purchase; each is usable once."}
              </p>
            </div>
            {block.rows.map((row, ri) => (
              <div key={ri} className="grid grid-cols-[1fr_92px_24px] items-center gap-2">
                <ServicePicker
                  value={row.service_id || null}
                  onChange={(sel) => {
                    const s = picked(sel);
                    if (!s) return;
                    const rows = [...block.rows];
                    rows[ri] = {
                      service_id: s.service_id,
                      service_name: s.service_name,
                      unit_price_paise: s.base_price_paise,
                    };
                    setRows<ChoiceRow>(rows);
                  }}
                />
                <MoneyCell
                  aria-label="Price"
                  valuePaise={row.unit_price_paise}
                  onCommit={(paise) => {
                    const rows = [...block.rows];
                    rows[ri] = { ...rows[ri], unit_price_paise: paise };
                    setRows<ChoiceRow>(rows);
                  }}
                />
                <button
                  type="button"
                  className={removeRowBtn}
                  aria-label="Remove option"
                  onClick={() => setRows<ChoiceRow>(block.rows.filter((_, i) => i !== ri))}
                >
                  <X size={14} />
                </button>
              </div>
            ))}
            <button
              type="button"
              className={addRowBtn}
              onClick={() =>
                setRows<ChoiceRow>([
                  ...block.rows,
                  { service_id: "", service_name: "", unit_price_paise: 0 },
                ])
              }
            >
              <Plus size={14} /> Add option
            </button>
          </>
        )}

        {/* ── Unlimited ── */}
        {block.kind === "unlimited" && (
          <>
            {block.rows.map((row, ri) => (
              <div key={ri} className="grid grid-cols-[1fr_24px] items-center gap-2">
                <ServicePicker
                  value={row.service_id || null}
                  onChange={(sel) => {
                    const s = picked(sel);
                    if (!s) return;
                    const rows = [...block.rows];
                    rows[ri] = { service_id: s.service_id, service_name: s.service_name };
                    setRows<UnlimitedRow>(rows);
                  }}
                />
                <button
                  type="button"
                  className={removeRowBtn}
                  aria-label="Remove service"
                  onClick={() => setRows<UnlimitedRow>(block.rows.filter((_, i) => i !== ri))}
                >
                  <X size={14} />
                </button>
              </div>
            ))}
            <button
              type="button"
              className={addRowBtn}
              onClick={() =>
                setRows<UnlimitedRow>([
                  ...block.rows,
                  { service_id: "", service_name: "" },
                ])
              }
            >
              <Plus size={14} /> Add service
            </button>
            <div className="grid grid-cols-2 gap-2 border-t border-dashed border-border-default pt-2.5">
              <label className="space-y-1">
                <span className={overline}>Assigned value for pricing (₹)</span>
                <MoneyCell
                  valuePaise={block.assigned_value_paise}
                  onCommit={(paise) => onChange({ ...block, assigned_value_paise: paise })}
                />
              </label>
              <label className="space-y-1">
                <span className={overline}>Fair-use cap per day</span>
                <CountCell
                  min={1}
                  placeholder="None"
                  value={block.daily_cap}
                  onCommit={(raw) => onChange({ ...block, daily_cap: raw })}
                  className="text-center"
                />
              </label>
            </div>
          </>
        )}

        {/* ── Session pool ── */}
        {block.kind === "pool" && (
          <>
            <div className="flex flex-wrap items-center gap-2 text-[13px] text-text-secondary">
              <span>A pool of</span>
              <CountCell
                aria-label="Number of sessions"
                min={1}
                value={block.sessions}
                onCommit={(raw) => onChange({ ...block, sessions: raw })}
                onBlurEmpty={() => onChange({ ...block, sessions: "1" })}
                className="w-16 text-center"
              />
              <span>sessions, spendable on any service below</span>
            </div>
            {block.rows.map((row, ri) => (
              <div key={ri} className="grid grid-cols-[1fr_92px_24px] items-center gap-2">
                <ServicePicker
                  value={row.service_id || null}
                  onChange={(sel) => {
                    const s = picked(sel);
                    if (!s) return;
                    const rows = [...block.rows];
                    rows[ri] = {
                      service_id: s.service_id,
                      service_name: s.service_name,
                      unit_price_paise: s.base_price_paise,
                    };
                    setRows<PoolRow>(rows);
                  }}
                />
                <MoneyCell
                  aria-label="Price"
                  valuePaise={row.unit_price_paise}
                  onCommit={(paise) => {
                    const rows = [...block.rows];
                    rows[ri] = { ...rows[ri], unit_price_paise: paise };
                    setRows<PoolRow>(rows);
                  }}
                />
                <button
                  type="button"
                  className={removeRowBtn}
                  aria-label="Remove option"
                  onClick={() => setRows<PoolRow>(block.rows.filter((_, i) => i !== ri))}
                >
                  <X size={14} />
                </button>
              </div>
            ))}
            <button
              type="button"
              className={addRowBtn}
              onClick={() =>
                setRows<PoolRow>([
                  ...block.rows,
                  { service_id: "", service_name: "", unit_price_paise: 0 },
                ])
              }
            >
              <Plus size={14} /> Add service
            </button>
          </>
        )}

        {/* ── Credit ── */}
        {block.kind === "credit" && (
          <div className="space-y-2.5">
            <label className="space-y-1">
              <span className={overline}>Credit amount (₹)</span>
              <MoneyCell
                valuePaise={block.amount_paise}
                onCommit={(paise) => onChange({ ...block, amount_paise: paise })}
                className="font-semibold"
              />
            </label>
            <div className="space-y-1">
              <span className={overline}>Spendable on</span>
              <div>
                <Segmented<CreditScope>
                  value={block.scope}
                  onChange={(v) => onChange({ ...block, scope: v })}
                  options={[
                    { value: "any", label: "Anything" },
                    { value: "services", label: "Services only" },
                    { value: "retail", label: "Retail only" },
                  ]}
                />
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
