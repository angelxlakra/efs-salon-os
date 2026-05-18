import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { DayView } from "@/components/calendar/day-view";
import type { Appointment, StaffMember, ServiceItem } from "@/lib/api/appointments";

const staff: StaffMember[] = [
  { id: "s1", display_name: "Rahul", specialization: null, is_active: true, is_service_provider: true },
  { id: "s2", display_name: "Priya", specialization: null, is_active: true, is_service_provider: true },
];

const services: ServiceItem[] = [
  { id: "svc1", name: "Hair Cut", base_price: 30000, duration_minutes: 30, category_name: "Hair" },
];

const appt: Appointment = {
  id: "a1",
  ticket_number: "TKT-260505-001",
  visit_id: null,
  customer_id: null,
  customer_name: "Test Customer",
  customer_phone: null,
  service_id: "svc1",
  assigned_staff_id: "s1",
  scheduled_at: "2026-05-05T10:00:00+05:30",
  duration_minutes: 30,
  status: "scheduled",
  booking_notes: null,
  service_notes: null,
  checked_in_at: null,
  started_at: null,
  completed_at: null,
  cancelled_at: null,
  created_at: "2026-05-05T09:00:00+05:30",
  updated_at: "2026-05-05T09:00:00+05:30",
};

describe("DayView", () => {
  it("renders a header cell for each staff member", () => {
    render(
      <DayView
        appointments={[]}
        staff={staff}
        services={services}
        onAppointmentClick={vi.fn()}
        onSlotClick={vi.fn()}
        onAppointmentUpdate={vi.fn()}
      />
    );
    expect(screen.getByText("Rahul")).toBeInTheDocument();
    expect(screen.getByText("Priya")).toBeInTheDocument();
  });

  it("renders an Unassigned column header", () => {
    render(
      <DayView
        appointments={[]}
        staff={staff}
        services={services}
        onAppointmentClick={vi.fn()}
        onSlotClick={vi.fn()}
        onAppointmentUpdate={vi.fn()}
      />
    );
    expect(screen.getByText("Unassigned")).toBeInTheDocument();
  });

  it("renders an appointment block in the correct staff column", () => {
    render(
      <DayView
        appointments={[appt]}
        staff={staff}
        services={services}
        onAppointmentClick={vi.fn()}
        onSlotClick={vi.fn()}
        onAppointmentUpdate={vi.fn()}
      />
    );
    expect(screen.getByText("Test Customer")).toBeInTheDocument();
  });

  it("calls onSlotClick when an empty slot is clicked", async () => {
    const onSlotClick = vi.fn();
    render(
      <DayView
        appointments={[]}
        staff={staff}
        services={services}
        onAppointmentClick={vi.fn()}
        onSlotClick={onSlotClick}
        onAppointmentUpdate={vi.fn()}
      />
    );
    const slots = screen.getAllByTestId("grid-slot");
    await userEvent.click(slots[0]);
    expect(onSlotClick).toHaveBeenCalledOnce();
  });
});
