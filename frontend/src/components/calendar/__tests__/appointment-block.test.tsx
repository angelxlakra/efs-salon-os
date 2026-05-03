import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AppointmentBlock } from "@/components/calendar/appointment-block";
import type { Appointment } from "@/lib/api/appointments";

const base: Appointment = {
  id: "01APPT000001",
  ticket_number: "TKT-260505-001",
  visit_id: null,
  customer_id: null,
  customer_name: "Priya Sharma",
  customer_phone: "9876543210",
  service_id: "01SVC000001",
  assigned_staff_id: "01STF000001",
  scheduled_at: "2026-05-05T10:00:00+05:30",
  duration_minutes: 60,
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

describe("AppointmentBlock", () => {
  it("renders the customer name", () => {
    render(
      <AppointmentBlock
        appointment={base}
        serviceName="Hair Cut"
        top={64}
        height={64}
        onClick={vi.fn()}
      />
    );
    expect(screen.getByText("Priya Sharma")).toBeInTheDocument();
  });

  it("renders the service name", () => {
    render(
      <AppointmentBlock
        appointment={base}
        serviceName="Hair Cut"
        top={64}
        height={64}
        onClick={vi.fn()}
      />
    );
    expect(screen.getByText("Hair Cut")).toBeInTheDocument();
  });

  it("applies conflict styling when isConflict=true", () => {
    const { container } = render(
      <AppointmentBlock
        appointment={base}
        serviceName="Hair Cut"
        top={64}
        height={64}
        onClick={vi.fn()}
        isConflict
      />
    );
    expect(container.firstChild).toHaveAttribute("data-conflict", "true");
  });

  it("calls onClick when clicked", async () => {
    const onClick = vi.fn();
    render(
      <AppointmentBlock
        appointment={base}
        serviceName="Hair Cut"
        top={64}
        height={64}
        onClick={onClick}
      />
    );
    await userEvent.click(screen.getByText("Priya Sharma"));
    expect(onClick).toHaveBeenCalledOnce();
  });

  it("renders a resize handle div", () => {
    render(
      <AppointmentBlock
        appointment={base}
        serviceName="Hair Cut"
        top={64}
        height={64}
        onClick={vi.fn()}
      />
    );
    expect(screen.getByRole("separator", { hidden: true })).toBeInTheDocument();
  });
});
