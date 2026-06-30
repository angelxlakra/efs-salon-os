import * as React from "react";
import { cn } from "@/lib/utils";

type Props = {
  icon?: React.ReactNode;
  /** Required. Rendered in the display serif. */
  title: string;
  /** Required. One sentence guiding the next action. "No data" is not acceptable. */
  body: string;
  /** Heading level for the title. Default 3 — bump to 2 (or 1) when EmptyState is the sole content of a route. */
  headingLevel?: 2 | 3 | 4;
  primaryAction?: React.ReactNode;
  /** Only rendered alongside `primaryAction`. Pass a sole CTA as `primaryAction` instead. */
  secondaryAction?: React.ReactNode;
  className?: string;
};

/**
 * Standardised "no data" surface. Consumers MUST pass a specific, action-oriented
 * `body` string (one sentence). Generic copy like "No data" / "Nothing here" is
 * not acceptable per Phase 0 plan T14 — every empty state must guide the next move.
 */
/**
 * §06 "the Seal as a device": an empty state shows a faint mark above the
 * headline — calm, never an "error" icon. Used as the default when a consumer
 * doesn't pass a more specific icon.
 */
const FAINT_SEAL = (
  // eslint-disable-next-line @next/next/no-img-element
  <img src="/aasan-mark.svg" alt="" width={32} height={32} style={{ opacity: 0.18 }} />
);

export function EmptyState({
  icon,
  title,
  body,
  headingLevel = 3,
  primaryAction,
  secondaryAction,
  className,
}: Props) {
  const Heading = `h${headingLevel}` as const;
  const resolvedIcon = icon ?? FAINT_SEAL;
  return (
    <div className={cn("flex flex-col items-center justify-center text-center gap-4 py-12 px-6", className)}>
      <div className="text-text-muted [&_svg]:size-8" aria-hidden>{resolvedIcon}</div>
      <div className="flex flex-col gap-2 max-w-sm">
        <Heading className="text-display-md text-text-primary">{title}</Heading>
        <p className="text-body text-text-secondary">{body}</p>
      </div>
      {primaryAction && (
        <div className="flex gap-2 mt-2">
          {primaryAction}
          {secondaryAction}
        </div>
      )}
    </div>
  );
}
