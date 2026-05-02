"use client";

import * as React from "react";
import { Command } from "cmdk";
import { useRouter } from "next/navigation";
import { Receipt } from "lucide-react";
import { usePalette } from "@/components/command-palette/use-palette";

type Bill = { id: string; invoice_number: string; total_paise: number; customer_name?: string };

function useDebounced<T>(value: T, delayMs: number): T {
  const [debounced, setDebounced] = React.useState(value);
  React.useEffect(() => {
    const handle = setTimeout(() => setDebounced(value), delayMs);
    return () => clearTimeout(handle);
  }, [value, delayMs]);
  return debounced;
}

export function BillsProvider({ query }: { query: string }) {
  const debouncedQuery = useDebounced(query.trim(), 200);
  const [results, setResults] = React.useState<Bill[]>([]);
  const router = useRouter();
  const { close } = usePalette();

  React.useEffect(() => {
    if (!debouncedQuery) {
      setResults([]);
      return;
    }
    let cancelled = false;
    fetch(`/api/pos/bills?search=${encodeURIComponent(debouncedQuery)}&limit=5`)
      .then((r) => (r.ok ? r.json() : []))
      .then((data) => {
        if (cancelled) return;
        const arr: Bill[] = Array.isArray(data) ? data : (data?.items ?? []);
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
    <Command.Group heading="Bills" className="text-overline text-text-muted px-2 py-1">
      {results.map((b) => (
        <Command.Item
          key={b.id}
          value={`bill-${b.id} ${b.invoice_number} ${b.customer_name ?? ""}`}
          keywords={[b.invoice_number, b.customer_name ?? ""]}
          onSelect={() => {
            router.push(`/dashboard/bills/${b.id}`);
            close();
          }}
          className="flex items-center gap-2 px-3 h-9 rounded-md text-body-sm text-text-primary cursor-pointer aria-selected:bg-surface-row-hover"
        >
          <Receipt className="size-4 text-text-muted" />
          <span>{b.invoice_number}</span>
          {b.customer_name && <span className="text-text-muted">— {b.customer_name}</span>}
          <span className="ml-auto text-text-muted tabular text-caption">
            ₹{(b.total_paise / 100).toFixed(2)}
          </span>
        </Command.Item>
      ))}
    </Command.Group>
  );
}
