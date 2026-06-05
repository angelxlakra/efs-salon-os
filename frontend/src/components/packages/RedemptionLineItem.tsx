"use client";
import { cn } from "@/lib/utils";
import { Gift, Undo2 } from "lucide-react";
import { toast } from "sonner";
import { packagesApi } from "@/lib/api/packages";

interface BillItemLike {
  id: string;
  item_name: string;
  quantity: number;
  base_price: number;  // paise (snapshot price from package)
  line_total: number;  // paise
  item_type: string;
  package_sale_id?: string | null;
  // audit_id needed for undo — passed as prop since bill item doesn't hold it directly
}

interface Props {
  item: BillItemLike;
  auditId?: string;       // PackageRedemptionAudit.id for undo
  packageName?: string;   // display name from the PackageSale
  sessionInfo?: string;   // e.g. "3/10" — optional display
  onUndo?: () => void;    // callback after successful undo
  className?: string;
}

/** Bill line for item_type='package_redemption'. Gold left-rail = already paid. */
export function RedemptionLineItem({
  item,
  auditId,
  packageName,
  sessionInfo,
  onUndo,
  className,
}: Props) {
  async function handleUndo() {
    if (!auditId) {
      toast.error("Cannot undo — audit ID missing");
      return;
    }
    try {
      await packagesApi.undoRedemption(auditId);
      toast.success("Redemption undone");
      onUndo?.();
    } catch {
      toast.error("Failed to undo redemption");
    }
  }

  return (
    <div
      className={cn(
        "flex items-start gap-3 px-3 py-2.5 rounded-lg border border-border bg-card",
        className
      )}
      style={{ borderLeftWidth: "3px", borderLeftColor: "#c9a96e" }}
    >
      <Gift size={16} className="mt-0.5 shrink-0" style={{ color: "#c9a96e" }} />
      <div className="flex-1 min-w-0">
        <div className="flex items-start justify-between gap-2">
          <p className="text-sm font-medium leading-tight truncate">{item.item_name}</p>
          <div className="flex items-center gap-2 shrink-0">
            <p className="text-sm tabular-nums text-muted-foreground line-through">
              ₹{(item.base_price / 100).toFixed(2)}
            </p>
            {auditId && (
              <button
                type="button"
                onClick={handleUndo}
                className="inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full border border-border text-muted-foreground hover:text-foreground hover:border-border-strong transition-colors"
                title="Undo redemption"
              >
                <Undo2 size={11} />
                Undo
              </button>
            )}
          </div>
        </div>
        <p className="text-xs mt-0.5" style={{ color: "#c9a96e" }}>
          Paid via {packageName ?? "package"}
          {sessionInfo && ` · Session ${sessionInfo}`}
        </p>
      </div>
    </div>
  );
}
