import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { TimeGrid } from "@/components/calendar/time-grid";
import { DAY_START_HOUR, DAY_END_HOUR, GRID_HEIGHT } from "@/components/calendar/utils";

describe("TimeGrid", () => {
  it("renders an hour label for each hour from DAY_START_HOUR to DAY_END_HOUR", () => {
    render(<TimeGrid><div /></TimeGrid>);
    for (let h = DAY_START_HOUR; h < DAY_END_HOUR; h++) {
      const label = h < 12 ? `${h} AM` : h === 12 ? "12 PM" : `${h - 12} PM`;
      expect(screen.getByText(label)).toBeInTheDocument();
    }
  });

  it("grid body has min-height equal to GRID_HEIGHT", () => {
    const { container } = render(<TimeGrid><div data-testid="child" /></TimeGrid>);
    const body = container.querySelector("[data-testid='grid-body']");
    expect(body).toBeTruthy();
    expect((body as HTMLElement).style.minHeight).toBe(`${GRID_HEIGHT}px`);
  });

  it("renders children inside the grid body", () => {
    render(<TimeGrid><div data-testid="inner" /></TimeGrid>);
    expect(screen.getByTestId("inner")).toBeInTheDocument();
  });
});
