export const HOUR_HEIGHT = 64;
export const DAY_START_HOUR = 8;
export const DAY_END_HOUR = 21;
export const GRID_HEIGHT = (DAY_END_HOUR - DAY_START_HOUR) * HOUR_HEIGHT;

export function minutesToPx(minutes: number): number {
  return (minutes / 60) * HOUR_HEIGHT;
}

export function pxToMinutes(px: number): number {
  const raw = (px / HOUR_HEIGHT) * 60;
  return Math.round(raw / 15) * 15;
}

export function timeToTopOffset(iso: string): number {
  // Use Date object so UTC-stored times (e.g. "T04:30:00Z") are converted to local
  // timezone before computing the grid position. getHours()/getMinutes() return
  // local time — not UTC — which is what we want for display.
  const d = new Date(iso);
  if (isNaN(d.getTime())) return 0;
  const hour = d.getHours();
  const minute = d.getMinutes();
  const minutesSinceStart = (hour - DAY_START_HOUR) * 60 + minute;
  return Math.max(0, Math.min(minutesToPx(minutesSinceStart), GRID_HEIGHT));
}

const DATA_SERIES_COUNT = 6;

export function getServiceColor(serviceId: string): string {
  const tail = serviceId.slice(-6);
  let n = 0;
  for (let i = 0; i < tail.length; i++) {
    n = (n * 37 + tail.charCodeAt(i)) % DATA_SERIES_COUNT;
  }
  return `var(--data-series-${n + 1})`;
}

export function snapToSlot(iso: string): string {
  // Use fixed-position parsing so the timezone suffix (+05:30, Z, etc.) is preserved in the output.
  const tIdx = iso.indexOf("T");
  if (tIdx === -1) return iso;
  const datePart = iso.substring(0, tIdx);
  const timePart = iso.substring(tIdx + 1); // "08:07:00+05:30" or "08:07:00Z" or "08:07:00"
  const hour = parseInt(timePart.substring(0, 2), 10);
  const minute = parseInt(timePart.substring(3, 5), 10);
  const snappedMinutes = Math.floor(minute / 15) * 15;
  const tzSuffix = timePart.substring(8); // "+05:30", "Z", or ""
  return `${datePart}T${String(hour).padStart(2, "0")}:${String(snappedMinutes).padStart(2, "0")}:00${tzSuffix}`;
}

export function buildISO(dateStr: string, hour: number, minute: number): string {
  return `${dateStr}T${String(hour).padStart(2, "0")}:${String(minute).padStart(2, "0")}:00`;
}

/** Returns true if the appointment's local time falls outside business hours. */
export function isOffHours(iso: string): boolean {
  const d = new Date(iso);
  if (isNaN(d.getTime())) return false;
  const h = d.getHours(); // local timezone
  return h < DAY_START_HOUR || h >= DAY_END_HOUR;
}

/** Formats the local time from an ISO string as "9:30 AM" (12h, no seconds). */
export function formatApptTime(iso: string): string {
  const d = new Date(iso);
  if (isNaN(d.getTime())) return "";
  const h = d.getHours(); // local timezone
  const m = String(d.getMinutes()).padStart(2, "0");
  const period = h >= 12 ? "PM" : "AM";
  const h12 = h % 12 || 12;
  return `${h12}:${m} ${period}`;
}
