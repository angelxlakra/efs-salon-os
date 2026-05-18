import * as React from "react";
import { cn } from "@/lib/utils";

type Props = {
  keys: string[];
  className?: string;
};

export function Kbd({ keys, className }: Props) {
  return (
    <span className={cn("inline-flex items-center gap-0.5 font-mono text-[10px]", className)}>
      {keys.map((k, i) => (
        <kbd
          key={`${k}-${i}`}
          className="inline-flex items-center justify-center min-w-[18px] h-[18px] px-1 rounded bg-surface-row-hover text-text-secondary border border-border-subtle"
        >
          {k}
        </kbd>
      ))}
    </span>
  );
}
