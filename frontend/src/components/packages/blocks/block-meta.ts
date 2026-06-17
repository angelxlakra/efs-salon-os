// frontend/src/components/packages/blocks/block-meta.ts
//
// Per-block-type presentation metadata. Colors are semantic-token utility
// classes (never raw hex) so light/dark themes follow the token file.

import { Package, Gift, Infinity as InfinityIcon, Wallet, Layers } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import type { BlockKind } from "@/types/package";

export interface BlockTypeMeta {
  label: string;
  description: string;
  icon: LucideIcon;
  /** Chip + palette-glyph color classes (background + foreground). */
  chip: string;
  glyphBox: string;
}

export const BLOCK_META: Record<BlockKind, BlockTypeMeta> = {
  items: {
    label: "Fixed items",
    description: "Set services & quantities, e.g. 10 × Haircut",
    icon: Package,
    chip: "bg-accent-bg-soft text-accent",
    glyphBox: "bg-accent-bg-soft text-accent",
  },
  choice: {
    label: "Choice group",
    description: "Pick N from a list — at purchase or each visit",
    icon: Gift,
    chip: "bg-gold-soft text-gold-fg",
    glyphBox: "bg-gold-soft text-gold-fg",
  },
  unlimited: {
    label: "Unlimited",
    description: "Unlimited use until expiry, optional daily cap",
    icon: InfinityIcon,
    chip: "bg-info-bg-soft text-info-fg",
    glyphBox: "bg-info-bg-soft text-info-fg",
  },
  pool: {
    label: "Session pool",
    description: "N visits spendable across listed services",
    icon: Layers,
    chip: "bg-purple-bg-soft text-purple-fg",
    glyphBox: "bg-purple-bg-soft text-purple-fg",
  },
  credit: {
    label: "Credit",
    description: "A spendable balance, like a wallet",
    icon: Wallet,
    chip: "bg-success-bg-soft text-success-fg",
    glyphBox: "bg-success-bg-soft text-success-fg",
  },
};

export const BLOCK_ORDER: BlockKind[] = [
  "items",
  "choice",
  "unlimited",
  "pool",
  "credit",
];
