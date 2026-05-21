import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const cardVariants = cva(
  "rounded-lg bg-surface-card border border-border-subtle transition-shadow",
  {
    variants: {
      density: {
        sm: "[&_[data-slot=body]]:p-3 [&_[data-slot=header]]:px-3 [&_[data-slot=header]]:pt-3 [&_[data-slot=footer]]:px-3 [&_[data-slot=footer]]:pb-3",
        md: "[&_[data-slot=body]]:p-5 [&_[data-slot=header]]:px-5 [&_[data-slot=header]]:pt-5 [&_[data-slot=footer]]:px-5 [&_[data-slot=footer]]:pb-5",
        lg: "[&_[data-slot=body]]:p-6 [&_[data-slot=header]]:px-6 [&_[data-slot=header]]:pt-6 [&_[data-slot=footer]]:px-6 [&_[data-slot=footer]]:pb-6",
      },
      hover: {
        true: "hover:shadow-[var(--shadow-xs)]",
      },
    },
    defaultVariants: { density: "md" },
  }
);

type CardProps = React.HTMLAttributes<HTMLDivElement> & VariantProps<typeof cardVariants>;

function CardRoot({ className, density, hover, ...props }: CardProps) {
  return <div data-density={density ?? "md"} className={cn(cardVariants({ density, hover }), className)} {...props} />;
}

function HeaderSlot({
  title,
  description,
  action,
  className,
  children,
  ...props
}: React.HTMLAttributes<HTMLDivElement> & { title?: string; description?: string; action?: React.ReactNode }) {
  const hasLeft = title || description || children;
  return (
    <div data-slot="header" className={cn("flex items-start justify-between gap-4", className)} {...props}>
      {hasLeft && (
        <div className="flex flex-col gap-1 min-w-0">
          {title && <h3 className="text-heading-md text-text-primary truncate">{title}</h3>}
          {description && <p className="text-body-sm text-text-muted">{description}</p>}
          {children}
        </div>
      )}
      {action && <div className="shrink-0">{action}</div>}
    </div>
  );
}

function BodySlot({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div data-slot="body" className={cn("text-body text-text-primary", className)} {...props} />;
}

function FooterSlot({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div data-slot="footer" className={cn("border-t border-border-subtle text-body-sm text-text-muted", className)} {...props} />;
}

export const Card = Object.assign(CardRoot, {
  Header: HeaderSlot,
  Body: BodySlot,
  Footer: FooterSlot,
});

// V1 `CardContent` alias preserved — used by callers that never migrated past the shadcn default export shape.
export { BodySlot as CardContent };

// ---------------------------------------------------------------------------
// V1 legacy shims — deprecated. Do not reach for these in new code; use the
// compound `<Card.Header />` / `<Card.Body />` / `<Card.Footer />` API.
//
// Kept verbatim from the pre-T12 implementation so ~30 V1 pages continue to
// typecheck and render during Phase 0. Slated for removal during Phase 1
// retrofit once all callers migrate to the compound API. See plan T12
// amendment (2026-04-23).
// ---------------------------------------------------------------------------

function CardHeader({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="card-header"
      className={cn(
        "@container/card-header grid auto-rows-min grid-rows-[auto_auto] items-start gap-2 px-6 pt-6 has-data-[slot=card-action]:grid-cols-[1fr_auto] [.border-b]:pb-6",
        className
      )}
      {...props}
    />
  );
}

function CardTitle({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="card-title"
      className={cn("leading-none font-semibold", className)}
      {...props}
    />
  );
}

function CardDescription({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="card-description"
      className={cn("text-muted-foreground text-sm", className)}
      {...props}
    />
  );
}

function CardAction({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="card-action"
      className={cn(
        "col-start-2 row-span-2 row-start-1 self-start justify-self-end",
        className
      )}
      {...props}
    />
  );
}

function CardFooter({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="card-footer"
      className={cn("flex items-center px-6 pb-6 [.border-t]:pt-6", className)}
      {...props}
    />
  );
}

export { CardHeader, CardTitle, CardDescription, CardAction, CardFooter };
