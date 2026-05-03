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
  // Parse hour and minute directly from the ISO string to avoid timezone conversion issues
  const timePart = iso.split("T")[1]; // "10:00:00+05:30" or "10:00:00Z"
  const [hourStr, minuteStr] = timePart.split(":");
  const hour = parseInt(hourStr, 10);
  const minute = parseInt(minuteStr, 10);
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
  // Parse the time part directly to avoid timezone conversion issues
  const [datePart, timePart] = iso.split("T");
  const [hourStr, minuteStr] = timePart.split(":");
  const hour = parseInt(hourStr, 10);
  const minute = parseInt(minuteStr, 10);
  const snappedMinutes = Math.floor(minute / 15) * 15;
  return `${datePart}T${String(hour).padStart(2, "0")}:${String(snappedMinutes).padStart(2, "0")}:00`;
}

export function buildISO(dateStr: string, hour: number, minute: number): string {
  return `${dateStr}T${String(hour).padStart(2, "0")}:${String(minute).padStart(2, "0")}:00`;
}
