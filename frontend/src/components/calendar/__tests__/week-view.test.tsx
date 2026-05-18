import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { WeekView } from "@/components/calendar/week-view";
import type { Appointment, ServiceItem } from "@/lib/api/appointments";

const services: ServiceItem[] = [
  { id: "01SVC000001", name: "Hair Cut", duration_minutes: 60, base_price: 50000, category_name: "Cuts" },
];

const monday = new Date("2026-05-04T00:00:00+05:30");

const appt: Appointment = {
  id: "01APPT000001",
  ticket_number: "TKT-260504-001",
  visit_id: null,
  customer_id: null,
  customer_name: "Priya Sharma",
  customer_phone: "9876543210",
  service_id: "01SVC000001",
  assigned_staff_id: "01STF000001",
  scheduled_at: "2026-05-04T10:00:00+05:30",
  duration_minutes: 60,
  status: "scheduled",
  booking_notes: null,
  service_notes: null,
  checked_in_at: null,
  started_at: null,
  completed_at: null,
  cancelled_at: null,
  created_at: "2026-05-04T09:00:00+05:30",
  updated_at: "2026-05-04T09:00:00+05:30",
};

describe("WeekView", () => {
  it("renders 7 day column headers", () => {
    render(
      <WeekView
        appointments={[]}
        services={services}
        weekStart={monday}
        onAppointmentClick={vi.fn()}
        onSlotClick={vi.fn()}
      />
    );
    // Mon–Sun abbreviated day labels
    expect(screen.getByText("Mon")).toBeInTheDocument();
    expect(screen.getByText("Sun")).toBeInTheDocument();
  });

  it("renders an appointment in the correct day column", () => {
    render(
      <WeekView
        appointments={[appt]}
        services={services}
        weekStart={monday}
        onAppointmentClick={vi.fn()}
        onSlotClick={vi.fn()}
      />
    );
    expect(screen.getByText("Priya Sharma")).toBeInTheDocument();
  });

  it("calls onAppointmentClick when an appointment is clicked", async () => {
    const onClick = vi.fn();
    render(
      <WeekView
        appointments={[appt]}
        services={services}
        weekStart={monday}
        onAppointmentClick={onClick}
        onSlotClick={vi.fn()}
      />
    );
    await userEvent.click(screen.getByText("Priya Sharma"));
    expect(onClick).toHaveBeenCalledOnce();
    expect(onClick).toHaveBeenCalledWith(appt);
  });
});
