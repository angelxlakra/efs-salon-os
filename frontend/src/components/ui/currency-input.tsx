import * as React from "react";
import { Input } from "@/components/ui/input";

type Props = Omit<React.ComponentProps<typeof Input>, "value" | "onChange" | "leadingAddon" | "type"> & {
  /** Value in paise (integer). */
  value: number;
  /** Called with updated paise value. */
  onChange: (paise: number) => void;
};

/**
 * Displays a paise integer as a rupees decimal and normalises back on change.
 * All money in Aasan is stored as paise; this is the only place rupees↔paise
 * conversion should live in forms.
 */
export const CurrencyInput = React.forwardRef<HTMLInputElement, Props>(
  ({ value, onChange, ...rest }, ref) => {
    const [text, setText] = React.useState(() => (value / 100).toFixed(2));
    const lastEmittedRef = React.useRef<number>(value);

    React.useEffect(() => {
      if (value !== lastEmittedRef.current) {
        setText((value / 100).toFixed(2));
        lastEmittedRef.current = value;
      }
    }, [value]);

    return (
      <Input
        ref={ref}
        type="text"
        inputMode="decimal"
        leadingAddon="₹"
        className="tabular"
        value={text}
        onChange={(e) => {
          const raw = e.target.value;
          setText(raw);
          const numeric = parseFloat(raw);
          if (!Number.isFinite(numeric) || numeric < 0) return;
          const paise = Math.round(numeric * 100) + 0; // normalises -0 → +0
          if (!Number.isSafeInteger(paise) || paise < 0) return;
          lastEmittedRef.current = paise;
          onChange(paise);
        }}
        onBlur={() => {
          // Normalise on blur — e.g. "250" → "250.00"
          const numeric = parseFloat(text);
          if (Number.isFinite(numeric) && numeric >= 0) {
            setText(numeric.toFixed(2));
          } else {
            setText((value / 100).toFixed(2));
          }
        }}
        {...rest}
      />
    );
  }
);
CurrencyInput.displayName = "CurrencyInput";
