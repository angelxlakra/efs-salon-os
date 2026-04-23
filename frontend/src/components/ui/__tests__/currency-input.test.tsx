import * as React from "react";
import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { CurrencyInput } from "@/components/ui/currency-input";

describe("CurrencyInput", () => {
  it("displays paise as rupees with 2 decimals", () => {
    render(<CurrencyInput label="Amount" value={24800} onChange={() => {}} />);
    const input = screen.getByLabelText("Amount") as HTMLInputElement;
    expect(input.value).toBe("248.00");
  });

  it("calls onChange with paise integer when user types rupees", async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    render(<CurrencyInput label="Amount" value={0} onChange={onChange} />);
    const input = screen.getByLabelText("Amount");
    await user.clear(input);
    await user.type(input, "250");
    // Last call should be paise = 25000
    const last = onChange.mock.calls[onChange.mock.calls.length - 1][0];
    expect(last).toBe(25000);
  });

  it("rejects negative values", async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    render(<CurrencyInput label="Amount" value={0} onChange={onChange} />);
    const input = screen.getByLabelText("Amount");
    await user.clear(input);
    await user.type(input, "-5");
    // onChange never called with negative paise
    for (const [arg] of onChange.mock.calls) expect(arg).toBeGreaterThanOrEqual(0);
  });

  it("renders ₹ leading addon", () => {
    render(<CurrencyInput label="Amount" value={0} onChange={() => {}} />);
    expect(screen.getByText("₹")).toBeInTheDocument();
  });

  it("preserves decimal point while typing (no cursor jump on echo)", async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    function Wrapper() {
      const [v, setV] = React.useState(0);
      return (
        <CurrencyInput
          label="Amount"
          value={v}
          onChange={(p) => {
            setV(p);
            onChange(p);
          }}
        />
      );
    }
    render(<Wrapper />);
    const input = screen.getByLabelText("Amount") as HTMLInputElement;
    await user.clear(input);
    await user.type(input, "12.50");
    // The last onChange must reflect the full 12.50, not just 12 or 1250 after a reset
    const last = onChange.mock.calls[onChange.mock.calls.length - 1][0];
    expect(last).toBe(1250);
    // And the visible text must still contain the user's decimal entry
    expect(input.value).toMatch(/^12\.50?$/);
  });

  it("does not emit -0 paise", async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    render(<CurrencyInput label="Amount" value={0} onChange={onChange} />);
    const input = screen.getByLabelText("Amount");
    await user.clear(input);
    await user.type(input, "-0");
    for (const [arg] of onChange.mock.calls) {
      expect(Object.is(arg, -0)).toBe(false);
    }
  });

  it("rejects values that overflow Number.isSafeInteger in paise", async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    render(<CurrencyInput label="Amount" value={0} onChange={onChange} />);
    const input = screen.getByLabelText("Amount");
    await user.clear(input);
    await user.type(input, "1e308");
    // No onChange call should deliver Infinity or an unsafe integer
    for (const [arg] of onChange.mock.calls) {
      expect(Number.isFinite(arg)).toBe(true);
      expect(Number.isSafeInteger(arg)).toBe(true);
    }
  });
});
