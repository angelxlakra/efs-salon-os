const STORAGE_KEY = "salon.palette.history";
const MAX_ENTRIES = 10;

export type HistoryEntry = {
  id: string;
  label: string;
  href: string;
};

export function readHistory(): HistoryEntry[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export function recordCommand(entry: HistoryEntry): void {
  if (typeof window === "undefined") return;
  const current = readHistory();
  const filtered = current.filter((e) => e.id !== entry.id);
  const next = [entry, ...filtered].slice(0, MAX_ENTRIES);
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
  } catch {
    // storage unavailable — fail silent.
  }
}

export function clearHistory(): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.removeItem(STORAGE_KEY);
  } catch {
    // ignore
  }
}
