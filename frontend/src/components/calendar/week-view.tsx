"use client";

import * as React from "react";
import { TimeGrid } from "@/components/calendar/time-grid";
import { AppointmentBlock } from "@/components/calendar/appointment-block";
import {
  GRID_HEIGHT,
  minutesToPx,
  timeToTopOffset,
  buildISO,
  DAY_START_HOUR,
  HOUR_HEIGHT,
} from "@/components/calendar/utils";
import type { Appointment, ServiceItem } from "@/lib/api/appointments";
import { format, addDays, isToday } from "date-fns";

const DAY_COLUMN_MIN_WIDTH = 100;

type WeekViewProps = {
  appointments: Appointment[];
  services: ServiceItem[];
  weekStart: Date;
  onAppointmentClick: (appt: Appointment) => void;
  onSlotClick: (staffId: null, datetime: string) => void;
};

export function WeekView({
  appointments,
  services,
  weekStart,
  onAppointmentClick,
  onSlotClick,
}: WeekViewProps) {
  const days = Array.from({ length: 7 }, (_, i) => addDays(weekStart, i));

  const serviceMap = React.useMemo(
    () => new Map(services.map((s) => [s.id, s])),
    [services]
  );

  const apptByDay = React.useMemo(() => {
    const map = new Map<string, Appointment[]>();
    days.forEach((d) => map.set(format(d, "yyyy-MM-dd"), []));
    appointments.forEach((a) => {
      const key = format(new Date(a.scheduled_at), "yyyy-MM-dd");
      map.get(key)?.push(a);
    });
    return map;
  }, [appointments, days]);

  const headerScrollRef = React.useRef<HTMLDivElement>(null);
  const bodyScrollRef = React.useRef<HTMLDivElement>(null);

  React.useEffect(() => {
    const body = bodyScrollRef.current;
    const header = headerScrollRef.current;
    if (!body || !header) return;
    const syncHeader = () => { header.scrollLeft = body.scrollLeft; };
    body.addEventListener("scroll", syncHeader, { passive: true });
    return () => body.removeEventListener("scroll", syncHeader);
  }, []);

  const handleSlotClick = React.useCallback(
    (day: Date, e: React.MouseEvent<HTMLDivElement>) => {
      const rect = e.currentTarget.getBoundingClientRect();
      const relY = e.clientY - rect.top;
      const totalMinutes =
        DAY_START_HOUR * 60 + Math.round(((relY / HOUR_HEIGHT) * 60) / 15) * 15;
      const h = Math.floor(totalMinutes / 60);
      const m = totalMinutes % 60;
      onSlotClick(null, buildISO(format(day, "yyyy-MM-dd"), h, m));
    },
    [onSlotClick]
  );

  return (
    <div className="flex flex-col h-full">
      <div className="flex border-b border-border-default bg-surface-card sticky top-0 z-20">
        <div className="w-14 shrink-0 border-r border-border-subtle" />
        <div ref={headerScrollRef} className="flex overflow-x-hidden">
          {days.map((day) => (
            <div
              key={format(day, "yyyy-MM-dd")}
              className="border-r border-border-subtle px-2 py-2 text-center"
              style={{ minWidth: DAY_COLUMN_MIN_WIDTH }}
            >
              <span className="text-[11px] text-text-muted block">
                {format(day, "EEE")}
              </span>
              <span
                className={`text-sm font-semibold block ${
                  isToday(day) ? "text-accent" : "text-text-primary"
                }`}
              >
                {format(day, "d")}
              </span>
            </div>
          ))}
        </div>
      </div>

      <div ref={bodyScrollRef} className="flex-1 overflow-y-auto overflow-x-auto">
        <TimeGrid>
          <div className="flex absolute inset-0">
            {days.map((day) => {
              const key = format(day, "yyyy-MM-dd");
              const dayAppts = apptByDay.get(key) ?? [];
              return (
                <div
                  key={key}
                  className={`relative border-r border-border-subtle ${
                    isToday(day) ? "bg-accent/5" : ""
                  }`}
                  style={{ minWidth: DAY_COLUMN_MIN_WIDTH, height: GRID_HEIGHT }}
                  onClick={(e) => handleSlotClick(day, e)}
                >
                  {dayAppts.map((appt) => (
                    <AppointmentBlock
                      key={appt.id}
                      appointment={appt}
                      serviceName={serviceMap.get(appt.service_id)?.name ?? "Service"}
                      top={timeToTopOffset(appt.scheduled_at)}
                      height={minutesToPx(appt.duration_minutes)}
                      onClick={onAppointmentClick}
                    />
                  ))}
                </div>
              );
            })}
          </div>
        </TimeGrid>
      </div>
    </div>
  );
}
