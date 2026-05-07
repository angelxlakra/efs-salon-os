"use client";

import * as React from "react";
import { TimeGrid } from "@/components/calendar/time-grid";
import { AppointmentBlock } from "@/components/calendar/appointment-block";
import {
  HOUR_HEIGHT,
  GRID_HEIGHT,
  DAY_START_HOUR,
  minutesToPx,
  timeToTopOffset,
  buildISO,
  pxToMinutes,
} from "@/components/calendar/utils";
import type { Appointment, StaffMember, ServiceItem } from "@/lib/api/appointments";
import { format } from "date-fns";
import { DndContext, type DragEndEvent, pointerWithin } from "@dnd-kit/core";
import { useDroppable } from "@dnd-kit/core";
import { cn } from "@/lib/utils";

const COLUMN_MIN_WIDTH = 120;

function DroppableSlot({
  id,
  children,
  style,
  className,
  onClick,
}: {
  id: string;
  children: React.ReactNode;
  style?: React.CSSProperties;
  className?: string;
  onClick?: (e: React.MouseEvent<HTMLDivElement>) => void;
}) {
  const { setNodeRef, isOver } = useDroppable({ id });
  return (
    <div
      ref={setNodeRef}
      data-testid="grid-slot"
      className={cn(className, isOver && "bg-accent-bg-soft/40")}
      style={style}
      onClick={onClick}
    >
      {children}
    </div>
  );
}

type DayViewProps = {
  appointments: Appointment[];
  staff: StaffMember[];
  services: ServiceItem[];
  date?: Date;
  onAppointmentClick: (appt: Appointment) => void;
  onSlotClick: (staffId: string | null, datetime: string) => void;
  onAppointmentUpdate: (id: string, patch: { scheduled_at?: string; duration_minutes?: number }) => void;
};

export function DayView({
  appointments,
  staff,
  services,
  date = new Date(),
  onAppointmentClick,
  onSlotClick,
  onAppointmentUpdate,
}: DayViewProps) {
  const dateStr = format(date, "yyyy-MM-dd");

  const serviceMap = React.useMemo(
    () => new Map(services.map((s) => [s.id, s])),
    [services]
  );

  const columns = React.useMemo(
    () => [
      ...staff.map((s) => ({ id: s.id as string | null, label: s.display_name })),
      { id: null as string | null, label: "Unassigned" },
    ],
    [staff]
  );

  const apptByColumn = React.useMemo(() => {
    const map = new Map<string | null, Appointment[]>();
    columns.forEach((c) => map.set(c.id, []));
    appointments.forEach((a) => {
      const key = a.assigned_staff_id ?? null;
      if (map.has(key)) {
        map.get(key)!.push(a);
      } else {
        map.get(null)!.push(a);
      }
    });
    return map;
  }, [appointments, columns]);

  // O(n²) per column — acceptable for a salon's appointment count
  const conflictIds = React.useMemo(() => {
    const ids = new Set<string>();
    apptByColumn.forEach((colAppts) => {
      for (let i = 0; i < colAppts.length; i++) {
        for (let j = i + 1; j < colAppts.length; j++) {
          const a = colAppts[i];
          const b = colAppts[j];
          if (a.status === "cancelled" || b.status === "cancelled") continue;
          const aStart = new Date(a.scheduled_at).getTime();
          const aEnd = aStart + a.duration_minutes * 60_000;
          const bStart = new Date(b.scheduled_at).getTime();
          const bEnd = bStart + b.duration_minutes * 60_000;
          if (aStart < bEnd && bStart < aEnd) {
            ids.add(a.id);
            ids.add(b.id);
          }
        }
      }
    });
    return ids;
  }, [apptByColumn]);

  const headerScrollRef = React.useRef<HTMLDivElement>(null);
  const bodyScrollRef = React.useRef<HTMLDivElement>(null);

  const resizeRef = React.useRef<{
    apptId: string;
    startY: number;
    startDuration: number;
    currentDuration: number;
  } | null>(null);

  const handleResizeStart = React.useCallback(
    (e: React.MouseEvent, appt: Appointment) => {
      e.preventDefault();
      resizeRef.current = {
        apptId: appt.id,
        startY: e.clientY,
        startDuration: appt.duration_minutes,
        currentDuration: appt.duration_minutes,
      };
    },
    []
  );

  React.useEffect(() => {
    const onMouseMove = (e: MouseEvent) => {
      if (!resizeRef.current) return;
      const { startY, startDuration } = resizeRef.current;
      const deltaY = e.clientY - startY;
      const deltaMins = Math.round(((deltaY / HOUR_HEIGHT) * 60) / 15) * 15;
      resizeRef.current.currentDuration = Math.max(15, startDuration + deltaMins);
    };
    const onMouseUp = () => {
      if (resizeRef.current) {
        const { apptId, currentDuration } = resizeRef.current;
        onAppointmentUpdate(apptId, { duration_minutes: currentDuration });
      }
      resizeRef.current = null;
    };
    window.addEventListener("mousemove", onMouseMove);
    window.addEventListener("mouseup", onMouseUp);
    return () => {
      window.removeEventListener("mousemove", onMouseMove);
      window.removeEventListener("mouseup", onMouseUp);
    };
  }, [onAppointmentUpdate]);

  React.useEffect(() => {
    const body = bodyScrollRef.current;
    const header = headerScrollRef.current;
    if (!body || !header) return;
    const syncHeader = () => { header.scrollLeft = body.scrollLeft; };
    body.addEventListener("scroll", syncHeader, { passive: true });
    return () => body.removeEventListener("scroll", syncHeader);
  }, []);

  const handleSlotClick = React.useCallback(
    (colId: string | null, e: React.MouseEvent<HTMLDivElement>) => {
      const rect = (e.currentTarget as HTMLDivElement).getBoundingClientRect();
      const relY = e.clientY - rect.top;
      const totalMinutes = DAY_START_HOUR * 60 + Math.round(((relY / HOUR_HEIGHT) * 60) / 15) * 15;
      const h = Math.floor(totalMinutes / 60);
      const m = totalMinutes % 60;
      onSlotClick(colId, buildISO(dateStr, h, m));
    },
    [dateStr, onSlotClick]
  );

  const handleDragEnd = React.useCallback(
    (event: DragEndEvent) => {
      const { active, over, delta } = event;
      if (!over || !active.data.current) return;
      const appt: Appointment = active.data.current.appointment;
      // Never reschedule a cancelled appointment
      if (appt.status === "cancelled") return;

      // Compute new time from original position + vertical drag delta
      const originalTop = timeToTopOffset(appt.scheduled_at);
      // Clamp: not before grid start, not past last slot that fits the block
      const maxTop = GRID_HEIGHT - minutesToPx(appt.duration_minutes);
      const newTop = Math.max(0, Math.min(maxTop, originalTop + delta.y));
      const snappedMins = pxToMinutes(newTop); // minutes from grid start, snapped to 15
      const totalMins = DAY_START_HOUR * 60 + snappedMins;
      const newHour = Math.floor(totalMins / 60);
      const newMin = totalMins % 60;
      // Use substring(0,10) to extract date timezone-safely
      const dayStr = appt.scheduled_at.substring(0, 10);
      const newScheduledAt = `${buildISO(dayStr, newHour, newMin)}+05:30`;

      onAppointmentUpdate(appt.id, { scheduled_at: newScheduledAt });
    },
    [onAppointmentUpdate]
  );

  return (
    <DndContext collisionDetection={pointerWithin} onDragEnd={handleDragEnd}>
      <div className="flex flex-col h-full">
      <div className="flex border-b border-border-default bg-surface-card sticky top-0 z-20">
        <div className="w-14 shrink-0 border-r border-border-subtle" />
        <div ref={headerScrollRef} className="flex overflow-x-auto">
          {columns.map((col) => (
            <div
              key={col.id ?? "unassigned"}
              className="border-r border-border-subtle px-2 py-2 text-center"
              style={{ minWidth: COLUMN_MIN_WIDTH }}
            >
              <span className="text-sm font-semibold text-text-primary truncate block">
                {col.label}
              </span>
            </div>
          ))}
        </div>
      </div>

      <div ref={bodyScrollRef} className="flex-1 overflow-y-auto overflow-x-auto">
        <TimeGrid>
          <div className="flex absolute inset-0">
            {columns.map((col) => {
              const colAppts = apptByColumn.get(col.id) ?? [];
              return (
                <DroppableSlot
                  key={col.id ?? "unassigned"}
                  id={col.id ?? "null"}
                  className="relative border-r border-border-subtle"
                  style={{ minWidth: COLUMN_MIN_WIDTH, height: GRID_HEIGHT }}
                  onClick={(e) => handleSlotClick(col.id, e)}
                >
                  {colAppts.map((appt) => (
                    <AppointmentBlock
                      key={appt.id}
                      appointment={appt}
                      serviceName={serviceMap.get(appt.service_id)?.name ?? "Service"}
                      top={timeToTopOffset(appt.scheduled_at)}
                      height={minutesToPx(appt.duration_minutes)}
                      onClick={onAppointmentClick}
                      isConflict={conflictIds.has(appt.id)}
                      isDraggable={appt.status !== "cancelled"}
                      onResizeStart={handleResizeStart}
                    />
                  ))}
                </DroppableSlot>
              );
            })}
          </div>
        </TimeGrid>
      </div>
    </div>
    </DndContext>
  );
}
