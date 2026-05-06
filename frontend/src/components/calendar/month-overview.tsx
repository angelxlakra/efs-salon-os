"use client";

import * as React from "react";
import {
  format,
  startOfMonth,
  endOfMonth,
  startOfWeek,
  endOfWeek,
  addDays,
  isSameMonth,
  isSameDay,
  isToday,
} from "date-fns";
import type { Appointment } from "@/lib/api/appointments";
import { cn } from "@/lib/utils";

type MonthOverviewProps = {
  month: Date;
  appointments: Appointment[];
  onDayClick: (date: Date) => void;
  selectedDate?: Date;
};

export function MonthOverview({
  month,
  appointments,
  onDayClick,
  selectedDate,
}: MonthOverviewProps) {
  const days = React.useMemo(() => {
    const monthStart = startOfMonth(month);
    const monthEnd = endOfMonth(month);
    const gridStart = startOfWeek(monthStart, { weekStartsOn: 1 });
    const gridEnd = endOfWeek(monthEnd, { weekStartsOn: 1 });
    const result: Date[] = [];
    let d = gridStart;
    while (d <= gridEnd) {
      result.push(d);
      d = addDays(d, 1);
    }
    return result;
  }, [month]);

  // Count appointments per day
  const countByDay = React.useMemo(() => {
    const map = new Map<string, number>();
    appointments.forEach((a) => {
      const key = a.scheduled_at.substring(0, 10);
      map.set(key, (map.get(key) ?? 0) + 1);
    });
    return map;
  }, [appointments]);

  return (
    <div className="p-4">
      {/* Weekday header */}
      <div className="grid grid-cols-7 mb-1">
        {["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"].map((wd) => (
          <div key={wd} className="text-center text-[11px] text-text-muted py-1">
            {wd}
          </div>
        ))}
      </div>

      {/* Day cells */}
      <div className="grid grid-cols-7 gap-0.5">
        {days.map((day) => {
          const key = format(day, "yyyy-MM-dd");
          const count = countByDay.get(key) ?? 0;
          const inMonth = isSameMonth(day, month);
          const isSelected = selectedDate ? isSameDay(day, selectedDate) : false;
          const today = isToday(day);

          return (
            <button
              key={key}
              type="button"
              onClick={() => onDayClick(day)}
              className={cn(
                "flex flex-col items-center justify-center rounded-md p-1.5 min-h-[44px] text-[13px]",
                "transition-colors hover:bg-surface-row-hover",
                !inMonth && "opacity-30",
                today && "font-semibold text-accent",
                isSelected && "bg-accent-bg-soft ring-1 ring-accent"
              )}
            >
              <span>{format(day, "d")}</span>
              {count > 0 && (
                <span className="mt-0.5 h-1.5 w-1.5 rounded-full bg-accent" aria-label={`${count} ${count === 1 ? "appointment" : "appointments"}`} />
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}
