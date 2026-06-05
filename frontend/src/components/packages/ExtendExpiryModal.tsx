"use client";
import { useState } from "react";
import { Loader2 } from "lucide-react";
import { toast } from "sonner";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { packagesApi } from "@/lib/api/packages";
import type { PackageSale } from "@/types/package";

interface Props {
  open: boolean;
  sale: PackageSale | null;
  onClose: () => void;
  onExtended: () => void;
}

export function ExtendExpiryModal({ open, sale, onClose, onExtended }: Props) {
  const [newExpiry, setNewExpiry] = useState("");
  const [reason, setReason] = useState("");
  const [loading, setLoading] = useState(false);

  if (!sale) return null;

  const currentExpiry = new Date(sale.expires_at).toISOString().split("T")[0];

  async function handleExtend() {
    if (!newExpiry) { toast.error("Select a new expiry date"); return; }
    if (newExpiry <= currentExpiry) { toast.error("New expiry must be after current expiry"); return; }
    if (!reason.trim()) { toast.error("Reason is required"); return; }

    setLoading(true);
    try {
      await packagesApi.extendSale(sale!.id, {
        new_expires_at: new Date(newExpiry).toISOString(),
        reason: reason.trim(),
      });
      toast.success("Expiry extended");
      onExtended();
      onClose();
    } catch {
      toast.error("Failed to extend expiry");
    } finally {
      setLoading(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-w-sm">
        <DialogHeader>
          <DialogTitle>Extend Package Expiry</DialogTitle>
        </DialogHeader>

        <div className="space-y-4 py-2">
          <div className="rounded-lg border border-border bg-surface-row p-3">
            <p className="font-medium text-sm">{sale.package_definition_name ?? "Package"}</p>
            <p className="text-xs text-muted-foreground">
              Current expiry: {new Date(sale.expires_at).toLocaleDateString("en-IN")}
            </p>
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="new-expiry">New expiry date *</Label>
            <Input
              id="new-expiry"
              type="date"
              value={newExpiry}
              min={currentExpiry}
              onChange={(e) => setNewExpiry(e.target.value)}
            />
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="extend-reason">Reason *</Label>
            <Textarea
              id="extend-reason"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="Why is the expiry being extended?"
              rows={2}
            />
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={onClose} disabled={loading}>Cancel</Button>
          <Button
            onClick={handleExtend}
            disabled={loading || !newExpiry || !reason.trim()}
          >
            {loading && <Loader2 size={14} className="mr-2 animate-spin" />}
            Extend Expiry
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
