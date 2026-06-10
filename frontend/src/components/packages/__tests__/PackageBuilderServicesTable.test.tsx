import { describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { PackageBuilderServicesTable } from "@/components/packages/PackageBuilderServicesTable";
import type { LineItem } from "@/components/packages/PackageBuilderServicesTable";

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

// Mock ServicePicker so tests are isolated from the combobox / hook internals
vi.mock("@/components/packages/ServicePicker", () => ({
  ServicePicker: ({ value, onChange }: { value: string | null; onChange: (sel: { service_id: string; service_name: string } | null) => void }) => (
    <input
      data-testid="service-picker"
      value={value ?? ""}
      onChange={(e) =>
        onChange(e.target.value ? { service_id: e.target.value, service_name: e.target.value } : null)
      }
    />
  ),
}));

function makeItem(overrides: Partial<LineItem> = {}): LineItem {
  return {
    service_id: "s1",
    service_name: "Haircut",
    quantity: 1,
    unit_price_paise: 50000,
    locked: false,
    display_order: 0,
    max_redemptions: null,
    ...overrides,
  };
}

describe("PackageBuilderServicesTable", () => {
  it("renders a row for each item", () => {
    const items = [makeItem(), makeItem({ service_id: "s2", service_name: "Color" })];
    render(
      <PackageBuilderServicesTable
        items={items}
        onChange={vi.fn()}
        entitlementType="counted"
      />
    );
    const pickers = screen.getAllByTestId("service-picker");
    expect(pickers).toHaveLength(2);
  });

  it("calls onChange with updated service when ServicePicker fires", () => {
    const onChangeMock = vi.fn();
    render(
      <PackageBuilderServicesTable
        items={[makeItem()]}
        onChange={onChangeMock}
        entitlementType="counted"
      />
    );
    const picker = screen.getByTestId("service-picker");
    fireEvent.change(picker, { target: { value: "s99" } });
    expect(onChangeMock).toHaveBeenCalledWith(
      expect.arrayContaining([
        expect.objectContaining({ service_id: "s99", service_name: "s99" }),
      ])
    );
  });

  it("adds a new row when Add service is clicked", () => {
    const onChangeMock = vi.fn();
    render(
      <PackageBuilderServicesTable
        items={[makeItem()]}
        onChange={onChangeMock}
        entitlementType="counted"
      />
    );
    const addBtn = screen.getByRole("button", { name: /add service/i });
    addBtn.click();
    expect(onChangeMock).toHaveBeenCalledWith(expect.arrayContaining([expect.any(Object)]));
    const emitted = onChangeMock.mock.calls[0][0] as LineItem[];
    expect(emitted).toHaveLength(2);
  });

  it("removes the correct row when delete is clicked", () => {
    const onChangeMock = vi.fn();
    const items = [
      makeItem({ service_id: "s1" }),
      makeItem({ service_id: "s2" }),
    ];
    render(
      <PackageBuilderServicesTable
        items={items}
        onChange={onChangeMock}
        entitlementType="counted"
      />
    );
    // Click the first delete button (Trash2)
    const trashBtns = screen.getAllByRole("button").filter((b) =>
      b.querySelector("svg")
    );
    // Delete buttons are the last button in each row — find by aria / position
    // The rows render: Lock, Delete — so every other pair; simpler: just fire on the first trash
    const allButtons = screen.getAllByRole("button");
    // Buttons per row (limited): lock, delete. Plus "Add service" at the end.
    // Row 0 buttons are at index 0 (lock) and 1 (delete)
    allButtons[1].click();
    const emitted = onChangeMock.mock.calls[0][0] as LineItem[];
    expect(emitted).toHaveLength(1);
    expect(emitted[0].service_id).toBe("s2");
  });

  it("hides Qty column for unlimited entitlement type", () => {
    render(
      <PackageBuilderServicesTable
        items={[makeItem()]}
        onChange={vi.fn()}
        entitlementType="unlimited"
      />
    );
    // There should be no Qty header
    expect(screen.queryByText("Qty")).not.toBeInTheDocument();
  });

  it("shows Qty column for limited entitlement type", () => {
    render(
      <PackageBuilderServicesTable
        items={[makeItem()]}
        onChange={vi.fn()}
        entitlementType="counted"
      />
    );
    expect(screen.getByText("Qty")).toBeInTheDocument();
  });

  // New tests for max_redemptions / Limit column

  it("renders Limit input for each row", () => {
    render(
      <PackageBuilderServicesTable
        items={[makeItem({ max_redemptions: 3 })]}
        onChange={vi.fn()}
        entitlementType="counted"
      />
    );
    const limitInput = screen.getByRole("spinbutton", { name: /limit/i });
    expect(limitInput).toBeInTheDocument();
    expect((limitInput as HTMLInputElement).value).toBe("3");
  });

  it("calls onChange with max_redemptions when limit is edited", () => {
    const onChangeMock = vi.fn();
    render(
      <PackageBuilderServicesTable
        items={[makeItem()]}
        onChange={onChangeMock}
        entitlementType="counted"
      />
    );
    const limitInput = screen.getByRole("spinbutton", { name: /limit/i });
    fireEvent.change(limitInput, { target: { value: "5" } });
    expect(onChangeMock).toHaveBeenCalledWith(
      expect.arrayContaining([
        expect.objectContaining({ max_redemptions: 5 }),
      ])
    );
  });
});
