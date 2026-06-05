import { cn } from "@/lib/utils";
import { Gift } from "lucide-react";

interface Props {
  active: boolean;
  onClick: () => void;
  count?: number; // number of published packages
  className?: string;
}

export function PackageSelectorChip({ active, onClick, count, className }: Props) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm border transition-colors",
        active
          ? "bg-accent text-accent-foreground border-accent"
          : "border-border text-muted-foreground hover:border-border-strong",
        className
      )}
    >
      <Gift size={14} />
      Packages
      {count != null && count > 0 && (
        <span
          className={cn(
            "text-[10px] px-1.5 py-0.5 rounded-full",
            active ? "bg-accent-foreground/20" : "bg-surface-row"
          )}
        >
          {count}
        </span>
      )}
    </button>
  );
}
