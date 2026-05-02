"use client";

import * as React from "react";
import { Command } from "cmdk";
import { useRouter } from "next/navigation";
import { Package } from "lucide-react";
import { usePalette } from "@/components/command-palette/use-palette";

type SKU = { id: string; name: string; sku_code: string };

function useDebounced<T>(value: T, delayMs: number): T {
  const [debounced, setDebounced] = React.useState(value);
  React.useEffect(() => {
    const handle = setTimeout(() => setDebounced(value), delayMs);
    return () => clearTimeout(handle);
  }, [value, delayMs]);
  return debounced;
}

export function SkusProvider({ query }: { query: string }) {
  const debouncedQuery = useDebounced(query.trim(), 200);
  const [results, setResults] = React.useState<SKU[]>([]);
  const router = useRouter();
  const { close } = usePalette();

  React.useEffect(() => {
    if (!debouncedQuery) {
      setResults([]);
      return;
    }
    let cancelled = false;
    fetch(`/api/inventory?search=${encodeURIComponent(debouncedQuery)}&limit=5`)
      .then((r) => (r.ok ? r.json() : []))
      .then((data) => {
        if (cancelled) return;
        const arr: SKU[] = Array.isArray(data) ? data : (data?.items ?? []);
        setResults(arr.slice(0, 5));
      })
      .catch(() => {
        if (!cancelled) setResults([]);
      });
    return () => {
      cancelled = true;
    };
  }, [debouncedQuery]);

  if (!debouncedQuery || results.length === 0) return null;

  return (
    <Command.Group heading="Inventory" className="text-overline text-text-muted px-2 py-1">
      {results.map((s) => (
        <Command.Item
          key={s.id}
          value={`sku-${s.id} ${s.name} ${s.sku_code}`}
          keywords={[s.name, s.sku_code]}
          onSelect={() => {
            router.push(`/dashboard/inventory/${s.id}`);
            close();
          }}
          className="flex items-center gap-2 px-3 h-9 rounded-md text-body-sm text-text-primary cursor-pointer aria-selected:bg-surface-row-hover"
        >
          <Package className="size-4 text-text-muted" />
          <span>{s.name}</span>
          <span className="ml-auto text-text-muted text-caption">{s.sku_code}</span>
        </Command.Item>
      ))}
    </Command.Group>
  );
}
