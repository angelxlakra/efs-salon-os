import { cn } from "@/lib/utils";

interface ExpiryBadgeProps {
  /** ISO 8601 timestamp string */
  expiresAt: string;
  className?: string;
}

export function ExpiryBadge({ expiresAt, className }: ExpiryBadgeProps) {
  const now = Date.now();
  const exp = new Date(expiresAt).getTime();
  const daysLeft = Math.floor((exp - now) / (24 * 60 * 60 * 1000));

  let tone: string;
  let label: string;

  if (daysLeft < 0) {
    // Expired
    tone = "bg-muted/30 text-muted-foreground border-border";
    label = `Expired ${Math.abs(daysLeft)}d ago`;
  } else if (daysLeft <= 7) {
    // Urgent — within 7 days
    tone = "bg-danger-bg-soft text-danger-fg border-danger-border";
    label = `${daysLeft}d left`;
  } else if (daysLeft <= 30) {
    // Warning — within 30 days
    tone = "bg-warning-bg-soft text-warning-fg border-warning-border";
    label = `${daysLeft}d left`;
  } else {
    // Safe — more than 30 days
    tone = "bg-success-bg-soft text-success-fg border-success-border";
    label = `${daysLeft}d left`;
  }

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs border tabular-nums",
        tone,
        className
      )}
    >
      {label}
    </span>
  );
}
