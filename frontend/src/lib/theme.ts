export type AccentName = 'violet' | 'rose' | 'amber' | 'teal';

const STORAGE_KEY = 'salon-accent';
const VALID_ACCENTS: AccentName[] = ['violet', 'rose', 'amber', 'teal'];

export function getAccent(): AccentName {
  if (typeof window === 'undefined') return 'violet';
  const stored = localStorage.getItem(STORAGE_KEY);
  if (stored && (VALID_ACCENTS as string[]).includes(stored)) {
    return stored as AccentName;
  }
  return 'violet';
}

export function setAccent(accent: AccentName): void {
  if (typeof window === 'undefined') return;
  localStorage.setItem(STORAGE_KEY, accent);
  applyAccent(accent);
}

export function applyAccent(accent: AccentName): void {
  if (typeof document === 'undefined') return;
  const html = document.documentElement;
  if (accent === 'violet') {
    html.removeAttribute('data-accent');
  } else {
    html.setAttribute('data-accent', accent);
  }
}

export function initAccent(): void {
  applyAccent(getAccent());
}
