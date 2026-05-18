import * as React from "react";
import { Check, ChevronsUpDown } from "lucide-react";
import { Command, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList } from "@/components/ui/command";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export type ComboboxOption = {
  value: string;
  label: string;
  keywords?: string[];
};

type Props = {
  options: ComboboxOption[];
  value: string | null;
  onChange: (value: string | null) => void;
  placeholder?: string;
  searchPlaceholder?: string;
  emptyMessage?: string;
  disabled?: boolean;
  className?: string;
};

export function Combobox({
  options,
  value,
  onChange,
  placeholder = "Select…",
  searchPlaceholder = "Search…",
  emptyMessage = "No results.",
  disabled,
  className,
}: Props) {
  const [open, setOpen] = React.useState(false);
  const selected = options.find((o) => o.value === value) ?? null;
  const commandRef = React.useRef<HTMLDivElement>(null);

  // Fix: Radix Dialog uses react-remove-scroll which attaches a document-level
  // *bubble-phase* wheel listener (shouldPrevent) that calls preventDefault() for
  // targets outside the dialog's shards. The Combobox Popover is portaled to
  // <body> and is not in those shards, so every wheel event over the dropdown
  // gets silently cancelled.
  //
  // The normal workaround (React fiber onWheelCapture on RemoveScroll) never
  // fires here because RemoveScroll (DialogOverlay) is a *sibling*, not an
  // ancestor, of the Combobox in the React fiber tree — React only dispatches
  // capture/bubble along the target's ancestry, not to siblings.
  //
  // Solution: attach a *capture-phase* listener at document level. Capture always
  // runs before bubble, so we intercept first, manually scroll [cmdk-list], and
  // call stopPropagation() so the bubble-phase shouldPrevent never fires.
  React.useEffect(() => {
    if (!open) return;
    const handleWheel = (evt: Event) => {
      const e = evt as WheelEvent;
      const el = commandRef.current;
      if (!el || !el.contains(e.target as Node)) return;
      const list = el.querySelector<HTMLElement>("[cmdk-list]");
      if (!list || list.scrollHeight <= list.clientHeight) return;
      e.stopPropagation(); // prevents bubble-phase shouldPrevent at document
      e.preventDefault();  // prevents browser from double-scrolling
      list.scrollTop += e.deltaY;
    };
    document.addEventListener("wheel", handleWheel, { capture: true, passive: false });
    return () => document.removeEventListener("wheel", handleWheel, { capture: true });
  }, [open]);

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="secondary"
          role="combobox"
          aria-haspopup="listbox"
          aria-expanded={open}
          disabled={disabled}
          className={cn("w-full justify-between font-normal", className)}
        >
          <span className={cn(!selected && "text-text-muted")}>
            {selected ? selected.label : placeholder}
          </span>
          <ChevronsUpDown className="opacity-60" />
        </Button>
      </PopoverTrigger>
      <PopoverContent className="p-0 w-[var(--radix-popover-trigger-width)]">
        <Command ref={commandRef}>
          <CommandInput placeholder={searchPlaceholder} />
          <CommandList>
            <CommandEmpty>{emptyMessage}</CommandEmpty>
            <CommandGroup>
              {options.map((opt) => (
                <CommandItem
                  key={opt.value}
                  value={opt.label}
                  keywords={opt.keywords}
                  onSelect={() => {
                    onChange(opt.value === value ? null : opt.value);
                    setOpen(false);
                  }}
                >
                  <Check className={cn("mr-2 size-4", opt.value === value ? "opacity-100" : "opacity-0")} />
                  {opt.label}
                </CommandItem>
              ))}
            </CommandGroup>
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  );
}
