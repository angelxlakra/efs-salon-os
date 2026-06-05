"use client";
import { useEffect, useState } from "react";
import { usePackagesStore } from "@/stores/packages-store";
import { Gift } from "lucide-react";

interface Props {
  customerId: string;
}

/** Compact overflow pill (<768px). Shows count; tap to see details (basic popover). */
export function ActivePackagesBadge({ customerId }: Props) {
  const loadEligibility = usePackagesStore((s) => s.loadEligibility);
  const entry = usePackagesStore((s) => s.eligibilityCache.get(customerId));
  const packages = entry?.packages ?? [];
  const [open, setOpen] = useState(false);

  useEffect(() => {
    loadEligibility(customerId);
  }, [customerId, loadEligibility]);

  if (packages.length === 0) return null;

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full border border-border bg-card text-sm"
        style={{ borderLeftWidth: "3px", borderLeftColor: "#c9a96e" }}
        aria-label={`${packages.length} active packages`}
      >
        <Gift size={14} style={{ color: "#c9a96e" }} />
        <span className="font-medium">{packages.length}</span>
        <span className="text-muted-foreground text-xs">
          {packages.length === 1 ? "package" : "packages"}
        </span>
      </button>

      {open && (
        <div className="absolute left-0 top-full mt-1 z-50 w-60 rounded-xl border border-border bg-card shadow-lg p-2 flex flex-col gap-1.5">
          <button
            className="absolute right-2 top-2 text-xs text-muted-foreground hover:text-foreground"
            onClick={() => setOpen(false)}
          >
            &#x2715;
          </button>
          {packages.map((sale) => (
            <div key={sale.id} className="text-xs p-2 rounded-lg border border-border">
              <p className="font-medium">{sale.package_definition_name}</p>
              <p className="text-muted-foreground">
                {sale.sessions_remaining != null
                  ? `${sale.sessions_remaining} sessions left`
                  : "Unlimited"}
                {" · "}
                {new Date(sale.expires_at).toLocaleDateString("en-IN")}
              </p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
