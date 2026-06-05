"use client";
import { useState } from "react";
import { AlertTriangle, Loader2 } from "lucide-react";
import { toast } from "sonner";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { packagesApi } from "@/lib/api/packages";
import type { PackageSale } from "@/types/package";

interface Props {
  open: boolean;
  sale: PackageSale | null;
  onClose: () => void;
  onRefunded: () => void;
}

const PAYMENT_METHODS = [
  { value: "cash", label: "Cash" },
  { value: "upi", label: "UPI" },
  { value: "card", label: "Card" },
  { value: "pending_balance", label: "Pending balance" },
];

export function RefundPackageModal({ open, sale, onClose, onRefunded }: Props) {
  const [paymentMethod, setPaymentMethod] = useState("cash");
  const [reason, setReason] = useState("");
  const [loading, setLoading] = useState(false);

  if (!sale) return null;

  const isCounted = sale.entitlement_type_snapshot === "counted";
  const sessionsUsed =
    sale.total_sessions_snapshot != null && sale.sessions_remaining != null
      ? sale.total_sessions_snapshot - sale.sessions_remaining
      : null;

  async function handleRefund() {
    if (!reason.trim()) {
      toast.error("Reason is required");
      return;
    }
    setLoading(true);
    try {
      await packagesApi.refundSale(sale!.id, {
        payment_method: paymentMethod,
        reason: reason.trim(),
      });
      toast.success("Refund issued");
      onRefunded();
      onClose();
    } catch {
      toast.error("Failed to issue refund");
    } finally {
      setLoading(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Refund Package</DialogTitle>
        </DialogHeader>

        <div className="space-y-4 py-2">
          {/* Package summary */}
          <div className="rounded-lg border border-border bg-surface-row p-3 space-y-1">
            <p className="font-medium text-sm">
              {sale.package_definition_name ?? "Package"}
            </p>
            {isCounted && sessionsUsed != null && (
              <p className="text-xs text-muted-foreground">
                {sessionsUsed} of {sale.total_sessions_snapshot} sessions used
              </p>
            )}
            {!isCounted && (
              <p className="text-xs text-muted-foreground">Unlimited package</p>
            )}
            <p className="text-xs text-muted-foreground">
              Expires: {new Date(sale.expires_at).toLocaleDateString("en-IN")}
            </p>
          </div>

          {/* Expired goodwill banner */}
          {new Date(sale.expires_at) < new Date() && (
            <div className="flex gap-2 rounded-lg border border-warning-border bg-warning-bg-soft p-3">
              <AlertTriangle size={14} className="text-warning-fg mt-0.5 shrink-0" />
              <p className="text-xs text-warning-fg">
                This package has expired. Issuing a goodwill refund.
              </p>
            </div>
          )}

          {/* Refund-to */}
          <div className="space-y-1.5">
            <Label>Refund to</Label>
            <Select value={paymentMethod} onValueChange={setPaymentMethod}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {PAYMENT_METHODS.map((m) => (
                  <SelectItem key={m.value} value={m.value}>{m.label}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Reason */}
          <div className="space-y-1.5">
            <Label htmlFor="refund-reason">Reason *</Label>
            <Textarea
              id="refund-reason"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="Why is this package being refunded?"
              rows={3}
            />
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={onClose} disabled={loading}>Cancel</Button>
          <Button
            variant="destructive"
            onClick={handleRefund}
            disabled={loading || !reason.trim()}
          >
            {loading && <Loader2 size={14} className="mr-2 animate-spin" />}
            Issue Credit Note
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
