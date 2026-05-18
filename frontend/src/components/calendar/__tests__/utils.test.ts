import { describe, expect, it } from "vitest";
import {
  HOUR_HEIGHT,
  DAY_START_HOUR,
  DAY_END_HOUR,
  GRID_HEIGHT,
  minutesToPx,
  pxToMinutes,
  timeToTopOffset,
  getServiceColor,
  snapToSlot,
  buildISO,
} from "@/components/calendar/utils";

describe("calendar utils", () => {
  it("GRID_HEIGHT equals (DAY_END_HOUR - DAY_START_HOUR) * HOUR_HEIGHT", () => {
    expect(GRID_HEIGHT).toBe((DAY_END_HOUR - DAY_START_HOUR) * HOUR_HEIGHT);
  });

  it("minutesToPx converts 60 min to HOUR_HEIGHT px", () => {
    expect(minutesToPx(60)).toBe(HOUR_HEIGHT);
  });

  it("minutesToPx converts 30 min to half HOUR_HEIGHT", () => {
    expect(minutesToPx(30)).toBe(HOUR_HEIGHT / 2);
  });

  it("pxToMinutes snaps to 15-minute grid", () => {
    const px = (HOUR_HEIGHT / 60) * 15;
    expect(pxToMinutes(px)).toBe(15);
  });

  it("pxToMinutes rounds non-15-min values to nearest 15", () => {
    const px = (HOUR_HEIGHT / 60) * 22;
    expect(pxToMinutes(px)).toBe(15);
  });

  it("timeToTopOffset places 8:00 AM at 0 when DAY_START_HOUR is 8", () => {
    const iso = `2026-05-05T${String(DAY_START_HOUR).padStart(2, "0")}:00:00+05:30`;
    expect(timeToTopOffset(iso)).toBe(0);
  });

  it("timeToTopOffset places 9:00 AM at HOUR_HEIGHT when DAY_START_HOUR is 8", () => {
    const iso = `2026-05-05T${String(DAY_START_HOUR + 1).padStart(2, "0")}:00:00+05:30`;
    expect(timeToTopOffset(iso)).toBe(HOUR_HEIGHT);
  });

  it("getServiceColor returns a CSS var string", () => {
    const color = getServiceColor("01ABCDEF1234");
    expect(color).toMatch(/^var\(--data-series-[1-6]\)$/);
  });

  it("getServiceColor is deterministic for the same id", () => {
    expect(getServiceColor("01ABCDEF1234")).toBe(getServiceColor("01ABCDEF1234"));
  });

  it("getServiceColor produces different values for different ids", () => {
    const colors = new Set([
      getServiceColor("aaaa"),
      getServiceColor("bbbb"),
      getServiceColor("cccc"),
      getServiceColor("dddd"),
      getServiceColor("eeee"),
      getServiceColor("ffff"),
    ]);
    expect(colors.size).toBeGreaterThan(1);
  });

  it("snapToSlot snaps a datetime string to 15-min boundary", () => {
    const snapped = snapToSlot("2026-05-05T08:07:00+05:30");
    expect(snapped).toBe("2026-05-05T08:00:00+05:30");
  });

  it("snapToSlot preserves the timezone suffix", () => {
    const snapped = snapToSlot("2026-05-05T08:07:00+05:30");
    expect(snapped).toBe("2026-05-05T08:00:00+05:30");
  });

  it("buildISO formats single-digit hours and minutes with padding", () => {
    expect(buildISO("2026-05-05", 8, 0)).toBe("2026-05-05T08:00:00");
    expect(buildISO("2026-05-05", 9, 5)).toBe("2026-05-05T09:05:00");
  });

  it("pxToMinutes returns 0 for 0 px input", () => {
    expect(pxToMinutes(0)).toBe(0);
  });
});
