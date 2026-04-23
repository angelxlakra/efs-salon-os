import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import { Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md font-medium transition-colors " +
    "focus-visible:outline-none disabled:opacity-50 disabled:pointer-events-none " +
    "[&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0",
  {
    variants: {
      variant: {
        primary:
          "bg-accent text-accent-fg hover:bg-accent-hover active:bg-accent-active",
        secondary:
          "bg-surface-card text-text-primary border border-border-default hover:bg-surface-row-hover",
        ghost:
          "text-text-primary hover:bg-surface-row-hover",
        danger:
          "bg-danger-fg text-text-inverse hover:opacity-90",
        icon:
          "text-text-secondary hover:bg-surface-row-hover hover:text-text-primary",
      },
      size: {
        sm: "h-7 px-3 text-[13px]",
        md: "h-9 px-4 text-sm",
        lg: "h-11 px-6 text-base",
      },
      fullWidth: {
        true: "w-full",
      },
    },
    compoundVariants: [
      { variant: "icon", size: "sm", class: "h-7 w-7 p-0" },
      { variant: "icon", size: "md", class: "h-9 w-9 p-0" },
      { variant: "icon", size: "lg", class: "h-11 w-11 p-0" },
    ],
    defaultVariants: { variant: "primary", size: "md" },
  }
);

type ButtonProps = React.ButtonHTMLAttributes<HTMLButtonElement> &
  VariantProps<typeof buttonVariants> & {
    asChild?: boolean;
    loading?: boolean;
    leadingIcon?: React.ReactNode;
    trailingIcon?: React.ReactNode;
  };

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  (
    { className, variant, size, fullWidth, asChild, loading, disabled, leadingIcon, trailingIcon, children, ...props },
    ref
  ) => {
    const Comp = asChild ? Slot : "button";
    return (
      <Comp
        ref={ref}
        className={cn(buttonVariants({ variant, size, fullWidth }), className)}
        disabled={disabled || loading}
        aria-busy={loading || undefined}
        {...props}
      >
        {loading ? (
          <>
            <Loader2 data-slot="spinner" className="animate-spin" aria-hidden />
            <span className="sr-only sm:not-sr-only">{children}</span>
          </>
        ) : (
          <>
            {leadingIcon}
            {children}
            {trailingIcon}
          </>
        )}
      </Comp>
    );
  }
);
Button.displayName = "Button";

export { buttonVariants };
