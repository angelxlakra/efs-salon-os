"use client";

import * as React from "react";
import * as DialogPrimitive from "@radix-ui/react-dialog";
import { X } from "lucide-react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const contentVariants = cva(
  "fixed z-50 left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 " +
    "bg-surface-card text-text-primary rounded-lg shadow-[var(--shadow-md)] " +
    "w-[calc(100vw-2rem)] max-h-[90dvh] flex flex-col overflow-hidden " +
    "data-[state=open]:animate-in data-[state=open]:fade-in-0 " +
    "data-[state=closed]:animate-out data-[state=closed]:fade-out-0",
  {
    variants: {
      size: {
        sm: "sm:max-w-[400px]",
        md: "sm:max-w-[560px]",
        lg: "sm:max-w-[720px]",
        xl: "sm:max-w-[960px]",
        full: "sm:max-w-[calc(100vw-3rem)]",
      },
      variant: {
        default: "",
        destructive: "border border-danger-border",
      },
    },
    defaultVariants: { size: "md", variant: "default" },
  }
);

// Backwards-compat type so command.tsx's `extends DialogProps {}` still compiles
export type DialogProps = React.ComponentPropsWithoutRef<typeof DialogPrimitive.Root>;

export const Dialog = DialogPrimitive.Root;
export const DialogTrigger = DialogPrimitive.Trigger;
export const DialogClose = DialogPrimitive.Close;
export const DialogPortal = DialogPrimitive.Portal;
export const DialogTitle = DialogPrimitive.Title;
export const DialogDescription = DialogPrimitive.Description;

export const DialogOverlay = React.forwardRef<
  React.ElementRef<typeof DialogPrimitive.Overlay>,
  React.ComponentPropsWithoutRef<typeof DialogPrimitive.Overlay>
>(({ className, ...props }, ref) => (
  <DialogPrimitive.Overlay
    ref={ref}
    className={cn(
      "fixed inset-0 z-50 bg-[var(--surface-overlay)] data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=open]:fade-in-0 data-[state=closed]:fade-out-0",
      className
    )}
    {...props}
  />
));
DialogOverlay.displayName = "DialogOverlay";

type DialogContentProps = React.ComponentPropsWithoutRef<typeof DialogPrimitive.Content> &
  VariantProps<typeof contentVariants> & {
    hideClose?: boolean;
  };

export const DialogContent = React.forwardRef<
  React.ElementRef<typeof DialogPrimitive.Content>,
  DialogContentProps
>(({ className, size, variant, hideClose, children, ...props }, ref) => (
  <DialogPortal>
    <DialogOverlay />
    <DialogPrimitive.Content
      ref={ref}
      data-size={size ?? "md"}
      data-variant={variant ?? "default"}
      className={cn(contentVariants({ size, variant }), className)}
      {...props}
    >
      {children}
      {!hideClose && (
        <DialogPrimitive.Close
          aria-label="Close"
          className="absolute right-4 top-4 text-text-muted hover:text-text-primary transition-colors"
        >
          <X className="size-4" />
        </DialogPrimitive.Close>
      )}
    </DialogPrimitive.Content>
  </DialogPortal>
));
DialogContent.displayName = "DialogContent";

export const DialogHeader = ({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) => (
  <div className={cn("flex flex-col gap-1 p-6 border-b border-border-subtle", className)} {...props} />
);
export const DialogBody = ({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) => (
  <div className={cn("flex-1 overflow-y-auto min-h-0 p-6", className)} {...props} />
);
export const DialogFooter = ({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) => (
  <div className={cn("flex flex-col-reverse sm:flex-row sm:justify-end gap-2 p-6 border-t border-border-subtle", className)} {...props} />
);
