"use client";
// Five dashed tiles that append a fresh block of the chosen kind.

import { cn } from "@/lib/utils";
import { BLOCK_META, BLOCK_ORDER } from "./block-meta";
import type { BlockKind, PackageBlock } from "@/types/package";

let seq = 0;
const nextId = () => `blk-${Date.now().toString(36)}-${seq++}`;

/** Build an empty block of the given kind with sensible defaults. */
export function makeBlock(kind: BlockKind): PackageBlock {
  const id = nextId();
  switch (kind) {
    case "items":
      return { id, kind, bonus: false, rows: [] };
    case "choice":
      return { id, kind, bonus: false, picks: "2", choose_at: "visit", rows: [] };
    case "unlimited":
      return { id, kind, bonus: false, assigned_value_paise: 0, daily_cap: "", rows: [] };
    case "pool":
      return { id, kind, bonus: false, sessions: "10", rows: [] };
    case "credit":
      return { id, kind, bonus: false, amount_paise: 200000, scope: "any" };
  }
}

export function AddBlockPalette({ onAdd }: { onAdd: (kind: BlockKind) => void }) {
  return (
    <div className="grid grid-cols-5 gap-2">
      {BLOCK_ORDER.map((kind) => {
        const meta = BLOCK_META[kind];
        const Icon = meta.icon;
        return (
          <button
            key={kind}
            type="button"
            onClick={() => onAdd(kind)}
            className={cn(
              "flex flex-col items-start gap-1.5 rounded-[10px] border border-dashed",
              "border-border-default p-2.5 text-left transition-colors hover:border-accent"
            )}
          >
            <span
              className={cn(
                "flex h-[22px] w-[22px] items-center justify-center rounded-md",
                meta.glyphBox
              )}
            >
              <Icon size={13} aria-hidden />
            </span>
            <span className="text-[12px] font-semibold text-text-primary">{meta.label}</span>
            <span className="text-[10.5px] leading-tight text-text-muted">
              {meta.description}
            </span>
          </button>
        );
      })}
    </div>
  );
}
