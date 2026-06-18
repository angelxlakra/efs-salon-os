"use client";
// Draft-while-focused numeric inputs. A fully-controlled value={formatted}
// input reformats on every keystroke, which breaks typing and backspace; these
// show the raw typed string while focused and normalize only on blur.

import { useState } from "react";
import { cn } from "@/lib/utils";

const baseInput =
  "h-[30px] rounded-md border border-border-default bg-surface-card px-2 text-[13px] " +
  "text-text-primary placeholder:text-text-muted tabular-nums w-full " +
  "focus-visible:outline-none focus-visible:border-accent focus-visible:shadow-[var(--shadow-focus)] " +
  "disabled:opacity-50 disabled:cursor-not-allowed";

type CountProps = {
  value: string;
  onCommit: (raw: string) => void;
  onBlurEmpty?: () => void;
} & Omit<
  React.InputHTMLAttributes<HTMLInputElement>,
  "value" | "onChange" | "onFocus" | "onBlur"
>;

/** Count input (qty, picks, sessions, daily-cap). Commits the raw string. */
export function CountCell({ value, onCommit, onBlurEmpty, className, ...rest }: CountProps) {
  const [draft, setDraft] = useState<string | null>(null);
  return (
    <input
      {...rest}
      type="number"
      value={draft ?? value}
      onFocus={() => setDraft(value)}
      onChange={(e) => {
        setDraft(e.target.value);
        onCommit(e.target.value);
      }}
      onBlur={() => {
        if (draft === "" && onBlurEmpty) onBlurEmpty();
        setDraft(null);
      }}
      className={cn(baseInput, className)}
    />
  );
}

const rupees = (paise: number) => (paise / 100).toFixed(2);
const toPaise = (r: string) => Math.round((parseFloat(r || "0") || 0) * 100);

type MoneyProps = {
  valuePaise: number;
  onCommit: (paise: number) => void;
} & Omit<
  React.InputHTMLAttributes<HTMLInputElement>,
  "value" | "onChange" | "onFocus" | "onBlur" | "type"
>;

/** Money input: shows rupees, stores/commits paise integers. */
export function MoneyCell({ valuePaise, onCommit, className, ...rest }: MoneyProps) {
  const [draft, setDraft] = useState<string | null>(null);
  return (
    <input
      {...rest}
      type="number"
      step="0.01"
      min={0}
      value={draft ?? rupees(valuePaise)}
      onFocus={() => setDraft(rupees(valuePaise))}
      onChange={(e) => {
        setDraft(e.target.value);
        onCommit(toPaise(e.target.value));
      }}
      onBlur={() => setDraft(null)}
      className={cn(baseInput, "text-right", className)}
    />
  );
}
