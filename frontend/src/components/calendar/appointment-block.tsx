"use client";

import * as React from "react";
import { cn } from "@/lib/utils";
import { getServiceColor, isOffHours, formatApptTime } from "@/components/calendar/utils";
import type { Appointment } from "@/lib/api/appointments";
import { useDraggable } from "@dnd-kit/core";
import { CSS } from "@dnd-kit/utilities";

type AppointmentBlockProps = {
  appointment: Appointment;
  serviceName: string;
  top: number;
  height: number;
  onClick: (appointment: Appointment) => void;
  isConflict?: boolean;
  isDragging?: boolean;
  isDraggable?: boolean;
  onResizeStart?: (e: React.MouseEvent, appointment: Appointment) => void;
};

export function AppointmentBlock({
  appointment,
  serviceName,
  top,
  height,
  onClick,
  isConflict = false,
  isDragging = false,
  isDraggable = true,
  onResizeStart,
}: AppointmentBlockProps) {
  const color = getServiceColor(appointment.service_id ?? "");
  const offHours = isOffHours(appointment.scheduled_at);
  const timeStr = formatApptTime(appointment.scheduled_at);

  const { attributes, listeners, setNodeRef, transform, isDragging: dndIsDragging } = useDraggable({
    id: appointment.id,
    data: { appointment },
    disabled: !isDraggable,
  });

  return (
    <div
      ref={setNodeRef}
      {...attributes}
      {...listeners}
      role="button"
      tabIndex={0}
      aria-label={`${appointment.customer_name} — ${serviceName}`}
      data-conflict={isConflict || undefined}
      data-status={appointment.status}
      onClick={(e) => { if (!dndIsDragging) { e.stopPropagation(); onClick(appointment); } }}
      onKeyDown={(e) => e.key === "Enter" && onClick(appointment)}
      className={cn(
        "absolute left-0.5 right-0.5 rounded-md px-2 py-1 cursor-grab select-none overflow-hidden",
        "border-l-[3px] transition-opacity",
        "hover:brightness-95 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent",
        (isDragging || dndIsDragging) && "opacity-50 cursor-grabbing z-50",
        isConflict && "ring-2 ring-danger-fg ring-offset-1",
        appointment.status === "cancelled" && "opacity-40 line-through"
      )}
      style={{
        top,
        height: Math.max(height, 24),
        borderLeftColor: color,
        backgroundColor: `color-mix(in srgb, ${color} 15%, transparent)`,
        transform: CSS.Translate.toString(transform) ?? undefined,
      }}
    >
      <div className="flex items-start justify-between gap-0.5">
        <p className="text-[11px] font-semibold text-text-primary truncate leading-tight">
          {appointment.customer_name}
        </p>
        {offHours && (
          <span className="shrink-0 text-[8px] font-bold text-warning-fg bg-warning-bg-soft px-0.5 rounded leading-tight whitespace-nowrap">
            ⚠ off-hrs
          </span>
        )}
        {isConflict && !offHours && (
          <span className="shrink-0 text-[9px] text-danger-fg font-bold leading-tight">⚠</span>
        )}
      </div>
      {height > 36 && (
        <p className="text-[10px] text-text-secondary truncate leading-tight">
          {timeStr} · {serviceName}
        </p>
      )}
      <div
        role="separator"
        aria-hidden
        className="absolute bottom-0 left-0 right-0 h-2 cursor-s-resize bg-transparent hover:bg-border-default rounded-b-md"
        onMouseDown={(e) => {
          e.stopPropagation();
          onResizeStart?.(e, appointment);
        }}
      />
    </div>
  );
}
