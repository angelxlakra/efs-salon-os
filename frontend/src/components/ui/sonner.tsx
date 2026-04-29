"use client";

import { Toaster as SonnerToaster, type ToasterProps } from "sonner";

export function Toaster(props: ToasterProps) {
  return (
    <SonnerToaster
      position="bottom-right"
      closeButton
      richColors={false}
      toastOptions={{
        classNames: {
          toast:
            "bg-surface-card text-text-primary border border-border-default shadow-[var(--shadow-md)] rounded-lg",
          title: "text-body font-semibold",
          description: "text-body-sm text-text-secondary",
          success: "[&]:border-success-border [&_[data-icon]]:text-success-fg",
          warning: "[&]:border-warning-border [&_[data-icon]]:text-warning-fg",
          error:   "[&]:border-danger-border  [&_[data-icon]]:text-danger-fg",
          info:    "[&]:border-info-border    [&_[data-icon]]:text-info-fg",
          closeButton: "text-text-muted hover:text-text-primary",
          actionButton: "bg-accent text-accent-fg",
          cancelButton: "text-text-secondary",
        },
      }}
      {...props}
    />
  );
}
