import { cn } from "@/lib/utils";

interface SessionsLeftProps {
  /** null = unlimited (no session tracking) */
  remaining: number | null;
  /** null = unlimited */
  total: number | null;
  size?: "sm" | "md" | "lg";
  className?: string;
}

export function SessionsLeft({
  remaining,
  total,
  size = "md",
  className,
}: SessionsLeftProps) {
  const isUnlimited = remaining === null && total === null;
  const sizeClass =
    size === "sm" ? "text-sm" : size === "lg" ? "text-2xl" : "text-base";

  if (isUnlimited) {
    return (
      <span className={cn("tabular-nums font-semibold", sizeClass, className)}>
        ∞
      </span>
    );
  }

  return (
    <span className={cn("tabular-nums font-semibold", sizeClass, className)}>
      <span className="text-foreground">{remaining}</span>
      <span className="text-muted-foreground">/{total}</span>
    </span>
  );
}
