import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MonthOverview } from "@/components/calendar/month-overview";
import type { Appointment } from "@/lib/api/appointments";

// May 2026 in IST — month has 31 days, starts on Friday
// Grid: Mon 27 Apr … Sun 31 May = 5 rows × 7 = 35 days
const MAY_2026 = new Date("2026-05-01T00:00:00+05:30");

const baseAppointment: Appointment = {
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

describe("MonthOverview", () => {
  it("renders the 7 weekday header labels", () => {
    render(
      <MonthOverview
        month={MAY_2026}
        appointments={[]}
        onDayClick={vi.fn()}
      />
    );

    for (const label of ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]) {
      expect(screen.getByText(label)).toBeInTheDocument();
    }
  });

  it("renders between 28 and 42 day buttons", () => {
    render(
      <MonthOverview
        month={MAY_2026}
        appointments={[]}
        onDayClick={vi.fn()}
      />
    );

    const buttons = screen.getAllByRole("button");
    expect(buttons.length).toBeGreaterThanOrEqual(28);
    expect(buttons.length).toBeLessThanOrEqual(42);
  });

  it("shows a dot with aria-label for a day that has an appointment", () => {
    render(
      <MonthOverview
        month={MAY_2026}
        appointments={[baseAppointment]}
        onDayClick={vi.fn()}
      />
    );

    // The dot span has aria-label matching "N appointments"
    const dot = screen.getByLabelText(/\d+ appointments/);
    expect(dot).toBeInTheDocument();
    expect(dot).toHaveAttribute("aria-label", "1 appointments");
  });

  it("calls onDayClick with the correct Date when a day button is clicked", async () => {
    const user = userEvent.setup();
    const onDayClick = vi.fn();

    render(
      <MonthOverview
        month={MAY_2026}
        appointments={[]}
        onDayClick={onDayClick}
      />
    );

    // Find the button for the 5th — it shows the text "5"
    // getAllByRole returns all buttons; find the one with text "5" that is in-month
    const buttons = screen.getAllByRole("button");
    // The grid starts Mon 27 Apr, so days 1-4 are buttons[4..7], day 5 is buttons[8]
    // Safer: find by text content "5"
    const dayFiveButton = buttons.find((btn) => btn.textContent?.trim() === "5");
    expect(dayFiveButton).toBeDefined();

    await user.click(dayFiveButton!);

    expect(onDayClick).toHaveBeenCalledTimes(1);
    const calledWith: Date = onDayClick.mock.calls[0][0];
    expect(calledWith).toBeInstanceOf(Date);
    // Should be May 5 2026
    expect(calledWith.getFullYear()).toBe(2026);
    expect(calledWith.getMonth()).toBe(4); // May = month index 4
    expect(calledWith.getDate()).toBe(5);
  });
});
