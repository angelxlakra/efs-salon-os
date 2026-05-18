import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const fieldVariants = cva(
  "w-full rounded-md border bg-surface-card text-text-primary placeholder:text-text-muted " +
    "focus-visible:outline-none focus-visible:border-accent focus-visible:shadow-[var(--shadow-focus)] " +
    "disabled:opacity-50 disabled:cursor-not-allowed",
  {
    variants: {
      size: {
        sm: "h-7 px-2.5 text-[13px]",
        md: "h-9 px-3 text-sm",
        lg: "h-11 px-4 text-base",
      },
      invalid: {
        true: "border-danger-border focus-visible:border-danger-fg",
        false: "border-border-default",
      },
    },
    defaultVariants: { size: "md", invalid: false },
  }
);

type InputProps = Omit<React.InputHTMLAttributes<HTMLInputElement>, "size"> &
  VariantProps<typeof fieldVariants> & {
    label?: string;
    hint?: string;
    error?: string;
    leadingAddon?: React.ReactNode;
    trailingAddon?: React.ReactNode;
  };

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, size, label, hint, error, leadingAddon, trailingAddon, id, ...props }, ref) => {
    const reactId = React.useId();
    const inputId = id ?? reactId;
    const describedById = error ? `${inputId}-err` : hint ? `${inputId}-hint` : undefined;

    return (
      <div className="flex flex-col gap-1">
        {label && (
          <label htmlFor={inputId} className="text-heading-sm text-text-secondary">
            {label}
          </label>
        )}
        <div className="relative flex items-center">
          {leadingAddon && (
            <span className="absolute left-3 text-text-muted" aria-hidden>
              {leadingAddon}
            </span>
          )}
          <input
            ref={ref}
            id={inputId}
            aria-invalid={!!error || undefined}
            aria-describedby={describedById}
            className={cn(
              fieldVariants({ size, invalid: !!error }),
              leadingAddon && "pl-8",
              trailingAddon && "pr-8",
              className
            )}
            {...props}
          />
          {trailingAddon && (
            <span className="absolute right-3 text-text-muted" aria-hidden>
              {trailingAddon}
            </span>
          )}
        </div>
        {error ? (
          <p id={`${inputId}-err`} className="text-body-sm text-danger-fg">
            {error}
          </p>
        ) : hint ? (
          <p id={`${inputId}-hint`} className="text-body-sm text-text-muted">
            {hint}
          </p>
        ) : null}
      </div>
    );
  }
);
Input.displayName = "Input";
