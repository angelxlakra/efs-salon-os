"use client";

import * as React from "react";
import {
  format,
  addDays,
  subDays,
  addWeeks,
  subWeeks,
  addMonths,
  subMonths,
  startOfWeek,
  startOfMonth,
} from "date-fns";
import { ChevronLeft, ChevronRight, Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { DayView } from "@/components/calendar/day-view";
import { WeekView } from "@/components/calendar/week-view";
import { MonthOverview } from "@/components/calendar/month-overview";
import { AppointmentFormDialog } from "@/components/calendar/appointment-form-dialog";
import { useCalendarKeyboard } from "@/components/calendar/use-calendar-keyboard";
import {
  listAppointments,
  listActiveStaff,
  listServices,
  updateAppointment,
} from "@/lib/api/appointments";
import type { Appointment, StaffMember, ServiceItem } from "@/lib/api/appointments";
import { toast } from "sonner";
import { cn } from "@/lib/utils";

type CalendarView = "day" | "week" | "month";

export default function AppointmentsPage() {
  const [view, setView] = React.useState<CalendarView>("day");
  const [date, setDate] = React.useState<Date>(new Date());

  // Data
  const [appointments, setAppointments] = React.useState<Appointment[]>([]);
  const [staff, setStaff] = React.useState<StaffMember[]>([]);
  const [services, setServices] = React.useState<ServiceItem[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);

  // Dialog state
  const [formOpen, setFormOpen] = React.useState(false);
  const [selectedAppt, setSelectedAppt] = React.useState<Appointment | undefined>();
  const [defaultDatetime, setDefaultDatetime] = React.useState<string | undefined>();
  const [defaultStaffId, setDefaultStaffId] = React.useState<string | undefined>();

  // -- Static data (staff + services, fetched once) -------------------------
  React.useEffect(() => {
    Promise.all([listActiveStaff(), listServices()])
      .then(([s, svc]) => { setStaff(s); setServices(svc); })
      .catch(() => toast.error("Failed to load staff or services"));
  }, []);

  // ── Appointments (re-fetch when date or view changes) ─────────────────────
  const refetchRef = React.useRef<() => void>(() => {});

  React.useEffect(() => {
    let cancelled = false;

    const run = async () => {
      setLoading(true);
      setError(null);
      try {
        let dates: string[];
        if (view === "day") {
          dates = [format(date, "yyyy-MM-dd")];
        } else if (view === "week") {
          const ws = startOfWeek(date, { weekStartsOn: 1 });
          dates = Array.from({ length: 7 }, (_, i) =>
            format(addDays(ws, i), "yyyy-MM-dd")
          );
        } else {
          // TODO: replace with a single date-range endpoint to avoid 28-31 concurrent requests.
          const ms = startOfMonth(date);
          const days = new Date(date.getFullYear(), date.getMonth() + 1, 0).getDate();
          dates = Array.from({ length: days }, (_, i) =>
            format(addDays(ms, i), "yyyy-MM-dd")
          );
        }
        const results = await Promise.all(dates.map((date) => listAppointments(date)));
        if (cancelled) return;
        const seen = new Set<string>();
        const all: Appointment[] = [];
        results.flat().forEach((a) => {
          if (!seen.has(a.id)) { seen.add(a.id); all.push(a); }
        });
        setAppointments(all);
      } catch {
        if (!cancelled) setError("Failed to load appointments");
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    refetchRef.current = run;
    run();
    return () => { cancelled = true; };
  }, [date, view]);

  // -- Navigation helpers ---------------------------------------------------
  const navigate = (dir: "prev" | "next") => {
    if (view === "day") setDate((d) => (dir === "next" ? addDays(d, 1) : subDays(d, 1)));
    else if (view === "week") setDate((d) => (dir === "next" ? addWeeks(d, 1) : subWeeks(d, 1)));
    else setDate((d) => (dir === "next" ? addMonths(d, 1) : subMonths(d, 1)));
  };

  const pageTitle = React.useMemo(() => {
    if (view === "day") return format(date, "EEEE, d MMMM yyyy");
    if (view === "week") {
      const ws = startOfWeek(date, { weekStartsOn: 1 });
      return `Week of ${format(ws, "d MMM")}`;
    }
    return format(date, "MMMM yyyy");
  }, [view, date]);

  // -- Optimistic appointment update ----------------------------------------
  const handleAppointmentUpdate = React.useCallback(
    async (id: string, patch: { scheduled_at?: string; duration_minutes?: number }) => {
      setAppointments((prev) => prev.map((a) => (a.id === id ? { ...a, ...patch } : a)));
      try {
        const updated = await updateAppointment(id, patch);
        setAppointments((prev) => prev.map((a) => (a.id === id ? updated : a)));
      } catch {
        toast.error("Failed to update appointment");
        refetchRef.current();
      }
    },
    []
  );

  // -- Form interactions ----------------------------------------------------
  const openNewForm = (staffId?: string, datetime?: string) => {
    setSelectedAppt(undefined);
    setDefaultStaffId(staffId ?? undefined);
    setDefaultDatetime(datetime ?? `${format(date, "yyyy-MM-dd")}T10:00:00`);
    setFormOpen(true);
  };

  const handleSlotClick = (staffId: string | null, datetime: string) => {
    openNewForm(staffId ?? undefined, datetime);
  };

  const handleAppointmentClick = (appt: Appointment) => {
    setSelectedAppt(appt);
    setDefaultDatetime(undefined);
    setDefaultStaffId(undefined);
    setFormOpen(true);
  };

  const handleFormSaved = (appt: Appointment) => {
    setAppointments((prev) => {
      const exists = prev.find((a) => a.id === appt.id);
      if (exists) return prev.map((a) => (a.id === appt.id ? appt : a));
      return [...prev, appt];
    });
  };

  // -- Keyboard shortcuts ---------------------------------------------------
  useCalendarKeyboard({
    onNew: () => openNewForm(),
    onPrev: () => navigate("prev"),
    onNext: () => navigate("next"),
    onGoToday: () => setDate(new Date()),
    onSetView: setView,
  });

  // -- Render ---------------------------------------------------------------
  const weekStart = startOfWeek(date, { weekStartsOn: 1 });

  return (
    <div className="flex flex-col h-[calc(100dvh-3rem)] overflow-hidden">
      {/* Topbar */}
      <div className="flex items-center justify-between gap-3 px-4 py-2 border-b border-border-subtle bg-surface-card shrink-0">
        {/* View switcher — hidden on mobile (day view only per spec) */}
        <div className="hidden sm:flex rounded-md border border-border-default overflow-hidden">
          {(["day", "week", "month"] as CalendarView[]).map((v) => (
            <button
              key={v}
              type="button"
              onClick={() => setView(v)}
              className={cn(
                "px-3 py-1 text-[13px] font-medium capitalize transition-colors",
                v === view
                  ? "bg-accent text-accent-fg"
                  : "text-text-secondary hover:bg-surface-row-hover"
              )}
            >
              {v}
            </button>
          ))}
        </div>

        {/* Date nav */}
        <div className="flex items-center gap-1">
          <Button variant="icon" size="sm" onClick={() => navigate("prev")} aria-label="Previous">
            <ChevronLeft className="size-4" />
          </Button>
          <button
            type="button"
            onClick={() => setDate(new Date())}
            className="text-body-sm font-medium text-text-primary px-2 hover:text-accent min-w-[160px] text-center"
          >
            {pageTitle}
          </button>
          <Button variant="icon" size="sm" onClick={() => navigate("next")} aria-label="Next">
            <ChevronRight className="size-4" />
          </Button>
        </div>

        {/* New appointment */}
        <Button onClick={() => openNewForm()} size="sm" leadingIcon={<Plus className="size-3.5" />}>
          New
        </Button>
      </div>

      {/* Content area */}
      <div className="flex-1 overflow-hidden">
        {loading ? (
          <div className="p-6 flex flex-col gap-3">
            <Skeleton shape="text" width="40%" />
            <Skeleton shape="row" />
            <Skeleton shape="row" />
            <Skeleton shape="row" />
          </div>
        ) : error ? (
          <div className="p-6 text-danger-fg text-body-sm">{error}</div>
        ) : view === "day" ? (
          <DayView
            appointments={appointments}
            staff={staff}
            services={services}
            date={date}
            onAppointmentClick={handleAppointmentClick}
            onSlotClick={handleSlotClick}
            onAppointmentUpdate={handleAppointmentUpdate}
          />
        ) : view === "week" ? (
          <WeekView
            appointments={appointments}
            services={services}
            weekStart={weekStart}
            onAppointmentClick={handleAppointmentClick}
            onSlotClick={handleSlotClick}
          />
        ) : (
          <MonthOverview
            month={date}
            appointments={appointments}
            onDayClick={(d) => { setDate(d); setView("day"); }}
            selectedDate={date}
          />
        )}
      </div>

      {/* Form dialog */}
      <AppointmentFormDialog
        open={formOpen}
        onOpenChange={setFormOpen}
        appointment={selectedAppt}
        defaultDatetime={defaultDatetime}
        defaultStaffId={defaultStaffId}
        staff={staff}
        services={services}
        onSaved={handleFormSaved}
      />
    </div>
  );
}
