import { describe, expect, it } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { useState } from "react";
import { PackageBuilderDiscountControl } from "@/components/packages/PackageBuilderDiscountControl";
import { toDiscountPayload } from "@/components/packages/PackageBuilder";
import type { DiscountMode } from "@/types/package";

// Stateful harness mirroring how PackageBuilder wires the control
function Harness({ totalPaise = 0 }: { totalPaise?: number }) {
  const [discount, setDiscount] = useState<
    { mode: DiscountMode; value: string } | undefined
  >(undefined);
  return (
    <div>
      <PackageBuilderDiscountControl
        totalPaise={totalPaise}
        discount={discount}
        onChange={setDiscount}
      />
      <output data-testid="emitted">
        {discount ? `${discount.mode}:${discount.value}` : "none"}
      </output>
    </div>
  );
}

// ₹1000 package total
const TOTAL = 100000;

function field(label: string): HTMLInputElement {
  return screen.getByLabelText(label) as HTMLInputElement;
}

describe("PackageBuilderDiscountControl", () => {
  it("derives ₹ off and final price when % is entered", () => {
    render(<Harness totalPaise={TOTAL} />);

    fireEvent.change(field("% off"), { target: { value: "10" } });

    expect(field("₹ off").value).toBe("100");
    expect(field("Final price").value).toBe("900");
    expect(screen.getByTestId("emitted").textContent).toBe("pct:10");
  });

  it("derives % and final price when ₹ off is entered", () => {
    render(<Harness totalPaise={TOTAL} />);

    fireEvent.change(field("₹ off"), { target: { value: "250" } });

    expect(field("% off").value).toBe("25");
    expect(field("Final price").value).toBe("750");
    expect(screen.getByTestId("emitted").textContent).toBe("flat:250");
  });

  it("derives % and ₹ off when final price is entered", () => {
    render(<Harness totalPaise={TOTAL} />);

    fireEvent.change(field("Final price"), { target: { value: "900" } });

    expect(field("% off").value).toBe("10");
    expect(field("₹ off").value).toBe("100");
    expect(screen.getByTestId("emitted").textContent).toBe("final:900");
  });

  it("clears the discount when the edited field is emptied", () => {
    render(<Harness totalPaise={TOTAL} />);

    fireEvent.change(field("% off"), { target: { value: "10" } });
    fireEvent.change(field("% off"), { target: { value: "" } });

    expect(field("₹ off").value).toBe("");
    expect(field("Final price").value).toBe("");
    expect(screen.getByTestId("emitted").textContent).toBe("none");
  });

  it("shows no derived values when the package total is zero", () => {
    render(<Harness totalPaise={0} />);

    fireEvent.change(field("% off"), { target: { value: "10" } });

    expect(field("₹ off").value).toBe("");
    expect(field("Final price").value).toBe("");
    expect(screen.getByTestId("emitted").textContent).toBe("pct:10");
  });
});

describe("toDiscountPayload", () => {
  it("converts flat/final rupee values to paise for the API", () => {
    // Regression: final ₹3499 was sent raw and read by the backend as 3499 paise
    expect(toDiscountPayload({ mode: "final", value: "3499" })).toEqual({
      mode: "final",
      value: "349900",
    });
    expect(toDiscountPayload({ mode: "flat", value: "250.50" })).toEqual({
      mode: "flat",
      value: "25050",
    });
  });

  it("passes percentages through unchanged", () => {
    expect(toDiscountPayload({ mode: "pct", value: "12.5" })).toEqual({
      mode: "pct",
      value: "12.5",
    });
  });

  it("returns undefined for empty or invalid values", () => {
    expect(toDiscountPayload(undefined)).toBeUndefined();
    expect(toDiscountPayload({ mode: "final", value: "" })).toBeUndefined();
    expect(toDiscountPayload({ mode: "final", value: "abc" })).toBeUndefined();
  });
});
