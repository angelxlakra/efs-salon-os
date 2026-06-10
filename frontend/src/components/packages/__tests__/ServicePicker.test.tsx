import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ServicePicker } from "@/components/packages/ServicePicker";

// jsdom lacks ResizeObserver and Element.scrollIntoView, both of which cmdk uses internally.
class ResizeObserverStub {
  observe() {}
  unobserve() {}
  disconnect() {}
}
globalThis.ResizeObserver =
  globalThis.ResizeObserver ??
  (ResizeObserverStub as unknown as typeof ResizeObserver);
if (!Element.prototype.scrollIntoView) {
  Element.prototype.scrollIntoView = function scrollIntoView() {};
}

const MOCK_SERVICES = [
  {
    id: "s1",
    name: "Haircut",
    base_price: 50000,
    duration_minutes: 30,
    category_name: "Hair",
  },
];

vi.mock("@/hooks/useServicesList", () => ({
  useServicesList: () => ({
    services: MOCK_SERVICES,
    loading: false,
    error: null,
  }),
}));

describe("ServicePicker", () => {
  it("shows selected service name", () => {
    render(<ServicePicker value="s1" onChange={vi.fn()} />);
    expect(screen.getByText("Haircut")).toBeInTheDocument();
  });

  it("calls onChange with id and name on selection", async () => {
    const mockFn = vi.fn();
    const user = userEvent.setup();

    render(<ServicePicker value={null} onChange={mockFn} />);

    // Open the combobox by clicking the trigger button
    const trigger = screen.getByRole("combobox");
    await user.click(trigger);

    // Click the "Haircut" option
    const option = await screen.findByText("Haircut");
    await user.click(option);

    expect(mockFn).toHaveBeenCalledWith({
      service_id: "s1",
      service_name: "Haircut",
    });
  });
});
