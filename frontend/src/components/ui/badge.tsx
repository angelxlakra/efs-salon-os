import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center gap-1 rounded-full border font-semibold whitespace-nowrap",
  {
    variants: {
      tone: {
        neutral: "bg-surface-row text-text-secondary border-border-subtle",
        success: "bg-success-bg-soft text-success-fg border-success-border",
        warning: "bg-warning-bg-soft text-warning-fg border-warning-border",
        danger:  "bg-danger-bg-soft  text-danger-fg  border-danger-border",
        info:    "bg-info-bg-soft    text-info-fg    border-info-border",
        accent:  "bg-accent-bg-soft  text-accent     border-transparent",
      },
      size: {
        sm: "px-2 py-0.5 text-[11px]",
        md: "px-2.5 py-1 text-[12px]",
      },
    },
    defaultVariants: { tone: "neutral", size: "sm" },
  }
);

type Tone = NonNullable<VariantProps<typeof badgeVariants>["tone"]>;

/**
 * Legacy shim — maps the V1 shadcn `variant` prop onto the V2 `tone` prop.
 * Deprecated: do not reach for `variant` in new code; use `tone` directly.
 * Kept additive to preserve tsc+next-build health on 24 V1 caller files
 * (40 call sites) until Phase 1 retrofit migrates them. See plan T13
 * amendment (2026-04-25).
 */
type LegacyVariant = "default" | "secondary" | "destructive" | "outline";
const LEGACY_VARIANT_TO_TONE: Record<LegacyVariant, Tone> = {
  default: "neutral",
  secondary: "neutral",
  destructive: "danger",
  // V1 `outline` was visually distinct (transparent bg, prominent border).
  // V2 maps it to neutral — a deliberate visual drift; revisit per call-site
  // during Phase 1 retrofit if any chips read as wrong.
  outline: "neutral",
};

type BadgeProps = React.HTMLAttributes<HTMLSpanElement> &
  VariantProps<typeof badgeVariants> & {
    /** @deprecated Use `tone` instead. Mapped internally to a tone for V1 compat. */
    variant?: LegacyVariant;
  };

export function Badge({ tone, size, variant, className, ...props }: BadgeProps) {
  const resolvedTone: Tone = tone ?? (variant ? LEGACY_VARIANT_TO_TONE[variant] : "neutral");
  return (
    <span
      data-tone={resolvedTone}
      className={cn(badgeVariants({ tone: resolvedTone, size }), className)}
      {...props}
    />
  );
}
