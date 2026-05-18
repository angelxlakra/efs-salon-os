"use client";

import * as React from "react";
import { cn } from "@/lib/utils";
import {
  HOUR_HEIGHT,
  DAY_START_HOUR,
  DAY_END_HOUR,
  GRID_HEIGHT,
} from "@/components/calendar/utils";

const HOURS = Array.from(
  { length: DAY_END_HOUR - DAY_START_HOUR },
  (_, i) => DAY_START_HOUR + i
);

/** Returns the pixel offset from the top of the grid for the current wall-clock time,
 *  or null if outside business hours. */
function getNowOffset(): number | null {
  const now = new Date();
  const h = now.getHours();
  const m = now.getMinutes();
  if (h < DAY_START_HOUR || h >= DAY_END_HOUR) return null;
  return (h - DAY_START_HOUR) * HOUR_HEIGHT + (m / 60) * HOUR_HEIGHT;
}

function hourLabel(h: number): string {
  if (h < 12) return `${h} AM`;
  if (h === 12) return "12 PM";
  return `${h - 12} PM`;
}

type TimeGridProps = {
  children: React.ReactNode;
  className?: string;
};

/**
 * Scrollable time-grid canvas shared by DayView and WeekView.
 * Renders hour labels on the left + an absolutely-positioned body on the right.
 * Children (swimlane columns) are rendered inside the body.
 */
export function TimeGrid({ children, className }: TimeGridProps) {
  // Start null to avoid server/client mismatch (React #418).
  // The indicator is set after hydration and updated every minute.
  const [nowOffset, setNowOffset] = React.useState<number | null>(null);

  React.useEffect(() => {
    setNowOffset(getNowOffset());
    const id = setInterval(() => setNowOffset(getNowOffset()), 60_000);
    return () => clearInterval(id);
  }, []);

  return (
    <div className={cn("flex overflow-y-auto", className)}>
      <div className="sticky left-0 z-10 w-14 shrink-0 bg-surface-card border-r border-border-subtle select-none">
        {HOURS.map((h) => (
          <div
            key={h}
            style={{ height: HOUR_HEIGHT }}
            className="flex items-start justify-end pr-2 pt-0.5"
          >
            <span className="text-[11px] text-text-muted leading-none">
              {hourLabel(h)}
            </span>
          </div>
        ))}
      </div>

      <div
        data-testid="grid-body"
        className="relative flex-1"
        style={{ minHeight: GRID_HEIGHT }}
      >
        {HOURS.map((h) => (
          <div
            key={h}
            className="absolute left-0 right-0 border-t border-border-subtle"
            style={{ top: (h - DAY_START_HOUR) * HOUR_HEIGHT }}
            aria-hidden
          />
        ))}
        {HOURS.flatMap((h) =>
          [1, 2, 3].map((q) => (
            <div
              key={`${h}-${q}`}
              className="absolute left-0 right-0 border-t border-border-subtle opacity-40"
              style={{ top: (h - DAY_START_HOUR) * HOUR_HEIGHT + q * (HOUR_HEIGHT / 4) }}
              aria-hidden
            />
          ))
        )}
        {/* Current-time indicator — red dot on left gutter + full-width line */}
        {nowOffset !== null && (
          <div
            className="absolute left-0 right-0 z-20 pointer-events-none"
            style={{ top: nowOffset }}
            aria-hidden
          >
            <div className="relative">
              <div className="absolute -left-1.5 -top-1.5 w-3 h-3 rounded-full bg-accent" />
              <div className="h-0.5 bg-accent opacity-70" />
            </div>
          </div>
        )}
        {children}
      </div>
    </div>
  );
}
