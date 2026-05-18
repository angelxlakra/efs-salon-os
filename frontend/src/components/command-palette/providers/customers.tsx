"use client";

import * as React from "react";
import { Command } from "cmdk";
import { useRouter } from "next/navigation";
import { Users } from "lucide-react";
import { usePalette } from "@/components/command-palette/use-palette";

type Customer = { id: string; first_name: string; last_name: string; phone: string };

function useDebounced<T>(value: T, delayMs: number): T {
  const [debounced, setDebounced] = React.useState(value);
  React.useEffect(() => {
    const handle = setTimeout(() => setDebounced(value), delayMs);
    return () => clearTimeout(handle);
  }, [value, delayMs]);
  return debounced;
}

export function CustomersProvider({ query }: { query: string }) {
  const debouncedQuery = useDebounced(query.trim(), 200);
  const [results, setResults] = React.useState<Customer[]>([]);
  const router = useRouter();
  const { close } = usePalette();

  React.useEffect(() => {
    if (!debouncedQuery) {
      setResults([]);
      return;
    }
    let cancelled = false;
    fetch(`/api/customers/autocomplete?q=${encodeURIComponent(debouncedQuery)}`)
      .then((r) => (r.ok ? r.json() : []))
      .then((data: Customer[]) => {
        if (!cancelled) setResults(Array.isArray(data) ? data.slice(0, 5) : []);
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
    <Command.Group heading="Customers" className="text-overline text-text-muted px-2 py-1">
      {results.map((c) => (
        <Command.Item
          key={c.id}
          value={`customer-${c.id} ${c.first_name} ${c.last_name} ${c.phone}`}
          keywords={[c.first_name, c.last_name, c.phone]}
          onSelect={() => {
            router.push(`/dashboard/customers/${c.id}`);
            close();
          }}
          className="flex items-center gap-2 px-3 h-9 rounded-md text-body-sm text-text-primary cursor-pointer aria-selected:bg-surface-row-hover"
        >
          <Users className="size-4 text-text-muted" />
          <span>{c.first_name} {c.last_name}</span>
          <span className="ml-auto text-text-muted tabular text-caption">{c.phone}</span>
        </Command.Item>
      ))}
    </Command.Group>
  );
}
