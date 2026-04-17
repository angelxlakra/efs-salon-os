export type AccentName = 'violet' | 'rose' | 'amber' | 'teal';

const STORAGE_KEY = 'salon-accent';
const VALID_ACCENTS: AccentName[] = ['violet', 'rose', 'amber', 'teal'];

export function getAccent(): AccentName {
  if (typeof window === 'undefined') return 'violet';
  const stored = localStorage.getItem(STORAGE_KEY) as AccentName | null;
  return stored && VALID_ACCENTS.includes(stored) ? stored : 'violet';
}

export function setAccent(accent: AccentName): void {
  localStorage.setItem(STORAGE_KEY, accent);
  applyAccent(accent);
}

export function applyAccent(accent: AccentName): void {
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
