import * as React from "react";
import { cn } from "@/lib/utils";

type Shape = "text" | "row" | "card" | "kpi";

type Props = React.HTMLAttributes<HTMLDivElement> & {
  shape?: Shape;
  width?: React.CSSProperties["width"];
};

const shapeClass: Record<Shape, string> = {
  text: "h-4 rounded",
  row:  "h-9 rounded-md",
  card: "h-32 rounded-lg",
  kpi:  "h-20 rounded-lg",
};

const defaultWidthClass: Record<Shape, string> = {
  text: "w-3/4",
  row:  "w-full",
  card: "w-full",
  kpi:  "w-full",
};

export function Skeleton({ shape = "text", width, className, style, ...rest }: Props) {
  // Decorative-by-default: announce loading state via `aria-busy` on the live
  // container, not the skeleton. Callers can opt in by passing `aria-hidden={false}`.
  // `width !== undefined` (not truthy check) so `width={0}` doesn't fall back to defaults.
  const hasWidth = width !== undefined;
  return (
    <div
      data-shape={shape}
      style={hasWidth ? { ...style, width } : style}
      className={cn(
        "animate-pulse bg-surface-row-hover",
        shapeClass[shape],
        !hasWidth && defaultWidthClass[shape],
        className
      )}
      aria-hidden
      {...rest}
    />
  );
}
