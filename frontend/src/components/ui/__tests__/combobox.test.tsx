import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Combobox } from "@/components/ui/combobox";

// jsdom lacks ResizeObserver and Element.scrollIntoView, both of which cmdk uses internally.
class ResizeObserverStub {
  observe() {}
  unobserve() {}
  disconnect() {}
}
globalThis.ResizeObserver = globalThis.ResizeObserver ?? (ResizeObserverStub as unknown as typeof ResizeObserver);
if (!Element.prototype.scrollIntoView) {
  Element.prototype.scrollIntoView = function scrollIntoView() {};
}

const options = [
  { value: "1", label: "Priya" },
  { value: "2", label: "Rajni" },
  { value: "3", label: "Anjali" },
];

describe("Combobox", () => {
  it("shows selected value label on trigger", () => {
    render(<Combobox options={options} value="2" onChange={() => {}} placeholder="Pick customer" />);
    expect(screen.getByRole("combobox")).toHaveTextContent("Rajni");
  });

  it("shows placeholder when no value", () => {
    render(<Combobox options={options} value={null} onChange={() => {}} placeholder="Pick customer" />);
    expect(screen.getByRole("combobox")).toHaveTextContent("Pick customer");
  });

  it("filters options when typing", async () => {
    const user = userEvent.setup();
    render(<Combobox options={options} value={null} onChange={() => {}} placeholder="Pick" />);
    await user.click(screen.getByRole("combobox"));
    await user.type(screen.getByPlaceholderText(/search/i), "raj");
    expect(screen.getByText("Rajni")).toBeInTheDocument();
    expect(screen.queryByText("Priya")).not.toBeInTheDocument();
  });

  it("calls onChange with option value on select", async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    render(<Combobox options={options} value={null} onChange={onChange} placeholder="Pick" />);
    await user.click(screen.getByRole("combobox"));
    await user.click(screen.getByText("Anjali"));
    expect(onChange).toHaveBeenCalledWith("3");
  });
});
