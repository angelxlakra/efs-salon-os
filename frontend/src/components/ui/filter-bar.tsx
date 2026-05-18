import * as React from "react";
import { Search } from "lucide-react";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

function Root({ className, children }: { className?: string; children: React.ReactNode }) {
  return (
    <div className={cn("flex flex-wrap items-center gap-2 py-2", className)}>
      {children}
    </div>
  );
}

function Search_({
  value,
  onChange,
  placeholder = "Search…",
  className,
}: {
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  className?: string;
}) {
  return (
    <div className={cn("flex-1 min-w-[200px]", className)}>
      <Input
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        leadingAddon={<Search className="size-4" />}
        aria-label="Search"
      />
    </div>
  );
}

type PillOption = { value: string; label: string; count?: number };

function Pills({
  value,
  onChange,
  options,
  className,
}: {
  value: string;
  onChange: (v: string) => void;
  options: PillOption[];
  className?: string;
}) {
  return (
    <div className={cn("flex flex-wrap gap-1", className)} role="group" aria-label="Filters">
      {options.map((opt) => {
        const active = opt.value === value;
        return (
          <button
            key={opt.value}
            type="button"
            aria-pressed={active}
            data-active={active}
            onClick={() => onChange(opt.value)}
            className={cn(
              "inline-flex items-center gap-1.5 rounded-full px-3 h-7 text-body-sm border transition-colors",
              active
                ? "bg-accent text-accent-fg border-transparent font-semibold"
                : "bg-surface-card text-text-secondary border-border-default hover:bg-surface-row-hover"
            )}
          >
            <span>{opt.label}</span>
            {opt.count !== undefined && (
              <span className={cn("tabular text-[11px]", active ? "opacity-80" : "text-text-muted")}>
                · {opt.count}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}

function Actions({ className, children }: { className?: string; children: React.ReactNode }) {
  return <div className={cn("flex items-center gap-2 ml-auto", className)}>{children}</div>;
}

export const FilterBar = Object.assign(Root, {
  Search: Search_,
  Pills,
  Actions,
});
